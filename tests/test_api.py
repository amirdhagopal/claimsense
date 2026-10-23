"""
Unit and integration tests for FastAPI service endpoints
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from src.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ClaimSense AI"


def test_get_mock_claim(client):
    response = client.get("/claims/CLM-2026-0101")
    assert response.status_code == 200
    claim = response.json()
    assert claim["claim_id"] == "CLM-2026-0101"
    assert claim["claimant"]["name"] == "Sarah Chen"


def test_adjudicate_unauthorized_refusal(client):
    # Requesting user is NOT entitled to CLM-2026-0101
    payload = {
        "user_id": "unauthorized-user",
        "claim_id": "CLM-2026-0101",
        "entitled_claims": ["CLM-OTHER-9999"],
    }
    response = client.post("/adjudicate", json=payload)
    # Refusal on entitlement: must be HTTP 403 Forbidden with zero claim data
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_idempotent_decision_write_back(client):
    key = str(uuid.uuid4())
    payload = {
        "idempotency_key": key,
        "claim_id": "CLM-2026-0101",
        "decision": "approve",
        "decision_detail": "standard_approval",
        "adjuster_id": "adjuster-jane",
        "reasoning": "Collision damage verified and covered under policy terms.",
        "cited_clauses": ["CLS-PER-001", "CLS-COV-001"],
        "payout_authorized": 2300.0,
    }

    # First write attempt -> 201 Created
    resp1 = client.post("/claims/CLM-2026-0101/decisions", json=payload)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["idempotent_replay"] is False
    assert data1["decision"] == "approve"

    # Second write attempt with identical key -> 200 OK (Idempotent Replay)
    resp2 = client.post("/claims/CLM-2026-0101/decisions", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["idempotent_replay"] is True
    assert data2["decision_id"] == data1["decision_id"]

    # Third write attempt with SAME key but CONFLICTING payload -> 409 Conflict
    conflicting_payload = dict(payload)
    conflicting_payload["decision"] = "deny"
    resp3 = client.post("/claims/CLM-2026-0101/decisions", json=conflicting_payload)
    assert resp3.status_code == 409
    assert "conflicting" in resp3.json()["detail"].lower()
