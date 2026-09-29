"""Persistência que não depende de Postgres nem de Redis."""

from __future__ import annotations

import importlib.util

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from fabrica.persistence.bus import InMemoryStatusBus, build_status_bus
from fabrica.persistence.checkpointer import build_checkpointer
from fabrica.persistence.db import SqlIssueStore, make_engine
from fabrica.records import IssueView


def test_sqlite_em_memoria_grava_historico() -> None:
    store = SqlIssueStore(make_engine("sqlite://"))
    view = IssueView(
        id="pedido-1",
        pedido="bug: botão",
        fase="aguardando_aprovacao",
        registro_de_status=[{"agent": "produto", "status": "issue especificada", "detail": "P1"}],
        documento={"issue": {"title": "Botão", "priority": "P1"}},
    )
    store.save(view)
    loaded = store.get("pedido-1")
    assert loaded is not None
    assert loaded.titulo == "Botão"
    assert loaded.registro_de_status[0]["agent"] == "produto"
    assert store.get("ausente") is None


def test_canal_em_memoria_acumula() -> None:
    bus = build_status_bus("")
    assert isinstance(bus, InMemoryStatusBus)
    bus.publish("abc", {"agent": "produto", "status": "issue especificada", "detail": "P1"})
    assert bus.history("abc")[0]["status"] == "issue especificada"
    assert bus.history("outro") == []


def test_checkpointer_padrao_e_memoria() -> None:
    assert isinstance(build_checkpointer("memory"), InMemorySaver)


def test_postgres_sem_extra_explica_o_pacote(monkeypatch) -> None:
    if importlib.util.find_spec("langgraph.checkpoint.postgres") and importlib.util.find_spec("psycopg_pool"):
        pytest.skip("extra infra instalado neste ambiente")
    monkeypatch.delenv("FABRICA_CHECKPOINTER_URL", raising=False)
    with pytest.raises(RuntimeError, match="langgraph-checkpoint-postgres"):
        build_checkpointer("postgres", url="postgresql://fabrica:fabrica@localhost:5432/fabrica")


def test_redis_sem_pacote_explica_o_extra(monkeypatch) -> None:
    if importlib.util.find_spec("redis") is not None:
        pytest.skip("redis está instalado neste ambiente")
    monkeypatch.setenv("FABRICA_REDIS_URL", "redis://localhost:6379/0")
    with pytest.raises(RuntimeError, match="redis"):
        build_status_bus()
