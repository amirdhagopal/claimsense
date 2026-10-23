"""
Unit tests for Deterministic Spine components:
  - AccessControlEngine (Entitlement checks)
  - PolicyDateEngine (Date calculations & stale status flags)
  - FinancialArithmeticEngine (Deductibles, ratios, total loss)
  - AuditLogger (Append-only logging)
  - DeterministicSpine orchestrator
"""

import pytest
from datetime import date
from src.contracts.cms import ClaimRecord, ClaimantInfo, VehicleInfo, ClaimStatus
from src.contracts.policyadmin import PolicyRecord, PolicyClause, PolicyCoverageType
from src.spine.access_control import AccessControlEngine, UserIdentity
from src.spine.audit_logger import AuditLogger
from src.spine.date_engine import PolicyDateEngine
from src.spine.financial_engine import FinancialArithmeticEngine
from src.spine.orchestrator import DeterministicSpine, AccessDeniedException


@pytest.fixture
def sample_claim():
    return ClaimRecord(
        claim_id="CLM-2026-0001",
        claimant=ClaimantInfo(name="John Doe", policy_id="POL-10001", contact="john@example.com"),
        status=ClaimStatus.NEW,
        incident_date=date(2026, 4, 15),
        incident_location="Highway 101",
        incident_description="Rear-end collision at red light.",
        vehicle=VehicleInfo(make="Toyota", model="Camry", year=2022, vin="4T1BF1FK5CU000101", market_value=25000.0),
        damage_description="Cracked rear bumper",
        repair_estimate=2500.0,
    )


@pytest.fixture
def sample_policy():
    return PolicyRecord(
        policy_id="POL-10001",
        policyholder="John Doe",
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
                text="In force between effective and expiry dates.",
                applies_to_coverage=[PolicyCoverageType.COMPREHENSIVE]
            )
        ],
        deductible=500.0,
        coverage_limit=50000.0,
    )


def test_access_control_authorized():
    user = UserIdentity(user_id="adjuster-jane", entitled_claims=["*"])
    granted, reason = AccessControlEngine.verify_entitlement(user, "CLM-2026-0001")
    assert granted is True
    assert reason is None


def test_access_control_unauthorized():
    user = UserIdentity(user_id="adjuster-bob", entitled_claims=["CLM-2026-9999"])
    granted, reason = AccessControlEngine.verify_entitlement(user, "CLM-2026-0001")
    assert granted is False
    assert "Access denied" in reason


def test_spine_throws_on_unauthorized(sample_claim, sample_policy):
    unauth_user = UserIdentity(user_id="adjuster-bob", entitled_claims=["CLM-2026-9999"])
    with pytest.raises(AccessDeniedException) as exc_info:
        DeterministicSpine.execute_pre_agent_checks(unauth_user, sample_claim, sample_policy)
    assert exc_info.value.claim_id == "CLM-2026-0001"


def test_date_engine_lapsed_policy(sample_claim, sample_policy):
    # Incident date is 2026-04-15, set expiry to 2026-04-10 (5 days before incident)
    lapsed_policy = sample_policy.model_copy(update={"expiry_date": date(2026, 4, 10)})
    is_in_force, days_past = PolicyDateEngine.evaluate_in_force(sample_claim, lapsed_policy)
    assert is_in_force is False
    assert days_past == 5


def test_financial_engine_calculations(sample_claim, sample_policy):
    fin = FinancialArithmeticEngine.compute_financials(sample_claim, sample_policy)
    # $2500 repair - $500 deductible = $2000 payout
    assert fin["max_authorized_payout"] == 2000.0
    assert fin["repair_to_value_ratio"] == 0.10
    assert fin["is_constructive_total_loss"] is False


def test_financial_engine_total_loss(sample_claim, sample_policy):
    # Repair estimate $20,000 on $25,000 market value = 80% (>= 75%)
    severe_claim = sample_claim.model_copy(update={"repair_estimate": 20000.0})
    fin = FinancialArithmeticEngine.compute_financials(severe_claim, sample_policy)
    assert fin["is_constructive_total_loss"] is True
    assert fin["repair_to_value_ratio"] == 0.80


def test_audit_logger_records_to_file():
    record = AuditLogger.log(
        user_id="adjuster-test",
        action="test_action",
        resource="CLM-TEST-0001",
        outcome="granted",
        decision="approve",
        details={"test_key": "test_val"}
    )
    assert record.user_id == "adjuster-test"
    assert record.outcome == "granted"
