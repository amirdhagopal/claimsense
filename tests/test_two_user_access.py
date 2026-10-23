"""
ClaimSense AI — Milestone 4 Two-User Access Control Test Suite

Demonstrates that access control is:
1. Implemented in code and evaluated before any agent is invoked.
2. Enforced on the exact same claim (CLM-2026-0101) for:
   - User 1 (Authorized adjuster-jane): Granted full adjudication dossier.
   - User 2 (Unauthorized adjuster-bob): Refused with HTTP 403 Forbidden and zero claim data.
3. Completely logged in the immutable audit trail for both granted and denied attempts.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.spine.audit_logger import AUDIT_LOG_FILE


@pytest.fixture
def client():
    return TestClient(app)


def test_two_user_access_on_same_claim(client):
    target_claim_id = "CLM-2026-0101"

    # =========================================================================
    # USER 1: Authorized Adjuster (Jane) -> GRANTED (200 OK)
    # =========================================================================
    jane_headers = {"Authorization": "Bearer token-jane-full-access"}

    # 1. User 1: CMS Claim Read
    jane_claim_resp = client.get(f"/claims/{target_claim_id}", headers=jane_headers)
    assert jane_claim_resp.status_code == 200, f"Jane expected 200, got {jane_claim_resp.status_code}"
    jane_claim_data = jane_claim_resp.json()
    assert jane_claim_data["claim_id"] == target_claim_id
    assert jane_claim_data["claimant"]["name"] == "Sarah Chen"

    # 2. User 1: DocStore Document Read
    jane_doc_resp = client.get(f"/documents?claim_id={target_claim_id}", headers=jane_headers)
    assert jane_doc_resp.status_code == 200
    assert len(jane_doc_resp.json()["documents"]) >= 1

    # 3. User 1: Full Adjudication Pipeline
    jane_adj_resp = client.post("/adjudicate", json={"claim_id": target_claim_id}, headers=jane_headers)
    assert jane_adj_resp.status_code == 200
    jane_adj_data = jane_adj_resp.json()
    assert jane_adj_data["claim_id"] == target_claim_id
    assert jane_adj_data["decision"] in ["approve", "flag", "route", "deny"]
    assert "reasoning" in jane_adj_data
    assert "spine_facts" in jane_adj_data
    assert jane_adj_data["requires_human_confirmation"] is True

    # =========================================================================
    # USER 2: Unauthorized Adjuster (Bob) -> DENIED (403 Forbidden)
    # =========================================================================
    bob_headers = {"Authorization": "Bearer token-bob-limited-access"}

    # 1. User 2: CMS Claim Read Refusal
    bob_claim_resp = client.get(f"/claims/{target_claim_id}", headers=bob_headers)
    assert bob_claim_resp.status_code == 403, f"Bob expected 403, got {bob_claim_resp.status_code}"
    bob_claim_data = bob_claim_resp.json()
    assert "detail" in bob_claim_data
    assert "Access denied" in bob_claim_data["detail"]
    # Zero claim leakage assertion
    assert "claimant" not in bob_claim_data
    assert "vehicle" not in bob_claim_data
    assert "loss_date" not in bob_claim_data

    # 2. User 2: DocStore Document Read Refusal
    bob_doc_resp = client.get(f"/documents?claim_id={target_claim_id}", headers=bob_headers)
    assert bob_doc_resp.status_code == 403
    bob_doc_data = bob_doc_resp.json()
    assert "documents" not in bob_doc_data
    assert "Access denied" in bob_doc_data["detail"]

    # 3. User 2: Adjudication Pipeline Refusal (Pre-Agent Interception)
    bob_adj_resp = client.post("/adjudicate", json={"claim_id": target_claim_id}, headers=bob_headers)
    assert bob_adj_resp.status_code == 403
    bob_adj_data = bob_adj_resp.json()
    assert "Access denied" in bob_adj_data["detail"]
    # Verify zero AI/Agent inference data is leaked
    assert "decision" not in bob_adj_data
    assert "reasoning" not in bob_adj_data
    assert "spine_facts" not in bob_adj_data
    assert "payout_authorized" not in bob_adj_data

    # =========================================================================
    # 4. IMMUTABLE AUDIT TRAIL VERIFICATION
    # =========================================================================
    assert AUDIT_LOG_FILE.exists()
    records = []
    with open(AUDIT_LOG_FILE, "r") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line.strip()))
                except Exception:
                    pass

    # Find audit entries for target_claim_id
    claim_events = [r for r in records if r.get("resource") == target_claim_id]
    assert len(claim_events) >= 2, "Expected at least 2 audit events on the target claim"

    jane_events = [r for r in claim_events if r.get("user_id") == "adjuster-jane"]
    bob_events = [r for r in claim_events if r.get("user_id") == "adjuster-bob"]

    assert len(jane_events) >= 1, "Expected granted audit event for adjuster-jane"
    assert any(e["outcome"] == "granted" for e in jane_events)

    assert len(bob_events) >= 1, "Expected denied audit event for adjuster-bob"
    assert any(e["outcome"] == "denied" for e in bob_events)
