"""Pruebas del dominio con datos totalmente ficticios."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from trama_publica.db.base import Base
from trama_publica.db.models import (
    Entity,
    EvidenceClaim,
    ManualReview,
    Organization,
    SourceDocument,
)
from trama_publica.domain.enums import (
    AccessStatus,
    CaseStatus,
    EntityType,
    EvidenceLevel,
    FinalityStatus,
    JudicialOutcome,
    JudicialRole,
    OrganizationType,
    Predicate,
    PublicationStatus,
    ReviewStatus,
    SourceType,
)
from trama_publica.domain.schemas import ClaimCreate, SourceDocumentCreate
from trama_publica.domain.services import (
    DomainValidationError,
    add_document,
    add_source_identity,
    approve_claim,
    correct_claim,
    create_claim,
    create_person,
    link_person_to_case,
    publish_claim,
    register_judicial_case,
    reject_claim,
    submit_claim_for_review,
    withdraw_published_claim,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
        del connection_record
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database_session:
        yield database_session


def document(
    session: Session,
    source_type: SourceType = SourceType.OFFICIAL_DOCUMENT,
    suffix: str = "a",
) -> SourceDocument:
    return add_document(
        session,
        SourceDocumentCreate(
            source_key=f"fictitious-source-{suffix}",
            source_type=source_type,
            title=f"Documento ficticio {suffix}",
            retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            sha256=(suffix[0] * 64),
            access_status=AccessStatus.AVAILABLE,
        ),
    )


def object_claim(
    *,
    person_id: Any,
    object_id: Any,
    document_id: Any,
    predicate: Predicate,
    level: EvidenceLevel = EvidenceLevel.OFFICIAL_DOCUMENT,
) -> ClaimCreate:
    return ClaimCreate(
        subject_entity_id=person_id,
        predicate=predicate,
        object_entity_id=object_id,
        evidence_level=level,
        source_document_id=document_id,
        source_excerpt="Fragmento completamente ficticio.",
    )


def test_claim_requires_exactly_one_object() -> None:
    with pytest.raises(ValidationError):
        ClaimCreate(
            subject_entity_id="00000000-0000-0000-0000-000000000001",
            predicate=Predicate.HELD_OFFICE,
            evidence_level=EvidenceLevel.OFFICIAL_DOCUMENT,
            source_document_id="00000000-0000-0000-0000-000000000002",
            source_excerpt="Ficticio",
        )


def test_equal_names_do_not_merge_people(session: Session) -> None:
    first = create_person(session, canonical_name="Nombre Ficticio Repetido")
    second = create_person(session, canonical_name="Nombre Ficticio Repetido")
    add_source_identity(
        session,
        person_entity_id=first.entity_id,
        source_key="fuente-ficticia-a",
        source_person_id="1",
        displayed_name="Nombre Ficticio Repetido",
    )
    add_source_identity(
        session,
        person_entity_id=second.entity_id,
        source_key="fuente-ficticia-b",
        source_person_id="1",
        displayed_name="Nombre Ficticio Repetido",
    )

    assert first.entity_id != second.entity_id


@pytest.mark.parametrize(
    "predicate",
    [
        "CONSPIRED_WITH",
        "CORRUPT_NETWORK",
        "CRIMINAL_ASSOCIATE",
        "IS_CORRUPT",
        "IS_CRIMINAL",
        "IS_SUSPICIOUS",
    ],
)
def test_prohibited_predicates_are_rejected(predicate: str) -> None:
    with pytest.raises(ValidationError):
        ClaimCreate(
            subject_entity_id="00000000-0000-0000-0000-000000000001",
            predicate=predicate,
            object_entity_id="00000000-0000-0000-0000-000000000002",
            evidence_level=EvidenceLevel.OFFICIAL_DOCUMENT,
            source_document_id="00000000-0000-0000-0000-000000000003",
            source_excerpt="Ficticio",
        )


def test_discovered_cannot_publish_and_private_cannot_publish(
    session: Session,
) -> None:
    person = create_person(session, canonical_name="Persona Ficticia A")
    organization = Entity(entity_type=EntityType.ORGANIZATION)
    session.add(organization)
    session.flush()
    doc = document(session)
    claim = create_claim(
        session,
        object_claim(
            person_id=person.entity_id,
            object_id=organization.id,
            document_id=doc.id,
            predicate=Predicate.MEMBER_OF_ORGANIZATION,
        ),
    )

    with pytest.raises(DomainValidationError):
        publish_claim(session, claim)

    assert claim.publication_status is PublicationStatus.PRIVATE


def test_discovered_claim_can_be_submitted_for_review(session: Session) -> None:
    person = create_person(session, canonical_name="Persona Ficticia A")
    organization = Entity(entity_type=EntityType.ORGANIZATION)
    session.add(organization)
    session.flush()
    doc = document(session)
    command = object_claim(
        person_id=person.entity_id,
        object_id=organization.id,
        document_id=doc.id,
        predicate=Predicate.MEMBER_OF_ORGANIZATION,
    ).model_copy(update={"review_status": ReviewStatus.DISCOVERED})
    claim = create_claim(session, command)

    submit_claim_for_review(session, claim)

    assert claim.review_status is ReviewStatus.PENDING_REVIEW
    assert claim.publication_status is PublicationStatus.REVIEW_ONLY


def test_allowed_review_publish_withdraw_flow(session: Session) -> None:
    person = create_person(session, canonical_name="Persona Ficticia A")
    organization = Entity(entity_type=EntityType.ORGANIZATION)
    session.add(organization)
    session.flush()
    doc = document(session)
    claim = create_claim(
        session,
        object_claim(
            person_id=person.entity_id,
            object_id=organization.id,
            document_id=doc.id,
            predicate=Predicate.SHAREHOLDER_OF,
        ),
    )

    submit_claim_for_review(session, claim)
    approve_claim(
        session,
        claim,
        reviewer_identifier="reviewer-local",
        notes="Revisión ficticia.",
    )
    publish_claim(session, claim)
    withdraw_published_claim(
        session,
        claim,
        reviewer_identifier="reviewer-local",
        notes="Retiro ficticio.",
    )

    assert claim.review_status is ReviewStatus.ARCHIVED
    assert claim.publication_status is PublicationStatus.WITHDRAWN


def test_rejected_claim_cannot_be_published(session: Session) -> None:
    person = create_person(session, canonical_name="Persona Ficticia A")
    organization = Entity(entity_type=EntityType.ORGANIZATION)
    session.add(organization)
    session.flush()
    doc = document(session)
    claim = create_claim(
        session,
        object_claim(
            person_id=person.entity_id,
            object_id=organization.id,
            document_id=doc.id,
            predicate=Predicate.DIRECTOR_OF,
        ),
    )
    submit_claim_for_review(session, claim)
    reject_claim(
        session,
        claim,
        reviewer_identifier="reviewer-local",
        notes="Evidencia ficticia insuficiente.",
    )

    with pytest.raises(DomainValidationError):
        publish_claim(session, claim)


def test_media_cannot_verify_convicted_claim(session: Session) -> None:
    person = create_person(session, canonical_name="Persona Ficticia B")
    media = document(session, SourceType.MEDIA_REFERENCE, "b")
    case = register_judicial_case(
        session,
        case_identifier="CAUSA-FICTICIA-2",
        court_name="Tribunal Ficticio",
        source_document_id=media.id,
        current_status=CaseStatus.DECIDED,
        finality_status=FinalityStatus.FINAL,
    )
    link_person_to_case(
        session,
        judicial_case_entity_id=case.entity_id,
        person_entity_id=person.entity_id,
        original_role="rol ficticio",
        normalized_role=JudicialRole.CONVICTED_PERSON,
        outcome=JudicialOutcome.CONVICTED,
        finality_status=FinalityStatus.FINAL,
        source_document_id=media.id,
    )
    claim = create_claim(
        session,
        object_claim(
            person_id=person.entity_id,
            object_id=case.entity_id,
            document_id=media.id,
            predicate=Predicate.CONVICTED_IN,
            level=EvidenceLevel.MEDIA_REFERENCE,
        ),
    )
    submit_claim_for_review(session, claim)

    with pytest.raises(DomainValidationError):
        approve_claim(
            session,
            claim,
            reviewer_identifier="reviewer-local",
            notes="No procede.",
        )


def test_final_conviction_requires_matching_participation_and_human_review(
    session: Session,
) -> None:
    person = create_person(session, canonical_name="Persona Ficticia B")
    decision = document(session, SourceType.FINAL_JUDICIAL_DECISION, "c")
    case = register_judicial_case(
        session,
        case_identifier="CAUSA-FICTICIA-3",
        court_name="Tribunal Ficticio",
        source_document_id=decision.id,
        current_status=CaseStatus.DECIDED,
        finality_status=FinalityStatus.FINAL,
    )
    link_person_to_case(
        session,
        judicial_case_entity_id=case.entity_id,
        person_entity_id=person.entity_id,
        original_role="condenado ficticio",
        normalized_role=JudicialRole.CONVICTED_PERSON,
        outcome=JudicialOutcome.CONVICTED,
        finality_status=FinalityStatus.FINAL,
        source_document_id=decision.id,
    )
    claim = create_claim(
        session,
        object_claim(
            person_id=person.entity_id,
            object_id=case.entity_id,
            document_id=decision.id,
            predicate=Predicate.CONVICTED_IN,
            level=EvidenceLevel.FINAL_JUDICIAL_DECISION,
        ),
    )
    submit_claim_for_review(session, claim)
    approve_claim(
        session,
        claim,
        reviewer_identifier="reviewer-local",
        notes="Decisión ficticia revisada.",
    )

    assert claim.review_status is ReviewStatus.VERIFIED
    assert session.scalar(select(ManualReview).where(ManualReview.claim_id == claim.id))


def test_accusation_and_acquittal_are_both_preserved(session: Session) -> None:
    person = create_person(session, canonical_name="Persona Ficticia A")
    filing = document(session, SourceType.JUDICIAL_FILING, "d")
    decision = document(session, SourceType.FINAL_JUDICIAL_DECISION, "e")
    case = register_judicial_case(
        session,
        case_identifier="CAUSA-FICTICIA-1",
        court_name="Tribunal Ficticio",
        source_document_id=filing.id,
    )
    link_person_to_case(
        session,
        judicial_case_entity_id=case.entity_id,
        person_entity_id=person.entity_id,
        original_role="acusada ficticia",
        normalized_role=JudicialRole.ACCUSED,
        outcome=JudicialOutcome.ACQUITTED,
        finality_status=FinalityStatus.FINAL,
        source_document_id=decision.id,
    )
    accused = create_claim(
        session,
        object_claim(
            person_id=person.entity_id,
            object_id=case.entity_id,
            document_id=filing.id,
            predicate=Predicate.ACCUSED_IN,
            level=EvidenceLevel.JUDICIAL_FILING,
        ),
    )
    acquitted = create_claim(
        session,
        object_claim(
            person_id=person.entity_id,
            object_id=case.entity_id,
            document_id=decision.id,
            predicate=Predicate.ACQUITTED_IN,
            level=EvidenceLevel.FINAL_JUDICIAL_DECISION,
        ),
    )
    session.flush()

    claims = session.scalars(
        select(EvidenceClaim).where(EvidenceClaim.subject_entity_id == person.entity_id)
    ).all()
    assert {item.predicate for item in claims} == {
        Predicate.ACCUSED_IN,
        Predicate.ACQUITTED_IN,
    }
    assert all(item.predicate is not Predicate.CONVICTED_IN for item in claims)
    assert accused.id != acquitted.id


def test_correction_creates_new_claim_without_deleting_original(
    session: Session,
) -> None:
    person = create_person(session, canonical_name="Persona Ficticia A")
    organization_entity = Entity(entity_type=EntityType.ORGANIZATION)
    session.add(organization_entity)
    session.flush()
    organization = Organization(
        entity_id=organization_entity.id,
        organization_type=OrganizationType.COMPANY,
        canonical_name="Empresa Ficticia Uno",
    )
    session.add(organization)
    doc = document(session, suffix="f")
    command = object_claim(
        person_id=person.entity_id,
        object_id=organization.entity_id,
        document_id=doc.id,
        predicate=Predicate.PARTNER_OF,
    )
    claim = create_claim(session, command)
    submit_claim_for_review(session, claim)
    approve_claim(
        session,
        claim,
        reviewer_identifier="reviewer-local",
        notes="Aprobación ficticia.",
    )
    replacement = correct_claim(
        session,
        claim,
        command,
        reviewer_identifier="reviewer-local",
        notes="Corrección ficticia.",
    )

    assert session.get(EvidenceClaim, claim.id) is claim
    assert claim.review_status is ReviewStatus.CORRECTED
    assert replacement.supersedes_claim_id == claim.id


def test_database_constraints_prevent_empty_manual_review_target(
    session: Session,
) -> None:
    session.add(
        ManualReview(
            reviewer_identifier="reviewer-local",
            decision="approve",
            notes="Ficticio",
            reviewed_at=datetime.now(UTC),
            resulting_status=ReviewStatus.VERIFIED,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_database_claim_object_constraint_is_enforced(session: Session) -> None:
    person = create_person(session, canonical_name="Persona Ficticia A")
    organization = Entity(entity_type=EntityType.ORGANIZATION)
    session.add(organization)
    session.flush()
    doc = document(session)
    session.add(
        EvidenceClaim(
            subject_entity_id=person.entity_id,
            predicate=Predicate.PARTNER_OF,
            object_entity_id=organization.id,
            literal_value={"also": "present"},
            evidence_level=EvidenceLevel.OFFICIAL_DOCUMENT,
            source_document_id=doc.id,
            source_excerpt="Ficticio",
            review_status=ReviewStatus.EXTRACTED,
            publication_status=PublicationStatus.PRIVATE,
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()


def test_historical_evidence_is_not_cascade_deleted(session: Session) -> None:
    person = create_person(session, canonical_name="Persona Ficticia A")
    organization = Entity(entity_type=EntityType.ORGANIZATION)
    session.add(organization)
    session.flush()
    doc = document(session)
    create_claim(
        session,
        object_claim(
            person_id=person.entity_id,
            object_id=organization.id,
            document_id=doc.id,
            predicate=Predicate.PARTNER_OF,
        ),
    )
    session.delete(doc)

    with pytest.raises(IntegrityError):
        session.flush()


def test_technical_confidence_never_auto_publishes(session: Session) -> None:
    person = create_person(session, canonical_name="Persona Ficticia A")
    organization = Entity(entity_type=EntityType.ORGANIZATION)
    session.add(organization)
    session.flush()
    doc = document(session)
    command = object_claim(
        person_id=person.entity_id,
        object_id=organization.id,
        document_id=doc.id,
        predicate=Predicate.MEMBER_OF_ORGANIZATION,
    ).model_copy(update={"technical_confidence": 1.0})
    claim = create_claim(session, command)

    assert claim.review_status is ReviewStatus.EXTRACTED
    assert claim.publication_status is PublicationStatus.PRIVATE
    with pytest.raises(DomainValidationError):
        publish_claim(session, claim)
