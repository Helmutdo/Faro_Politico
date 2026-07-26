from pathlib import Path

from trama_publica.etl.camara_xml import (
    parse_attendance,
    parse_deputy_periods,
    parse_individual_votes,
)

FIXTURES = Path(__file__).parent / "fixtures" / "camara"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_deputy_parser_preserves_missing_district() -> None:
    deputies = parse_deputy_periods(fixture("diputados_periodo_without_district.xml"))

    assert len(deputies) == 1
    assert deputies[0].deputy_id == "1074"
    assert deputies[0].district is None


def test_attendance_parser_preserves_original_label() -> None:
    attendance = parse_attendance(fixture("session_attendance.xml"))

    assert attendance["803"].original_status == "Asiste"


def test_vote_parser_preserves_original_option() -> None:
    votes = parse_individual_votes(fixture("vote_detail.xml"))

    assert votes["803"].original_option == "Afirmativo"
