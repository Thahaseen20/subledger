from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def normalize_currency(value: str) -> str:
    currency = value.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("currency must be a three-letter ISO-style code")
    return currency


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=320)


class CustomerRead(ORMModel):
    id: int
    name: str
    email: str
    created_at: datetime


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = "USD"
    billing_interval_months: int = Field(default=1, ge=1, le=12)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)


class PlanRead(ORMModel):
    id: int
    name: str
    description: str | None
    price: Decimal
    currency: str
    billing_interval_months: int
    is_active: bool
    created_at: datetime


class SubscriptionCreate(BaseModel):
    customer_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    start_date: date | None = None


class SubscriptionRead(ORMModel):
    id: int
    customer_id: int
    plan_id: int
    status: str
    start_date: date
    current_period_start: date
    current_period_end: date
    created_at: datetime


class InvoiceGenerate(BaseModel):
    subscription_id: int = Field(gt=0)
    period_start: date | None = None
    period_end: date | None = None
    due_date: date | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "InvoiceGenerate":
        if self.period_start and self.period_end and self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        if (self.period_start is None) != (self.period_end is None):
            raise ValueError("period_start and period_end must be provided together")
        return self


class InvoiceRead(ORMModel):
    id: int
    subscription_id: int
    customer_id: int
    amount_due: Decimal
    amount_paid: Decimal
    currency: str
    status: str
    period_start: date
    period_end: date
    due_date: date
    created_at: datetime


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = "USD"
    status: Literal["succeeded", "failed"]
    provider_reference: str = Field(min_length=1, max_length=160)
    failure_reason: str | None = Field(default=None, max_length=500)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)


class PaymentAttemptRead(ORMModel):
    id: int
    invoice_id: int
    amount: Decimal
    currency: str
    status: str
    provider_reference: str
    failure_reason: str | None
    created_at: datetime


class PaymentResult(BaseModel):
    payment_attempt: PaymentAttemptRead
    invoice: InvoiceRead


class LedgerEntryRead(ORMModel):
    id: int
    customer_id: int
    invoice_id: int | None
    entry_type: str
    amount: Decimal
    currency: str
    reference_id: str
    description: str | None
    created_at: datetime
