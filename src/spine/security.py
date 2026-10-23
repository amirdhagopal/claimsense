"""
ClaimSense AI — Security, Authentication & Trust Boundary

Enforces cryptographic Bearer token authentication and role/entitlement verification
across all API routes in accordance with Milestone 4 requirements:
  "2. Authorisation enforced on every route; requests without a valid token are refused."
  "3. Access control implemented in code and executed before any agent is invoked."
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional
from fastapi import Header, HTTPException, status

from src.spine.access_control import UserIdentity
from src.spine.audit_logger import AuditLogger

# Secret key for HMAC token signing (in production, loaded from AWS Secrets Manager)
SECRET_KEY = b"claimsense-secure-signing-key-2026-autumn"

# Pre-seeded test tokens for immediate use and testing
PRESEEDED_TOKENS: dict[str, UserIdentity] = {
    # User 1: Authorized adjuster (Jane) — Has access to CLM-2026-0101
    "token-jane-full-access": UserIdentity(
        user_id="adjuster-jane",
        role="licensed_adjuster",
        entitled_claims=["*"],
    ),
    # User 2: Limited adjuster (Bob) — Lacks access to CLM-2026-0101 (Only has 0104, 0109, 0113)
    "token-bob-limited-access": UserIdentity(
        user_id="adjuster-bob",
        role="licensed_adjuster",
        entitled_claims=["CLM-2026-0104", "CLM-2026-0109", "CLM-2026-0113"],
    ),
    # User 3: Single-claim adjuster (EVAL-017 & EVAL-018)
    "token-limited-access": UserIdentity(
        user_id="adjuster-limited",
        role="licensed_adjuster",
        entitled_claims=["CLM-2026-0117"],
    ),
    # Admin / Compliance Auditor
    "token-admin-access": UserIdentity(
        user_id="compliance-auditor",
        role="compliance_auditor",
        entitled_claims=["*"],
    ),
}


class TokenManager:
    """
    Creates and verifies HMAC-SHA256 signed tokens and pre-seeded tokens.
    """

    @classmethod
    def create_signed_token(cls, user_id: str, role: str, entitled_claims: list[str], ttl_seconds: int = 86400) -> str:
        payload = {
            "sub": user_id,
            "role": role,
            "claims": entitled_claims,
            "exp": int(time.time()) + ttl_seconds,
        }
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
        signature = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"cs.{payload_b64}.{signature}"

    @classmethod
    def verify_token(cls, raw_token: str) -> Optional[UserIdentity]:
        raw_token = raw_token.strip()

        # Check pre-seeded tokens first
        if raw_token in PRESEEDED_TOKENS:
            return PRESEEDED_TOKENS[raw_token]

        # Verify HMAC signed tokens (cs.<payload>.<sig>)
        if raw_token.startswith("cs."):
            parts = raw_token.split(".")
            if len(parts) == 3:
                _, payload_b64, sig = parts
                expected_sig = hmac.new(SECRET_KEY, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
                if hmac.compare_digest(sig, expected_sig):
                    try:
                        # Add padding if needed
                        rem = len(payload_b64) % 4
                        padded = payload_b64 + ("=" * (4 - rem) if rem else "")
                        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
                        if payload.get("exp", 0) >= time.time():
                            return UserIdentity(
                                user_id=payload["sub"],
                                role=payload.get("role", "licensed_adjuster"),
                                entitled_claims=payload.get("claims", []),
                            )
                    except Exception:
                        return None
        return None


def authenticate_request(
    authorization: Optional[str] = Header(None, description="Bearer <token>")
) -> UserIdentity:
    """
    FastAPI route dependency enforcing authentication on every route.
    Refuses requests without a valid Bearer token.
    """
    if not authorization:
        AuditLogger.log(
            user_id="anonymous",
            action="api_request",
            resource="trust_boundary",
            outcome="denied",
            details={"error": "missing_authorization_header"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Expected: 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        AuditLogger.log(
            user_id="anonymous",
            action="api_request",
            resource="trust_boundary",
            outcome="denied",
            details={"error": "malformed_authorization_header"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed Authorization header. Format: 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    user = TokenManager.verify_token(token)
    if not user:
        AuditLogger.log(
            user_id="unverified",
            action="api_request",
            resource="trust_boundary",
            outcome="denied",
            details={"error": "invalid_or_expired_token"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authorization token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
