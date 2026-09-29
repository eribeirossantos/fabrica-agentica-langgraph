"""Orquestra o grafo, a projeção SQL e o canal de status.

A API e o servidor MCP chamam esta mesma classe. O checkpoint guarda o fio
do LangGraph; o banco guarda a issue que a pessoa consulta.
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable
from typing import Any

from langgraph.types import Command

from fabrica.graph import build_graph
from fabrica.llm import build_models
from fabrica.persistence.bus import build_status_bus
from fabrica.persistence.checkpointer import build_checkpointer
from fabrica.persistence.db import SqlIssueStore, make_engine
from fabrica.rag.retriever import get_retriever, reset_store
from fabrica.records import IssueView
from fabrica.runner import initial_state
from fabrica.telemetry import configure_observability


class NotFoundError(Exception):
    """Pedido inexistente."""


class ConflictError(Exception):
    """Ação incompatível com a fase atual."""


class FactoryService:
    """Uma instância atende várias threads de pedido."""

    def __init__(self, graph: Any, store: SqlIssueStore, bus: Any) -> None:
        self.graph = graph
        self.store = store
        self.bus = bus

    @classmethod
    def create(
        cls,
        *,
        database_url: str | None = None,
        offline: bool | None = None,
        model: Any = None,
        checkpointer: Any = None,
        status_bus: Any = None,
    ) -> FactoryService:
        configure_observability()
        _with_retry("o índice de conhecimento", _prepare_vector_store)
        url = database_url or os.getenv("FABRICA_DATABASE_URL", "sqlite:///fabrica.db")
        store = _with_retry("o banco da issue", lambda: SqlIssueStore(make_engine(url)))
        saver = checkpointer if checkpointer is not None else _with_retry("o checkpointer", build_checkpointer)
        bus = status_bus if status_bus is not None else _with_retry("o canal de status", build_status_bus)
        if model is not None:
            graph = build_graph(model=model, checkpointer=saver, retriever=get_retriever())
        else:
            graph = build_graph(
                models=build_models(offline=offline),
                checkpointer=saver,
                retriever=get_retriever(),
            )
        return cls(graph, store, bus)

    def criar(self, pedido: str) -> IssueView:
        texto = pedido.strip()
        if not texto:
            raise ConflictError("Informe o pedido.")
        issue_id = str(uuid.uuid4())
        self.graph.invoke(initial_state(texto), _config(issue_id))
        return self._sync(issue_id, texto)

    def obter(self, issue_id: str) -> IssueView:
        view = self.store.get(issue_id)
        if view is None:
            raise NotFoundError("Pedido não encontrado.")
        return view

    def decidir(self, issue_id: str, decision: str, feedback: str = "") -> IssueView:
        view = self.obter(issue_id)
        if view.fase != "aguardando_aprovacao":
            raise ConflictError("O pedido não está aguardando aprovação.")
        self.graph.invoke(
            Command(resume={"decision": decision, "feedback": feedback}),
            _config(issue_id),
        )
        return self._sync(issue_id, view.pedido)

    def publicar_ate_o_fim(self, issue_id: str) -> IssueView:
        """Aprova enquanto o grafo estiver parado no interrupt. Usado pelo MCP."""
        view = self.obter(issue_id)
        guard = 0
        while view.fase == "aguardando_aprovacao" and guard < 5:
            view = self.decidir(issue_id, "approve", "")
            guard += 1
        return view

    def _sync(self, issue_id: str, pedido: str) -> IssueView:
        snapshot = self.graph.get_state(_config(issue_id))
        values = dict(snapshot.values or {})
        log = [dict(event) for event in values.get("status_log") or []]
        previous = self.store.get(issue_id)
        previous_len = len(previous.registro_de_status) if previous else 0
        documento = values.get("final_document") or {
            "pedido": pedido,
            "resultado": values.get("outcome") or "",
            "issue": values.get("issue") or {},
            "design": values.get("design_spec") or {},
            "plano_de_implementacao": values.get("dev_plan") or {},
            "revisao": values.get("review") or {},
            "registro_de_status": log,
        }
        view = IssueView(
            id=issue_id,
            pedido=pedido,
            fase=_fase(snapshot, values),
            resultado=str(values.get("outcome") or ""),
            registro_de_status=log,
            markdown=str(values.get("final_markdown") or ""),
            documento=documento,
        )
        self.store.save(view)
        for event in log[previous_len:]:
            self.bus.publish(issue_id, event)
        return view


def _config(issue_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": issue_id}, "recursion_limit": 50}


def _fase(snapshot: Any, values: dict[str, Any]) -> str:
    if getattr(snapshot, "interrupts", None):
        return "aguardando_aprovacao"
    outcome = str(values.get("outcome") or "")
    if outcome in {"publicado", "cancelado", "encerrado_no_limite"}:
        return outcome
    if getattr(snapshot, "next", None):
        return "em_andamento"
    return "desconhecido"


def _with_retry(label: str, fn: Callable[[], Any]) -> Any:
    """Repete a conexão na subida. O compose aumenta ``FABRICA_STARTUP_RETRIES``."""
    attempts = max(1, int(os.getenv("FABRICA_STARTUP_RETRIES", "1")))
    delay = float(os.getenv("FABRICA_STARTUP_DELAY", "2"))
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last = exc
            if attempt == attempts:
                break
            time.sleep(delay)
    assert last is not None
    raise RuntimeError(f"Não foi possível iniciar {label}: {last}") from last


def _prepare_vector_store() -> None:
    kind = os.getenv("FABRICA_VECTOR_STORE", "memory").strip().lower()
    if kind == "pgvector":
        reset_store()
        get_retriever()
