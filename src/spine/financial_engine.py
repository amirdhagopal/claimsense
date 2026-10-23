"""
ClaimSense AI — Financial Arithmetic Engine (Deterministic Spine)

Computes deductibles, payout caps, and total-loss repair-to-value ratios
in exact floating-point / decimal arithmetic. Never delegated to a model.
"""

from __future__ import annotations

from src.contracts.cms import ClaimRecord
from src.contracts.policyadmin import PolicyRecord


class FinancialArithmeticEngine:
    """
    Executes all monetary arithmetic for claims.
    """

    @staticmethod
    def compute_financials(
        claim: ClaimRecord,
        policy: PolicyRecord,
        total_loss_threshold: float = 0.75
    ) -> dict[str, float | bool]:
        repair = float(claim.repair_estimate)
        market_value = float(claim.vehicle.market_value)
        deductible = float(policy.deductible)
        limit = float(policy.coverage_limit)

        # Ratio
        ratio = (repair / market_value) if market_value > 0 else 0.0
        is_total_loss = ratio >= total_loss_threshold

        # Net authorized payout calculation
        covered_loss = min(repair, limit)
        net_payout = max(0.0, covered_loss - deductible)

        return {
            "repair_estimate": repair,
            "market_value": market_value,
            "repair_to_value_ratio": round(ratio, 4),
            "is_constructive_total_loss": is_total_loss,
            "applicable_deductible": deductible,
            "coverage_limit": limit,
            "max_authorized_payout": round(net_payout, 2)
        }
