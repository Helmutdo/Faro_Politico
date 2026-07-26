"""Servicios explícitos y transiciones del núcleo histórico."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from trama_publica.db.base import utc_now
from trama_publica.db.models import (
    Entity,
    EvidenceClaim,
    JudicialCase,
    JudicialCasePerson,
    JudicialEvent,
    Mandate,
    ManualReview,
    Person,
    PersonIdentity,
    SourceDocument,
)
from trama_publica.domain.enums import (
    CaseStatus,
    EntityType,
    FinalityStatus,
    IdentityStatus,
    JudicialEventType,
    JudicialOutcome,
    JudicialRole,
    MandateStatus,
    Predicate,
    PublicationStatus,
    ReviewDecision,
    ReviewStatus,
    SourceType,
)
from trama_publica.domain.schemas import ClaimCreate, SourceDocumentCreate


class DomainValidationError(ValueError):
    """La operación viola una regla explícita del dominio."""


def _entity(session: Session, entity_type: EntityType) -> Entity:
    entity = Entity(entity_type=entity_type)
    session.add(entity)
    session.flush()
    return entity


def create_person(
    session: Session,
    *,
    canonical_name: str,
    given_names: str | None = None,
    paternal_surname: str | None = None,
    maternal_surname: str | None = None,
    birth_date: date | None = None,
    death_date: date | None = None,
    nationality: str | None = None,
    biography_summary: str | None = None,
) -> Person:
    if not canonical_name.strip():
        raise DomainValidationError("canonical_name cannot be empty")
    entity = _entity(session, EntityType.PERSON)
    person = Person(
        entity_id=entity.id,
        canonical_name=canonical_name,
        given_names=given_names,
        paternal_surname=paternal_surname,
        maternal_surname=maternal_surname,
        birth_date=birth_date,
        death_date=death_date,
        nationality=nationality,
        biography_summary=biography_summary,
        identity_review_status=ReviewStatus.PENDING_REVIEW,
    )
    session.add(person)
    session.flush()
    return person


def add_source_identity(
    session: Session,
    *,
    person_entity_id: UUID,
    source_key: str,
    source_person_id: str,
    displayed_name: str,
    status: IdentityStatus = IdentityStatus.CANDIDATE,
    source_document_id: UUID | None = None,
) -> PersonIdentity:
    identity = PersonIdentity(
        person_entity_id=person_entity_id,
        source_key=source_key,
        source_person_id=source_person_id,
        displayed_name=displayed_name,
        identity_status=status,
        source_document_id=source_document_id,
    )
    session.add(identity)
    session.flush()
    return identity


def add_document(session: Session, command: SourceDocumentCreate) -> SourceDocument:
    document = SourceDocument(
        source_key=command.source_key,
        source_type=command.source_type,
        title=command.title,
        original_url=command.original_url,
        issuing_body=command.issuing_body,
        publication_date=command.publication_date,
        document_date=command.document_date,
        retrieved_at=command.retrieved_at,
        storage_path=command.storage_path,
        sha256=command.sha256.lower(),
        mime_type=command.mime_type,
        language=command.language,
        access_status=command.access_status,
        document_metadata=command.metadata,
    )
    session.add(document)
    session.flush()
    return document


def create_mandate(
    session: Session,
    *,
    person_entity_id: UUID,
    public_office_entity_id: UUID,
    start_date: date,
    original_title: str,
    status: MandateStatus,
    source_document_id: UUID,
    electoral_territory_entity_id: UUID | None = None,
    organization_entity_id: UUID | None = None,
    end_date: date | None = None,
) -> Mandate:
    if end_date is not None and end_date < start_date:
        raise DomainValidationError("mandate end_date precedes start_date")
    entity = _entity(session, EntityType.MANDATE)
    mandate = Mandate(
        entity_id=entity.id,
        person_entity_id=person_entity_id,
        public_office_entity_id=public_office_entity_id,
        electoral_territory_entity_id=electoral_territory_entity_id,
        organization_entity_id=organization_entity_id,
        start_date=start_date,
        end_date=end_date,
        original_title=original_title,
        status=status,
        source_document_id=source_document_id,
        review_status=ReviewStatus.PENDING_REVIEW,
    )
    session.add(mandate)
    session.flush()
    return mandate


def register_judicial_case(
    session: Session,
    *,
    case_identifier: str,
    court_name: str,
    source_document_id: UUID,
    current_status: CaseStatus = CaseStatus.UNKNOWN,
    finality_status: FinalityStatus = FinalityStatus.UNKNOWN,
    jurisdiction: str | None = None,
    case_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    result_summary: str | None = None,
) -> JudicialCase:
    entity = _entity(session, EntityType.JUDICIAL_CASE)
    case = JudicialCase(
        entity_id=entity.id,
        case_identifier=case_identifier,
        court_name=court_name,
        jurisdiction=jurisdiction,
        case_type=case_type,
        start_date=start_date,
        end_date=end_date,
        current_status=current_status,
        result_summary=result_summary,
        finality_status=finality_status,
        source_document_id=source_document_id,
        review_status=ReviewStatus.PENDING_REVIEW,
    )
    session.add(case)
    session.flush()
    return case


def link_person_to_case(
    session: Session,
    *,
    judicial_case_entity_id: UUID,
    person_entity_id: UUID,
    original_role: str,
    normalized_role: JudicialRole,
    outcome: JudicialOutcome,
    finality_status: FinalityStatus,
    source_document_id: UUID,
) -> JudicialCasePerson:
    participation = JudicialCasePerson(
        judicial_case_entity_id=judicial_case_entity_id,
        person_entity_id=person_entity_id,
        original_role=original_role,
        normalized_role=normalized_role,
        outcome=outcome,
        finality_status=finality_status,
        source_document_id=source_document_id,
        review_status=ReviewStatus.PENDING_REVIEW,
    )
    session.add(participation)
    session.flush()
    return participation


def register_judicial_event(
    session: Session,
    *,
    judicial_case_entity_id: UUID,
    event_type: JudicialEventType,
    original_description: str,
    legal_effect: str,
    source_document_id: UUID,
    event_date: date | None = None,
    normalized_summary: str | None = None,
) -> JudicialEvent:
    entity = _entity(session, EntityType.JUDICIAL_EVENT)
    event = JudicialEvent(
        entity_id=entity.id,
        judicial_case_entity_id=judicial_case_entity_id,
        event_type=event_type,
        event_date=event_date,
        original_description=original_description,
        normalized_summary=normalized_summary,
        legal_effect=legal_effect,
        source_document_id=source_document_id,
        review_status=ReviewStatus.PENDING_REVIEW,
    )
    session.add(event)
    session.flush()
    return event


def create_claim(session: Session, command: ClaimCreate) -> EvidenceClaim:
    claim = EvidenceClaim(**command.model_dump())
    session.add(claim)
    session.flush()
    return claim


def submit_claim_for_review(session: Session, claim: EvidenceClaim) -> None:
    if claim.review_status not in {ReviewStatus.DISCOVERED, ReviewStatus.EXTRACTED}:
        raise DomainValidationError("claim cannot be submitted from current status")
    claim.review_status = ReviewStatus.PENDING_REVIEW
    claim.publication_status = PublicationStatus.REVIEW_ONLY
    session.flush()


def _review(
    session: Session,
    *,
    claim: EvidenceClaim,
    reviewer_identifier: str,
    decision: ReviewDecision,
    resulting_status: ReviewStatus,
    notes: str,
) -> ManualReview:
    if not reviewer_identifier.strip():
        raise DomainValidationError("reviewer_identifier cannot be empty")
    previous = claim.review_status
    review = ManualReview(
        claim_id=claim.id,
        reviewer_identifier=reviewer_identifier,
        decision=decision,
        notes=notes,
        reviewed_at=utc_now(),
        previous_status=previous,
        resulting_status=resulting_status,
    )
    session.add(review)
    return review


def _validate_conviction(session: Session, claim: EvidenceClaim) -> None:
    if claim.predicate is not Predicate.CONVICTED_IN:
        return
    document = session.get(SourceDocument, claim.source_document_id)
    if document is None or document.source_type not in {
        SourceType.JUDICIAL_DECISION,
        SourceType.FINAL_JUDICIAL_DECISION,
    }:
        raise DomainValidationError("CONVICTED_IN requires a judicial decision source")
    if claim.object_entity_id is None:
        raise DomainValidationError("CONVICTED_IN requires a judicial case object")
    participation = session.scalar(
        select(JudicialCasePerson).where(
            JudicialCasePerson.person_entity_id == claim.subject_entity_id,
            JudicialCasePerson.judicial_case_entity_id == claim.object_entity_id,
            JudicialCasePerson.outcome == JudicialOutcome.CONVICTED,
        )
    )
    if participation is None:
        raise DomainValidationError(
            "CONVICTED_IN requires a corresponding convicted participation"
        )
    if (
        document.source_type is SourceType.FINAL_JUDICIAL_DECISION
        and participation.finality_status is not FinalityStatus.FINAL
    ):
        raise DomainValidationError(
            "final conviction source requires final participation status"
        )
    if participation.finality_status is FinalityStatus.REVOKED:
        raise DomainValidationError("revoked participation cannot verify conviction")


def approve_claim(
    session: Session,
    claim: EvidenceClaim,
    *,
    reviewer_identifier: str,
    notes: str,
) -> ManualReview:
    if claim.review_status is not ReviewStatus.PENDING_REVIEW:
        raise DomainValidationError("only pending claims can be approved")
    _validate_conviction(session, claim)
    review = _review(
        session,
        claim=claim,
        reviewer_identifier=reviewer_identifier,
        decision=ReviewDecision.APPROVE,
        resulting_status=ReviewStatus.VERIFIED,
        notes=notes,
    )
    claim.review_status = ReviewStatus.VERIFIED
    claim.publication_status = PublicationStatus.PUBLISHABLE
    claim.reviewed_at = review.reviewed_at
    session.flush()
    return review


def reject_claim(
    session: Session,
    claim: EvidenceClaim,
    *,
    reviewer_identifier: str,
    notes: str,
) -> ManualReview:
    if claim.review_status is not ReviewStatus.PENDING_REVIEW:
        raise DomainValidationError("only pending claims can be rejected")
    review = _review(
        session,
        claim=claim,
        reviewer_identifier=reviewer_identifier,
        decision=ReviewDecision.REJECT,
        resulting_status=ReviewStatus.REJECTED,
        notes=notes,
    )
    claim.review_status = ReviewStatus.REJECTED
    claim.publication_status = PublicationStatus.PRIVATE
    claim.reviewed_at = review.reviewed_at
    session.flush()
    return review


def publish_claim(session: Session, claim: EvidenceClaim) -> None:
    if (
        claim.review_status is not ReviewStatus.VERIFIED
        or claim.publication_status is not PublicationStatus.PUBLISHABLE
    ):
        raise DomainValidationError("only verified publishable claims can publish")
    claim.publication_status = PublicationStatus.PUBLISHED
    claim.published_at = utc_now()
    session.flush()


def correct_claim(
    session: Session,
    claim: EvidenceClaim,
    replacement: ClaimCreate,
    *,
    reviewer_identifier: str,
    notes: str,
) -> EvidenceClaim:
    if claim.review_status not in {ReviewStatus.VERIFIED, ReviewStatus.CORRECTED}:
        raise DomainValidationError("only reviewed claims can be corrected")
    _review(
        session,
        claim=claim,
        reviewer_identifier=reviewer_identifier,
        decision=ReviewDecision.CORRECT,
        resulting_status=ReviewStatus.CORRECTED,
        notes=notes,
    )
    claim.review_status = ReviewStatus.CORRECTED
    claim.publication_status = PublicationStatus.WITHDRAWN
    claim.corrected_at = utc_now()
    replacement_claim = EvidenceClaim(
        **replacement.model_dump(), supersedes_claim_id=claim.id
    )
    replacement_claim.review_status = ReviewStatus.PENDING_REVIEW
    replacement_claim.publication_status = PublicationStatus.REVIEW_ONLY
    session.add(replacement_claim)
    session.flush()
    return replacement_claim


def withdraw_published_claim(
    session: Session,
    claim: EvidenceClaim,
    *,
    reviewer_identifier: str,
    notes: str,
) -> ManualReview:
    if claim.publication_status is not PublicationStatus.PUBLISHED:
        raise DomainValidationError("only published claims can be withdrawn")
    review = _review(
        session,
        claim=claim,
        reviewer_identifier=reviewer_identifier,
        decision=ReviewDecision.ARCHIVE,
        resulting_status=ReviewStatus.ARCHIVED,
        notes=notes,
    )
    claim.review_status = ReviewStatus.ARCHIVED
    claim.publication_status = PublicationStatus.WITHDRAWN
    session.flush()
    return review
