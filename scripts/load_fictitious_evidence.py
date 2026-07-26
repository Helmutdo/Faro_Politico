#!/usr/bin/env python3
"""Carga un dossier demostrativo completamente ficticio."""

from datetime import UTC, date, datetime

from sqlalchemy import select
from trama_publica.db.models import (
    Entity,
    Organization,
    PublicOffice,
    SourceDocument,
)
from trama_publica.db.session import SessionLocal
from trama_publica.domain.enums import (
    AccessStatus,
    CaseStatus,
    EntityType,
    EvidenceLevel,
    FinalityStatus,
    JudicialOutcome,
    JudicialRole,
    MandateStatus,
    OfficeLevel,
    OrganizationType,
    Predicate,
    SourceType,
)
from trama_publica.domain.schemas import ClaimCreate, SourceDocumentCreate
from trama_publica.domain.services import (
    add_document,
    approve_claim,
    create_claim,
    create_mandate,
    create_person,
    link_person_to_case,
    register_judicial_case,
    submit_claim_for_review,
)

FIXTURE_SOURCE = "fixture-ficticio-v0"
REVIEWER = "fixture-reviewer-local"


def source_document(
    *,
    title: str,
    suffix: str,
    source_type: SourceType,
) -> SourceDocumentCreate:
    return SourceDocumentCreate(
        source_key=FIXTURE_SOURCE,
        source_type=source_type,
        title=title,
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        document_date=date(2025, 1, 1),
        storage_path=f"data/fixtures/fictitious/{suffix}.txt",
        sha256=suffix * 64,
        access_status=AccessStatus.AVAILABLE,
        metadata={"fictitious": True, "production_source": False},
    )


def run() -> None:
    with SessionLocal.begin() as session:
        existing = session.scalar(
            select(SourceDocument).where(SourceDocument.source_key == FIXTURE_SOURCE)
        )
        if existing is not None:
            print("fixture ficticio ya cargado; no se hicieron cambios")
            return

        mandate_document = add_document(
            session,
            source_document(
                title="Registro ficticio de mandatos",
                suffix="a",
                source_type=SourceType.OFFICIAL_DOCUMENT,
            ),
        )
        filing_document = add_document(
            session,
            source_document(
                title="Acusación ficticia de Persona A",
                suffix="b",
                source_type=SourceType.JUDICIAL_FILING,
            ),
        )
        acquittal_document = add_document(
            session,
            source_document(
                title="Absolución final ficticia de Persona A",
                suffix="c",
                source_type=SourceType.FINAL_JUDICIAL_DECISION,
            ),
        )
        conviction_document = add_document(
            session,
            source_document(
                title="Condena final ficticia de Persona B",
                suffix="d",
                source_type=SourceType.FINAL_JUDICIAL_DECISION,
            ),
        )
        company_document = add_document(
            session,
            source_document(
                title="Registro societario ficticio",
                suffix="e",
                source_type=SourceType.PUBLIC_REGISTRY,
            ),
        )

        person_a = create_person(session, canonical_name="Persona Ficticia A")
        person_b = create_person(session, canonical_name="Persona Ficticia B")

        office_entity = Entity(entity_type=EntityType.PUBLIC_OFFICE)
        organization_entity = Entity(entity_type=EntityType.ORGANIZATION)
        session.add_all([office_entity, organization_entity])
        session.flush()
        session.add_all(
            [
                PublicOffice(
                    entity_id=office_entity.id,
                    normalized_name="cargo demostrativo",
                    original_name="Cargo Demostrativo Ficticio",
                    office_level=OfficeLevel.NATIONAL,
                    institution_name="Institución Ficticia",
                ),
                Organization(
                    entity_id=organization_entity.id,
                    organization_type=OrganizationType.COMPANY,
                    canonical_name="Empresa Ficticia Uno",
                    original_name="Empresa Ficticia Uno SpA",
                ),
            ]
        )
        session.flush()

        create_mandate(
            session,
            person_entity_id=person_a.entity_id,
            public_office_entity_id=office_entity.id,
            start_date=date(2018, 3, 11),
            end_date=date(2022, 3, 10),
            original_title="Mandato Ficticio A",
            status=MandateStatus.COMPLETED,
            source_document_id=mandate_document.id,
        )
        create_mandate(
            session,
            person_entity_id=person_b.entity_id,
            public_office_entity_id=office_entity.id,
            start_date=date(2022, 3, 11),
            original_title="Mandato Ficticio B",
            status=MandateStatus.ELECTED,
            source_document_id=mandate_document.id,
        )

        case_a = register_judicial_case(
            session,
            case_identifier="FICTICIA-A-1",
            court_name="Tribunal Completamente Ficticio",
            source_document_id=filing_document.id,
            current_status=CaseStatus.CLOSED,
            finality_status=FinalityStatus.FINAL,
        )
        link_person_to_case(
            session,
            judicial_case_entity_id=case_a.entity_id,
            person_entity_id=person_a.entity_id,
            original_role="persona acusada ficticia",
            normalized_role=JudicialRole.ACCUSED,
            outcome=JudicialOutcome.ACQUITTED,
            finality_status=FinalityStatus.FINAL,
            source_document_id=acquittal_document.id,
        )

        case_b = register_judicial_case(
            session,
            case_identifier="FICTICIA-B-1",
            court_name="Tribunal Completamente Ficticio",
            source_document_id=conviction_document.id,
            current_status=CaseStatus.DECIDED,
            finality_status=FinalityStatus.FINAL,
        )
        link_person_to_case(
            session,
            judicial_case_entity_id=case_b.entity_id,
            person_entity_id=person_b.entity_id,
            original_role="persona condenada ficticia",
            normalized_role=JudicialRole.CONVICTED_PERSON,
            outcome=JudicialOutcome.CONVICTED,
            finality_status=FinalityStatus.FINAL,
            source_document_id=conviction_document.id,
        )

        commands = [
            ClaimCreate(
                subject_entity_id=person_a.entity_id,
                predicate=Predicate.ACCUSED_IN,
                object_entity_id=case_a.entity_id,
                evidence_level=EvidenceLevel.JUDICIAL_FILING,
                source_document_id=filing_document.id,
                source_excerpt="Acusación ficticia, sin declaración de culpabilidad.",
            ),
            ClaimCreate(
                subject_entity_id=person_a.entity_id,
                predicate=Predicate.ACQUITTED_IN,
                object_entity_id=case_a.entity_id,
                evidence_level=EvidenceLevel.FINAL_JUDICIAL_DECISION,
                source_document_id=acquittal_document.id,
                source_excerpt="Absolución final completamente ficticia.",
            ),
            ClaimCreate(
                subject_entity_id=person_b.entity_id,
                predicate=Predicate.CONVICTED_IN,
                object_entity_id=case_b.entity_id,
                evidence_level=EvidenceLevel.FINAL_JUDICIAL_DECISION,
                source_document_id=conviction_document.id,
                source_excerpt="Condena final completamente ficticia.",
            ),
            ClaimCreate(
                subject_entity_id=person_a.entity_id,
                predicate=Predicate.PARTNER_OF,
                object_entity_id=organization_entity.id,
                evidence_level=EvidenceLevel.OFFICIAL_DOCUMENT,
                source_document_id=company_document.id,
                source_excerpt=(
                    "Relación societaria ficticia; no implica actividad ilícita."
                ),
            ),
        ]
        for command in commands:
            claim = create_claim(session, command)
            submit_claim_for_review(session, claim)
            approve_claim(
                session,
                claim,
                reviewer_identifier=REVIEWER,
                notes="Revisión manual de fixture completamente ficticio.",
            )

    print("fixture ficticio cargado correctamente")


if __name__ == "__main__":
    run()
