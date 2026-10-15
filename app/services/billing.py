from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Invoice, LedgerEntry, PaymentAttempt
from app.repositories.billing import InvoiceRepository, LedgerRepository, PaymentAttemptRepository
from app.repositories.catalog import PlanRepository, SubscriptionRepository
from app.schemas import InvoiceGenerate, PaymentCreate


class LedgerService:
    def __init__(self, db: Session, ledger_repo: LedgerRepository | None = None):
        self.db = db
        self.ledger_repo = ledger_repo or LedgerRepository(db)

    def record(
        self,
        *,
        customer_id: int,
        invoice_id: int | None,
        entry_type: str,
        amount: Decimal,
        currency: str,
        reference_id: str,
        description: str,
    ) -> LedgerEntry:
        return self.ledger_repo.add(
            LedgerEntry(
                customer_id=customer_id,
                invoice_id=invoice_id,
                entry_type=entry_type,
                amount=amount,
                currency=currency,
                reference_id=reference_id,
                description=description,
            )
        )


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.subscription_repo = SubscriptionRepository(db)
        self.plan_repo = PlanRepository(db)
        self.ledger_service = LedgerService(db)

    def generate_invoice(self, data: InvoiceGenerate) -> Invoice:
        subscription = self.subscription_repo.get(data.subscription_id)
        if subscription is None:
            raise NotFoundError("Subscription not found")
        if subscription.status != "active":
            raise BusinessRuleError("Invoices can only be generated for active subscriptions")
        plan = self.plan_repo.get(subscription.plan_id)
        if plan is None:
            raise NotFoundError("Subscription plan not found")

        period_start = data.period_start or subscription.current_period_start
        period_end = data.period_end or subscription.current_period_end
        if period_end <= period_start:
            raise BusinessRuleError("Invoice period end must be after period start")
        if self.invoice_repo.get_for_period(subscription.id, period_start, period_end):
            raise ConflictError("An invoice already exists for this subscription period")

        amount_due = Decimal(plan.price)
        invoice = self.invoice_repo.add(
            Invoice(
                subscription_id=subscription.id,
                customer_id=subscription.customer_id,
                amount_due=amount_due,
                amount_paid=Decimal("0.00"),
                currency=plan.currency,
                status="issued",
                period_start=period_start,
                period_end=period_end,
                due_date=data.due_date or period_start + timedelta(days=30),
            )
        )
        self.ledger_service.record(
            customer_id=subscription.customer_id,
            invoice_id=invoice.id,
            entry_type="invoice_created",
            amount=amount_due,
            currency=plan.currency,
            reference_id=f"invoice:{invoice.id}",
            description=f"Invoice created for subscription {subscription.id}",
        )
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def list_invoices(self) -> list[Invoice]:
        return self.invoice_repo.list()


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.payment_repo = PaymentAttemptRepository(db)
        self.ledger_service = LedgerService(db)

    def record_payment(self, invoice_id: int, data: PaymentCreate) -> tuple[PaymentAttempt, Invoice]:
        invoice = self.invoice_repo.get(invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found")
        if data.currency != invoice.currency:
            raise BusinessRuleError("Payment currency must match the invoice currency")
        if invoice.status == "paid":
            raise BusinessRuleError("Cannot record a payment for a fully paid invoice")
        if data.status == "succeeded" and data.amount > Decimal(invoice.amount_due) - Decimal(invoice.amount_paid):
            raise BusinessRuleError("Successful payment cannot exceed the remaining invoice balance")

        attempt = self.payment_repo.add(
            PaymentAttempt(
                invoice_id=invoice.id,
                amount=data.amount,
                currency=data.currency,
                status=data.status,
                provider_reference=data.provider_reference,
                failure_reason=data.failure_reason if data.status == "failed" else None,
            )
        )
        if data.status == "succeeded":
            invoice.amount_paid = Decimal(invoice.amount_paid) + data.amount
            invoice.status = "paid" if invoice.amount_paid == invoice.amount_due else "partially_paid"
            entry_type = "payment_success"
        else:
            entry_type = "payment_failure"

        self.ledger_service.record(
            customer_id=invoice.customer_id,
            invoice_id=invoice.id,
            entry_type=entry_type,
            amount=data.amount,
            currency=data.currency,
            reference_id=data.provider_reference,
            description=data.failure_reason or f"Payment {data.status} for invoice {invoice.id}",
        )
        self.db.commit()
        self.db.refresh(attempt)
        self.db.refresh(invoice)
        return attempt, invoice
