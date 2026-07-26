#!/usr/bin/env python3
"""Auditoría reproducible del contrato XML oficial de la Cámara.

No escribe en PostgreSQL, no construye el ETL definitivo y nunca convierte una
coincidencia temporal entre sesión y votación en una relación confirmada.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
from lxml import etree, html

from trama_publica.etl.camara_xml import (
    Attendance,
    DeputyPeriod,
    IndividualVote,
    Session,
    inspect_session_votes,
    parse_attendance,
    parse_current_period,
    parse_deputy_periods,
    parse_sessions,
    parse_vote_detail,
    parse_vote_summaries,
    parse_xml,
)

BASE = "https://opendata.camara.cl/camaradiputados/WServices"
BCN_REPORT = "https://www.bcn.cl/siit/reportesdistritales/reporte_final.html"
USER_AGENT = (
    "TramaPublica-ContractAudit/0.2 "
    "(transparencia parlamentaria; github.com/Helmutdo/Faro_Politico)"
)
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
NS = "http://opendata.camara.cl/camaradiputados/v1"

SERVICES = {
    "diputado": f"{BASE}/WSDiputado.asmx",
    "legislativo": f"{BASE}/WSLegislativo.asmx",
    "sala": f"{BASE}/WSSala.asmx",
}


class RawRecorder:
    def __init__(self, client: httpx.Client, raw_dir: Path) -> None:
        self.client = client
        self.raw_dir = raw_dir
        self.files: list[dict[str, Any]] = []
        raw_dir.mkdir(parents=True, exist_ok=True)

    def request(
        self,
        operation: str,
        protocol: str,
        *,
        service: str,
        params: dict[str, str] | None = None,
    ) -> bytes:
        service_url = SERVICES[service]
        observed_at = datetime.now(UTC)
        if protocol == "http_get":
            response = self.client.get(f"{service_url}/{operation}", params=params)
        elif protocol == "http_post":
            response = self.client.post(
                f"{service_url}/{operation}",
                data=params or {},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        elif protocol in {"soap11", "soap12"}:
            envelope_ns = (
                "http://schemas.xmlsoap.org/soap/envelope/"
                if protocol == "soap11"
                else "http://www.w3.org/2003/05/soap-envelope"
            )
            arguments = "".join(
                f"<{name}>{value}</{name}>" for name, value in (params or {}).items()
            )
            body = (
                '<?xml version="1.0" encoding="utf-8"?>'
                f'<soap:Envelope xmlns:soap="{envelope_ns}">'
                f'<soap:Body><{operation} xmlns="{NS}">'
                f"{arguments}</{operation}></soap:Body></soap:Envelope>"
            ).encode()
            action = f"{NS}/{operation}"
            headers = (
                {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": f'"{action}"',
                }
                if protocol == "soap11"
                else {
                    "Content-Type": (
                        f'application/soap+xml; charset=utf-8; action="{action}"'
                    )
                }
            )
            response = self.client.post(service_url, content=body, headers=headers)
        else:
            raise ValueError(f"Protocolo no soportado: {protocol}")
        response.raise_for_status()
        return self._save(
            response,
            operation=operation,
            protocol=protocol,
            observed_at=observed_at,
        )

    def external_get(
        self, operation: str, url: str, *, params: dict[str, str]
    ) -> bytes:
        observed_at = datetime.now(UTC)
        response = self.client.get(url, params=params, headers={"Accept": "text/html"})
        response.raise_for_status()
        return self._save(
            response,
            operation=operation,
            protocol="http_get_html_validation",
            observed_at=observed_at,
            extension="html",
        )

    def _save(
        self,
        response: httpx.Response,
        *,
        operation: str,
        protocol: str,
        observed_at: datetime,
        extension: str = "xml",
    ) -> bytes:
        digest = hashlib.sha256(response.content).hexdigest()
        stamp = observed_at.strftime("%Y%m%dT%H%M%SZ")
        path = self.raw_dir / (
            f"{operation}_{protocol}_{stamp}_{digest[:12]}.{extension}"
        )
        path.write_bytes(response.content)
        self.files.append(
            {
                "operation": operation,
                "protocol": protocol,
                "observed_at": observed_at.isoformat(),
                "url": str(response.url),
                "status_code": response.status_code,
                "bytes": len(response.content),
                "sha256": digest,
                "file": str(path.relative_to(ROOT)),
            }
        )
        return response.content


def unwrap_soap(content: bytes) -> bytes:
    root = parse_xml(content)
    bodies = cast(
        list[etree._Element],
        root.xpath('//*[local-name()="Body"]/*[1]/*[1]'),
    )
    if not bodies:
        return content
    return etree.tostring(bodies[0], encoding="utf-8")


def raw_district_presence(content: bytes) -> dict[str, int]:
    root = parse_xml(content)
    periods = cast(
        list[etree._Element],
        root.xpath('//*[local-name()="DiputadoPeriodo"]'),
    )
    return {
        "deputy_periods": len(periods),
        "district": len(
            cast(
                list[etree._Element],
                root.xpath(
                    '//*[local-name()="DiputadoPeriodo"]/*[local-name()="Distrito"]'
                ),
            )
        ),
        "district_number": len(
            cast(
                list[etree._Element],
                root.xpath(
                    '//*[local-name()="DiputadoPeriodo"]'
                    '/*[local-name()="Distrito"]/*[local-name()="Numero"]'
                ),
            )
        ),
        "district_communes": len(
            cast(
                list[etree._Element],
                root.xpath(
                    '//*[local-name()="DiputadoPeriodo"]'
                    '/*[local-name()="Distrito"]/*[local-name()="Comunas"]'
                ),
            )
        ),
    }


def parse_legislature_ids(content: bytes) -> list[str]:
    root = parse_xml(content)
    values = cast(
        list[str],
        root.xpath('//*[local-name()="Legislatura"]/*[local-name()="Id"]/text()'),
    )
    return list(dict.fromkeys(values))


def celebrated_sample(
    sessions: list[Session], size: int = 3, *, year: int | None = None
) -> list[Session]:
    celebrated = [session for session in sessions if session.state == "Celebrada"]
    if year is not None:
        celebrated = [
            session for session in celebrated if session.started_at.year == year
        ]
    return sorted(celebrated, key=lambda item: item.started_at, reverse=True)[:size]


def normalized_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name)
    return " ".join(
        "".join(
            character
            for character in decomposed
            if not unicodedata.combining(character)
        )
        .casefold()
        .split()
    )


def parse_bcn_deputy_names(content: bytes) -> list[str]:
    document = html.fromstring(content)
    cells = cast(
        list[html.HtmlElement],
        document.xpath('//tr[td[1][normalize-space()="Diputados"]]/td[2]'),
    )
    if len(cells) != 1:
        raise ValueError("Reporte BCN sin fila única de Diputados")
    text = " ".join(cells[0].text_content().split())
    return [name.strip() for name in text.split(",") if name.strip()]


def match_bcn_validation(
    names: list[str], deputies: list[DeputyPeriod]
) -> list[DeputyPeriod]:
    by_name = {normalized_name(deputy.name): deputy for deputy in deputies}
    return [
        by_name[normalized_name(name)]
        for name in names
        if normalized_name(name) in by_name
    ]


def find_entity_match(
    deputies: list[DeputyPeriod],
    attendance: dict[str, Attendance],
    votes: dict[str, IndividualVote],
) -> tuple[DeputyPeriod, Attendance, IndividualVote] | None:
    for deputy in deputies:
        if deputy.deputy_id in attendance and deputy.deputy_id in votes:
            return deputy, attendance[deputy.deputy_id], votes[deputy.deputy_id]
    return None


def explore(district: int, timeout: float) -> tuple[dict[str, Any], bool]:
    with httpx.Client(
        timeout=httpx.Timeout(timeout),
        headers={"User-Agent": USER_AGENT, "Accept": "application/xml, text/xml"},
        follow_redirects=True,
    ) as client:
        recorder = RawRecorder(client, RAW_DIR)

        current_by_protocol: dict[str, bytes] = {}
        district_matrix: dict[str, dict[str, int]] = {}
        for protocol in ("http_get", "http_post", "soap11", "soap12"):
            raw = recorder.request(
                "retornarDiputadosPeriodoActual",
                protocol,
                service="diputado",
            )
            payload = unwrap_soap(raw)
            current_by_protocol[protocol] = payload
            district_matrix[protocol] = raw_district_presence(raw)

        deputies = parse_deputy_periods(current_by_protocol["http_get"])
        approved_district_deputies = [
            deputy for deputy in deputies if deputy.district == str(district)
        ]

        period_xml = recorder.request(
            "retornarPeriodoLegislativoActual",
            "http_get",
            service="legislativo",
        )
        _, current_legislature_id = parse_current_period(period_xml)
        legislatures_xml = recorder.request(
            "retornarLegislaturas", "http_get", service="legislativo"
        )
        legislature_ids = parse_legislature_ids(legislatures_xml)
        current_index = legislature_ids.index(current_legislature_id)
        prior_legislature_id = legislature_ids[current_index - 1]

        session_sets: dict[str, list[Session]] = {}
        session_contract_samples: list[dict[str, Any]] = []
        attendance_by_session: dict[str, dict[str, Attendance]] = {}
        prior_sample_year = max(
            session.started_at.year
            for session in parse_sessions(
                recorder.request(
                    "retornarSesionesXLegislatura",
                    "http_get",
                    service="sala",
                    params={"prmLegislaturaId": prior_legislature_id},
                )
            )
            if session.started_at.year < datetime.now().year
        )
        for label, legislature_id in (
            ("recent", current_legislature_id),
            ("prior", prior_legislature_id),
        ):
            sessions_xml = recorder.request(
                "retornarSesionesXLegislatura",
                "http_get",
                service="sala",
                params={"prmLegislaturaId": legislature_id},
            )
            sessions = parse_sessions(sessions_xml)
            session_sets[label] = sessions
            sample_year = prior_sample_year if label == "prior" else None
            for session in celebrated_sample(sessions, year=sample_year):
                for protocol in ("http_get", "soap11"):
                    detail_raw = recorder.request(
                        "retornarSesionAsistencia",
                        protocol,
                        service="sala",
                        params={"prmSesionId": session.session_id},
                    )
                    detail = unwrap_soap(detail_raw)
                    contract = inspect_session_votes(detail)
                    session_contract_samples.append(
                        {
                            "period": label,
                            "protocol": protocol,
                            "session_id": session.session_id,
                            "votaciones_present": contract.container_present,
                            "vote_ids": list(contract.vote_ids),
                        }
                    )
                    if protocol == "http_get":
                        attendance_by_session[session.session_id] = parse_attendance(
                            detail
                        )

        current_year = max(
            session.started_at for session in session_sets["recent"]
        ).year
        prior_year = prior_sample_year
        for year in (current_year, prior_year):
            recorder.request(
                "retornarSesionesXAnno",
                "http_get",
                service="sala",
                params={"prmAnno": str(year)},
            )

        votes_xml = recorder.request(
            "retornarVotacionesXAnno",
            "http_get",
            service="legislativo",
            params={"prmAnno": str(current_year)},
        )
        vote_summaries = parse_vote_summaries(votes_xml)
        selected_summary = max(vote_summaries, key=lambda vote: vote.voted_at)
        vote_xml = recorder.request(
            "retornarVotacionDetalle",
            "http_get",
            service="legislativo",
            params={"prmVotacionId": selected_summary.vote_id},
        )
        vote_detail = parse_vote_detail(vote_xml)

        bcn_html = recorder.external_get(
            "bcn_reporte_distrital",
            BCN_REPORT,
            params={"anno": str(current_year), "distrito": str(district)},
        )
        bcn_names = parse_bcn_deputy_names(bcn_html)
        bcn_matches = match_bcn_validation(bcn_names, deputies)

        productive_match = None
        productive_session = None
        for session_id, attendance in attendance_by_session.items():
            productive_match = find_entity_match(
                approved_district_deputies,
                attendance,
                vote_detail.individual_votes,
            )
            if productive_match:
                productive_session = next(
                    session
                    for session in session_sets["recent"]
                    if session.session_id == session_id
                )
                break

        validation_match = None
        validation_session = None
        for session_id, attendance in attendance_by_session.items():
            validation_match = find_entity_match(
                bcn_matches, attendance, vote_detail.individual_votes
            )
            if validation_match:
                validation_session = next(
                    session
                    for session in session_sets["recent"]
                    if session.session_id == session_id
                )
                break

    complete = productive_match is not None and productive_session is not None
    match, selected_attendance, individual_vote = (
        productive_match if productive_match else (None, None, None)
    )
    validation_deputy, validation_attendance, validation_vote = (
        validation_match if validation_match else (None, None, None)
    )
    explicit_links = [
        sample for sample in session_contract_samples if sample["vote_ids"]
    ]
    summary: dict[str, Any] = {
        "status": (
            "complete_v0_contract" if complete else "incomplete_source_contract"
        ),
        "district_requested": district,
        "district_source_operation": (
            "retornarDiputadosPeriodoActual" if approved_district_deputies else None
        ),
        "district_raw_matrix": district_matrix,
        "district_deputies_found": len(approved_district_deputies),
        "deputy": (
            {
                "official_id": match.deputy_id,
                "name": match.name,
                "district": int(match.district or district),
                "district_source_operation": "retornarDiputadosPeriodoActual",
            }
            if match
            else None
        ),
        "attendance": (
            {
                "session_id": productive_session.session_id,
                "session_date": productive_session.started_at.isoformat(),
                "raw_status": selected_attendance.original_status,
                "confirmed_by_deputy_id": True,
            }
            if selected_attendance and productive_session
            else None
        ),
        "individual_vote": (
            {
                "vote_event_id": vote_detail.vote_id,
                "date": vote_detail.voted_at.isoformat(),
                "description": vote_detail.description,
                "raw_option": individual_vote.original_option,
                "confirmed_by_deputy_id": True,
                "session_id": vote_detail.session_id,
            }
            if individual_vote
            else None
        ),
        "session_vote_contract": {
            "samples": session_contract_samples,
            "explicit_links_found": len(explicit_links),
            "vote_session_id": vote_detail.session_id,
            "temporal_candidate": None,
        },
        "bcn_external_validation": {
            "productive_source": False,
            "reason": (
                "HTML server-rendered sin IDs oficiales de Cámara ni API "
                "estructurada documentada; se usa solo para validar cantidad/nombres."
            ),
            "expected_deputies": len(bcn_names),
            "names_matched_to_open_data": len(bcn_matches),
            "matched_official_ids": [deputy.deputy_id for deputy in bcn_matches],
            "entity_id_consistency_sample": (
                {
                    "official_id": validation_deputy.deputy_id,
                    "attendance": validation_attendance is not None,
                    "individual_vote": validation_vote is not None,
                    "not_productive_district_chain": True,
                    "session_id": (
                        validation_session.session_id if validation_session else None
                    ),
                }
                if validation_deputy
                else None
            ),
        },
        "evidence": recorder.files,
        "decision": {
            "deputy_official_id": "entity_resolution_key",
            "vote_session_id": "nullable",
            "temporal_match_as_confirmed_link": "forbidden",
            "bcn_html_as_automatic_productive_source": "not_approved",
        },
        "executed_at": datetime.now().astimezone().isoformat(),
    }
    return summary, complete


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--district", type=int, default=19)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    try:
        summary, complete = explore(args.district, args.timeout)
    except (httpx.HTTPError, ValueError, RuntimeError) as error:
        print(
            json.dumps(
                {"status": "request_or_contract_error", "error": str(error)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    sys.exit(main())
