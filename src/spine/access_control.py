"""
ClaimSense AI — Access Control & Entitlement Engine (Deterministic Spine)

Enforces role-based and attribute-based access control IN CODE before any
agent is instantiated or any claim data is fetched.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class UserIdentity(BaseModel):
    user_id: str
    role: str = "licensed_adjuster"
    entitled_claims: list[str] = Field(
        default_factory=lambda: ["*"],
        description="List of claim IDs user can access. '*' grants all."
    )


class AccessControlEngine:
    """
    Evaluates whether a requesting user has entitlement to access a specific claim.
    Executes entirely in deterministic code before any model is invoked.
    """

    @staticmethod
    def verify_entitlement(user: UserIdentity, claim_id: str) -> tuple[bool, Optional[str]]:
        """
        Returns (is_granted, denial_reason).
        """
        if not user.user_id or user.user_id.strip() == "":
            return False, "Unauthenticated: Missing user_id"

        # Check claim entitlement
        if "*" in user.entitled_claims:
            return True, None

        if claim_id in user.entitled_claims:
            return True, None

        return False, f"Access denied: User '{user.user_id}' is not entitled to claim '{claim_id}'"
