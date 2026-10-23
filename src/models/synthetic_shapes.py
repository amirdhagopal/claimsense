"""
ClaimSense AI — Synthetic Data Shapes & Canonical Fixture Schema

Provides canonical schemas, clause definitions, and synthetic data models
guaranteeing 100% synthetic motor claims, policies, and supporting documents.
"""

from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.contracts.cms import ClaimRecord, ClaimantInfo, VehicleInfo, PriorClaimRecord, ClaimStatus
from src.contracts.docstore import DocumentMetadata, DocumentContentResponse, DocumentType
from src.contracts.policyadmin import PolicyRecord, PolicyClause, PolicyCoverageType


# ---------------------------------------------------------------------------
# CANONICAL MOTOR POLICY CLAUSE CATALOG
# ---------------------------------------------------------------------------

CANONICAL_POLICY_CLAUSES = [
    # Period & Territory
    PolicyClause(
        clause_id="CLS-PER-001",
        title="Policy Period and In-Force Term",
        section="Period",
        text="This policy is in force from the effective date to the expiry date shown on the schedule, both dates inclusive. No coverage applies outside this period regardless of system status flags.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE, PolicyCoverageType.THIRD_PARTY_ONLY, PolicyCoverageType.COLLISION_ONLY]
    ),
    PolicyClause(
        clause_id="CLS-PER-006",
        title="Incident Date Precedence",
        section="Period",
        text="The determining factor for coverage validity is the date on which the loss incident occurred. Losses occurring even one calendar day after policy expiration or cancellation are strictly excluded.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE, PolicyCoverageType.THIRD_PARTY_ONLY, PolicyCoverageType.COLLISION_ONLY]
    ),
    # Coverage Grants
    PolicyClause(
        clause_id="CLS-COV-001",
        title="Accidental Collision and Impact Damage",
        section="Coverage",
        text="We will pay for loss of or damage to the insured vehicle caused by accidental collision with another vehicle, stationary object, or overturn, subject to applicable deductibles and policy limits.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE, PolicyCoverageType.COLLISION_ONLY]
    ),
    PolicyClause(
        clause_id="CLS-COV-002",
        title="Weather and Natural Perils Coverage",
        section="Coverage",
        text="We will indemnify the policyholder for direct physical loss caused by hail, lightning, storm, windstorm, flood, or falling objects, subject to standard deductible.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE]
    ),
    PolicyClause(
        clause_id="CLS-COV-003",
        title="Automotive Glass and Windshield Repair",
        section="Coverage",
        text="Covers repair or replacement of windshield and window glass damaged by road debris or accidental breakage. Subject to a reduced glass deductible of $100.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE]
    ),
    PolicyClause(
        clause_id="CLS-COV-004",
        title="Comprehensive Theft and Unrecovered Loss",
        section="Coverage",
        text="Covers total loss or repair resulting from theft of the insured vehicle. Requires immediate reporting to police and verification of anti-theft immobilizer status.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE]
    ),
    PolicyClause(
        clause_id="CLS-COV-006",
        title="Total Loss Economic Constructive Threshold",
        section="Coverage",
        text="A vehicle is deemed an economic total loss when the estimated cost of repairs exceeds 75% of the vehicle market value at the time of loss, or where structural integrity cannot be safely restored.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE, PolicyCoverageType.COLLISION_ONLY]
    ),
    PolicyClause(
        clause_id="CLS-COV-007",
        title="Bodily Injury Specialist Adjudication Routing",
        section="Coverage",
        text="Any claim involving hospitalisation, severe soft-tissue trauma, fractures, or third-party injury claims exceeding $5,000 must be routed to a designated Bodily Injury specialist adjuster.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE, PolicyCoverageType.THIRD_PARTY_ONLY]
    ),
    PolicyClause(
        clause_id="CLS-COV-008",
        title="Scheduled Vehicle Warranty",
        section="Coverage",
        text="Coverage applies strictly and exclusively to the vehicle(s) whose Vehicle Identification Number (VIN) is listed on the policy vehicle schedule.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE, PolicyCoverageType.THIRD_PARTY_ONLY, PolicyCoverageType.COLLISION_ONLY]
    ),
    PolicyClause(
        clause_id="CLS-COV-009",
        title="Mid-Term Endorsement Inception Verification",
        section="Coverage",
        text="Coverage upgrades or addition of comprehensive perils initiated via mid-term endorsement are subject to strict fraud verification if a high-severity claim occurs within 72 hours of upgrade.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE]
    ),
    PolicyClause(
        clause_id="CLS-COV-010",
        title="Agreed Value Classic Vehicle Protection",
        section="Coverage",
        text="For vehicles designated Classic or Antique, payout in the event of total loss is established at the agreed schedule valuation rather than market depreciation.",
        applies_to_coverage=[PolicyCoverageType.AGREED_VALUE_CLASSIC]
    ),
    PolicyClause(
        clause_id="CLS-COV-011",
        title="Classic Vehicle Specialist Restoration Routing",
        section="Coverage",
        text="Partial damage or mechanical rebuilding of Classic vehicles must be referred to a vintage automotive specialist appraiser.",
        applies_to_coverage=[PolicyCoverageType.AGREED_VALUE_CLASSIC]
    ),
    # Exclusions
    PolicyClause(
        clause_id="CLS-EXC-001",
        title="Intoxication and Impaired Operation Exclusion",
        section="Exclusion",
        text="No coverage applies if the operator of the insured vehicle is convicted of or breathalysed above the statutory Blood Alcohol Concentration (BAC) threshold at the time of loss.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE, PolicyCoverageType.THIRD_PARTY_ONLY, PolicyCoverageType.COLLISION_ONLY]
    ),
    PolicyClause(
        clause_id="CLS-EXC-003",
        title="Motorsport, Racing and Closed Circuit Exclusion",
        section="Exclusion",
        text="No coverage applies to loss, damage, or liability incurred while participating in any organized racing, speed trials, pace-making, or open-track circuit events.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE, PolicyCoverageType.THIRD_PARTY_ONLY, PolicyCoverageType.COLLISION_ONLY]
    ),
    # Deductibles
    PolicyClause(
        clause_id="CLS-DED-001",
        title="Standard Comprehensive Collision Deductible",
        section="Deductible",
        text="A deductible of $500 applies to each collision, upset, or physical damage claim, subtracted from final settlement.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE, PolicyCoverageType.COLLISION_ONLY]
    ),
    PolicyClause(
        clause_id="CLS-DED-002",
        title="Automotive Glass Waiver Deductible",
        section="Deductible",
        text="A reduced deductible of $100 applies to isolated glass claims where no other body panels are damaged.",
        applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE]
    )
]


# ---------------------------------------------------------------------------
# SYNTHETIC CLAIM DOSSIER SHAPE
# ---------------------------------------------------------------------------

class SyntheticClaimDossier(BaseModel):
    """
    Consolidated synthetic test fixture linking a claim, its policy, and documents.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim: ClaimRecord
    policy: PolicyRecord
    documents: list[DocumentContentResponse]
    ground_truth_decision: str
    ground_truth_fraud: bool = False
    ground_truth_detail: Optional[str] = None
    expected_citations: list[str] = Field(default_factory=list)
