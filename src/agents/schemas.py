"""
ClaimSense AI — Typed Schemas for the 4-Agent Adjudication Pipeline

Defines strict Pydantic models for every agent boundary in accordance with
Milestone 3 requirement: "Agent set implemented on the OpenAI Agents SDK with strict typed outputs."
"""

from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.contracts.cms import DecisionOutcome, DecisionDetail


class FileReaderOutput(BaseModel):
    """
    Typed output of Agent 1 (FileReaderAgent).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    fact_summary: str = Field(..., description="Chronological summary of verified facts")
    damage_locations: list[str] = Field(..., description="Extracted damaged components (e.g. rear bumper, front axle)")
    identified_contradictions: list[str] = Field(
        default_factory=list,
        description="Factual contradictions found between narrative and documents"
    )
    unwitnessed_loss: bool = Field(default=False, description="True if no third-party witnesses or CCTV exist")
    injuries_reported: bool = Field(default=False, description="True if any occupant sustained medical injuries")


class CoverageOutput(BaseModel):
    """
    Typed output of Agent 2 (CoverageAgent).
    Must strictly cite retrieved clause IDs.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    coverage_applies: bool = Field(..., description="True if policy grants coverage for this peril")
    covered_perils: list[str] = Field(default_factory=list, description="List of policy perils responding to loss")
    exclusions_triggered: list[str] = Field(default_factory=list, description="Exclusion clauses triggered (if any)")
    cited_clause_ids: list[str] = Field(
        ...,
        min_length=1,
        description="Authoritative clause IDs cited (must match pattern CLS-XXX-###)"
    )
    coverage_reasoning: str = Field(..., min_length=10, description="Legal analysis linking loss to clauses")

    @field_validator("cited_clause_ids")
    @classmethod
    def validate_clause_pattern(cls, v: list[str]) -> list[str]:
        pattern = re.compile(r"^CLS-[A-Z]{3}-[0-9]{3}$")
        for cid in v:
            if not pattern.match(cid):
                raise ValueError(f"Invalid clause ID format '{cid}'. Must be CLS-XXX-###")
        return v


class RiskOutput(BaseModel):
    """
    Typed output of Agent 3 (RiskAssessmentAgent).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    fraud_risk_score: float = Field(..., ge=0.0, le=1.0, description="Assessed likelihood of fraud (0.0 to 1.0)")
    is_fraud_flagged: bool = Field(..., description="True if claim should be referred to Special Investigation Unit")
    fraud_indicators: list[str] = Field(
        default_factory=list,
        description="Specific behavioral, document, or timing red flags"
    )
    is_total_loss: bool = Field(default=False, description="True if repair cost exceeds threshold")
    is_bodily_injury: bool = Field(default=False, description="True if severe injury requires specialist adjuster")
    is_specialist_required: bool = Field(default=False, description="True if rare/classic vehicle requires specialist")
    risk_summary: str = Field(..., min_length=10, description="Summary of risk evaluation")


class DraftDecisionOutput(BaseModel):
    """
    Typed output of Agent 4 (DecisionDraftAgent).
    Final adjudication dossier submitted to the licensed adjuster.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    decision: DecisionOutcome = Field(..., description="One of four standard outcomes: approve, flag, route, deny")
    decision_detail: Optional[DecisionDetail] = None
    reasoning: str = Field(..., min_length=20, description="Defensible justification citing facts and clauses")
    cited_clauses: list[str] = Field(..., min_length=1, description="Clause IDs supporting this decision")
    payout_authorized: Optional[float] = Field(default=None, ge=0.0, description="Payout calculated deterministically")
    verdict_source: str = Field(
        default="model_agent",
        description="Distinguishes model-generated verdicts ('model_agent') from 'deterministic_spine_fallback'"
    )
    requires_licensed_adjuster_confirmation: bool = Field(
        default=True,
        description="Always True. Human licensed adjuster is accountable for the outcome."
    )
