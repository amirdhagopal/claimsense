"""
ClaimSense AI — Document Store (DocStore) Typed Contracts

Defines the typed Pydantic models for the DocStore REST endpoints:
  - GET /documents?claim_id={claim_id}  (list document metadata)
  - GET /documents/{doc_id}/content    (fetch document content / text)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, Enum):
    POLICE_REPORT = "police_report"
    REPAIR_ESTIMATE = "repair_estimate"
    PHOTO = "photo"
    MEDICAL_REPORT = "medical_report"
    WEATHER_REPORT = "weather_report"
    POLICY_ENDORSEMENT = "policy_endorsement"
    VEHICLE_DIAGNOSTIC = "vehicle_diagnostic"
    WITNESS_STATEMENT = "witness_statement"
    INCIDENT_REPORT = "incident_report"


class DocumentMetadata(BaseModel):
    """
    Metadata representation of a stored supporting document.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_id: str = Field(..., pattern=r"^DOC-[0-9]{3}-[A-Z0-9]+$", description="Unique document ID")
    claim_id: str = Field(..., pattern=r"^CLM-[0-9]{4}-[0-9]{4}$", description="Associated claim ID")
    document_type: DocumentType = Field(..., description="Classification of the document")
    file_name: str = Field(..., min_length=1)
    file_size_bytes: int = Field(..., ge=0)
    mime_type: str = Field(..., description="MIME type (e.g. application/pdf, image/jpeg, text/plain)")
    sha256_hash: str = Field(..., min_length=64, max_length=64, description="Cryptographic hash for audit integrity")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    flags: list[str] = Field(default_factory=list, description="System tags or metadata annotations")


class DocumentListResponse(BaseModel):
    """
    Contract for GET /documents?claim_id={claim_id}
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    documents: list[DocumentMetadata]
    total_count: int


class DocumentContentResponse(BaseModel):
    """
    Contract for GET /documents/{doc_id}/content
    Returns the parsed text body or content summary of the requested document.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_id: str
    claim_id: str
    document_type: DocumentType
    content_summary: str = Field(..., min_length=5, description="Extracted textual content or summary")
    structured_data: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Key extracted fields (e.g. BAC value, weather observations, repair total)"
    )
    is_redacted: bool = Field(default=False, description="True if PII redaction was applied")
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
