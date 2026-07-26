from datetime import datetime
from pathlib import Path

from trama_publica.etl.camara_xml import DeputyPeriod
from trama_publica.etl.historical_coverage import (
    YearSignals,
    classify_deputies,
    coverage_row,
    group_multi_period_ids,
    historical_territory_contract,
    identity_names_consistent,
    identity_resolution,
    parse_periods,
)

FIXTURES = Path(__file__).parent / "fixtures" / "camara"


def deputy(deputy_id: str, name: str, district: str | None = None) -> DeputyPeriod:
    return DeputyPeriod(deputy_id=deputy_id, name=name, district=district)


def test_person_can_appear_in_multiple_periods_with_same_id() -> None:
    grouped = group_multi_period_ids(
        {"10": [deputy("100", "Persona Uno")], "11": [deputy("100", "Persona Uno")]}
    )

    assert list(grouped) == ["100"]
    assert identity_names_consistent(grouped["100"]) is True
    assert identity_resolution("100", "100") == "confirmed"


def test_inconsistent_ids_are_candidate_only() -> None:
    assert identity_resolution("100", "200") == "candidate_only"


def test_missing_district_is_documented_but_missing() -> None:
    assert classify_deputies(count=155, district_count=0) == ("documented_but_missing")


def test_historical_territory_is_versioned() -> None:
    territory = historical_territory_contract(
        territory_type="distrito",
        number="19",
        name=None,
        valid_from=datetime(2022, 3, 11),
        valid_to=datetime(2026, 3, 10),
        source="operacion-oficial",
    )

    assert territory.number == "19"
    assert territory.valid_from == "2022-03-11T00:00:00"
    assert territory.valid_to == "2026-03-10T00:00:00"


def test_year_without_data_is_unavailable() -> None:
    row = coverage_row(
        YearSignals(
            evaluated=True,
            session_count=0,
            attendance_evaluated=False,
            attendance_records=0,
            vote_count=0,
            individual_votes_evaluated=False,
            individual_vote_records=0,
        )
    )

    assert set(row.values()) == {"unavailable"}


def test_year_with_partial_data_preserves_partial_state() -> None:
    row = coverage_row(
        YearSignals(
            evaluated=True,
            session_count=2,
            attendance_evaluated=True,
            attendance_records=0,
            vote_count=3,
            individual_votes_evaluated=True,
            individual_vote_records=0,
        )
    )

    assert row["sessions"] == "available"
    assert row["attendance"] == "partial"
    assert row["votes"] == "available"
    assert row["individual_votes"] == "partial"


def test_unevaluated_year_is_untested() -> None:
    row = coverage_row(
        YearSignals(
            evaluated=False,
            session_count=0,
            attendance_evaluated=False,
            attendance_records=0,
            vote_count=0,
            individual_votes_evaluated=False,
            individual_vote_records=0,
        )
    )

    assert set(row.values()) == {"untested"}


def test_periods_include_official_legislature_references() -> None:
    periods = parse_periods((FIXTURES / "historical_periods.xml").read_bytes())

    assert periods[0].official_id == "3"
    assert periods[0].legislatures[0].official_id == "21"
