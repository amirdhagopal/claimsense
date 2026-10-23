"""
ClaimSense AI — Claims Management System (CMS) Typed Contracts & Idempotency Rules

Defines the typed Pydantic models for the CMS REST endpoints:
  - GET  /claims/{claim_id}
  - GET  /claims/{claim_id}/history
  - POST /claims/{claim_id}/decisions (Idempotent write operation)
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from enum import Enum
from typing import Annotated, Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClaimStatus(str, Enum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    PENDING_DOCUMENTS = "pending_documents"
    ADJUDICATED = "adjudicated"
    CLOSED = "closed"


class DecisionOutcome(str, Enum):
    APPROVE = "approve"
    FLAG = "flag"
    ROUTE = "route"
    DENY = "deny"


class DecisionDetail(str, Enum):
    STANDARD_APPROVAL = "standard_approval"
    TOTAL_LOSS = "total_loss"
    BODILY_INJURY = "bodily_injury"
    SPECIALIST = "specialist"
    FRAUD = "fraud"
    POLICY_LAPSED = "policy_lapsed"
    EXCLUDED_PERIL = "excluded_peril"
    VEHICLE_NOT_SCHEDULED = "vehicle_not_scheduled"
    ACCESS_DENIED = "access_denied"


class ClaimantInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., min_length=2, max_length=120, description="Full name of claimant")
    policy_id: str = Field(..., pattern=r"^POL-[0-9]{5}$", description="Associated policy identifier")
    contact: str = Field(..., description="Email or phone number for claimant contact")


class VehicleInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    make: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1900, le=2030)
    vin: str = Field(..., min_length=7, max_length=17, description="Vehicle Identification Number")
    market_value: float = Field(..., ge=0.0, description="Current market valuation in USD")


class PriorClaimRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(..., pattern=r"^CLM-[0-9]{4}-[0-9]{4}$")
    incident_date: date
    outcome: str
    amount_paid: float = Field(..., ge=0.0)


class ClaimRecord(BaseModel):
    """
    Contract for GET /claims/{claim_id}
    System of record claim data returned from the Claims Management System.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(..., pattern=r"^CLM-[0-9]{4}-[0-9]{4}$", description="Unique claim identifier")
    claimant: ClaimantInfo
    status: ClaimStatus = Field(default=ClaimStatus.NEW)
    incident_date: date = Field(..., description="Date on which the loss incident occurred")
    incident_time: Optional[str] = Field(default=None, description="Reported local time of incident (HH:MM)")
    incident_location: str = Field(..., min_length=3, description="Reported location of incident")
    incident_description: str = Field(..., min_length=10, description="Detailed loss narrative")
    vehicle: VehicleInfo
    damage_description: str = Field(..., min_length=5, description="Physical damage reported")
    repair_estimate: float = Field(..., ge=0.0, description="Total quoted repair cost in USD")
    prior_claims: list[PriorClaimRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_adjuster_id: Optional[str] = None


class ClaimHistoryEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime
    previous_status: Optional[ClaimStatus]
    new_status: ClaimStatus
    actor_id: str
    reason: Optional[str] = None


class ClaimHistoryResponse(BaseModel):
    """
    Contract for GET /claims/{claim_id}/history
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    events: list[ClaimHistoryEvent]


# ---------------------------------------------------------------------------
# WRITE OPERATION CONTRACTS & IDEMPOTENCY RULES
# ---------------------------------------------------------------------------

class ClaimDecisionRequest(BaseModel):
    """
    Contract for POST /claims/{claim_id}/decisions
    Written by a licensed adjuster to confirm an adjudication decision.
    
    IDEMPOTENCY RULES:
    1. Every request MUST provide an `idempotency_key` (UUIDv4) in the payload or 'Idempotency-Key' HTTP header.
    2. The CMS server caches the response paired with the idempotency key for 24 hours.
    3. Re-submitting an identical request with the same idempotency_key returns the original
       HTTP 200 response with `idempotent_replay: true`.
    4. Submitting a *different* payload with an already-used idempotency key produces HTTP 409 Conflict.
    5. A claim already in `ADJUDICATED` or `CLOSED` status cannot be rewritten without explicit re-opening.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    idempotency_key: str = Field(
        ...,
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        description="UUIDv4 ensuring single execution semantics"
    )
    claim_id: str = Field(..., pattern=r"^CLM-[0-9]{4}-[0-9]{4}$")
    decision: DecisionOutcome = Field(..., description="Confirmed decision outcome")
    decision_detail: Optional[DecisionDetail] = Field(default=None)
    adjuster_id: str = Field(..., min_length=3, description="Licensed adjuster ID who confirmed this decision")
    reasoning: str = Field(..., min_length=15, description="Auditable justification for the outcome")
    cited_clauses: list[str] = Field(
        default_factory=list,
        description="Policy clauses cited (must match ^CLS-[A-Z]{3}-[0-9]{3}$)"
    )
    override_reason: Optional[str] = Field(
        default=None,
        description="Required if human adjuster overrides the AI co-pilot's draft"
    )
    payout_authorized: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Deterministic payout authorized net of deductible (if approved)"
    )

    @field_validator("cited_clauses")
    @classmethod
    def validate_clause_identifiers(cls, clauses: list[str]) -> list[str]:
        pattern = re.compile(r"^CLS-[A-Z]{3}-[0-9]{3}$")
        for c in clauses:
            if not pattern.match(c):
                raise ValueError(f"Invalid clause identifier '{c}'. Must match pattern CLS-XXX-###")
        return clauses


class ClaimDecisionResponse(BaseModel):
    """
    Response returned by POST /claims/{claim_id}/decisions
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str = Field(..., description="Unique decision record ID in CMS")
    claim_id: str
    idempotency_key: str
    status: ClaimStatus = Field(default=ClaimStatus.ADJUDICATED)
    decision: DecisionOutcome
    adjuster_id: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    idempotent_replay: bool = Field(
        default=False,
        description="True if this response was served from cache due to a repeated idempotency key"
    )
