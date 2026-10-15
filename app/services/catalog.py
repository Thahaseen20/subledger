from datetime import date

from sqlalchemy.orm import Session

from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Customer, Plan, Subscription
from app.repositories.catalog import CustomerRepository, PlanRepository, SubscriptionRepository
from app.schemas import CustomerCreate, PlanCreate, SubscriptionCreate
from app.services.dates import add_months


class CatalogService:
    def __init__(self, db: Session):
        self.db = db
        self.customers = CustomerRepository(db)
        self.plans = PlanRepository(db)
        self.subscriptions = SubscriptionRepository(db)

    def create_customer(self, data: CustomerCreate) -> Customer:
        email = data.email.strip().lower()
        if self.customers.get_by_email(email):
            raise ConflictError("A customer with this email already exists")
        customer = self.customers.add(Customer(name=data.name.strip(), email=email))
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def list_customers(self) -> list[Customer]:
        return self.customers.list()

    def create_plan(self, data: PlanCreate) -> Plan:
        plan = self.plans.add(
            Plan(
                name=data.name.strip(),
                description=data.description,
                price=data.price,
                currency=data.currency,
                billing_interval_months=data.billing_interval_months,
                is_active=True,
            )
        )
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def list_plans(self) -> list[Plan]:
        return self.plans.list()

    def deactivate_plan(self, plan_id: int) -> Plan:
        plan = self.plans.get(plan_id)
        if plan is None:
            raise NotFoundError("Plan not found")
        plan.is_active = False
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def create_subscription(self, data: SubscriptionCreate) -> Subscription:
        customer = self.customers.get(data.customer_id)
        if customer is None:
            raise NotFoundError("Customer not found")
        plan = self.plans.get(data.plan_id)
        if plan is None:
            raise NotFoundError("Plan not found")
        if not plan.is_active:
            raise BusinessRuleError("Cannot subscribe to an inactive plan")
        if self.subscriptions.get_active_for_customer_plan(customer.id, plan.id):
            raise ConflictError("Customer already has an active subscription to this plan")

        start = data.start_date or date.today()
        subscription = self.subscriptions.add(
            Subscription(
                customer_id=customer.id,
                plan_id=plan.id,
                status="active",
                start_date=start,
                current_period_start=start,
                current_period_end=add_months(start, plan.billing_interval_months),
            )
        )
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def list_subscriptions(self) -> list[Subscription]:
        return self.subscriptions.list()

    def cancel_subscription(self, subscription_id: int) -> Subscription:
        subscription = self.subscriptions.get(subscription_id)
        if subscription is None:
            raise NotFoundError("Subscription not found")
        if subscription.status == "active":
            self.subscriptions.cancel(subscription)
            self.db.commit()
            self.db.refresh(subscription)
        return subscription
