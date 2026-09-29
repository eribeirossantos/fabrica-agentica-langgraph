"""Roda o dataset offline e imprime as métricas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fabrica.runner import execute

_DATASET = Path(__file__).with_name("dataset.json")


@dataclass(frozen=True)
class EvalReport:
    """Quatro razões entre zero e um. O conjunto cabe inteiro no modo offline."""

    total: int
    acerto_classificacao: float
    acerto_prioridade: float
    criterios_presentes: float
    perimetro_respeitado: float

    def aprovado(self) -> bool:
        return (
            self.acerto_classificacao == 1.0
            and self.acerto_prioridade == 1.0
            and self.criterios_presentes == 1.0
            and self.perimetro_respeitado == 1.0
        )


def load_dataset(path: Path | None = None) -> list[dict[str, str]]:
    raw = json.loads((path or _DATASET).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("O dataset de avaliação precisa ser uma lista.")
    return raw


def run_evals(path: Path | None = None) -> EvalReport:
    """Executa cada pedido com aprovação automática e o stub."""
    rows = load_dataset(path)
    tipo_ok = 0
    prioridade_ok = 0
    criterios_ok = 0
    perimetro_ok = 0
    for row in rows:
        state = execute(row["pedido"], auto_approve=True, offline=True)
        issue = state.get("issue") or {}
        design = state.get("design_spec") or {}
        review = state.get("review") or {}
        if issue.get("type_label") == row["tipo"]:
            tipo_ok += 1
        if issue.get("priority") == row["prioridade"]:
            prioridade_ok += 1
        if issue.get("acceptance_criteria"):
            criterios_ok += 1
        if design.get("do_not_touch") and review.get("verdict") == "aprovado":
            perimetro_ok += 1
    total = len(rows)
    return EvalReport(
        total=total,
        acerto_classificacao=_ratio(tipo_ok, total),
        acerto_prioridade=_ratio(prioridade_ok, total),
        criterios_presentes=_ratio(criterios_ok, total),
        perimetro_respeitado=_ratio(perimetro_ok, total),
    )


def format_report(report: EvalReport) -> str:
    linhas = [
        f"casos: {report.total}",
        f"acerto de classificação: {report.acerto_classificacao:.2f}",
        f"acerto de prioridade: {report.acerto_prioridade:.2f}",
        f"critérios de aceite presentes: {report.criterios_presentes:.2f}",
        f"perímetro respeitado: {report.perimetro_respeitado:.2f}",
    ]
    return "\n".join(linhas)


def run_cli(_argv: list[str] | None = None) -> int:
    report = run_evals()
    print(format_report(report))
    return 0 if report.aprovado() else 1


def _ratio(hits: int, total: int) -> float:
    if total == 0:
        return 0.0
    return hits / total


def report_as_dict(report: EvalReport) -> dict[str, Any]:
    return {
        "total": report.total,
        "acerto_classificacao": report.acerto_classificacao,
        "acerto_prioridade": report.acerto_prioridade,
        "criterios_presentes": report.criterios_presentes,
        "perimetro_respeitado": report.perimetro_respeitado,
    }
