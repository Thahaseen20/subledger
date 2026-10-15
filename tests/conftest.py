import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def create_customer(client: TestClient, email: str = "buyer@example.com") -> dict:
    response = client.post("/api/v1/customers", json={"name": "Buyer", "email": email})
    assert response.status_code == 201, response.text
    return response.json()


def create_plan(client: TestClient, price: str = "25.00") -> dict:
    response = client.post(
        "/api/v1/plans",
        json={"name": "Basic", "price": price, "currency": "USD", "billing_interval_months": 1},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_subscription(client: TestClient, *, plan_id: int, customer_id: int) -> dict:
    response = client.post(
        "/api/v1/subscriptions",
        json={"customer_id": customer_id, "plan_id": plan_id, "start_date": "2026-01-01"},
    )
    assert response.status_code == 201, response.text
    return response.json()
