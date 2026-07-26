"""Modelos SQLAlchemy 2 del núcleo de evidencia histórica."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from trama_publica.db.base import JSON_TYPE, Base, TimestampMixin, utc_now
from trama_publica.domain.enums import (
    AccessStatus,
    CaseStatus,
    EntityType,
    EvidenceLevel,
    FinalityStatus,
    IdentityStatus,
    IngestionStatus,
    JudicialEventType,
    JudicialOutcome,
    JudicialRole,
    MandateStatus,
    OfficeLevel,
    OrganizationType,
    Predicate,
    ProcessingStatus,
    PublicationStatus,
    ReviewDecision,
    ReviewStatus,
    SourceType,
    TerritoryType,
)


def enum_type(enum_class: type[Any], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda values: [item.value for item in values],
    )


class Entity(TimestampMixin, Base):
    __tablename__ = "entities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_type: Mapped[EntityType] = mapped_column(
        enum_type(EntityType, "entity_type")
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint(
            "source_key",
            "sha256",
            "retrieved_at",
            name="uq_source_document_provenance_version",
        ),
        CheckConstraint("length(sha256) = 64", name="source_document_sha256_length"),
        Index("ix_source_documents_source_key", "source_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_key: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[SourceType] = mapped_column(
        enum_type(SourceType, "source_type")
    )
    title: Mapped[str] = mapped_column(Text)
    original_url: Mapped[str | None] = mapped_column(Text)
    issuing_body: Mapped[str | None] = mapped_column(Text)
    publication_date: Mapped[date | None] = mapped_column(Date)
    document_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    storage_path: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    mime_type: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str | None] = mapped_column(String(20))
    access_status: Mapped[AccessStatus] = mapped_column(
        enum_type(AccessStatus, "access_status")
    )
    parent_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_documents.id")
    )
    supersedes_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_documents.id")
    )
    document_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Person(TimestampMixin, Base):
    __tablename__ = "persons"

    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(Text)
    given_names: Mapped[str | None] = mapped_column(Text)
    paternal_surname: Mapped[str | None] = mapped_column(Text)
    maternal_surname: Mapped[str | None] = mapped_column(Text)
    birth_date: Mapped[date | None] = mapped_column(Date)
    death_date: Mapped[date | None] = mapped_column(Date)
    nationality: Mapped[str | None] = mapped_column(String(120))
    biography_summary: Mapped[str | None] = mapped_column(Text)
    identity_review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus, "person_identity_review_status")
    )


class PersonIdentity(Base):
    __tablename__ = "person_identities"
    __table_args__ = (
        UniqueConstraint(
            "source_key",
            "source_person_id",
            name="uq_person_identity_source_identifier",
        ),
        Index("ix_person_identities_person", "person_entity_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    person_entity_id: Mapped[UUID] = mapped_column(ForeignKey("persons.entity_id"))
    source_key: Mapped[str] = mapped_column(String(120))
    source_person_id: Mapped[str] = mapped_column(String(255))
    displayed_name: Mapped[str] = mapped_column(Text)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    identity_status: Mapped[IdentityStatus] = mapped_column(
        enum_type(IdentityStatus, "identity_status")
    )
    source_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_documents.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class PublicOffice(Base):
    __tablename__ = "public_offices"

    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    normalized_name: Mapped[str] = mapped_column(Text)
    original_name: Mapped[str] = mapped_column(Text)
    office_level: Mapped[OfficeLevel] = mapped_column(
        enum_type(OfficeLevel, "office_level")
    )
    institution_name: Mapped[str | None] = mapped_column(Text)


class ElectoralTerritory(Base):
    __tablename__ = "electoral_territories"

    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    territory_type: Mapped[TerritoryType] = mapped_column(
        enum_type(TerritoryType, "territory_type")
    )
    number: Mapped[str | None] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(Text)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    source_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_documents.id")
    )


class Organization(Base):
    __tablename__ = "organizations"

    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    organization_type: Mapped[OrganizationType] = mapped_column(
        enum_type(OrganizationType, "organization_type")
    )
    canonical_name: Mapped[str] = mapped_column(Text)
    original_name: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


class Mandate(Base):
    __tablename__ = "mandates"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="mandate_valid_dates",
        ),
    )

    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    person_entity_id: Mapped[UUID] = mapped_column(ForeignKey("persons.entity_id"))
    public_office_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("public_offices.entity_id")
    )
    electoral_territory_entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("electoral_territories.entity_id")
    )
    organization_entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.entity_id")
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    original_title: Mapped[str] = mapped_column(Text)
    status: Mapped[MandateStatus] = mapped_column(
        enum_type(MandateStatus, "mandate_status")
    )
    source_document_id: Mapped[UUID] = mapped_column(ForeignKey("source_documents.id"))
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus, "mandate_review_status")
    )


class PoliticalAffiliation(Base):
    __tablename__ = "political_affiliations"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="affiliation_valid_dates",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    person_entity_id: Mapped[UUID] = mapped_column(ForeignKey("persons.entity_id"))
    organization_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.entity_id")
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    original_role: Mapped[str | None] = mapped_column(Text)
    source_document_id: Mapped[UUID] = mapped_column(ForeignKey("source_documents.id"))
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus, "affiliation_review_status")
    )


class JudicialCase(Base):
    __tablename__ = "judicial_cases"
    __table_args__ = (
        UniqueConstraint(
            "court_name",
            "case_identifier",
            name="uq_judicial_case_court_identifier",
        ),
    )

    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    case_identifier: Mapped[str] = mapped_column(String(255))
    court_name: Mapped[str] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(Text)
    case_type: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    current_status: Mapped[CaseStatus] = mapped_column(
        enum_type(CaseStatus, "case_status")
    )
    result_summary: Mapped[str | None] = mapped_column(Text)
    finality_status: Mapped[FinalityStatus] = mapped_column(
        enum_type(FinalityStatus, "case_finality_status")
    )
    source_document_id: Mapped[UUID] = mapped_column(ForeignKey("source_documents.id"))
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus, "case_review_status")
    )


class JudicialCasePerson(Base):
    __tablename__ = "judicial_case_persons"
    __table_args__ = (
        UniqueConstraint(
            "judicial_case_entity_id",
            "person_entity_id",
            "original_role",
            "participation_start",
            name="uq_case_person_historical_role",
        ),
        Index("ix_case_person_person", "person_entity_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    judicial_case_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("judicial_cases.entity_id")
    )
    person_entity_id: Mapped[UUID] = mapped_column(ForeignKey("persons.entity_id"))
    original_role: Mapped[str] = mapped_column(Text)
    normalized_role: Mapped[JudicialRole] = mapped_column(
        enum_type(JudicialRole, "judicial_role")
    )
    participation_start: Mapped[date | None] = mapped_column(Date)
    participation_end: Mapped[date | None] = mapped_column(Date)
    outcome: Mapped[JudicialOutcome] = mapped_column(
        enum_type(JudicialOutcome, "judicial_outcome")
    )
    finality_status: Mapped[FinalityStatus] = mapped_column(
        enum_type(FinalityStatus, "case_person_finality_status")
    )
    source_document_id: Mapped[UUID] = mapped_column(ForeignKey("source_documents.id"))
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus, "case_person_review_status")
    )


class JudicialEvent(Base):
    __tablename__ = "judicial_events"

    entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    judicial_case_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("judicial_cases.entity_id")
    )
    event_type: Mapped[JudicialEventType] = mapped_column(
        enum_type(JudicialEventType, "judicial_event_type")
    )
    event_date: Mapped[date | None] = mapped_column(Date)
    original_description: Mapped[str] = mapped_column(Text)
    normalized_summary: Mapped[str | None] = mapped_column(Text)
    legal_effect: Mapped[str] = mapped_column(Text)
    source_document_id: Mapped[UUID] = mapped_column(ForeignKey("source_documents.id"))
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus, "judicial_event_review_status")
    )


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "source_key",
            "sha256",
            "retrieved_at",
            name="uq_source_snapshot_provenance_version",
        ),
        CheckConstraint("length(sha256) = 64", name="snapshot_sha256_length"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_key: Mapped[str] = mapped_column(String(120))
    operation: Mapped[str | None] = mapped_column(Text)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(Text)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        enum_type(ProcessingStatus, "processing_status")
    )
    error_summary: Mapped[str | None] = mapped_column(Text)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint("records_created >= 0", name="records_created_nonnegative"),
        CheckConstraint("records_updated >= 0", name="records_updated_nonnegative"),
        CheckConstraint("records_skipped >= 0", name="records_skipped_nonnegative"),
        CheckConstraint("records_failed >= 0", name="records_failed_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_key: Mapped[str] = mapped_column(String(120))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[IngestionStatus] = mapped_column(
        enum_type(IngestionStatus, "ingestion_status")
    )
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    run_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, default=dict
    )


class EvidenceClaim(TimestampMixin, Base):
    __tablename__ = "evidence_claims"
    __table_args__ = (
        CheckConstraint(
            "(object_entity_id IS NOT NULL AND literal_value IS NULL) OR "
            "(object_entity_id IS NULL AND literal_value IS NOT NULL)",
            name="claim_exactly_one_object",
        ),
        CheckConstraint(
            "technical_confidence IS NULL OR "
            "(technical_confidence >= 0 AND technical_confidence <= 1)",
            name="claim_confidence_range",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="claim_valid_dates",
        ),
        Index("ix_evidence_claims_subject_predicate", "subject_entity_id", "predicate"),
        Index("ix_evidence_claims_object", "object_entity_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    subject_entity_id: Mapped[UUID] = mapped_column(ForeignKey("entities.id"))
    predicate: Mapped[Predicate] = mapped_column(
        enum_type(Predicate, "evidence_predicate")
    )
    object_entity_id: Mapped[UUID | None] = mapped_column(ForeignKey("entities.id"))
    literal_value: Mapped[
        dict[str, Any] | list[Any] | str | int | float | bool | None
    ] = mapped_column(JSON_TYPE)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    evidence_level: Mapped[EvidenceLevel] = mapped_column(
        enum_type(EvidenceLevel, "evidence_level")
    )
    source_document_id: Mapped[UUID] = mapped_column(ForeignKey("source_documents.id"))
    source_excerpt: Mapped[str] = mapped_column(Text)
    source_location: Mapped[str | None] = mapped_column(Text)
    technical_confidence: Mapped[float | None] = mapped_column(Float)
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus, "claim_review_status")
    )
    publication_status: Mapped[PublicationStatus] = mapped_column(
        enum_type(PublicationStatus, "publication_status")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_claim_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evidence_claims.id")
    )


class ManualReview(Base):
    __tablename__ = "manual_reviews"
    __table_args__ = (
        CheckConstraint(
            "claim_id IS NOT NULL OR person_entity_id IS NOT NULL OR "
            "source_document_id IS NOT NULL",
            name="manual_review_has_target",
        ),
        CheckConstraint(
            "length(trim(reviewer_identifier)) > 0",
            name="manual_review_reviewer_not_empty",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    claim_id: Mapped[UUID | None] = mapped_column(ForeignKey("evidence_claims.id"))
    person_entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("persons.entity_id")
    )
    source_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_documents.id")
    )
    reviewer_identifier: Mapped[str] = mapped_column(String(255))
    decision: Mapped[ReviewDecision] = mapped_column(
        enum_type(ReviewDecision, "review_decision")
    )
    notes: Mapped[str] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_status: Mapped[ReviewStatus | None] = mapped_column(
        enum_type(ReviewStatus, "previous_review_status")
    )
    resulting_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus, "resulting_review_status")
    )
    review_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, default=dict
    )
