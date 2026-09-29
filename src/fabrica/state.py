"""Estado tipado do grafo.

Cada agente devolve só o pedaço que alterou. O registro de status usa um
redutor que acumula eventos, no mesmo espírito de um canal de status: nada
se perde quando o fluxo volta para um agente anterior.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class StatusEvent(TypedDict):
    """Uma transição publicada no canal de status."""

    agent: str
    status: str
    detail: str


class FactoryState(TypedDict, total=False):
    """Estado compartilhado da fábrica, do pedido até a issue publicada."""

    raw_request: str
    product_feedback: str
    approval_rounds: int
    approval_decision: str
    approval_feedback: str
    issue: dict[str, Any]
    design_spec: dict[str, Any]
    design_feedback: str
    dev_plan: dict[str, Any]
    dev_feedback: str
    review: dict[str, Any]
    review_iterations: int
    status_log: Annotated[list[StatusEvent], operator.add]
    outcome: str
    final_markdown: str
    final_document: dict[str, Any]
