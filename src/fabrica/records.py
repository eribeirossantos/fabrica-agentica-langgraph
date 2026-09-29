"""Projeção de um pedido, compartilhada pela API, pelo MCP e pelo banco."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IssueView:
    """Estado consultável de um pedido, fora do checkpoint do grafo."""

    id: str
    pedido: str
    fase: str
    resultado: str = ""
    registro_de_status: list[dict[str, str]] = field(default_factory=list)
    markdown: str = ""
    documento: dict[str, Any] = field(default_factory=dict)

    @property
    def titulo(self) -> str:
        issue = self.documento.get("issue") or {}
        return str(issue.get("title") or "")

    @property
    def prioridade(self) -> str:
        issue = self.documento.get("issue") or {}
        return str(issue.get("priority") or "")
