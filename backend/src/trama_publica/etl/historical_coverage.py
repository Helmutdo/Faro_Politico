"""Contrato y clasificación para la auditoría histórica de Cámara."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast

from lxml import etree

from trama_publica.etl.camara_xml import (
    DeputyPeriod,
    descendants,
    parse_deputy_periods,
    parse_xml,
    value,
)

CoverageState = Literal[
    "available",
    "partial",
    "documented_but_missing",
    "unavailable",
    "untested",
]


@dataclass(frozen=True)
class LegislatureRef:
    official_id: str
    number: str
    started_at: str
    ended_at: str


@dataclass(frozen=True)
class LegislativePeriod:
    official_id: str
    name: str
    started_at: str
    ended_at: str
    legislatures: tuple[LegislatureRef, ...]


@dataclass(frozen=True)
class HistoricalTerritory:
    territory_type: str
    number: str | None
    name: str | None
    valid_from: str | None
    valid_to: str | None
    source: str


@dataclass(frozen=True)
class YearSignals:
    evaluated: bool
    session_count: int
    attendance_evaluated: bool
    attendance_records: int
    vote_count: int
    individual_votes_evaluated: bool
    individual_vote_records: int


def parse_periods(content: bytes) -> list[LegislativePeriod]:
    root = parse_xml(content)
    result: list[LegislativePeriod] = []
    for period in descendants(root, "PeriodoLegislativo"):
        period_id = value(period, "Id")
        name = value(period, "Nombre")
        start = value(period, "FechaInicio")
        end = value(period, "FechaTermino")
        legislatures: list[LegislatureRef] = []
        for legislature in descendants(period, "Legislatura"):
            legislature_id = value(legislature, "Id")
            number = value(legislature, "Numero")
            legislature_start = value(legislature, "FechaInicio")
            legislature_end = value(legislature, "FechaTermino")
            assert (
                legislature_id
                and number is not None
                and legislature_start
                and legislature_end
            )
            legislatures.append(
                LegislatureRef(
                    official_id=legislature_id,
                    number=number,
                    started_at=legislature_start,
                    ended_at=legislature_end,
                )
            )
        assert period_id and name and start and end
        result.append(
            LegislativePeriod(
                official_id=period_id,
                name=name,
                started_at=start,
                ended_at=end,
                legislatures=tuple(legislatures),
            )
        )
    return result


def count_direct_items(content: bytes, item_name: str) -> int:
    root = parse_xml(content)
    return len(
        cast(
            list[etree._Element],
            root.xpath(f'/*/*[local-name()="{item_name}"]'),
        )
    )


def extract_deputy_ids(content: bytes) -> set[str]:
    root = parse_xml(content)
    return set(
        cast(
            list[str],
            root.xpath(
                '//*[local-name()="Diputado"]'
                '/*[local-name()="Id" or local-name()="DIPID"]/text()'
            ),
        )
    )


def territory_presence(content: bytes) -> dict[str, int]:
    root = parse_xml(content)
    return {
        name: len(
            cast(
                list[etree._Element],
                root.xpath(f'//*[local-name()="{name}"]'),
            )
        )
        for name in ("Distrito", "Circunscripcion", "Comunas", "Region")
    }


def group_multi_period_ids(
    periods: dict[str, list[DeputyPeriod]],
) -> dict[str, list[tuple[str, DeputyPeriod]]]:
    grouped: dict[str, list[tuple[str, DeputyPeriod]]] = {}
    for period_id, deputies in periods.items():
        for deputy in deputies:
            grouped.setdefault(deputy.deputy_id, []).append((period_id, deputy))
    return {
        deputy_id: appearances
        for deputy_id, appearances in grouped.items()
        if len({period_id for period_id, _ in appearances}) > 1
    }


def identity_names_consistent(
    appearances: list[tuple[str, DeputyPeriod]],
) -> bool:
    return len({deputy.name for _, deputy in appearances}) == 1


def identity_resolution(
    left_id: str, right_id: str
) -> Literal["confirmed", "candidate_only"]:
    return "confirmed" if left_id == right_id else "candidate_only"


def classify_deputies(count: int, district_count: int) -> CoverageState:
    if count == 0:
        return "unavailable"
    if district_count == count:
        return "available"
    if district_count == 0:
        return "documented_but_missing"
    return "partial"


def classify_list(evaluated: bool, count: int) -> CoverageState:
    if not evaluated:
        return "untested"
    return "available" if count > 0 else "unavailable"


def classify_detail(
    *,
    list_count: int,
    detail_evaluated: bool,
    detail_records: int,
) -> CoverageState:
    if list_count == 0:
        return "unavailable"
    if not detail_evaluated:
        return "untested"
    return "available" if detail_records > 0 else "partial"


def coverage_row(signals: YearSignals) -> dict[str, CoverageState]:
    if not signals.evaluated:
        return {
            "sessions": "untested",
            "attendance": "untested",
            "votes": "untested",
            "individual_votes": "untested",
        }
    return {
        "sessions": classify_list(True, signals.session_count),
        "attendance": classify_detail(
            list_count=signals.session_count,
            detail_evaluated=signals.attendance_evaluated,
            detail_records=signals.attendance_records,
        ),
        "votes": classify_list(True, signals.vote_count),
        "individual_votes": classify_detail(
            list_count=signals.vote_count,
            detail_evaluated=signals.individual_votes_evaluated,
            detail_records=signals.individual_vote_records,
        ),
    }


def historical_territory_contract(
    *,
    territory_type: str,
    number: str | None,
    name: str | None,
    valid_from: datetime | None,
    valid_to: datetime | None,
    source: str,
) -> HistoricalTerritory:
    return HistoricalTerritory(
        territory_type=territory_type,
        number=number,
        name=name,
        valid_from=valid_from.isoformat() if valid_from else None,
        valid_to=valid_to.isoformat() if valid_to else None,
        source=source,
    )


def parse_period_deputies(content: bytes) -> list[DeputyPeriod]:
    return parse_deputy_periods(content)
