"""
ClaimSense AI — REST API Service (FastAPI)

Provides the HTTP API endpoints for:
  - System health (/health)
  - Claim Adjudication (/adjudicate)
  - Client system mocks (/claims, /policies, /documents)
  - Idempotent decision write-back (/claims/{id}/decisions)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Header, Response, status
from pydantic import BaseModel, Field

from src.agents.pipeline import AdjudicationPipeline
from src.config import settings
from src.contracts.cms import (
    ClaimRecord,
    ClaimDecisionRequest,
    ClaimDecisionResponse,
    ClaimStatus,
)
from src.contracts.docstore import DocumentContentResponse, DocumentListResponse
from src.contracts.policyadmin import PolicyRecord, PolicyResponse
from src.spine.access_control import UserIdentity
from src.spine.orchestrator import AccessDeniedException

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Motor claims adjudication co-pilot bounded by a deterministic spine.",
)

# In-memory stores for synthetic fixtures and idempotency cache
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


# ---------------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------------

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
        "model": settings.openai_model,
    }


# ---------------------------------------------------------------------------
# ADJUDICATION ENDPOINT
# ---------------------------------------------------------------------------

class AdjudicateRequest(BaseModel):
    user_id: str = Field(..., description="Licensed adjuster ID")
    claim_id: str = Field(..., description="Target claim ID")
    role: str = "licensed_adjuster"
    entitled_claims: list[str] = Field(default_factory=lambda: ["*"])


@app.post("/adjudicate")
def adjudicate_claim(req: AdjudicateRequest) -> dict[str, Any]:
    """
    Executes pre-agent deterministic checks, followed by the 4-agent adjudication pipeline.
    If the user lacks entitlement, returns HTTP 403 Forbidden with zero claim data.
    """
    if req.claim_id not in CLAIMS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{req.claim_id}' not found in system.",
        )

    fixture = CLAIMS_DB[req.claim_id]
    claim = ClaimRecord.model_validate(fixture["claim"])
    policy = PolicyRecord.model_validate(fixture["policy"])
    documents = [DocumentContentResponse.model_validate(d) for d in fixture["documents"]]

    user = UserIdentity(
        user_id=req.user_id,
        role=req.role,
        entitled_claims=req.entitled_claims,
    )

    try:
        dossier = pipeline.adjudicate(
            user=user,
            claim=claim,
            policy=policy,
            documents=documents,
        )
    except AccessDeniedException as e:
        # Refusal on entitlement: return HTTP 403 and ZERO claim data
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
# CLIENT SYSTEM MOCKS & IDEMPOTENT DECISION WRITE-BACK
# ---------------------------------------------------------------------------

@app.get("/claims/{claim_id}")
def get_claim(claim_id: str) -> dict[str, Any]:
    if claim_id not in CLAIMS_DB:
        raise HTTPException(status_code=404, detail="Claim not found")
    return CLAIMS_DB[claim_id]["claim"]


@app.get("/policies/{policy_id}")
def get_policy(policy_id: str) -> dict[str, Any]:
    for item in CLAIMS_DB.values():
        if item["policy"]["policy_id"] == policy_id:
            return {"policy": item["policy"]}
    raise HTTPException(status_code=404, detail="Policy not found")


@app.get("/documents")
def get_documents(claim_id: str) -> dict[str, Any]:
    if claim_id not in CLAIMS_DB:
        raise HTTPException(status_code=404, detail="Claim not found")
    docs = CLAIMS_DB[claim_id]["documents"]
    return {"claim_id": claim_id, "documents": docs, "total_count": len(docs)}


@app.post("/claims/{claim_id}/decisions", response_model=ClaimDecisionResponse)
def write_claim_decision(
    claim_id: str,
    req: ClaimDecisionRequest,
    response: Response,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> ClaimDecisionResponse:
    """
    Idempotent decision write-back endpoint implementing ADR-006:
      - Validates UUIDv4 idempotency key
      - Replays identical response on exact duplicate request
      - Returns HTTP 409 Conflict if key is reused with a different payload
    """
    key = req.idempotency_key or idempotency_key_header
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required idempotency key.",
        )

    # Compute payload fingerprint
    payload_str = json.dumps(req.model_dump(exclude={"idempotency_key"}), sort_keys=True)
    fingerprint = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    if key in IDEMPOTENCY_STORE:
        stored = IDEMPOTENCY_STORE[key]
        if stored["fingerprint"] == fingerprint:
            # Exact match: Replay cached response
            response.headers["X-Idempotent-Replay"] = "true"
            cached_resp = stored["response"]
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
            # Reused key with different payload: 409 Conflict
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

    response.status_code = status.HTTP_201_CREATED
    return resp_obj
