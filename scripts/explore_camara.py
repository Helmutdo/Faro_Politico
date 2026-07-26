#!/usr/bin/env python3
"""Spike reproducible de los servicios XML oficiales de la Cámara.

Guarda cada respuesta sin modificar en ``data/raw`` y emite un resumen JSON.
No escribe en PostgreSQL ni constituye el ETL definitivo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from trama_publica.etl.camara_xml import (
    Attendance,
    DeputyPeriod,
    IndividualVote,
    Session,
    VoteSummary,
    parse_attendance,
    parse_current_period,
    parse_deputy_periods,
    parse_individual_votes,
    parse_sessions,
    parse_vote_summaries,
)

BASE = "https://opendata.camara.cl/camaradiputados/WServices"
USER_AGENT = (
    "TramaPublica-Spike/0.1 "
    "(transparencia parlamentaria; repositorio github.com/Helmutdo/Faro_Politico)"
)
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

ENDPOINTS = {
    "diputados_wsdl": f"{BASE}/WSDiputado.asmx?WSDL",
    "legislativo_wsdl": f"{BASE}/WSLegislativo.asmx?WSDL",
    "sala_wsdl": f"{BASE}/WSSala.asmx?WSDL",
    "periodo_actual": f"{BASE}/WSLegislativo.asmx/retornarPeriodoLegislativoActual",
    "diputados_periodo": f"{BASE}/WSDiputado.asmx/retornarDiputadosXPeriodo",
    "sesiones_legislatura": f"{BASE}/WSSala.asmx/retornarSesionesXLegislatura",
    "sesion_asistencia": f"{BASE}/WSSala.asmx/retornarSesionAsistencia",
    "votaciones_anno": f"{BASE}/WSLegislativo.asmx/retornarVotacionesXAnno",
    "votacion_detalle": f"{BASE}/WSLegislativo.asmx/retornarVotacionDetalle",
}


class RawRecorder:
    def __init__(self, client: httpx.Client, raw_dir: Path) -> None:
        self.client = client
        self.raw_dir = raw_dir
        self.files: list[dict[str, Any]] = []
        raw_dir.mkdir(parents=True, exist_ok=True)

    def get(self, operation: str, *, params: dict[str, str] | None = None) -> bytes:
        response = self.client.get(ENDPOINTS[operation], params=params)
        response.raise_for_status()
        digest = hashlib.sha256(response.content).hexdigest()
        suffix = "_".join(f"{key}-{value}" for key, value in (params or {}).items())
        stem = f"{operation}_{suffix}" if suffix else operation
        path = self.raw_dir / f"{stem}_{digest[:12]}.xml"
        path.write_bytes(response.content)
        self.files.append(
            {
                "operation": operation,
                "url": str(response.url),
                "status_code": response.status_code,
                "bytes": len(response.content),
                "sha256": digest,
                "file": str(path.relative_to(ROOT)),
            }
        )
        return response.content


def choose_session_and_vote(
    sessions: list[Session], votes: list[VoteSummary]
) -> tuple[Session, VoteSummary]:
    """Match by timestamp because the real vote response has no session ID."""
    matches = [
        (session, vote)
        for vote in votes
        for session in sessions
        if session.started_at <= vote.voted_at <= session.ended_at
    ]
    if not matches:
        raise RuntimeError(
            "No hay votación cuyo timestamp caiga dentro de una sesión retornada"
        )
    return max(matches, key=lambda pair: pair[1].voted_at)


def select_district_vote(
    deputies: list[DeputyPeriod],
    attendance: dict[str, Attendance],
    votes: dict[str, IndividualVote],
    district: str,
) -> tuple[DeputyPeriod, Attendance, IndividualVote] | None:
    for deputy in deputies:
        if (
            deputy.district == district
            and deputy.deputy_id in attendance
            and deputy.deputy_id in votes
        ):
            return deputy, attendance[deputy.deputy_id], votes[deputy.deputy_id]
    return None


def explore(district: int, timeout: float) -> tuple[dict[str, Any], bool]:
    with httpx.Client(
        timeout=httpx.Timeout(timeout),
        headers={"User-Agent": USER_AGENT, "Accept": "application/xml, text/xml"},
        follow_redirects=True,
    ) as client:
        recorder = RawRecorder(client, RAW_DIR)
        for wsdl in ("diputados_wsdl", "legislativo_wsdl", "sala_wsdl"):
            recorder.get(wsdl)

        period_xml = recorder.get("periodo_actual")
        period_id, legislature_id = parse_current_period(period_xml)

        deputies_xml = recorder.get(
            "diputados_periodo", params={"prmPeriodoID": period_id}
        )
        deputies = parse_deputy_periods(deputies_xml)
        district_deputies = [
            deputy for deputy in deputies if deputy.district == str(district)
        ]

        sessions_xml = recorder.get(
            "sesiones_legislatura",
            params={"prmLegislaturaId": legislature_id},
        )
        sessions = parse_sessions(sessions_xml)

        year = max(session.started_at for session in sessions).year
        votes_xml = recorder.get("votaciones_anno", params={"prmAnno": str(year)})
        vote_summaries = parse_vote_summaries(votes_xml)
        session, vote = choose_session_and_vote(sessions, vote_summaries)

        attendance_xml = recorder.get(
            "sesion_asistencia", params={"prmSesionId": session.session_id}
        )
        attendance = parse_attendance(attendance_xml)
        vote_xml = recorder.get(
            "votacion_detalle", params={"prmVotacionId": vote.vote_id}
        )
        individual_votes = parse_individual_votes(vote_xml)
        match = select_district_vote(
            deputies, attendance, individual_votes, str(district)
        )

    diagnostics: list[str] = []
    if not any(deputy.district for deputy in deputies):
        diagnostics.append(
            "BLOQUEANTE: retornarDiputadosXPeriodo omitió DiputadoPeriodo/Distrito "
            "aunque el XSD/WSDL lo declara; no es posible identificar el Distrito "
            f"{district} sin inventar o incorporar otra fuente."
        )
    diagnostics.append(
        "La relación sesión-votación es una inferencia temporal: la respuesta real "
        "de votación no incluye un identificador de sesión."
    )
    complete = match is not None
    selected_deputy, selected_attendance, selected_vote = (
        match if match else (None, None, None)
    )
    summary: dict[str, Any] = {
        "status": "complete" if complete else "incomplete_source_contract",
        "district_requested": district,
        "period_id": period_id,
        "legislature_id": legislature_id,
        "district_deputies_found": len(district_deputies),
        "deputy": asdict(selected_deputy) if selected_deputy else None,
        "session": {
            "id": session.session_id,
            "number": session.number,
            "date": session.started_at.isoformat(),
            "attendance_original": (
                selected_attendance.original_status if selected_attendance else None
            ),
            "source": ENDPOINTS["sesion_asistencia"],
        },
        "vote": {
            "id": vote.vote_id,
            "description": vote.description,
            "date": vote.voted_at.isoformat(),
            "option_original": (
                selected_vote.original_option if selected_vote else None
            ),
            "source": ENDPOINTS["votacion_detalle"],
        },
        "evidence": recorder.files,
        "diagnostics": diagnostics,
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
