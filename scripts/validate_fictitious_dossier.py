#!/usr/bin/env python3
"""Valida invariantes del dossier ficticio cargado en PostgreSQL."""

import json
import sys
from typing import Any

from sqlalchemy import text
from trama_publica.db.session import create_database_engine
from trama_publica.domain.enums import PROHIBITED_PREDICATES


def validate() -> dict[str, Any]:
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        raise RuntimeError("fictitious dossier validation requires PostgreSQL")
    with engine.connect() as connection:
        counts = {
            table: connection.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in (
                "entities",
                "persons",
                "person_identities",
                "mandates",
                "organizations",
                "judicial_cases",
                "judicial_case_persons",
                "judicial_events",
                "source_documents",
                "evidence_claims",
                "manual_reviews",
            )
        }
        claims = (
            connection.execute(
                text(
                    """
                SELECT p.canonical_name, c.predicate, d.source_type
                FROM evidence_claims c
                JOIN persons p ON p.entity_id = c.subject_entity_id
                JOIN source_documents d ON d.id = c.source_document_id
                ORDER BY p.canonical_name, c.predicate
                """
                )
            )
            .mappings()
            .all()
        )
    person_a = {
        row["predicate"]
        for row in claims
        if row["canonical_name"] == "Persona Ficticia A"
    }
    person_b_final_convictions = [
        row
        for row in claims
        if row["canonical_name"] == "Persona Ficticia B"
        and row["predicate"] == "CONVICTED_IN"
        and row["source_type"] == "final_judicial_decision"
    ]
    predicates = {row["predicate"] for row in claims}
    invariants = {
        "person_a_keeps_accusation": "ACCUSED_IN" in person_a,
        "person_a_keeps_acquittal": "ACQUITTED_IN" in person_a,
        "person_a_has_no_conviction": "CONVICTED_IN" not in person_a,
        "person_b_has_final_conviction": len(person_b_final_convictions) == 1,
        "company_relation_is_neutral": "PARTNER_OF" in person_a,
        "no_prohibited_predicates": predicates.isdisjoint(PROHIBITED_PREDICATES),
    }
    return {
        "status": "ok" if all(invariants.values()) else "failed",
        "counts": counts,
        "invariants": invariants,
    }


def main() -> None:
    try:
        result = validate()
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, indent=2))
        raise SystemExit(2) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
