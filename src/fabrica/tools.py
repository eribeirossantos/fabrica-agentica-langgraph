"""Tools explícitas do LangChain usadas pelos agentes e pelo servidor MCP."""

from __future__ import annotations

from langchain_core.tools import tool

from fabrica.rag.retriever import search


@tool
def buscar_conhecimento(consulta: str) -> str:
    """Busca trechos da base de conhecimento: copy pt-BR, WCAG, ADRs e critérios de aceite."""
    hits = search(consulta, k=3)
    if not hits:
        return "Nenhum trecho encontrado."
    blocks = [f"Fonte: {hit.citation}\n{hit.text}" for hit in hits]
    return "\n\n".join(blocks)
