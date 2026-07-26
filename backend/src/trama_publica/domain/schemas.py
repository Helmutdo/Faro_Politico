"""Comandos Pydantic para operaciones sensibles del dominio."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trama_publica.domain.enums import (
    AccessStatus,
    EvidenceLevel,
    Predicate,
    PublicationStatus,
    ReviewStatus,
    SourceType,
)


class SourceDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(min_length=1, max_length=120)
    source_type: SourceType
    title: str = Field(min_length=1)
    retrieved_at: datetime
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    access_status: AccessStatus
    original_url: str | None = None
    issuing_body: str | None = None
    publication_date: date | None = None
    document_date: date | None = None
    storage_path: str | None = None
    mime_type: str | None = None
    language: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_entity_id: UUID
    predicate: Predicate
    object_entity_id: UUID | None = None
    literal_value: dict[str, Any] | list[Any] | str | int | float | bool | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    evidence_level: EvidenceLevel
    source_document_id: UUID
    source_excerpt: str = Field(min_length=1)
    source_location: str | None = None
    technical_confidence: float | None = Field(default=None, ge=0, le=1)
    review_status: ReviewStatus = ReviewStatus.EXTRACTED
    publication_status: PublicationStatus = PublicationStatus.PRIVATE

    @model_validator(mode="after")
    def exactly_one_object(self) -> "ClaimCreate":
        if (self.object_entity_id is None) == (self.literal_value is None):
            raise ValueError("exactly one claim object must be provided")
        return self
