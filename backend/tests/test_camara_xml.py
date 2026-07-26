from pathlib import Path

from trama_publica.etl.camara_xml import (
    confirmed_session_id,
    inspect_session_votes,
    parse_attendance,
    parse_deputy_periods,
    parse_individual_votes,
    parse_vote_detail,
)

FIXTURES = Path(__file__).parent / "fixtures" / "camara"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_deputy_parser_preserves_missing_district() -> None:
    deputies = parse_deputy_periods(fixture("diputados_periodo_without_district.xml"))

    assert len(deputies) == 1
    assert deputies[0].deputy_id == "1074"
    assert deputies[0].district is None


def test_deputy_parser_reads_documented_district_shape() -> None:
    deputies = parse_deputy_periods(fixture("documented_deputies_with_district.xml"))

    assert deputies[0].deputy_id == "9999"
    assert deputies[0].district == "19"


def test_attendance_parser_preserves_original_label() -> None:
    attendance = parse_attendance(fixture("session_attendance.xml"))

    assert attendance["803"].original_status == "Asiste"


def test_vote_parser_preserves_original_option() -> None:
    votes = parse_individual_votes(fixture("vote_detail.xml"))

    assert votes["803"].original_option == "Afirmativo"


def test_official_id_resolves_attendance_and_vote() -> None:
    attendance = parse_attendance(fixture("session_attendance.xml"))
    votes = parse_individual_votes(fixture("vote_detail.xml"))

    assert set(attendance).intersection(votes) == {"803"}


def test_session_with_documented_votaciones_exposes_ids() -> None:
    contract = inspect_session_votes(fixture("documented_session_with_votes.xml"))

    assert contract.container_present is True
    assert contract.vote_ids == ("8888",)


def test_real_session_without_votaciones_has_no_link() -> None:
    contract = inspect_session_votes(fixture("session_attendance.xml"))

    assert contract.container_present is False
    assert contract.vote_ids == ()


def test_real_vote_has_nullable_session_id() -> None:
    detail = parse_vote_detail(fixture("vote_detail.xml"))

    assert detail.session_id is None


def test_temporal_candidate_cannot_become_confirmed_link() -> None:
    detail = parse_vote_detail(fixture("vote_detail.xml"))

    assert confirmed_session_id(detail, temporal_candidate="4804") is None
