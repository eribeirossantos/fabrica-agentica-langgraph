"""Revisão objetiva do pacote.

O veredito não depende do modelo. A checagem olha perímetro, copy, WCAG e
cobertura dos critérios de aceite no plano de testes. Isso deixa o laço
condicional testável e impede que uma alucinação aprove um pacote incompleto
ou rejeite um pacote completo para sempre.
"""

from __future__ import annotations

import re
from typing import Any

from fabrica.schemas import ReviewResult


def evaluate_package(issue: dict[str, Any], design: dict[str, Any], dev: dict[str, Any]) -> ReviewResult:
    """Compara design e plano com os critérios e com o perímetro."""
    design_findings: list[str] = []
    dev_findings: list[str] = []
    design = design or {}
    dev = dev or {}

    if not design.get("do_not_touch"):
        design_findings.append("Perímetro vazio: declare o que não pode ser alterado.")
    if not design.get("copy_pt_br"):
        design_findings.append("Falta a copy final em pt-BR.")
    accessibility = " ".join(design.get("accessibility") or [])
    if "WCAG" not in accessibility or "2.1" not in accessibility:
        design_findings.append("Faltam requisitos de acessibilidade WCAG 2.1 AA.")

    if not dev.get("files_and_areas"):
        dev_findings.append("Plano sem arquivos ou áreas.")
    if not dev.get("test_plan"):
        dev_findings.append("Plano de testes vazio.")
    if not dev.get("pr_evidence"):
        dev_findings.append("Faltam evidências esperadas no PR.")

    test_blob = " ".join(dev.get("test_plan") or [])
    for index, _criterion in enumerate(issue.get("acceptance_criteria") or [], start=1):
        if re.search(rf"\bCA{index}\b", test_blob) is None:
            dev_findings.append(f"O plano de testes não cobre o critério CA{index}.")

    if design_findings:
        return ReviewResult(
            verdict="devolver",
            target="design",
            findings=design_findings + dev_findings,
        )
    if dev_findings:
        return ReviewResult(verdict="devolver", target="dev", findings=dev_findings)
    return ReviewResult(
        verdict="aprovado",
        target="nenhum",
        findings=["Pacote cobre os critérios de aceite e respeita o perímetro."],
    )
