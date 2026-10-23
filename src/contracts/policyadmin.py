"""
ClaimSense AI — Policy Administration (PolicyAdmin) Typed Contracts

Defines the typed Pydantic models for the PolicyAdmin REST endpoints:
  - GET /policies/{policy_id}          (fetch policy header, schedule, and coverages)
  - GET /policies/{policy_id}/clauses  (fetch searchable policy clause corpus)
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PolicyCoverageType(str, Enum):
    COMPREHENSIVE = "Comprehensive"
    THIRD_PARTY_ONLY = "Third-Party Only"
    COLLISION_ONLY = "Collision Only"
    AGREED_VALUE_CLASSIC = "Agreed Value - Classic"


class PolicyClause(BaseModel):
    """
    Representation of a single policy clause for citation and retrieval.
    Clause IDs follow the hierarchical taxonomy: CLS-{SECTION}-{NUMBER}
      e.g. CLS-PER-001, CLS-COV-001, CLS-EXC-003, CLS-DED-001
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    clause_id: str = Field(
        ...,
        pattern=r"^CLS-[A-Z]{3}-[0-9]{3}$",
        description="Immutable hierarchical clause identifier"
    )
    title: str = Field(..., min_length=3, max_length=120)
    section: str = Field(default="General", description="Taxonomy section (e.g. Period, Coverage, Exclusion, Deductible)")
    text: str = Field(..., min_length=10, description="Full authoritative clause wording")
    applies_to_coverage: list[PolicyCoverageType] = Field(
        default_factory=list,
        description="Coverage types where this clause is active"
    )


class PolicyRecord(BaseModel):
    """
    Contract for GET /policies/{policy_id}
    System of record policy details.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_id: str = Field(..., pattern=r"^POL-[0-9]{5}$", description="Unique policy identifier")
    policyholder: str = Field(..., min_length=2, max_length=120)
    effective_date: date = Field(..., description="Start of policy period (inclusive)")
    expiry_date: date = Field(..., description="End of policy period (inclusive)")
    status: str = Field(..., description="System status string (e.g. Active, Suspended, Lapsed)")
    coverage_type: PolicyCoverageType
    vehicle_schedule: list[str] = Field(
        ...,
        min_length=1,
        description="List of VINs or vehicle identifiers covered by this policy"
    )
    clauses: list[PolicyClause] = Field(..., min_length=1, description="All policy clauses")
    deductible: float = Field(..., ge=0.0, description="Standard policy deductible in USD")
    coverage_limit: float = Field(..., ge=0.0, description="Maximum indemnity limit in USD")

    def is_in_force_on(self, check_date: date) -> bool:
        """
        Deterministic Python date verification.
        Evaluates whether check_date falls within [effective_date, expiry_date].
        """
        return self.effective_date <= check_date <= self.expiry_date

    def covers_vehicle(self, vin: str) -> bool:
        """
        Deterministic vehicle schedule check.
        """
        return vin in self.vehicle_schedule


class PolicyResponse(BaseModel):
    """
    Response model for GET /policies/{policy_id}
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy: PolicyRecord


class PolicyClausesResponse(BaseModel):
    """
    Contract for GET /policies/{policy_id}/clauses
    Returns the policy clause corpus formatted for RAG indexing and citation verification.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_id: str
    total_clauses: int
    clauses: list[PolicyClause]
