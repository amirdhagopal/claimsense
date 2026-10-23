"""
ClaimSense AI — Deterministic Spine Context

Holds immutable, verified facts computed strictly in compiled Python code
before any model agent is invoked.
"""

from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SpineContext(BaseModel):
    """
    Immutable facts established deterministically by code.
    Agents receive this as input and must never contradict these facts.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    user_id: str
    user_entitled: bool = True
    
    # Date verification
    incident_date: date
    policy_effective_date: date
    policy_expiry_date: date
    policy_in_force: bool = True
    days_past_expiry: int = 0  # > 0 indicates loss occurred after policy lapsed

    # Vehicle verification
    vehicle_vin: str
    vehicle_scheduled: bool = True

    # Financial arithmetic
    repair_estimate: float = 0.0
    vehicle_market_value: float = 0.0
    repair_to_value_ratio: float = 0.0
    is_constructive_total_loss: bool = False
    deductible: float = 500.0
    coverage_limit: float = 50000.0
    max_authorized_payout: float = 0.0

    # Deterministic flags
    spine_must_reject: bool = False
    rejection_reason: Optional[str] = None
