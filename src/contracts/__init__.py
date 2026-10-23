"""
ClaimSense AI — Client Systems Typed Contracts Package

Exports typed Pydantic models for:
  - Claims Management System (CMS)
  - Document Store (DocStore)
  - Policy Administration (PolicyAdmin)
"""

from src.contracts.cms import (
    ClaimRecord,
    ClaimStatus,
    ClaimantInfo,
    VehicleInfo,
    PriorClaimRecord,
    ClaimHistoryEvent,
    ClaimHistoryResponse,
    DecisionOutcome,
    DecisionDetail,
    ClaimDecisionRequest,
    ClaimDecisionResponse,
)
from src.contracts.docstore import (
    DocumentType,
    DocumentMetadata,
    DocumentListResponse,
    DocumentContentResponse,
)
from src.contracts.policyadmin import (
    PolicyCoverageType,
    PolicyClause,
    PolicyRecord,
    PolicyResponse,
    PolicyClausesResponse,
)

__all__ = [
    # CMS
    "ClaimRecord",
    "ClaimStatus",
    "ClaimantInfo",
    "VehicleInfo",
    "PriorClaimRecord",
    "ClaimHistoryEvent",
    "ClaimHistoryResponse",
    "DecisionOutcome",
    "DecisionDetail",
    "ClaimDecisionRequest",
    "ClaimDecisionResponse",
    # DocStore
    "DocumentType",
    "DocumentMetadata",
    "DocumentListResponse",
    "DocumentContentResponse",
    # PolicyAdmin
    "PolicyCoverageType",
    "PolicyClause",
    "PolicyRecord",
    "PolicyResponse",
    "PolicyClausesResponse",
]
