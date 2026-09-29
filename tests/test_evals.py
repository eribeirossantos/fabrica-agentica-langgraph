"""Avaliação offline do dataset versionado."""

from __future__ import annotations

from fabrica.cli import main
from fabrica.evals.runner import format_report, run_evals


def test_metricas_fecham_no_stub() -> None:
    report = run_evals()
    assert report.total == 8
    assert report.aprovado()
    texto = format_report(report)
    assert "acerto de classificação: 1.00" in texto
    assert "perímetro respeitado: 1.00" in texto


def test_comando_evals(capsys) -> None:
    assert main(["evals"]) == 0
    saida = capsys.readouterr().out
    assert "acerto de prioridade: 1.00" in saida
