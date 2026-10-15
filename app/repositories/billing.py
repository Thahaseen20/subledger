from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Invoice, LedgerEntry, PaymentAttempt


class InvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, invoice_id: int) -> Invoice | None:
        return self.db.get(Invoice, invoice_id)

    def get_for_period(self, subscription_id: int, period_start: date, period_end: date) -> Invoice | None:
        statement = select(Invoice).where(
            Invoice.subscription_id == subscription_id,
            Invoice.period_start == period_start,
            Invoice.period_end == period_end,
        )
        return self.db.scalar(statement)

    def list(self) -> list[Invoice]:
        return list(self.db.scalars(select(Invoice).order_by(Invoice.id)))

    def add(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        self.db.flush()
        return invoice


class PaymentAttemptRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, attempt: PaymentAttempt) -> PaymentAttempt:
        self.db.add(attempt)
        self.db.flush()
        return attempt

    def list_for_invoice(self, invoice_id: int) -> list[PaymentAttempt]:
        statement = select(PaymentAttempt).where(PaymentAttempt.invoice_id == invoice_id).order_by(PaymentAttempt.id)
        return list(self.db.scalars(statement))


class LedgerRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, entry: LedgerEntry) -> LedgerEntry:
        self.db.add(entry)
        self.db.flush()
        return entry

    def list(self, customer_id: int | None = None) -> list[LedgerEntry]:
        statement = select(LedgerEntry)
        if customer_id is not None:
            statement = statement.where(LedgerEntry.customer_id == customer_id)
        return list(self.db.scalars(statement.order_by(LedgerEntry.id)))
