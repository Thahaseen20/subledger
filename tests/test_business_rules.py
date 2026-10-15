from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import create_customer, create_plan, create_subscription


def test_plan_price_must_be_greater_than_zero(client: TestClient):
    response = client.post("/api/v1/plans", json={"name": "Free", "price": "0.00"})
    assert response.status_code == 422


def test_customer_email_must_be_unique(client: TestClient):
    create_customer(client)
    response = client.post("/api/v1/customers", json={"name": "Other", "email": "BUYER@example.com"})
    assert response.status_code == 409


def test_cannot_subscribe_to_inactive_plan(client: TestClient):
    customer = create_customer(client)
    plan = create_plan(client)
    assert client.post(f"/api/v1/plans/{plan['id']}/deactivate").status_code == 200
    response = client.post(
        "/api/v1/subscriptions", json={"customer_id": customer["id"], "plan_id": plan["id"]}
    )
    assert response.status_code == 422


def test_customer_cannot_have_two_active_subscriptions_to_same_plan(client: TestClient):
    customer = create_customer(client)
    plan = create_plan(client)
    create_subscription(client, plan_id=plan["id"], customer_id=customer["id"])
    response = client.post(
        "/api/v1/subscriptions", json={"customer_id": customer["id"], "plan_id": plan["id"]}
    )
    assert response.status_code == 409


def test_invoice_uses_plan_price_at_generation_time_and_writes_ledger(client: TestClient):
    customer = create_customer(client)
    plan = create_plan(client, "48.50")
    subscription = create_subscription(client, plan_id=plan["id"], customer_id=customer["id"])
    response = client.post("/api/v1/invoices", json={"subscription_id": subscription["id"]})
    assert response.status_code == 201
    invoice = response.json()
    assert Decimal(invoice["amount_due"]) == Decimal("48.50")
    entries = client.get("/api/v1/ledger", params={"customer_id": customer["id"]}).json()
    assert len(entries) == 1
    assert entries[0]["entry_type"] == "invoice_created"
    assert entries[0]["reference_id"] == f"invoice:{invoice['id']}"


def test_successful_payment_updates_invoice_and_partial_payments_are_supported(client: TestClient):
    customer = create_customer(client)
    plan = create_plan(client, "60.00")
    subscription = create_subscription(client, plan_id=plan["id"], customer_id=customer["id"])
    invoice = client.post("/api/v1/invoices", json={"subscription_id": subscription["id"]}).json()

    first = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        json={"amount": "20.00", "currency": "USD", "status": "succeeded", "provider_reference": "pay-1"},
    )
    assert first.status_code == 201
    assert first.json()["invoice"]["status"] == "partially_paid"
    assert Decimal(first.json()["invoice"]["amount_paid"]) == Decimal("20.00")

    final = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        json={"amount": "40.00", "currency": "USD", "status": "succeeded", "provider_reference": "pay-2"},
    )
    assert final.status_code == 201
    assert final.json()["invoice"]["status"] == "paid"
    assert Decimal(final.json()["invoice"]["amount_paid"]) == Decimal("60.00")


def test_failed_payment_does_not_increase_amount_paid(client: TestClient):
    customer = create_customer(client)
    plan = create_plan(client, "30.00")
    subscription = create_subscription(client, plan_id=plan["id"], customer_id=customer["id"])
    invoice = client.post("/api/v1/invoices", json={"subscription_id": subscription["id"]}).json()
    response = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        json={
            "amount": "30.00", "currency": "USD", "status": "failed",
            "provider_reference": "pay-fail", "failure_reason": "Declined",
        },
    )
    assert response.status_code == 201
    assert Decimal(response.json()["invoice"]["amount_paid"]) == Decimal("0.00")
    assert response.json()["invoice"]["status"] == "issued"
    entries = client.get("/api/v1/ledger", params={"customer_id": customer["id"]}).json()
    assert entries[-1]["entry_type"] == "payment_failure"


def test_successful_payment_cannot_exceed_remaining_balance(client: TestClient):
    customer = create_customer(client)
    plan = create_plan(client, "20.00")
    subscription = create_subscription(client, plan_id=plan["id"], customer_id=customer["id"])
    invoice = client.post("/api/v1/invoices", json={"subscription_id": subscription["id"]}).json()
    response = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        json={"amount": "20.01", "currency": "USD", "status": "succeeded", "provider_reference": "too-much"},
    )
    assert response.status_code == 422
