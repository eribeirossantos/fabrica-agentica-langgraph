"""Executa o grafo até o fim, retomando a aprovação humana quando ela pausa."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from langgraph.types import Command

from fabrica.graph import build_graph
from fabrica.llm import build_models
from fabrica.state import FactoryState
from fabrica.telemetry import configure_observability

Approver = Callable[[dict[str, Any]], dict[str, str]]


def initial_state(raw_request: str) -> FactoryState:
    """Estado inicial de um pedido."""
    return {
        "raw_request": raw_request.strip(),
        "product_feedback": "",
        "approval_rounds": 0,
        "approval_decision": "",
        "approval_feedback": "",
        "issue": {},
        "design_spec": {},
        "design_feedback": "",
        "dev_plan": {},
        "dev_feedback": "",
        "review": {},
        "review_iterations": 0,
        "status_log": [],
        "outcome": "",
        "final_markdown": "",
        "final_document": {},
    }


def execute(
    raw_request: str,
    *,
    auto_approve: bool = False,
    offline: bool | None = None,
    model: Any = None,
    approver: Approver | None = None,
    thread_id: str | None = None,
    checkpointer: Any = None,
    on_status: Callable[[dict[str, str]], None] | None = None,
) -> FactoryState:
    """Roda o fluxo. Sem ``auto_approve`` nem ``approver``, pergunta no terminal."""
    configure_observability()
    if model is not None:
        graph = build_graph(model=model, checkpointer=checkpointer)
    else:
        graph = build_graph(models=build_models(offline=offline), checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}, "recursion_limit": 50}
    graph.invoke(initial_state(raw_request), config)
    seen = 0
    while True:
        snapshot = graph.get_state(config)
        events = list(snapshot.values.get("status_log") or [])
        if on_status is not None:
            for event in events[seen:]:
                on_status(event)
        seen = len(events)
        if not snapshot.interrupts:
            break
        payload = snapshot.interrupts[0].value
        if auto_approve:
            decision = {"decision": "approve", "feedback": ""}
        elif approver is not None:
            decision = approver(payload)
        else:
            decision = prompt_approval(payload)
        graph.invoke(Command(resume=decision), config)
    values = graph.get_state(config).values
    return values  # type: ignore[return-value]


def prompt_approval(payload: dict[str, Any]) -> dict[str, str]:
    """Pergunta ao product owner se a issue segue para design."""
    issue = payload.get("issue") or {}
    round_number = payload.get("round") or 1
    max_rounds = payload.get("max_rounds") or 1
    print()
    print(f"Issue para aprovação (rodada {round_number} de {max_rounds})")
    print(f"Título: {issue.get('title', '')}")
    print(f"Prioridade: {issue.get('priority', '')} — {issue.get('priority_reason', '')}")
    print(f"Tipo: {issue.get('type_label', '')}")
    print(f"Área: {issue.get('area_label', '')}")
    print()
    print("Problema:")
    print(issue.get("problem", ""))
    print()
    print("Menor incremento:")
    print(issue.get("smallest_increment", ""))
    print()
    while True:
        try:
            answer = input("Aprovar esta issue? [s]im / [n]ão: ")
        except EOFError:
            return {"decision": "reject", "feedback": "Entrada encerrada."}
        normalized = answer.strip().lower()
        if normalized in {"s", "sim", "a", "aprovar", "approve", "y", "yes"}:
            return {"decision": "approve", "feedback": ""}
        if normalized in {"n", "nao", "não", "r", "rejeitar", "reject"}:
            try:
                feedback = input("Feedback para o agente de produto: ").strip()
            except EOFError:
                feedback = ""
            return {
                "decision": "reject",
                "feedback": feedback or "Rejeitada sem comentário.",
            }
        print("Responda s ou n.")
