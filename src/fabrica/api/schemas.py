"""Contratos HTTP. Os nomes dos campos seguem o português da API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    """Saúde do processo."""

    status: Literal["ok"] = "ok"
    offline: bool
    vector_store: str
    checkpointer: str


class PedidoIn(BaseModel):
    """Pedido que inicia o grafo."""

    pedido: str = Field(
        min_length=1,
        examples=["bug: botão de pagar não responde no celular"],
        description="Texto com prefixo bug:, melhoria: ou dúvida:.",
    )


class DecisaoIn(BaseModel):
    """Retomada do interrupt de aprovação."""

    decision: Literal["approve", "reject", "aprovar", "rejeitar"] = Field(
        description="approve segue para design. reject devolve o texto ao produto.",
    )
    feedback: str = Field(default="", description="Comentário obrigatório na prática quando a decisão é reject.")


class StatusItem(BaseModel):
    """Uma linha do canal de status."""

    agent: str
    status: str
    detail: str


class PedidoOut(BaseModel):
    """Estado consultável do pedido."""

    id: str
    pedido: str
    fase: str
    resultado: str = ""
    titulo: str = ""
    prioridade: str = ""
    registro_de_status: list[StatusItem]


class IssueOut(BaseModel):
    """Issue final em Markdown e no documento JSON."""

    id: str
    markdown: str
    documento: dict[str, Any]


class ErroOut(BaseModel):
    """Erro em português."""

    detalhe: str
