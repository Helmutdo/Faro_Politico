#!/usr/bin/env python3
"""Audita cobertura parlamentaria histórica con snapshots reutilizables."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
from lxml import etree
from trama_publica.etl.camara_xml import parse_xml
from trama_publica.etl.historical_coverage import (
    LegislativePeriod,
    YearSignals,
    classify_deputies,
    coverage_row,
    extract_deputy_ids,
    group_multi_period_ids,
    identity_names_consistent,
    parse_period_deputies,
    parse_periods,
    territory_presence,
)

BASE = "https://opendata.camara.cl/camaradiputados/WServices"
ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "data" / "raw" / "historical"
REPORT_PATH = SNAPSHOT_DIR / "historical-coverage-report.json"
MATRIX_PATH = SNAPSHOT_DIR / "historical-coverage-matrix.md"
USER_AGENT = (
    "FaroPolitico-HistoricalAudit/0.1 "
    "(investigacion de cobertura; github.com/Helmutdo/Faro_Politico)"
)

ENDPOINTS = {
    "retornarPeriodosLegislativos": (
        f"{BASE}/WSLegislativo.asmx/retornarPeriodosLegislativos"
    ),
    "retornarDiputadosXPeriodo": (f"{BASE}/WSDiputado.asmx/retornarDiputadosXPeriodo"),
    "retornarDiputados": f"{BASE}/WSDiputado.asmx/retornarDiputados",
    "retornarSesionesXAnno": f"{BASE}/WSSala.asmx/retornarSesionesXAnno",
    "retornarSesionesXLegislatura": (
        f"{BASE}/WSSala.asmx/retornarSesionesXLegislatura"
    ),
    "retornarSesionAsistencia": f"{BASE}/WSSala.asmx/retornarSesionAsistencia",
    "retornarVotacionesXAnno": (f"{BASE}/WSLegislativo.asmx/retornarVotacionesXAnno"),
    "retornarVotacionDetalle": (f"{BASE}/WSLegislativo.asmx/retornarVotacionDetalle"),
}


class SnapshotStore:
    def __init__(
        self, client: httpx.Client, directory: Path, *, offline: bool, verbose: bool
    ) -> None:
        self.client = client
        self.directory = directory
        self.offline = offline
        self.verbose = verbose
        self.requests = 0
        self.cache_hits = 0
        self.errors: list[dict[str, str]] = []
        directory.mkdir(parents=True, exist_ok=True)

    def get(self, operation: str, params: dict[str, str] | None = None) -> bytes | None:
        params = params or {}
        suffix = "_".join(f"{key}-{value}" for key, value in sorted(params.items()))
        key = f"{operation}_{suffix}" if suffix else operation
        path = self.directory / f"{key}.xml"
        metadata_path = self.directory / f"{key}.meta.json"
        error_path = self.directory / f"{key}.error.xml"
        error_metadata_path = self.directory / f"{key}.error.meta.json"
        if path.exists():
            self.cache_hits += 1
            if self.verbose:
                print(f"CACHE {key}", file=sys.stderr)
            return path.read_bytes()
        if error_path.exists():
            self.cache_hits += 1
            self.errors.append({"operation": key, "error": "cached_http_error"})
            return None
        if self.offline:
            self.errors.append({"operation": key, "error": "snapshot_missing"})
            return None
        try:
            response = self.client.get(ENDPOINTS[operation], params=params)
        except httpx.HTTPError as error:
            self.errors.append({"operation": key, "error": str(error)})
            return None
        self.requests += 1
        digest = hashlib.sha256(response.content).hexdigest()
        fetched_at = datetime.now(UTC).isoformat()
        if response.is_error:
            error_path.write_bytes(response.content)
            error_metadata_path.write_text(
                json.dumps(
                    {
                        "operation": operation,
                        "params": params,
                        "url": str(response.url),
                        "status_code": response.status_code,
                        "fetched_at": fetched_at,
                        "sha256": digest,
                        "bytes": len(response.content),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            self.errors.append(
                {
                    "operation": key,
                    "error": f"http_status_{response.status_code}",
                }
            )
            return None
        path.write_bytes(response.content)
        metadata_path.write_text(
            json.dumps(
                {
                    "operation": operation,
                    "params": params,
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "fetched_at": fetched_at,
                    "sha256": digest,
                    "bytes": len(response.content),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if self.verbose:
            print(
                f"GET {key}: {response.status_code}, {len(response.content)} bytes",
                file=sys.stderr,
            )
        return response.content

    def snapshot_count(self) -> int:
        return len(list(self.directory.glob("*.xml")))


def direct_elements(content: bytes, name: str) -> list[etree._Element]:
    root = parse_xml(content)
    return cast(
        list[etree._Element],
        root.xpath(f'/*/*[local-name()="{name}"]'),
    )


def direct_id(element: etree._Element) -> str | None:
    values = cast(
        list[str],
        element.xpath('./*[local-name()="Id" or local-name()="ID"]/text()'),
    )
    return values[0] if values else None


def count_descendants(content: bytes, name: str) -> int:
    root = parse_xml(content)
    return len(
        cast(
            list[etree._Element],
            root.xpath(f'.//*[local-name()="{name}"]'),
        )
    )


def inspect_details(
    store: SnapshotStore,
    items: list[etree._Element],
    *,
    max_items: int,
    operation: str,
    parameter: str,
    record_name: str,
) -> tuple[bool, int, set[str]]:
    if not items:
        return False, 0, set()
    evaluated = False
    records = 0
    deputy_ids: set[str] = set()
    if max_items >= len(items):
        sample = items
    elif max_items == 1:
        sample = [items[0]]
    else:
        indexes = {
            round(index * (len(items) - 1) / (max_items - 1))
            for index in range(max_items)
        }
        sample = [items[index] for index in sorted(indexes)]
    for item in sample:
        official_id = direct_id(item)
        if not official_id:
            continue
        detail = store.get(operation, {parameter: official_id})
        if detail is None:
            continue
        evaluated = True
        records += count_descendants(detail, record_name)
        deputy_ids.update(extract_deputy_ids(detail))
    return evaluated, records, deputy_ids


def period_report(
    store: SnapshotStore, periods: list[LegislativePeriod]
) -> tuple[list[dict[str, Any]], dict[str, list[Any]]]:
    rows: list[dict[str, Any]] = []
    deputies_by_period: dict[str, list[Any]] = {}
    for period in periods:
        content = store.get(
            "retornarDiputadosXPeriodo", {"prmPeriodoID": period.official_id}
        )
        if content is None:
            rows.append(
                {
                    **asdict(period),
                    "deputy_count": None,
                    "status": "untested",
                    "error": "request_or_snapshot_missing",
                }
            )
            continue
        deputies = parse_period_deputies(content)
        deputies_by_period[period.official_id] = deputies
        territories = territory_presence(content)
        district_count = territories["Distrito"]
        ids = [deputy.deputy_id for deputy in deputies]
        rows.append(
            {
                **asdict(period),
                "deputy_count": len(deputies),
                "district_count": district_count,
                "territory_nodes": territories,
                "official_id_count": len(ids),
                "unique_official_id_count": len(set(ids)),
                "militancia_count": count_descendants(content, "Militancia"),
                "deputies_status": ("available" if deputies else "unavailable"),
                "district_status": classify_deputies(len(deputies), district_count),
                "status": (
                    "available"
                    if deputies and district_count == len(deputies)
                    else "partial"
                    if deputies
                    else "unavailable"
                ),
            }
        )
    return rows, deputies_by_period


def audit_years(
    store: SnapshotStore,
    years: list[int],
    sample_years: set[int],
    *,
    max_sessions: int,
    max_votes: int,
) -> tuple[list[dict[str, Any]], dict[str, int | None], set[str], set[str]]:
    rows: list[dict[str, Any]] = []
    first: dict[str, int | None] = {
        "sessions": None,
        "attendance": None,
        "votes": None,
        "individual_votes": None,
    }
    attendance_ids: set[str] = set()
    vote_ids: set[str] = set()
    for year in years:
        sessions_xml = store.get("retornarSesionesXAnno", {"prmAnno": str(year)})
        votes_xml = store.get("retornarVotacionesXAnno", {"prmAnno": str(year)})
        if sessions_xml is None or votes_xml is None:
            signals = YearSignals(False, 0, False, 0, 0, False, 0)
            rows.append(
                {
                    "year": year,
                    **asdict(signals),
                    **coverage_row(signals),
                    "quality": "untested",
                    "error": "request_or_snapshot_missing",
                }
            )
            continue
        sessions = direct_elements(sessions_xml, "Sesion")
        votes = direct_elements(votes_xml, "Votacion")
        if sessions and first["sessions"] is None:
            first["sessions"] = year
        if votes and first["votes"] is None:
            first["votes"] = year

        inspect_attendance = year in sample_years or first["attendance"] is None
        attendance_evaluated = False
        attendance_records = 0
        year_attendance_ids: set[str] = set()
        if inspect_attendance and sessions:
            (
                attendance_evaluated,
                attendance_records,
                year_attendance_ids,
            ) = inspect_details(
                store,
                sessions,
                max_items=max_sessions,
                operation="retornarSesionAsistencia",
                parameter="prmSesionId",
                record_name="Asistencia",
            )
            if attendance_records and first["attendance"] is None:
                first["attendance"] = year
        attendance_ids.update(year_attendance_ids)

        inspect_individual = year in sample_years or first["individual_votes"] is None
        individual_evaluated = False
        individual_records = 0
        year_vote_ids: set[str] = set()
        if inspect_individual and votes:
            (
                individual_evaluated,
                individual_records,
                year_vote_ids,
            ) = inspect_details(
                store,
                votes,
                max_items=max_votes,
                operation="retornarVotacionDetalle",
                parameter="prmVotacionId",
                record_name="Voto",
            )
            if individual_records and first["individual_votes"] is None:
                first["individual_votes"] = year
        vote_ids.update(year_vote_ids)

        signals = YearSignals(
            evaluated=True,
            session_count=len(sessions),
            attendance_evaluated=attendance_evaluated,
            attendance_records=attendance_records,
            vote_count=len(votes),
            individual_votes_evaluated=individual_evaluated,
            individual_vote_records=individual_records,
        )
        states = coverage_row(signals)
        available_count = sum(state == "available" for state in states.values())
        quality = (
            "available"
            if available_count == 4
            else "partial"
            if available_count
            else "unavailable"
        )
        rows.append(
            {
                "year": year,
                **asdict(signals),
                **states,
                "deputy_ids_in_attendance": len(year_attendance_ids),
                "deputy_ids_in_votes": len(year_vote_ids),
                "quality": quality,
            }
        )
    return rows, first, attendance_ids, vote_ids


def audit_legislature_range(
    store: SnapshotStore, periods: list[LegislativePeriod]
) -> dict[str, Any]:
    legislatures = [
        legislature for period in periods for legislature in period.legislatures
    ]
    tested: list[dict[str, Any]] = []
    first_with_sessions: str | None = None
    for legislature in legislatures:
        content = store.get(
            "retornarSesionesXLegislatura",
            {"prmLegislaturaId": legislature.official_id},
        )
        if content is None:
            tested.append(
                {
                    "legislature_id": legislature.official_id,
                    "sessions": None,
                    "status": "untested",
                }
            )
            continue
        count = len(direct_elements(content, "Sesion"))
        tested.append(
            {
                "legislature_id": legislature.official_id,
                "sessions": count,
                "status": "available" if count else "unavailable",
            }
        )
        if count and first_with_sessions is None:
            first_with_sessions = legislature.official_id
            break
    latest = legislatures[-1]
    if not tested or tested[-1]["legislature_id"] != latest.official_id:
        latest_xml = store.get(
            "retornarSesionesXLegislatura",
            {"prmLegislaturaId": latest.official_id},
        )
        tested.append(
            {
                "legislature_id": latest.official_id,
                "sessions": (
                    len(direct_elements(latest_xml, "Sesion"))
                    if latest_xml is not None
                    else None
                ),
                "status": "available" if latest_xml is not None else "untested",
            }
        )
    return {
        "first_legislature_with_sessions": first_with_sessions,
        "tested": tested,
    }


def identity_report(
    deputies_by_period: dict[str, list[Any]],
    catalog_xml: bytes | None,
    attendance_ids: set[str],
    vote_ids: set[str],
) -> dict[str, Any]:
    grouped = group_multi_period_ids(deputies_by_period)
    selected = sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )[:3]
    catalog_ids = extract_deputy_ids(catalog_xml) if catalog_xml else set()
    samples: list[dict[str, Any]] = []
    for deputy_id, appearances in selected:
        samples.append(
            {
                "official_id": deputy_id,
                "periods": [
                    {
                        "period_id": period_id,
                        "name": deputy.name,
                        "district": deputy.district,
                    }
                    for period_id, deputy in appearances
                ],
                "name_consistent": identity_names_consistent(appearances),
                "present_in_general_catalog": deputy_id in catalog_ids,
                "present_in_sampled_attendance": deputy_id in attendance_ids,
                "present_in_sampled_individual_votes": deputy_id in vote_ids,
            }
        )
    all_period_ids = {
        deputy.deputy_id
        for deputies in deputies_by_period.values()
        for deputy in deputies
    }
    return {
        "multi_period_official_ids": len(grouped),
        "catalog_id_count": len(catalog_ids),
        "period_id_count": len(all_period_ids),
        "period_ids_missing_from_catalog": len(all_period_ids - catalog_ids),
        "samples": samples,
    }


def markdown_matrix(periods: list[dict[str, Any]], years: list[dict[str, Any]]) -> str:
    lines = [
        (
            "| Período/Año | Diputados | Distrito | Sesiones | Asistencia | "
            "Votaciones | Voto individual | Calidad |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    for period in periods:
        lines.append(
            f"| Período {period['official_id']} ({period['name']}) | "
            f"{period.get('deputies_status', period['status'])} | "
            f"{period.get('district_status', period['status'])} | "
            "untested | untested | "
            "untested | untested | "
            f"{period['status']} |"
        )
    for year in years:
        lines.append(
            f"| {year['year']} | untested | untested | {year['sessions']} | "
            f"{year['attendance']} | {year['votes']} | "
            f"{year['individual_votes']} | {year['quality']} |"
        )
    return "\n".join(lines) + "\n"


def parse_sample_years(values: list[str]) -> set[int]:
    result: set[int] = set()
    for value in values:
        result.update(int(item) for item in value.split(",") if item)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-year", type=int, default=1990)
    parser.add_argument("--to-year", type=int, default=datetime.now(UTC).year)
    parser.add_argument(
        "--sample-years",
        nargs="*",
        default=["2026,2025,2022,2018,2014,2010,2006"],
    )
    parser.add_argument("--max-sessions", type=int, default=2)
    parser.add_argument("--max-votes", type=int, default=2)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.from_year > args.to_year:
        raise ValueError("--from-year debe ser menor o igual a --to-year")
    sample_years = parse_sample_years(args.sample_years)
    years = list(range(args.from_year, args.to_year + 1))
    timeout = httpx.Timeout(60)
    with httpx.Client(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT, "Accept": "application/xml, text/xml"},
        follow_redirects=True,
    ) as client:
        store = SnapshotStore(
            client,
            SNAPSHOT_DIR,
            offline=args.offline,
            verbose=args.verbose,
        )
        periods_xml = store.get("retornarPeriodosLegislativos")
        if periods_xml is None:
            raise RuntimeError("No existe snapshot de retornarPeriodosLegislativos")
        periods = parse_periods(periods_xml)
        period_rows, deputies_by_period = period_report(store, periods)
        catalog_xml = store.get("retornarDiputados")
        year_rows, first, attendance_ids, vote_ids = audit_years(
            store,
            years,
            sample_years,
            max_sessions=args.max_sessions,
            max_votes=args.max_votes,
        )
        legislature_range = audit_legislature_range(store, periods)
        identities = identity_report(
            deputies_by_period,
            catalog_xml,
            attendance_ids,
            vote_ids,
        )
        report: dict[str, Any] = {
            "generated_at": datetime.now().astimezone().isoformat(),
            "mode": "offline" if args.offline else "online",
            "parameters": {
                "from_year": args.from_year,
                "to_year": args.to_year,
                "sample_years": sorted(sample_years),
                "max_sessions": args.max_sessions,
                "max_votes": args.max_votes,
            },
            "periods": period_rows,
            "years": year_rows,
            "first_available": first,
            "legislature_range": legislature_range,
            "identities": identities,
            "territory_contract": {
                "fields": [
                    "type",
                    "number",
                    "name",
                    "valid_from",
                    "valid_to",
                    "source",
                ],
                "retroactive_current_district_mapping": "forbidden",
            },
            "snapshots": {
                "count": store.snapshot_count(),
                "network_requests_this_run": store.requests,
                "cache_hits_this_run": store.cache_hits,
                "errors": store.errors,
            },
        }
    matrix = markdown_matrix(period_rows, year_rows)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    MATRIX_PATH.write_text(matrix, encoding="utf-8")
    return report


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = run(args)
    except (ValueError, RuntimeError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": "ok",
                "mode": report["mode"],
                "periods": len(report["periods"]),
                "years": len(report["years"]),
                "first_available": report["first_available"],
                "multi_period_official_ids": report["identities"][
                    "multi_period_official_ids"
                ],
                "snapshots": report["snapshots"],
                "report": str(REPORT_PATH.relative_to(ROOT)),
                "matrix": str(MATRIX_PATH.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
