"""Saídas estruturadas de cada agente.

Os modelos Pydantic são o contrato do grafo. No modo com API, o chat model
preenche esses campos via structured output. No modo offline, o stub preenche
os mesmos campos. Tipo, área e prioridade não entram no rascunho do modelo:
a política determinística grava esses três depois.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProductDraft(BaseModel):
    """Narrativa da issue. Classificação e prioridade vêm da política."""

    title: str = Field(description="Título curto da issue, em português.")
    summary: str = Field(description="Resumo de uma ou duas frases.")
    problem: str = Field(description="Problema observado, em português.")
    expected_result: str = Field(description="Resultado esperado para quem usa o produto.")
    smallest_increment: str = Field(description="Menor incremento seguro que resolve o pedido.")
    out_of_scope: list[str] = Field(description="O que fica de fora deste incremento.")
    risks: list[str] = Field(description="Riscos de implementar este incremento.")
    acceptance_criteria: list[str] = Field(
        description="Critérios de aceite verificáveis, no formato dado/quando/então."
    )


class CopyBlock(BaseModel):
    """Trecho final de interface."""

    onde: str = Field(description="Lugar da interface em que o texto aparece.")
    texto: str = Field(description="Texto final em português do Brasil.")


class DesignSpec(BaseModel):
    """Especificação de UI e copy, com perímetro e acessibilidade."""

    do_not_touch: list[str] = Field(description="Perímetro: o que não pode ser alterado.")
    ui_changes: list[str] = Field(description="Mudanças de interface dentro do perímetro.")
    copy_pt_br: list[CopyBlock] = Field(description="Copy final em português do Brasil.")
    accessibility: list[str] = Field(description="Requisitos WCAG 2.1 AA aplicáveis.")
    fontes: list[str] = Field(
        default_factory=list,
        description="Citações da base de conhecimento usadas nesta especificação.",
    )


class DevPlan(BaseModel):
    """Plano de implementação. Este agente não edita código."""

    files_and_areas: list[str] = Field(description="Arquivos ou áreas do aplicativo de exemplo.")
    test_plan: list[str] = Field(
        description="Plano de testes. Cada critério de aceite aparece como CA1, CA2, ..."
    )
    pr_evidence: list[str] = Field(description="Evidências que o PR precisa mostrar.")
    notes: str = Field(description="Observações do plano, em português.")


class ReviewResult(BaseModel):
    """Resultado da revisão do pacote contra critérios e perímetro."""

    verdict: Literal["aprovado", "devolver"]
    target: Literal["design", "dev", "nenhum"]
    findings: list[str] = Field(description="Achados objetivos da revisão.")
    fontes: list[str] = Field(
        default_factory=list,
        description="Citações da base de conhecimento usadas nesta revisão.",
    )
