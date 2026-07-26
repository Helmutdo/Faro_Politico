"""Parsers XML mínimos para explorar Open Data de la Cámara.

El código de este módulo es deliberadamente independiente de los prefijos XML:
solo compara nombres locales. No constituye el ETL definitivo.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import cast

from lxml import etree

Element = etree._Element


@dataclass(frozen=True)
class DeputyPeriod:
    deputy_id: str
    name: str
    district: str | None


@dataclass(frozen=True)
class Session:
    session_id: str
    number: str
    started_at: datetime
    ended_at: datetime
    state: str


@dataclass(frozen=True)
class Attendance:
    deputy_id: str
    original_status: str


@dataclass(frozen=True)
class VoteSummary:
    vote_id: str
    description: str
    voted_at: datetime


@dataclass(frozen=True)
class IndividualVote:
    deputy_id: str
    original_option: str


def parse_xml(content: bytes) -> Element:
    """Parse trusted response bytes without resolving external entities."""
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.fromstring(content, parser=parser)


def child(element: Element, name: str) -> Element | None:
    matches = cast(list[Element], element.xpath(f'./*[local-name()="{name}"]'))
    return matches[0] if matches else None


def descendants(element: Element, name: str) -> list[Element]:
    return cast(list[Element], element.xpath(f'.//*[local-name()="{name}"]'))


def value(element: Element, name: str, *, required: bool = True) -> str | None:
    target = child(element, name)
    text = target.text.strip() if target is not None and target.text else None
    if required and text is None:
        raise ValueError(f"XML sin valor requerido {name!r}")
    return text


def type_original(element: Element, name: str) -> str:
    target = child(element, name)
    if target is None:
        raise ValueError(f"XML sin elemento requerido {name!r}")
    return (target.text or "").strip()


def parse_current_period(content: bytes) -> tuple[str, str]:
    root = parse_xml(content)
    period_id = value(root, "Id")
    legislatures = descendants(root, "Legislatura")
    if not legislatures:
        raise ValueError("Período actual sin legislatura")
    legislature_id = value(legislatures[0], "Id")
    assert period_id is not None and legislature_id is not None
    return period_id, legislature_id


def parse_deputy_periods(content: bytes) -> list[DeputyPeriod]:
    root = parse_xml(content)
    result: list[DeputyPeriod] = []
    for period in descendants(root, "DiputadoPeriodo"):
        deputy = child(period, "Diputado")
        if deputy is None:
            continue
        deputy_id = value(deputy, "Id")
        name_parts = [
            value(deputy, field, required=False)
            for field in ("Nombre", "Nombre2", "ApellidoPaterno", "ApellidoMaterno")
        ]
        district_element = child(period, "Distrito")
        district = (
            value(district_element, "Numero", required=False)
            if district_element is not None
            else None
        )
        assert deputy_id is not None
        result.append(
            DeputyPeriod(
                deputy_id=deputy_id,
                name=" ".join(part for part in name_parts if part),
                district=district,
            )
        )
    return result


def parse_sessions(content: bytes) -> list[Session]:
    root = parse_xml(content)
    result: list[Session] = []
    for session in descendants(root, "Sesion"):
        session_id = value(session, "Id")
        number = value(session, "Numero")
        start = value(session, "FechaInicio")
        end = value(session, "FechaTermino")
        assert session_id and number is not None and start and end
        result.append(
            Session(
                session_id=session_id,
                number=number,
                started_at=datetime.fromisoformat(start),
                ended_at=datetime.fromisoformat(end),
                state=type_original(session, "Estado"),
            )
        )
    return result


def parse_attendance(content: bytes) -> dict[str, Attendance]:
    root = parse_xml(content)
    result: dict[str, Attendance] = {}
    for record in descendants(root, "Asistencia"):
        deputy = child(record, "Diputado")
        if deputy is None:
            continue
        deputy_id = value(deputy, "Id")
        assert deputy_id is not None
        result[deputy_id] = Attendance(
            deputy_id=deputy_id,
            original_status=type_original(record, "TipoAsistencia"),
        )
    return result


def parse_vote_summaries(content: bytes) -> list[VoteSummary]:
    root = parse_xml(content)
    result: list[VoteSummary] = []
    for vote in descendants(root, "Votacion"):
        vote_id = value(vote, "Id")
        description = value(vote, "Descripcion")
        voted_at = value(vote, "Fecha")
        assert vote_id and description is not None and voted_at
        result.append(
            VoteSummary(
                vote_id=vote_id,
                description=description,
                voted_at=datetime.fromisoformat(voted_at),
            )
        )
    return result


def parse_individual_votes(content: bytes) -> dict[str, IndividualVote]:
    root = parse_xml(content)
    result: dict[str, IndividualVote] = {}
    for vote in descendants(root, "Voto"):
        deputy = child(vote, "Diputado")
        if deputy is None:
            continue
        deputy_id = value(deputy, "Id")
        assert deputy_id is not None
        result[deputy_id] = IndividualVote(
            deputy_id=deputy_id,
            original_option=type_original(vote, "OpcionVoto"),
        )
    return result
