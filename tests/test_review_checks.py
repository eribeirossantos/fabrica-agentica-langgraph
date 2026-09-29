"""Checklist da revisão, sem passar pelo grafo."""

from __future__ import annotations

from fabrica.review_checks import evaluate_package

ISSUE = {"acceptance_criteria": ["um", "dois"]}
DESIGN_OK = {
    "do_not_touch": ["navegação"],
    "copy_pt_br": [{"onde": "Botão", "texto": "Pagar doação"}],
    "accessibility": ["WCAG 2.1 AA — contraste (1.4.3)."],
}
DEV_OK = {
    "files_and_areas": ["app/checkout/PayButton.tsx"],
    "test_plan": ["CA1. cobre o primeiro.", "CA2. cobre o segundo."],
    "pr_evidence": ["teste no CI"],
}


def test_pacote_completo_aprova() -> None:
    result = evaluate_package(ISSUE, DESIGN_OK, DEV_OK)
    assert result.verdict == "aprovado"
    assert result.target == "nenhum"


def test_perimetro_vazio_devolve_para_design() -> None:
    design = {**DESIGN_OK, "do_not_touch": []}
    result = evaluate_package(ISSUE, design, DEV_OK)
    assert result.verdict == "devolver"
    assert result.target == "design"
    assert any("Perímetro" in item for item in result.findings)


def test_criterio_descoberto_devolve_para_dev() -> None:
    dev = {**DEV_OK, "test_plan": ["CA1. só o primeiro."]}
    result = evaluate_package(ISSUE, DESIGN_OK, dev)
    assert result.verdict == "devolver"
    assert result.target == "dev"
    assert any("CA2" in item for item in result.findings)
