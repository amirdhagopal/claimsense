"""
ClaimSense AI — Deterministic Spine Orchestrator

Executes pre-agent security, calendar math, and financial verification.
Guarantees that unauthorized requests are aborted before any agent runs.
"""

from __future__ import annotations

from src.contracts.cms import ClaimRecord
from src.contracts.policyadmin import PolicyRecord
from src.spine.access_control import AccessControlEngine, UserIdentity
from src.spine.audit_logger import AuditLogger
from src.spine.context import SpineContext
from src.spine.date_engine import PolicyDateEngine
from src.spine.financial_engine import FinancialArithmeticEngine


class AccessDeniedException(Exception):
    def __init__(self, message: str, user_id: str, claim_id: str):
        super().__init__(message)
        self.message = message
        self.user_id = user_id
        self.claim_id = claim_id


class DeterministicSpine:
    """
    Coordinates all code-level invariants before model agents are invoked.
    """

    @staticmethod
    def execute_pre_agent_checks(
        user: UserIdentity,
        claim: ClaimRecord,
        policy: PolicyRecord,
    ) -> SpineContext:
        # 1. Access Control / Entitlement
        granted, denial_reason = AccessControlEngine.verify_entitlement(user, claim.claim_id)
        if not granted:
            AuditLogger.log(
                user_id=user.user_id,
                action="adjudicate_claim",
                resource=claim.claim_id,
                outcome="denied",
                decision="deny",
                details={"reason": denial_reason, "stage": "access_control_pre_check"},
            )
            raise AccessDeniedException(
                message=denial_reason or "Access denied",
                user_id=user.user_id,
                claim_id=claim.claim_id,
            )

        # 2. Policy Date Math
        is_in_force, days_past = PolicyDateEngine.evaluate_in_force(claim, policy)

        # 3. Vehicle Schedule
        vehicle_scheduled = policy.covers_vehicle(claim.vehicle.vin)

        # 4. Financial Calculations
        financials = FinancialArithmeticEngine.compute_financials(claim, policy)

        # 5. Deterministic Rejection Triggers
        must_reject = False
        rejection_reason = None
        if not is_in_force:
            must_reject = True
            rejection_reason = f"Policy lapsed: incident occurred on {claim.incident_date}, which is {days_past} days after policy expiry ({policy.expiry_date})."
        elif not vehicle_scheduled:
            must_reject = True
            rejection_reason = f"Vehicle VIN {claim.vehicle.vin} is not scheduled on policy {policy.policy_id}."

        context = SpineContext(
            claim_id=claim.claim_id,
            user_id=user.user_id,
            user_entitled=True,
            incident_date=claim.incident_date,
            policy_effective_date=policy.effective_date,
            policy_expiry_date=policy.expiry_date,
            policy_in_force=is_in_force,
            days_past_expiry=max(0, days_past),
            vehicle_vin=claim.vehicle.vin,
            vehicle_scheduled=vehicle_scheduled,
            repair_estimate=float(financials["repair_estimate"]),
            vehicle_market_value=float(financials["market_value"]),
            repair_to_value_ratio=float(financials["repair_to_value_ratio"]),
            is_constructive_total_loss=bool(financials["is_constructive_total_loss"]),
            deductible=float(financials["applicable_deductible"]),
            coverage_limit=float(financials["coverage_limit"]),
            max_authorized_payout=float(financials["max_authorized_payout"]),
            spine_must_reject=must_reject,
            rejection_reason=rejection_reason,
        )

        return context
