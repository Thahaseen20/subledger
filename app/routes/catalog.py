from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import CustomerCreate, CustomerRead, PlanCreate, PlanRead, SubscriptionCreate, SubscriptionRead
from app.services.catalog import CatalogService

router = APIRouter(tags=["catalog"])


@router.post("/customers", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    return CatalogService(db).create_customer(payload)


@router.get("/customers", response_model=list[CustomerRead])
def list_customers(db: Session = Depends(get_db)):
    return CatalogService(db).list_customers()


@router.post("/plans", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    return CatalogService(db).create_plan(payload)


@router.get("/plans", response_model=list[PlanRead])
def list_plans(db: Session = Depends(get_db)):
    return CatalogService(db).list_plans()


@router.post("/plans/{plan_id}/deactivate", response_model=PlanRead)
def deactivate_plan(plan_id: int, db: Session = Depends(get_db)):
    return CatalogService(db).deactivate_plan(plan_id)


@router.post("/subscriptions", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db)):
    return CatalogService(db).create_subscription(payload)


@router.get("/subscriptions", response_model=list[SubscriptionRead])
def list_subscriptions(db: Session = Depends(get_db)):
    return CatalogService(db).list_subscriptions()


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionRead)
def cancel_subscription(subscription_id: int, db: Session = Depends(get_db)):
    return CatalogService(db).cancel_subscription(subscription_id)
