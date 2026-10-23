"""
ClaimSense AI — Policy Date Verification Engine (Deterministic Spine)

Validates that the loss incident date occurred strictly within the in-force
term of the policy, ignoring stale database status flags.
"""

from __future__ import annotations

from datetime import date
from src.contracts.cms import ClaimRecord
from src.contracts.policyadmin import PolicyRecord


class PolicyDateEngine:
    """
    Executes compiled date math using Python datetime.date.
    Never delegates calendar arithmetic to an LLM.
    """

    @staticmethod
    def evaluate_in_force(claim: ClaimRecord, policy: PolicyRecord) -> tuple[bool, int]:
        """
        Evaluates whether incident_date is within [effective_date, expiry_date].
        Returns: (is_in_force, days_past_expiry)
        """
        incident = claim.incident_date
        effective = policy.effective_date
        expiry = policy.expiry_date

        if effective <= incident <= expiry:
            return True, 0

        if incident > expiry:
            days_lapsed = (incident - expiry).days
            return False, days_lapsed

        # Incident occurred before policy became effective
        days_early = (effective - incident).days
        return False, -days_early
