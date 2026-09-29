"""Grafo da fábrica: produto, aprovação humana, design, dev, revisão e publicação.

O approval usa ``interrupt``. O nó recomeça do zero quando a execução é
retomada, então não há efeito colateral antes do interrupt — o registro de
status da decisão só é gravado depois que a resposta chega.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from fabrica.policy import (
    TYPE_DISPLAY,
    classify_request,
    infer_area,
    normalize,
    prioritize_request,
    split_prefix,
)
from fabrica.prompts import DESIGN_PROMPT, DEV_PROMPT, PRODUCT_PROMPT
from fabrica.rag.retriever import get_retriever
from fabrica.render import render_document, render_markdown
from fabrica.review_checks import evaluate_package
from fabrica.schemas import DesignSpec, DevPlan, ProductDraft
from fabrica.state import FactoryState
from fabrica.stub import StubModel
from fabrica.telemetry import span
from fabrica.tools import buscar_conhecimento

MAX_APPROVAL_ROUNDS = 3
MAX_REVIEW_ITERATIONS = 3

_APPROVE = {"approve", "aprovar", "sim", "s", "y", "yes"}

NODE_LABELS = {
    "__start__": "início",
    "product": "Produto",
    "approval": "Aprovação humana",
    "design": "Design",
    "dev": "Dev",
    "review": "Revisão",
    "publish": "Publicação",
    "__end__": "fim",
}

EDGE_LABELS = {
    ("approval", "design"): "aprova",
    ("approval", "product"): "rejeita",
    ("approval", "publish"): "limite de rejeições",
    ("review", "publish"): "aprova ou encerra no limite",
    ("review", "design"): "devolver ao design",
    ("review", "dev"): "devolver ao dev",
}


def interpret_decision(value: Any) -> dict[str, str]:
    """Normaliza a resposta do product owner para approve ou reject."""
    if isinstance(value, str):
        approved = normalize(value) in _APPROVE
        feedback = "" if approved else (value.strip() or "Rejeitada sem comentário.")
        return {"decision": "approve" if approved else "reject", "feedback": feedback}
    if isinstance(value, dict):
        approved = normalize(str(value.get("decision", ""))) in _APPROVE
        feedback = str(value.get("feedback") or "").strip()
        if not approved and not feedback:
            feedback = "Rejeitada sem comentário."
        return {"decision": "approve" if approved else "reject", "feedback": feedback}
    return {"decision": "reject", "feedback": "Decisão inválida."}


def route_after_approval(state: FactoryState) -> str:
    """Aprova segue para design; rejeição volta ao produto até o limite."""
    if state.get("approval_decision") == "approve":
        return "design"
    if state.get("approval_rounds", 0) >= MAX_APPROVAL_ROUNDS:
        return "publish"
    return "product"


def route_after_review(state: FactoryState) -> str:
    """Revisão aprovada publica. Devolução respeita o limite de iterações."""
    review = state.get("review") or {}
    if review.get("verdict") == "aprovado":
        return "publish"
    if state.get("review_iterations", 0) >= MAX_REVIEW_ITERATIONS:
        return "publish"
    if review.get("target") == "design":
        return "design"
    return "dev"


def build_graph(
    model: Any = None,
    checkpointer: Any = None,
    *,
    models: dict[str, Any] | None = None,
    retriever: Any = None,
):
    """Compila o grafo. Sem checkpointer informado, usa memória do processo.

    ``model`` único vale para todos os agentes (é o que os testes injetam).
    ``models`` permite um provedor diferente por papel quando ``model`` não vem.
    """
    role_models = _role_models(model, models)
    if checkpointer is None:
        checkpointer = InMemorySaver()
    if retriever is None:
        retriever = get_retriever()

    def product(state: FactoryState) -> dict[str, Any]:
        raw = state["raw_request"]
        feedback = state.get("product_feedback") or ""
        issue_type = classify_request(raw)
        priority, reason = prioritize_request(raw, issue_type)
        area = infer_area(raw)
        _prefix, body = split_prefix(raw)
        system, user = _render(
            PRODUCT_PROMPT,
            {
                "request": raw,
                "body": body,
                "feedback": feedback,
                "type_label": issue_type,
                "priority": priority,
                "priority_reason": reason,
                "area_label": area,
            },
        )
        draft = role_models["product"].invoke(ProductDraft, system, user)
        issue = draft.model_dump()
        mark = f"Ajuste pedido pelo product owner: {feedback}" if feedback else ""
        if mark and mark not in issue["problem"]:
            issue["problem"] = f"{issue['problem'].rstrip()}\n\n{mark}"
        issue.update(
            {
                "type_label": issue_type,
                "area_label": area,
                "priority": priority,
                "priority_reason": reason,
                "source_request": raw,
            }
        )
        return {
            "issue": issue,
            "status_log": [
                {
                    "agent": "produto",
                    "status": "issue especificada",
                    "detail": f"{priority} · {TYPE_DISPLAY[issue_type]} · {area} — {issue['title']}",
                }
            ],
        }

    def approval(state: FactoryState) -> dict[str, Any]:
        # O interrupt pausa o grafo. Na retomada este nó roda de novo e
        # ``interrupt`` devolve a decisão, sem pausar outra vez.
        raw_decision = interrupt(
            {
                "kind": "aprovacao_da_issue",
                "message": (
                    "Aprove ou rejeite a issue. Uma rejeição com feedback "
                    "devolve o texto ao agente de produto."
                ),
                "issue": state.get("issue") or {},
                "round": state.get("approval_rounds", 0) + 1,
                "max_rounds": MAX_APPROVAL_ROUNDS,
            }
        )
        decision = interpret_decision(raw_decision)
        approved = decision["decision"] == "approve"
        updates: dict[str, Any] = {
            "approval_decision": decision["decision"],
            "approval_feedback": decision["feedback"],
            "status_log": [
                {
                    "agent": "product owner",
                    "status": "aprovado" if approved else "rejeitado",
                    "detail": decision["feedback"] or "Issue aprovada para design.",
                }
            ],
        }
        if not approved:
            updates["product_feedback"] = decision["feedback"]
            updates["approval_rounds"] = state.get("approval_rounds", 0) + 1
        return updates

    def design(state: FactoryState) -> dict[str, Any]:
        feedback = state.get("design_feedback") or ""
        issue = state.get("issue") or {}
        assunto = " ".join(
            str(issue.get(key) or "") for key in ("title", "problem", "expected_result")
        )
        fontes, conhecimento = _collect_sources(
            retriever,
            [
                f"{assunto} tom de voz copy botão português",
                f"{assunto} WCAG 2.1 contraste acessibilidade",
            ],
        )
        buscar_conhecimento.invoke({"consulta": f"{assunto} copy WCAG"})
        system, user = _render(
            DESIGN_PROMPT,
            {"issue": issue, "feedback": feedback, "conhecimento": conhecimento},
        )
        spec = role_models["design"].invoke(DesignSpec, system, user)
        data = spec.model_dump()
        data["fontes"] = fontes
        return {
            "design_spec": data,
            "status_log": [
                {
                    "agent": "design",
                    "status": "especificação de design pronta",
                    "detail": f"{len(spec.do_not_touch)} itens no perímetro.",
                }
            ],
        }

    def dev(state: FactoryState) -> dict[str, Any]:
        feedback = state.get("dev_feedback") or ""
        system, user = _render(
            DEV_PROMPT,
            {
                "issue": state.get("issue") or {},
                "design": state.get("design_spec") or {},
                "feedback": feedback,
            },
        )
        plan = role_models["dev"].invoke(DevPlan, system, user)
        return {
            "dev_plan": plan.model_dump(),
            "status_log": [
                {
                    "agent": "dev",
                    "status": "plano de implementação pronto",
                    "detail": f"{len(plan.test_plan)} testes planejados.",
                }
            ],
        }

    def review(state: FactoryState) -> dict[str, Any]:
        issue = state.get("issue") or {}
        criteria = " ".join(issue.get("acceptance_criteria") or [])
        fontes, _conhecimento = _collect_sources(
            retriever,
            [
                f"{criteria} dado quando então critério de aceite",
                "perímetro respeitado decisão de arquitetura",
            ],
        )
        buscar_conhecimento.invoke({"consulta": f"{criteria} critério de aceite perímetro"})
        result = evaluate_package(issue, state.get("design_spec") or {}, state.get("dev_plan") or {})
        if result.verdict == "aprovado":
            status = "revisão aprovada"
            detail = result.findings[0]
        elif result.target == "design":
            status = "devolvido para design"
            detail = "; ".join(result.findings)
        else:
            status = "devolvido para dev"
            detail = "; ".join(result.findings)
        review_data = result.model_dump()
        review_data["fontes"] = fontes
        updates: dict[str, Any] = {
            "review": review_data,
            "review_iterations": state.get("review_iterations", 0) + 1,
            "status_log": [{"agent": "revisão", "status": status, "detail": detail}],
        }
        if result.verdict != "aprovado" and result.target == "design":
            updates["design_feedback"] = "\n".join(result.findings)
        elif result.verdict != "aprovado" and result.target == "dev":
            updates["dev_feedback"] = "\n".join(result.findings)
        return updates

    def publish(state: FactoryState) -> dict[str, Any]:
        outcome = _outcome(state)
        event = _publish_event(outcome, state)
        enriched = dict(state)
        enriched["outcome"] = outcome
        enriched["status_log"] = list(state.get("status_log") or []) + [event]
        return {
            "outcome": outcome,
            "final_markdown": render_markdown(enriched),
            "final_document": render_document(enriched),
            "status_log": [event],
        }

    builder = StateGraph(FactoryState)
    builder.add_node("product", _traced("product", product))
    builder.add_node("approval", _traced("approval", approval))
    builder.add_node("design", _traced("design", design))
    builder.add_node("dev", _traced("dev", dev))
    builder.add_node("review", _traced("review", review))
    builder.add_node("publish", _traced("publish", publish))
    builder.add_edge(START, "product")
    builder.add_edge("product", "approval")
    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {"product": "product", "design": "design", "publish": "publish"},
    )
    builder.add_edge("design", "dev")
    builder.add_edge("dev", "review")
    builder.add_conditional_edges(
        "review",
        route_after_review,
        {"design": "design", "dev": "dev", "publish": "publish"},
    )
    builder.add_edge("publish", END)
    return builder.compile(checkpointer=checkpointer)


def graph_edges(compiled: Any = None) -> set[tuple[str, str]]:
    """Arestas do grafo compilado, inclusive as condicionais."""
    compiled = compiled or build_graph()
    pairs: set[tuple[str, str]] = set()
    for edge in compiled.get_graph().edges:
        source = str(getattr(edge, "source", edge[0]))
        target = str(getattr(edge, "target", edge[1]))
        pairs.add((source, target))
    return pairs


def readable_mermaid(compiled: Any = None) -> str:
    """Diagrama Mermaid legível, montado a partir das arestas compiladas."""
    compiled = compiled or build_graph()
    pairs = graph_edges(compiled)
    node_ids = {node for pair in pairs for node in pair}
    lines = ["flowchart TD"]
    for node_id in _node_order(node_ids):
        lines.append(_node_line(node_id))
    for source, target in sorted(pairs):
        label = EDGE_LABELS.get((source, target), "")
        if label:
            lines.append(f'    {source} -->|"{label}"| {target}')
        else:
            lines.append(f"    {source} --> {target}")
    return "\n".join(lines) + "\n"


def _node_order(node_ids: set[str]) -> list[str]:
    preferred = list(NODE_LABELS)
    ordered = [node_id for node_id in preferred if node_id in node_ids]
    ordered.extend(sorted(node_ids - set(ordered)))
    return ordered


def _node_line(node_id: str) -> str:
    label = NODE_LABELS.get(node_id, node_id)
    if node_id in {"__start__", "__end__"}:
        return f"    {node_id}([{label}])"
    return f'    {node_id}["{label}"]'


def _role_models(model: Any, models: dict[str, Any] | None) -> dict[str, Any]:
    roles = ("product", "design", "dev", "review")
    if model is not None:
        return {role: model for role in roles}
    fallback = StubModel()
    if not models:
        return {role: fallback for role in roles}
    return {role: models.get(role, fallback) for role in roles}


def _render(prompt: ChatPromptTemplate, payload: dict[str, Any]) -> tuple[str, str]:
    rendered = prompt.format_messages(payload=json.dumps(payload, ensure_ascii=False))
    return str(rendered[0].content), str(rendered[1].content)


def _collect_sources(retriever: Any, queries: list[str], limit: int = 3) -> tuple[list[str], str]:
    """Junta citações de cada consulta, sem deixar a primeira esgotar o limite."""
    fontes: list[str] = []
    blocks: list[str] = []
    seen: set[str] = set()
    per_query = 2
    for query in queries:
        taken = 0
        for document in retriever.invoke(query):
            citation = str(document.metadata.get("citation") or "")
            if not citation or citation in seen:
                continue
            seen.add(citation)
            fontes.append(citation)
            blocks.append(f"[{citation}]\n{document.page_content}")
            taken += 1
            if len(fontes) >= limit or taken >= per_query:
                break
        if len(fontes) >= limit:
            break
    return fontes, "\n\n".join(blocks)


def _traced(node_name: str, fn: Callable[[FactoryState], dict[str, Any]]) -> Callable[[FactoryState], dict[str, Any]]:
    def wrapped(state: FactoryState) -> dict[str, Any]:
        with span(f"fabrica.graph.{node_name}", node=node_name):
            return fn(state)

    return wrapped


def _outcome(state: FactoryState) -> str:
    if state.get("approval_decision") != "approve":
        return "cancelado"
    review = state.get("review") or {}
    if review.get("verdict") == "aprovado":
        return "publicado"
    return "encerrado_no_limite"


def _publish_event(outcome: str, state: FactoryState) -> dict[str, str]:
    if outcome == "publicado":
        return {
            "agent": "fábrica",
            "status": "publicado",
            "detail": "Issue publicada em Markdown e JSON.",
        }
    if outcome == "cancelado":
        return {
            "agent": "fábrica",
            "status": "cancelado sem aprovação",
            "detail": state.get("approval_feedback") or "Limite de rejeições atingido.",
        }
    findings = "; ".join((state.get("review") or {}).get("findings") or [])
    return {
        "agent": "fábrica",
        "status": "encerrado no limite de revisão",
        "detail": findings or "Limite de iterações atingido.",
    }
