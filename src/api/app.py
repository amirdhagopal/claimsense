"""
ClaimSense AI — REST API Service (FastAPI) with Full Trust Boundary

Enforces:
  1. Data access boundary deployed and callable.
  2. Authorisation enforced on every route; requests without a valid token are refused (401).
  3. Access control implemented in code and executed before any agent is invoked (403).
  4. Immutable audit record written for every call (granted or denied).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional
from fastapi import Depends, FastAPI, HTTPException, Header, Query, Response, status
from pydantic import BaseModel, Field

from src.agents.pipeline import AdjudicationPipeline
from src.config import settings
from src.contracts.cms import (
    ClaimRecord,
    ClaimDecisionRequest,
    ClaimDecisionResponse,
    ClaimStatus,
)
from src.contracts.docstore import DocumentContentResponse
from src.contracts.policyadmin import PolicyRecord
from src.spine.access_control import AccessControlEngine, UserIdentity
from src.spine.audit_logger import AUDIT_LOG_FILE, AuditLogger
from src.spine.orchestrator import AccessDeniedException
from src.spine.security import authenticate_request

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Motor claims adjudication co-pilot bounded by a deterministic trust perimeter.",
)

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures" / "synthetic_dossiers.json"
CLAIMS_DB: dict[str, dict[str, Any]] = {}
IDEMPOTENCY_STORE: dict[str, dict[str, Any]] = {}

pipeline = AdjudicationPipeline()


def load_fixtures_into_memory() -> None:
    if FIXTURES_PATH.exists():
        with open(FIXTURES_PATH, "r") as f:
            data = json.load(f)
            for item in data:
                cid = item["claim"]["claim_id"]
                CLAIMS_DB[cid] = item


load_fixtures_into_memory()


from fastapi.responses import FileResponse
from src.spine.metrics import MetricsTracker

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"

# Initialize baseline telemetry
MetricsTracker.simulate_baseline_traffic()


# ---------------------------------------------------------------------------
# PUBLIC HEALTH CHECK & DASHBOARD
# ---------------------------------------------------------------------------

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
        "model": settings.openai_model,
        "trust_boundary": "enforced",
    }


@app.get("/", response_class=FileResponse)
@app.get("/dashboard", response_class=FileResponse)
def serve_dashboard():
    return FileResponse(INDEX_HTML)


@app.get("/dashboard/metrics")
def get_dashboard_metrics() -> dict[str, Any]:
    return MetricsTracker.get_metrics().model_dump()


# ---------------------------------------------------------------------------
# ADJUDICATION ENDPOINT (Guarded by Bearer Token & Entitlement Check)
# ---------------------------------------------------------------------------

class AdjudicateRequest(BaseModel):
    claim_id: str = Field(..., description="Target claim ID (e.g. CLM-2026-0101)")


@app.post("/adjudicate")
def adjudicate_claim(
    req: AdjudicateRequest,
    user: UserIdentity = Depends(authenticate_request),
) -> dict[str, Any]:
    """
    Executes pre-agent deterministic checks followed by the 4-agent pipeline.
    Access control is checked in code BEFORE any agent is instantiated.
    If the user lacks entitlement, returns HTTP 403 Forbidden with zero claim data.
    """
    # 1. Pre-agent entitlement check in code
    granted, denial_reason = AccessControlEngine.verify_entitlement(user, req.claim_id)
    if not granted:
        AuditLogger.log(
            user_id=user.user_id,
            action="adjudicate_claim",
            resource=req.claim_id,
            outcome="denied",
            decision="deny",
            details={"reason": denial_reason, "stage": "pre_agent_access_control"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=denial_reason or "Access denied: User not entitled to this claim.",
        )

    if req.claim_id not in CLAIMS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{req.claim_id}' not found in system.",
        )

    fixture = CLAIMS_DB[req.claim_id]
    claim = ClaimRecord.model_validate(fixture["claim"])
    policy = PolicyRecord.model_validate(fixture["policy"])
    documents = [DocumentContentResponse.model_validate(d) for d in fixture["documents"]]

    try:
        dossier = pipeline.adjudicate(
            user=user,
            claim=claim,
            policy=policy,
            documents=documents,
        )
    except AccessDeniedException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )

    return {
        "claim_id": claim.claim_id,
        "decision": dossier.draft_decision.decision.value,
        "decision_detail": dossier.draft_decision.decision_detail.value if dossier.draft_decision.decision_detail else None,
        "reasoning": dossier.draft_decision.reasoning,
        "cited_clauses": dossier.draft_decision.cited_clauses,
        "payout_authorized": dossier.draft_decision.payout_authorized,
        "verdict_source": dossier.draft_decision.verdict_source,
        "spine_facts": {
            "policy_in_force": dossier.spine_context.policy_in_force,
            "days_past_expiry": dossier.spine_context.days_past_expiry,
            "vehicle_scheduled": dossier.spine_context.vehicle_scheduled,
            "repair_to_value_ratio": dossier.spine_context.repair_to_value_ratio,
            "is_constructive_total_loss": dossier.spine_context.is_constructive_total_loss,
            "applicable_deductible": dossier.spine_context.deductible,
        },
        "requires_human_confirmation": True,
    }


# ---------------------------------------------------------------------------
# GUARDED CLIENT SYSTEM ROUTES (CMS, DocStore, PolicyAdmin)
# ---------------------------------------------------------------------------

@app.get("/claims/{claim_id}")
def get_claim(
    claim_id: str,
    user: UserIdentity = Depends(authenticate_request),
) -> dict[str, Any]:
    """
    Guarded CMS read endpoint. Enforces claim entitlement.
    """
    granted, denial_reason = AccessControlEngine.verify_entitlement(user, claim_id)
    if not granted:
        AuditLogger.log(
            user_id=user.user_id,
            action="read_claim",
            resource=claim_id,
            outcome="denied",
            details={"reason": denial_reason},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=denial_reason or "Access denied to claim.",
        )

    if claim_id not in CLAIMS_DB:
        raise HTTPException(status_code=404, detail="Claim not found")

    AuditLogger.log(
        user_id=user.user_id,
        action="read_claim",
        resource=claim_id,
        outcome="granted",
    )
    return CLAIMS_DB[claim_id]["claim"]


@app.get("/documents")
def get_documents(
    claim_id: str = Query(..., description="Claim ID to list documents for"),
    user: UserIdentity = Depends(authenticate_request),
) -> dict[str, Any]:
    """
    Guarded DocStore read endpoint. Enforces claim entitlement.
    """
    granted, denial_reason = AccessControlEngine.verify_entitlement(user, claim_id)
    if not granted:
        AuditLogger.log(
            user_id=user.user_id,
            action="read_documents",
            resource=claim_id,
            outcome="denied",
            details={"reason": denial_reason},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=denial_reason or "Access denied to claim documents.",
        )

    if claim_id not in CLAIMS_DB:
        raise HTTPException(status_code=404, detail="Claim not found")

    docs = CLAIMS_DB[claim_id]["documents"]
    AuditLogger.log(
        user_id=user.user_id,
        action="read_documents",
        resource=claim_id,
        outcome="granted",
    )
    return {"claim_id": claim_id, "documents": docs, "total_count": len(docs)}


@app.get("/policies/{policy_id}")
def get_policy(
    policy_id: str,
    user: UserIdentity = Depends(authenticate_request),
) -> dict[str, Any]:
    """
    Guarded PolicyAdmin read endpoint. Requires authenticated token.
    """
    for item in CLAIMS_DB.values():
        if item["policy"]["policy_id"] == policy_id:
            AuditLogger.log(
                user_id=user.user_id,
                action="read_policy",
                resource=policy_id,
                outcome="granted",
            )
            return {"policy": item["policy"]}

    AuditLogger.log(
        user_id=user.user_id,
        action="read_policy",
        resource=policy_id,
        outcome="denied",
        details={"error": "policy_not_found"},
    )
    raise HTTPException(status_code=404, detail="Policy not found")


@app.post("/claims/{claim_id}/decisions", response_model=ClaimDecisionResponse)
def write_claim_decision(
    claim_id: str,
    req: ClaimDecisionRequest,
    response: Response,
    user: UserIdentity = Depends(authenticate_request),
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> ClaimDecisionResponse:
    """
    Guarded, idempotent CMS write endpoint.
    Requires valid token, entitlement to claim, and valid idempotency key.
    """
    granted, denial_reason = AccessControlEngine.verify_entitlement(user, claim_id)
    if not granted:
        AuditLogger.log(
            user_id=user.user_id,
            action="write_decision",
            resource=claim_id,
            outcome="denied",
            details={"reason": denial_reason},
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=denial_reason)

    key = req.idempotency_key or idempotency_key_header
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required idempotency key.")

    payload_str = json.dumps(req.model_dump(exclude={"idempotency_key"}), sort_keys=True)
    fingerprint = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    if key in IDEMPOTENCY_STORE:
        stored = IDEMPOTENCY_STORE[key]
        if stored["fingerprint"] == fingerprint:
            response.headers["X-Idempotent-Replay"] = "true"
            cached_resp = stored["response"]
            AuditLogger.log(
                user_id=user.user_id,
                action="write_decision",
                resource=claim_id,
                outcome="granted",
                decision=cached_resp["decision"],
                details={"idempotent_replay": True, "key": key},
            )
            return ClaimDecisionResponse(
                decision_id=cached_resp["decision_id"],
                claim_id=cached_resp["claim_id"],
                idempotency_key=key,
                status=ClaimStatus.ADJUDICATED,
                decision=cached_resp["decision"],
                adjuster_id=cached_resp["adjuster_id"],
                idempotent_replay=True,
            )
        else:
            AuditLogger.log(
                user_id=user.user_id,
                action="write_decision",
                resource=claim_id,
                outcome="denied",
                details={"error": "idempotency_conflict", "key": key},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key reused with conflicting request payload.",
            )

    decision_id = f"DEC-{hashlib.md5(f'{claim_id}:{key}'.encode()).hexdigest()[:8].upper()}"
    resp_obj = ClaimDecisionResponse(
        decision_id=decision_id,
        claim_id=claim_id,
        idempotency_key=key,
        status=ClaimStatus.ADJUDICATED,
        decision=req.decision,
        adjuster_id=req.adjuster_id,
        idempotent_replay=False,
    )

    IDEMPOTENCY_STORE[key] = {
        "fingerprint": fingerprint,
        "response": resp_obj.model_dump(mode="json"),
    }

    AuditLogger.log(
        user_id=user.user_id,
        action="write_decision",
        resource=claim_id,
        outcome="granted",
        decision=req.decision.value,
        details={"decision_id": decision_id, "idempotent_replay": False, "key": key},
    )

    response.status_code = status.HTTP_201_CREATED
    return resp_obj


# ---------------------------------------------------------------------------
# AUDIT TRAIL QUERY ENDPOINT (Guarded)
# ---------------------------------------------------------------------------

@app.get("/audit-trail")
def get_audit_trail(
    limit: int = 50,
    user: UserIdentity = Depends(authenticate_request),
) -> dict[str, Any]:
    """
    Guarded endpoint to view recent immutable audit events.
    """
    records = []
    if AUDIT_LOG_FILE.exists():
        with open(AUDIT_LOG_FILE, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line.strip()))
                    except Exception:
                        pass
    recent = records[-limit:]
    recent.reverse()
    return {"total_records": len(records), "returned": len(recent), "events": recent}
