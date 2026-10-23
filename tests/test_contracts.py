"""
Unit tests for Client System Typed Contracts & Idempotency Rules
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from src.contracts.cms import (
    ClaimRecord,
    ClaimantInfo,
    VehicleInfo,
    ClaimStatus,
    DecisionOutcome,
    DecisionDetail,
    ClaimDecisionRequest,
    ClaimDecisionResponse,
)
from src.contracts.docstore import (
    DocumentType,
    DocumentMetadata,
    DocumentContentResponse,
)
from src.contracts.policyadmin import (
    PolicyRecord,
    PolicyClause,
    PolicyCoverageType,
)


def test_claim_record_validation():
    claim = ClaimRecord(
        claim_id="CLM-2026-0001",
        claimant=ClaimantInfo(
            name="Alice Smith",
            policy_id="POL-12345",
            contact="alice@example.com"
        ),
        status=ClaimStatus.NEW,
        incident_date=date(2026, 5, 10),
        incident_location="Main St & 2nd Ave",
        incident_description="Rear-end collision at traffic signal.",
        vehicle=VehicleInfo(
            make="Honda",
            model="Civic",
            year=2022,
            vin="1HGCV1F1234567890",
            market_value=24000.0
        ),
        damage_description="Cracked rear bumper and tail light",
        repair_estimate=1850.0,
    )
    assert claim.claim_id == "CLM-2026-0001"
    assert claim.repair_estimate == 1850.0
    assert claim.claimant.policy_id == "POL-12345"


def test_claim_record_invalid_id():
    with pytest.raises(ValidationError):
        ClaimRecord(
            claim_id="INVALID-ID",
            claimant=ClaimantInfo(
                name="Alice Smith",
                policy_id="POL-12345",
                contact="alice@example.com"
            ),
            status=ClaimStatus.NEW,
            incident_date=date(2026, 5, 10),
            incident_location="Main St",
            incident_description="Accident description",
            vehicle=VehicleInfo(
                make="Honda",
                model="Civic",
                year=2022,
                vin="1HGCV1F1234567890",
                market_value=24000.0
            ),
            damage_description="Damage",
            repair_estimate=1000.0,
        )


def test_decision_request_idempotency_key_validation():
    # Valid UUIDv4
    req = ClaimDecisionRequest(
        idempotency_key="a1b2c3d4-e5f6-4a1b-8c2d-123456789abc",
        claim_id="CLM-2026-0001",
        decision=DecisionOutcome.APPROVE,
        decision_detail=DecisionDetail.STANDARD_APPROVAL,
        adjuster_id="adjuster-jane",
        reasoning="Collision covered under policy clause CLS-COV-001 with active coverage.",
        cited_clauses=["CLS-PER-001", "CLS-COV-001"],
        payout_authorized=1350.0
    )
    assert req.idempotency_key == "a1b2c3d4-e5f6-4a1b-8c2d-123456789abc"

    # Invalid idempotency key (not UUID format)
    with pytest.raises(ValidationError):
        ClaimDecisionRequest(
            idempotency_key="non-uuid-string",
            claim_id="CLM-2026-0001",
            decision=DecisionOutcome.APPROVE,
            adjuster_id="adjuster-jane",
            reasoning="Valid reasoning string here.",
        )


def test_policy_deterministic_date_math():
    policy = PolicyRecord(
        policy_id="POL-10001",
        policyholder="Sarah Chen",
        effective_date=date(2026, 1, 1),
        expiry_date=date(2026, 12, 31),
        status="Active",
        coverage_type=PolicyCoverageType.COMPREHENSIVE,
        vehicle_schedule=["4T1BF1FK5CU000101"],
        clauses=[
            PolicyClause(
                clause_id="CLS-PER-001",
                title="Policy Period",
                section="Period",
                text="Policy is in force between effective and expiry dates.",
                applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE]
            )
        ],
        deductible=500.0,
        coverage_limit=50000.0
    )

    # In-force on valid date
    assert policy.is_in_force_on(date(2026, 6, 15)) is True
    # In-force on boundary dates
    assert policy.is_in_force_on(date(2026, 1, 1)) is True
    assert policy.is_in_force_on(date(2026, 12, 31)) is True
    # Lapsed after expiry
    assert policy.is_in_force_on(date(2027, 1, 1)) is False
    # Before effective date
    assert policy.is_in_force_on(date(2025, 12, 31)) is False

    # Vehicle schedule check
    assert policy.covers_vehicle("4T1BF1FK5CU000101") is True
    assert policy.covers_vehicle("UNKNOWN_VIN_99999") is False


def test_clause_citation_regex():
    with pytest.raises(ValidationError):
        # Invalid clause ID regex
        PolicyClause(
            clause_id="INVALID-CLAUSE-ID",
            title="Title",
            section="Section",
            text="Text",
        )
