from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, Plan, Subscription


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, customer_id: int) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def get_by_email(self, email: str) -> Customer | None:
        return self.db.scalar(select(Customer).where(Customer.email == email))

    def list(self) -> list[Customer]:
        return list(self.db.scalars(select(Customer).order_by(Customer.id)))

    def add(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer


class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, plan_id: int) -> Plan | None:
        return self.db.get(Plan, plan_id)

    def list(self) -> list[Plan]:
        return list(self.db.scalars(select(Plan).order_by(Plan.id)))

    def add(self, plan: Plan) -> Plan:
        self.db.add(plan)
        self.db.flush()
        return plan


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, subscription_id: int) -> Subscription | None:
        return self.db.get(Subscription, subscription_id)

    def list(self) -> list[Subscription]:
        return list(self.db.scalars(select(Subscription).order_by(Subscription.id)))

    def get_active_for_customer_plan(self, customer_id: int, plan_id: int) -> Subscription | None:
        statement = select(Subscription).where(
            Subscription.customer_id == customer_id,
            Subscription.plan_id == plan_id,
            Subscription.status == "active",
        )
        return self.db.scalar(statement)

    def add(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        return subscription

    def cancel(self, subscription: Subscription) -> Subscription:
        subscription.status = "canceled"
        self.db.flush()
        return subscription
