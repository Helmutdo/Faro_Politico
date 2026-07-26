"""Constraints y servicios ejecutados contra PostgreSQL real."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from trama_publica.db.models import (
    Entity,
    EvidenceClaim,
    Mandate,
    ManualReview,
    Person,
    PersonIdentity,
    PublicOffice,
    SourceDocument,
)
from trama_publica.domain.enums import (
    AccessStatus,
    CaseStatus,
    EntityType,
    EvidenceLevel,
    FinalityStatus,
    IdentityStatus,
    JudicialEventType,
    JudicialOutcome,
    JudicialRole,
    MandateStatus,
    OfficeLevel,
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
    create_mandate,
    create_person,
    link_person_to_case,
    publish_claim,
    register_judicial_case,
    register_judicial_event,
    submit_claim_for_review,
    withdraw_published_claim,
)

pytestmark = pytest.mark.postgres


def add_test_document(
    session: Session,
    *,
    suffix: str,
    source_type: SourceType = SourceType.OFFICIAL_DOCUMENT,
) -> SourceDocument:
    return add_document(
        session,
        SourceDocumentCreate(
            source_key=f"postgres-test-{suffix}",
            source_type=source_type,
            title=f"Documento ficticio PostgreSQL {suffix}",
            retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            sha256=suffix * 64,
            access_status=AccessStatus.AVAILABLE,
        ),
    )


def add_object_claim(
    session: Session,
    *,
    subject_id: object,
    object_id: object,
    document: SourceDocument,
    predicate: Predicate,
    evidence_level: EvidenceLevel = EvidenceLevel.OFFICIAL_DOCUMENT,
) -> EvidenceClaim:
    return create_claim(
        session,
        ClaimCreate(
            subject_entity_id=subject_id,
            predicate=predicate,
            object_entity_id=object_id,
            evidence_level=evidence_level,
            source_document_id=document.id,
            source_excerpt="Fragmento ficticio de integración PostgreSQL.",
        ),
    )


def basic_entities(session: Session) -> tuple[Person, Entity, SourceDocument]:
    person = create_person(session, canonical_name="Persona PostgreSQL Ficticia")
    target = Entity(entity_type=EntityType.ORGANIZATION)
    session.add(target)
    session.flush()
    return person, target, add_test_document(session, suffix="a")


def test_schema_uses_uuid_primary_keys_and_jsonb(clean_postgres: Engine) -> None:
    inspector = inspect(clean_postgres)
    assert (
        len(
            [
                table
                for table in inspector.get_table_names()
                if table != "alembic_version"
            ]
        )
        == 16
    )
    entity_id = next(
        column for column in inspector.get_columns("entities") if column["name"] == "id"
    )
    literal = next(
        column
        for column in inspector.get_columns("evidence_claims")
        if column["name"] == "literal_value"
    )
    assert str(entity_id["type"]) == "UUID"
    assert str(literal["type"]) == "JSONB"


def test_invalid_entity_type_is_rejected(clean_postgres: Engine) -> None:
    with pytest.raises(DBAPIError), clean_postgres.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO entities
                    (id, entity_type, created_at, updated_at)
                VALUES
                    (:id, 'arbitrary', now(), now())
                """
            ),
            {"id": uuid4()},
        )


def test_duplicate_source_identity_only_allows_one(
    clean_postgres: Engine,
) -> None:
    with Session(clean_postgres) as setup:
        person = create_person(setup, canonical_name="Persona Doble Ficticia")
        setup.commit()
        person_id = person.entity_id
    with Session(clean_postgres) as first:
        add_source_identity(
            first,
            person_entity_id=person_id,
            source_key="fuente-concurrente-ficticia",
            source_person_id="ID-1",
            displayed_name="Nombre Ficticio",
        )
        first.commit()
    with Session(clean_postgres) as second:
        second.add(
            PersonIdentity(
                person_entity_id=person_id,
                source_key="fuente-concurrente-ficticia",
                source_person_id="ID-1",
                displayed_name="Otro Nombre",
                identity_status=IdentityStatus.CANDIDATE,
            )
        )
        with pytest.raises(IntegrityError):
            second.commit()
    with Session(clean_postgres) as verification:
        assert len(verification.scalars(select(PersonIdentity)).all()) == 1


@pytest.mark.parametrize(
    ("has_object", "has_literal"),
    [(False, False), (True, True)],
)
def test_claim_requires_exactly_one_object_in_postgres(
    clean_postgres: Engine, has_object: bool, has_literal: bool
) -> None:
    with Session(clean_postgres, expire_on_commit=False) as session:
        person, target, document = basic_entities(session)
        session.add(
            EvidenceClaim(
                subject_entity_id=person.entity_id,
                predicate=Predicate.PARTNER_OF,
                object_entity_id=target.id if has_object else None,
                literal_value={"value": "fictitious"} if has_literal else None,
                evidence_level=EvidenceLevel.OFFICIAL_DOCUMENT,
                source_document_id=document.id,
                source_excerpt="Ficticio",
                review_status=ReviewStatus.EXTRACTED,
                publication_status=PublicationStatus.PRIVATE,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_range_is_enforced(
    clean_postgres: Engine, confidence: float
) -> None:
    with Session(clean_postgres) as session:
        person, target, document = basic_entities(session)
        claim = add_object_claim(
            session,
            subject_id=person.entity_id,
            object_id=target.id,
            document=document,
            predicate=Predicate.PARTNER_OF,
        )
        claim.technical_confidence = confidence
        with pytest.raises(IntegrityError):
            session.commit()


@pytest.mark.parametrize(
    ("target", "reviewer"),
    [(False, "reviewer"), (True, "   ")],
)
def test_manual_review_constraints(
    clean_postgres: Engine, target: bool, reviewer: str
) -> None:
    with Session(clean_postgres) as session:
        person = create_person(session, canonical_name="Persona Revisión Ficticia")
        session.add(
            ManualReview(
                person_entity_id=person.entity_id if target else None,
                reviewer_identifier=reviewer,
                decision="approve",
                notes="Ficticio",
                reviewed_at=datetime.now(UTC),
                resulting_status=ReviewStatus.VERIFIED,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


@pytest.mark.parametrize(
    "predicate",
    [
        "CONSPIRED_WITH",
        "CORRUPT_NETWORK",
        "CRIMINAL_ASSOCIATE",
        "IS_CORRUPT",
        "IS_CRIMINAL",
        "IS_SUSPICIOUS",
        "UNKNOWN_RELATIONSHIP",
    ],
)
def test_invalid_predicates_are_rejected_by_postgres(
    clean_postgres: Engine, predicate: str
) -> None:
    with Session(clean_postgres, expire_on_commit=False) as session:
        person, target, document = basic_entities(session)
        session.commit()
    with pytest.raises(DBAPIError), clean_postgres.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO evidence_claims (
                    id, subject_entity_id, predicate, object_entity_id,
                    evidence_level, source_document_id, source_excerpt,
                    review_status, publication_status, created_at, updated_at
                ) VALUES (
                    :id, :subject_id, :predicate, :object_id,
                    'official_document', :document_id, 'Ficticio',
                    'extracted', 'private', now(), now()
                )
                """
            ),
            {
                "id": uuid4(),
                "subject_id": person.entity_id,
                "predicate": predicate,
                "object_id": target.id,
                "document_id": document.id,
            },
        )


def test_invalid_dates_and_hash_are_rejected(clean_postgres: Engine) -> None:
    with Session(clean_postgres) as session:
        person = create_person(session, canonical_name="Persona Fecha Ficticia")
        office_entity = Entity(entity_type=EntityType.PUBLIC_OFFICE)
        session.add(office_entity)
        session.flush()
        session.add(
            PublicOffice(
                entity_id=office_entity.id,
                normalized_name="cargo",
                original_name="Cargo Ficticio",
                office_level=OfficeLevel.NATIONAL,
            )
        )
        document = add_test_document(session, suffix="b")
        mandate_entity = Entity(entity_type=EntityType.MANDATE)
        session.add(mandate_entity)
        session.flush()
        session.add(
            Mandate(
                entity_id=mandate_entity.id,
                person_entity_id=person.entity_id,
                public_office_entity_id=office_entity.id,
                start_date=date(2025, 1, 1),
                end_date=date(2024, 1, 1),
                original_title="Mandato Ficticio",
                status=MandateStatus.COMPLETED,
                source_document_id=document.id,
                review_status=ReviewStatus.PENDING_REVIEW,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

    with Session(clean_postgres) as session:
        session.add(
            SourceDocument(
                source_key="hash-invalido",
                source_type=SourceType.OFFICIAL_DOCUMENT,
                title="Documento hash inválido",
                retrieved_at=datetime.now(UTC),
                sha256="short",
                access_status=AccessStatus.AVAILABLE,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_referenced_entities_and_evidence_do_not_cascade(
    clean_postgres: Engine,
) -> None:
    with Session(clean_postgres) as session:
        person, target, document = basic_entities(session)
        add_object_claim(
            session,
            subject_id=person.entity_id,
            object_id=target.id,
            document=document,
            predicate=Predicate.PARTNER_OF,
        )
        session.commit()
        entity = session.get(Entity, person.entity_id)
        assert entity is not None
        session.delete(entity)
        with pytest.raises(IntegrityError):
            session.commit()

    with Session(clean_postgres) as session:
        document = session.scalar(select(SourceDocument))
        assert document is not None
        session.delete(document)
        with pytest.raises(IntegrityError):
            session.commit()


def test_supersedes_foreign_key(clean_postgres: Engine) -> None:
    with Session(clean_postgres) as session:
        person, target, document = basic_entities(session)
        original = add_object_claim(
            session,
            subject_id=person.entity_id,
            object_id=target.id,
            document=document,
            predicate=Predicate.PARTNER_OF,
        )
        session.flush()
        replacement = add_object_claim(
            session,
            subject_id=person.entity_id,
            object_id=target.id,
            document=document,
            predicate=Predicate.PARTNER_OF,
        )
        replacement.supersedes_claim_id = original.id
        session.commit()
        assert replacement.supersedes_claim_id == original.id

    with Session(clean_postgres) as session:
        claim = session.scalar(select(EvidenceClaim))
        assert claim is not None
        claim.supersedes_claim_id = uuid4()
        with pytest.raises(IntegrityError):
            session.commit()


def test_failed_transaction_leaves_no_partial_data(clean_postgres: Engine) -> None:
    with Session(clean_postgres) as session:
        create_person(session, canonical_name="Persona Transacción Ficticia")
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    """
                    INSERT INTO entities
                        (id, entity_type, created_at, updated_at)
                    VALUES (:id, 'invalid', now(), now())
                    """
                ),
                {"id": uuid4()},
            )
        session.rollback()
    with Session(clean_postgres) as verification:
        assert verification.scalar(select(Person).limit(1)) is None


def test_domain_service_full_lifecycle(clean_postgres: Engine) -> None:
    with Session(clean_postgres, expire_on_commit=False) as session:
        document = add_test_document(session, suffix="c")
        person = create_person(session, canonical_name="Persona Servicio Ficticia")
        add_source_identity(
            session,
            person_entity_id=person.entity_id,
            source_key="servicio-ficticio",
            source_person_id="PERSON-1",
            displayed_name="Persona Servicio Ficticia",
        )
        office_entity = Entity(entity_type=EntityType.PUBLIC_OFFICE)
        session.add(office_entity)
        session.flush()
        session.add(
            PublicOffice(
                entity_id=office_entity.id,
                normalized_name="cargo ficticio",
                original_name="Cargo Ficticio",
                office_level=OfficeLevel.NATIONAL,
            )
        )
        create_mandate(
            session,
            person_entity_id=person.entity_id,
            public_office_entity_id=office_entity.id,
            start_date=date(2022, 1, 1),
            original_title="Mandato Ficticio",
            status=MandateStatus.ELECTED,
            source_document_id=document.id,
        )
        case = register_judicial_case(
            session,
            case_identifier="SERVICIO-FICTICIO-1",
            court_name="Tribunal Ficticio",
            source_document_id=document.id,
        )
        link_person_to_case(
            session,
            judicial_case_entity_id=case.entity_id,
            person_entity_id=person.entity_id,
            original_role="participante",
            normalized_role=JudicialRole.MENTIONED,
            outcome=JudicialOutcome.NOT_APPLICABLE,
            finality_status=FinalityStatus.NOT_APPLICABLE,
            source_document_id=document.id,
        )
        register_judicial_event(
            session,
            judicial_case_entity_id=case.entity_id,
            event_type=JudicialEventType.FILING,
            original_description="Evento ficticio",
            legal_effect="Sin efecto real",
            source_document_id=document.id,
        )
        claim = add_object_claim(
            session,
            subject_id=person.entity_id,
            object_id=case.entity_id,
            document=document,
            predicate=Predicate.PARTICIPATED_IN_CASE,
        )
        submit_claim_for_review(session, claim)
        approve_claim(
            session,
            claim,
            reviewer_identifier="postgres-reviewer",
            notes="Revisión ficticia",
        )
        publish_claim(session, claim)
        replacement_command = ClaimCreate(
            subject_entity_id=person.entity_id,
            predicate=Predicate.PARTICIPATED_IN_CASE,
            object_entity_id=case.entity_id,
            evidence_level=EvidenceLevel.OFFICIAL_DOCUMENT,
            source_document_id=document.id,
            source_excerpt="Fragmento ficticio corregido.",
        )
        replacement = correct_claim(
            session,
            claim,
            replacement_command,
            reviewer_identifier="postgres-reviewer",
            notes="Corrección ficticia",
        )
        approve_claim(
            session,
            replacement,
            reviewer_identifier="postgres-reviewer",
            notes="Revisión de reemplazo",
        )
        publish_claim(session, replacement)
        withdraw_published_claim(
            session,
            replacement,
            reviewer_identifier="postgres-reviewer",
            notes="Retiro ficticio",
        )
        session.commit()

        assert claim.review_status is ReviewStatus.CORRECTED
        assert replacement.supersedes_claim_id == claim.id
        assert replacement.publication_status is PublicationStatus.WITHDRAWN
        assert len(session.scalars(select(ManualReview)).all()) == 4


def conviction_setup(
    session: Session,
    *,
    source_type: SourceType,
    outcome: JudicialOutcome | None,
    finality: FinalityStatus = FinalityStatus.FINAL,
) -> EvidenceClaim:
    person = create_person(session, canonical_name="Persona Condena Ficticia")
    document = add_test_document(session, suffix="d", source_type=source_type)
    case = register_judicial_case(
        session,
        case_identifier=f"CONDENA-{uuid4()}",
        court_name="Tribunal Ficticio",
        source_document_id=document.id,
        current_status=CaseStatus.DECIDED,
        finality_status=finality,
    )
    if outcome is not None:
        link_person_to_case(
            session,
            judicial_case_entity_id=case.entity_id,
            person_entity_id=person.entity_id,
            original_role="rol ficticio",
            normalized_role=JudicialRole.CONVICTED_PERSON,
            outcome=outcome,
            finality_status=finality,
            source_document_id=document.id,
        )
    level = (
        EvidenceLevel.MEDIA_REFERENCE
        if source_type is SourceType.MEDIA_REFERENCE
        else EvidenceLevel.FINAL_JUDICIAL_DECISION
    )
    claim = add_object_claim(
        session,
        subject_id=person.entity_id,
        object_id=case.entity_id,
        document=document,
        predicate=Predicate.CONVICTED_IN,
        evidence_level=level,
    )
    submit_claim_for_review(session, claim)
    return claim


@pytest.mark.parametrize(
    ("source_type", "outcome", "finality"),
    [
        (SourceType.MEDIA_REFERENCE, JudicialOutcome.CONVICTED, FinalityStatus.FINAL),
        (SourceType.FINAL_JUDICIAL_DECISION, None, FinalityStatus.FINAL),
        (
            SourceType.FINAL_JUDICIAL_DECISION,
            JudicialOutcome.ACQUITTED,
            FinalityStatus.FINAL,
        ),
        (
            SourceType.FINAL_JUDICIAL_DECISION,
            JudicialOutcome.CONVICTED,
            FinalityStatus.PENDING,
        ),
    ],
)
def test_invalid_convictions_cannot_verify(
    clean_postgres: Engine,
    source_type: SourceType,
    outcome: JudicialOutcome | None,
    finality: FinalityStatus,
) -> None:
    with Session(clean_postgres) as session:
        claim = conviction_setup(
            session,
            source_type=source_type,
            outcome=outcome,
            finality=finality,
        )
        with pytest.raises(DomainValidationError):
            approve_claim(
                session,
                claim,
                reviewer_identifier="postgres-reviewer",
                notes="No procede",
            )
        assert claim.review_status is ReviewStatus.PENDING_REVIEW


def test_conviction_requires_nonempty_human_reviewer(
    clean_postgres: Engine,
) -> None:
    with Session(clean_postgres) as session:
        claim = conviction_setup(
            session,
            source_type=SourceType.FINAL_JUDICIAL_DECISION,
            outcome=JudicialOutcome.CONVICTED,
        )
        with pytest.raises(DomainValidationError):
            approve_claim(
                session,
                claim,
                reviewer_identifier=" ",
                notes="Sin revisor",
            )


def test_accusation_and_acquittal_coexist(clean_postgres: Engine) -> None:
    with Session(clean_postgres) as session:
        person = create_person(session, canonical_name="Persona Absuelta Ficticia")
        filing = add_test_document(
            session, suffix="e", source_type=SourceType.JUDICIAL_FILING
        )
        decision = add_test_document(
            session, suffix="f", source_type=SourceType.FINAL_JUDICIAL_DECISION
        )
        case = register_judicial_case(
            session,
            case_identifier="ABSOLUCION-FICTICIA",
            court_name="Tribunal Ficticio",
            source_document_id=filing.id,
        )
        add_object_claim(
            session,
            subject_id=person.entity_id,
            object_id=case.entity_id,
            document=filing,
            predicate=Predicate.ACCUSED_IN,
            evidence_level=EvidenceLevel.JUDICIAL_FILING,
        )
        add_object_claim(
            session,
            subject_id=person.entity_id,
            object_id=case.entity_id,
            document=decision,
            predicate=Predicate.ACQUITTED_IN,
            evidence_level=EvidenceLevel.FINAL_JUDICIAL_DECISION,
        )
        session.commit()
        predicates = set(session.scalars(select(EvidenceClaim.predicate)).all())
        assert predicates == {Predicate.ACCUSED_IN, Predicate.ACQUITTED_IN}
