"""
ClaimSense AI — Immutable Audit Logger (Deterministic Spine)

Appends structured audit records for every API call, granted or denied,
carrying {timestamp, user_id, action, resource, outcome, details}.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
AUDIT_LOG_FILE = LOGS_DIR / "audit_trail.jsonl"


class AuditRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_id: str
    action: str
    resource: str  # e.g. claim_id
    outcome: str   # "granted" | "denied"
    decision: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    """
    Append-only audit writer logging directly to local disk and standard output.
    """

    @classmethod
    def log(
        cls,
        user_id: str,
        action: str,
        resource: str,
        outcome: str,
        decision: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditRecord:
        record = AuditRecord(
            user_id=user_id,
            action=action,
            resource=resource,
            outcome=outcome,
            decision=decision,
            details=details or {},
        )

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(json.dumps(record.model_dump()) + "\n")

        return record
