"""Publicação da issue em Markdown e JSON."""

from __future__ import annotations

from typing import Any

from fabrica import __version__
from fabrica.policy import PRIORITY_REASONS, TYPE_DISPLAY

OUTCOME_LABEL = {
    "publicado": "Publicada após aprovação e revisão.",
    "cancelado": "Cancelada: o product owner não aprovou dentro do limite de rodadas.",
    "encerrado_no_limite": "Encerrada no limite de revisões, com pendências registradas.",
}


def format_status_line(event: dict[str, str]) -> str:
    """Uma linha do canal de status."""
    return f"[{event['agent']}] {event['status']} — {event['detail']}"


def format_status_log(events: list[dict[str, str]]) -> str:
    return "\n".join(format_status_line(event) for event in events)


def _bullets(items: list[str]) -> str:
    if not items:
        return "- (vazio)"
    return "\n".join(f"- {item}" for item in items)


def _criteria(items: list[str]) -> str:
    if not items:
        return "- (sem critérios)"
    lines = []
    for index, item in enumerate(items, start=1):
        lines.append(f"- [ ] CA{index}. {item}")
    return "\n".join(lines)


def render_document(state: dict[str, Any]) -> dict[str, Any]:
    """Documento JSON estável, sem relógio e sem segredo."""
    return {
        "schema_version": "1",
        "fabrica_version": __version__,
        "pedido": state.get("raw_request", ""),
        "resultado": state.get("outcome", ""),
        "resultado_descricao": OUTCOME_LABEL.get(state.get("outcome", ""), ""),
        "issue": state.get("issue") or {},
        "design": state.get("design_spec") or {},
        "plano_de_implementacao": state.get("dev_plan") or {},
        "revisao": state.get("review") or {},
        "registro_de_status": list(state.get("status_log") or []),
    }


def render_markdown(state: dict[str, Any]) -> str:
    """Issue final para leitura humana."""
    issue = state.get("issue") or {}
    outcome = state.get("outcome") or ""
    title = issue.get("title") or "Pedido sem título"
    headlines = {
        "cancelado": f"# Issue cancelada: {title}",
        "encerrado_no_limite": f"# Issue com revisão incompleta: {title}",
    }
    lines = [headlines.get(outcome, f"# Issue: {title}"), ""]
    description = OUTCOME_LABEL.get(outcome)
    if description:
        lines.extend([f"> {description}", ""])

    issue_type = issue.get("type_label", "")
    priority = issue.get("priority", "")
    area = issue.get("area_label", "")
    reason = issue.get("priority_reason") or PRIORITY_REASONS.get(priority, "")
    type_label = TYPE_DISPLAY.get(issue_type, issue_type)
    lines.extend(
        [
            f"- **Pedido original:** {state.get('raw_request', '')}",
            f"- **Tipo:** {type_label}",
            f"- **Área:** {area}",
            f"- **Prioridade:** {priority} — {reason}",
            f"- **Labels:** `tipo:{issue_type}` `área:{area}` `prioridade:{priority}`",
            "",
            "## Resumo",
            "",
            issue.get("summary") or "",
            "",
            "## Problema",
            "",
            issue.get("problem") or "",
            "",
            "## Resultado esperado",
            "",
            issue.get("expected_result") or "",
            "",
            "## Menor incremento seguro",
            "",
            issue.get("smallest_increment") or "",
            "",
            "## Fora de escopo",
            "",
            _bullets(issue.get("out_of_scope") or []),
            "",
            "## Riscos",
            "",
            _bullets(issue.get("risks") or []),
            "",
            "## Critérios de aceite",
            "",
            _criteria(issue.get("acceptance_criteria") or []),
            "",
        ]
    )

    design = state.get("design_spec") or {}
    if design:
        lines.extend(["## Especificação de design", "", "### Perímetro (não tocar)", ""])
        lines.append(_bullets(design.get("do_not_touch") or []))
        lines.extend(["", "### Mudanças de UI", ""])
        lines.append(_bullets(design.get("ui_changes") or []))
        lines.extend(["", "### Copy (pt-BR)", ""])
        copies = design.get("copy_pt_br") or []
        if copies:
            for block in copies:
                lines.append(f"- **{block.get('onde', '')}:** {block.get('texto', '')}")
        else:
            lines.append("- (sem copy)")
        lines.extend(["", "### Acessibilidade (WCAG 2.1 AA)", ""])
        lines.append(_bullets(design.get("accessibility") or []))
        lines.append("")

    plan = state.get("dev_plan") or {}
    if plan:
        lines.extend(
            [
                "## Plano de implementação",
                "",
                plan.get("notes") or "",
                "",
                "### Arquivos e áreas",
                "",
                _bullets(plan.get("files_and_areas") or []),
                "",
                "### Plano de testes",
                "",
                _bullets(plan.get("test_plan") or []),
                "",
                "### Evidências esperadas no PR",
                "",
                _bullets(plan.get("pr_evidence") or []),
                "",
            ]
        )

    review = state.get("review") or {}
    if review:
        lines.extend(["## Revisão", ""])
        target = review.get("target") or "nenhum"
        lines.append(f"- **Veredito:** {review.get('verdict', '')}")
        lines.append(f"- **Destino:** {target}")
        lines.extend(["", _bullets(review.get("findings") or []), ""])

    lines.extend(["## Registro de status", "", format_status_log(state.get("status_log") or []), ""])
    return "\n".join(lines)
