from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.exceptions import NotFoundError
from app.repositories.billing import InvoiceRepository, LedgerRepository, PaymentAttemptRepository
from app.schemas import (
    InvoiceGenerate,
    InvoiceRead,
    LedgerEntryRead,
    PaymentAttemptRead,
    PaymentCreate,
    PaymentResult,
)
from app.services.billing import InvoiceService, PaymentService

router = APIRouter(tags=["billing"])


@router.post("/invoices", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def generate_invoice(payload: InvoiceGenerate, db: Session = Depends(get_db)):
    return InvoiceService(db).generate_invoice(payload)


@router.get("/invoices", response_model=list[InvoiceRead])
def list_invoices(db: Session = Depends(get_db)):
    return InvoiceService(db).list_invoices()


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentResult, status_code=status.HTTP_201_CREATED)
def record_payment(invoice_id: int, payload: PaymentCreate, db: Session = Depends(get_db)):
    attempt, invoice = PaymentService(db).record_payment(invoice_id, payload)
    return {"payment_attempt": attempt, "invoice": invoice}


@router.get("/invoices/{invoice_id}/payments", response_model=list[PaymentAttemptRead])
def list_payments(invoice_id: int, db: Session = Depends(get_db)):
    if InvoiceRepository(db).get(invoice_id) is None:
        raise NotFoundError("Invoice not found")
    return PaymentAttemptRepository(db).list_for_invoice(invoice_id)


@router.get("/ledger", response_model=list[LedgerEntryRead])
def list_ledger(customer_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)):
    return LedgerRepository(db).list(customer_id=customer_id)
