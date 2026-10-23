"""
ClaimSense AI — API Test Suite & Security Boundary Verification

Tests:
1. Public endpoints (/health) are accessible without auth.
2. Protected endpoints refuse requests without valid Bearer token (401 Unauthorized).
3. Malformed and forged tokens are rejected (401 Unauthorized).
4. Valid HMAC-SHA256 signed tokens and preseeded tokens authenticate successfully.
5. In-code access control verifies claim entitlement before invoking agents.
6. Unauthorized access to a claim returns 403 Forbidden with zero claim data.
7. Idempotent decision write-back behavior (201 Created -> 200 Replay -> 409 Conflict).
8. Audit trail captures all actions, resources, users, and outcomes.
"""

import time
import uuid
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.spine.security import TokenManager, SECRET_KEY


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. PUBLIC HEALTH ENDPOINT
# ---------------------------------------------------------------------------

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ClaimSense AI"
    assert data["trust_boundary"] == "enforced"


# ---------------------------------------------------------------------------
# 2. AUTHENTICATION ENFORCEMENT ON EVERY ROUTE (401 Refusal)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "method,endpoint,json_payload",
    [
        ("get", "/claims/CLM-2026-0101", None),
        ("post", "/adjudicate", {"claim_id": "CLM-2026-0101"}),
        ("get", "/documents?claim_id=CLM-2026-0101", None),
        ("get", "/policies/POL-10001", None),
        ("post", "/claims/CLM-2026-0101/decisions", {"idempotency_key": "c71a364e-03a1-4043-85f8-842240b08051", "claim_id": "CLM-2026-0101", "decision": "approve", "adjuster_id": "adj-1", "reasoning": "Standard review verified."}),
        ("get", "/audit-trail", None),
    ],
)
def test_all_routes_refuse_unauthenticated_requests(client, method, endpoint, json_payload):
    """
    Rubric Area D / Milestone 4 Requirement 2:
    Authorisation enforced on every route; requests without a valid token are refused (401).
    """
    if method == "get":
        response = client.get(endpoint)
    else:
        response = client.post(endpoint, json=json_payload)

    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    assert "Authorization header" in response.json()["detail"]


def test_malformed_authorization_header(client):
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    response = client.get("/claims/CLM-2026-0101", headers=headers)
    assert response.status_code == 401
    assert "Malformed Authorization header" in response.json()["detail"]


def test_invalid_bearer_token(client):
    headers = {"Authorization": "Bearer completely-forged-or-invalid-token"}
    response = client.get("/claims/CLM-2026-0101", headers=headers)
    assert response.status_code == 401
    assert "Invalid or expired authorization token" in response.json()["detail"]


def test_cryptographic_hmac_token_lifecycle(client):
    """
    Verifies dynamic HMAC-SHA256 signed token generation and expiration handling.
    """
    # 1. Valid signed token
    valid_token = TokenManager.create_signed_token(
        user_id="test-adjuster",
        role="licensed_adjuster",
        entitled_claims=["CLM-2026-0101"],
        ttl_seconds=3600,
    )
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.get("/claims/CLM-2026-0101", headers=headers)
    assert response.status_code == 200
    assert response.json()["claim_id"] == "CLM-2026-0101"

    # 2. Tampered token payload
    parts = valid_token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}xyz.{parts[2]}"
    tampered_headers = {"Authorization": f"Bearer {tampered_token}"}
    tampered_resp = client.get("/claims/CLM-2026-0101", headers=tampered_headers)
    assert tampered_resp.status_code == 401

    # 3. Expired token (ttl = -10 seconds)
    expired_token = TokenManager.create_signed_token(
        user_id="expired-adjuster",
        role="licensed_adjuster",
        entitled_claims=["CLM-2026-0101"],
        ttl_seconds=-10,
    )
    expired_headers = {"Authorization": f"Bearer {expired_token}"}
    expired_resp = client.get("/claims/CLM-2026-0101", headers=expired_headers)
    assert expired_resp.status_code == 401


# ---------------------------------------------------------------------------
# 3. AUTHORIZED ACCESS (200 OK)
# ---------------------------------------------------------------------------

def test_get_mock_claim_authorized(client):
    headers = {"Authorization": "Bearer token-jane-full-access"}
    response = client.get("/claims/CLM-2026-0101", headers=headers)
    assert response.status_code == 200
    claim = response.json()
    assert claim["claim_id"] == "CLM-2026-0101"
    assert claim["claimant"]["name"] == "Sarah Chen"


def test_get_documents_authorized(client):
    headers = {"Authorization": "Bearer token-jane-full-access"}
    response = client.get("/documents?claim_id=CLM-2026-0101", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["claim_id"] == "CLM-2026-0101"
    assert len(data["documents"]) >= 1


def test_get_policy_authorized(client):
    headers = {"Authorization": "Bearer token-jane-full-access"}
    response = client.get("/policies/POL-10001", headers=headers)
    assert response.status_code == 200
    assert response.json()["policy"]["policy_id"] == "POL-10001"


# ---------------------------------------------------------------------------
# 4. PRE-AGENT IN-CODE ACCESS CONTROL (403 Refusal & Zero Leakage)
# ---------------------------------------------------------------------------

def test_adjudicate_unauthorized_refusal_zero_leakage(client):
    """
    User 2 (Bob) possesses a valid token but lacks entitlement to CLM-2026-0101.
    Must return 403 Forbidden with ZERO claim information leaked.
    """
    headers = {"Authorization": "Bearer token-bob-limited-access"}
    response = client.post("/adjudicate", json={"claim_id": "CLM-2026-0101"}, headers=headers)
    assert response.status_code == 403
    body = response.json()
    assert "detail" in body
    assert "Access denied" in body["detail"]
    # Ensure zero claim data is present in response
    assert "claimant" not in body
    assert "decision" not in body
    assert "spine_facts" not in body
    assert "payout_authorized" not in body


def test_get_claim_unauthorized_refusal(client):
    headers = {"Authorization": "Bearer token-bob-limited-access"}
    response = client.get("/claims/CLM-2026-0101", headers=headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_get_documents_unauthorized_refusal(client):
    headers = {"Authorization": "Bearer token-bob-limited-access"}
    response = client.get("/documents?claim_id=CLM-2026-0101", headers=headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_decision_write_unauthorized_refusal(client):
    headers = {"Authorization": "Bearer token-bob-limited-access"}
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "claim_id": "CLM-2026-0101",
        "decision": "approve",
        "adjuster_id": "adjuster-bob",
        "reasoning": "Attempting unauthorized decision update on claim CLM-2026-0101.",
    }
    response = client.post("/claims/CLM-2026-0101/decisions", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 5. IDEMPOTENT DECISION WRITE-BACK
# ---------------------------------------------------------------------------

def test_idempotent_decision_write_back(client):
    headers = {"Authorization": "Bearer token-jane-full-access"}
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
    resp1 = client.post("/claims/CLM-2026-0101/decisions", json=payload, headers=headers)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["idempotent_replay"] is False
    assert data1["decision"] == "approve"

    # Second write attempt with identical key -> 200 OK (Idempotent Replay)
    resp2 = client.post("/claims/CLM-2026-0101/decisions", json=payload, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["idempotent_replay"] is True
    assert data2["decision_id"] == data1["decision_id"]

    # Third write attempt with SAME key but CONFLICTING payload -> 409 Conflict
    conflicting_payload = dict(payload)
    conflicting_payload["decision"] = "deny"
    resp3 = client.post("/claims/CLM-2026-0101/decisions", json=conflicting_payload, headers=headers)
    assert resp3.status_code == 409
    assert "conflicting" in resp3.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. AUDIT TRAIL ENDPOINT
# ---------------------------------------------------------------------------

def test_audit_trail_endpoint(client):
    headers = {"Authorization": "Bearer token-admin-access"}
    response = client.get("/audit-trail?limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_records" in data
    assert "events" in data
    assert isinstance(data["events"], list)
    if data["events"]:
        event = data["events"][0]
        assert "timestamp" in event
        assert "user_id" in event
        assert "action" in event
        assert "resource" in event
        assert "outcome" in event
