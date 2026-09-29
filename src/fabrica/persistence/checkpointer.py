"""Checkpointer do LangGraph: memória, SQLite ou PostgreSQL."""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

_HELD: list[Any] = []


def build_checkpointer(kind: str | None = None, url: str | None = None) -> Any:
    """Devolve o saver pedido. Objetos de conexão ficam vivos no processo."""
    selected = (kind if kind is not None else os.getenv("FABRICA_CHECKPOINTER", "memory")).strip().lower()
    if selected in {"", "memory"}:
        return InMemorySaver()
    if selected == "sqlite":
        return _sqlite(url)
    if selected == "postgres":
        return _postgres(url)
    raise RuntimeError("FABRICA_CHECKPOINTER aceita memory, sqlite ou postgres.")


def _sqlite(url: str | None) -> Any:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:
        raise RuntimeError(
            "O checkpointer SQLite pede langgraph-checkpoint-sqlite. Instale com: pip install -e '.[infra]'"
        ) from exc
    target = url or os.getenv("FABRICA_CHECKPOINTER_URL", "").strip() or "fabrica-checkpoints.sqlite"
    path = target.removeprefix("sqlite:///") if target.startswith("sqlite:///") else target
    connection = sqlite3.connect(path, check_same_thread=False)
    _HELD.append(connection)
    return SqliteSaver(connection)


def _postgres(url: str | None) -> Any:
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool
    except ImportError as exc:
        raise RuntimeError(
            "O checkpointer PostgreSQL pede langgraph-checkpoint-postgres e psycopg. "
            "Instale com: pip install -e '.[infra]'"
        ) from exc
    target = (
        url
        or os.getenv("FABRICA_CHECKPOINTER_URL", "").strip()
        or os.getenv("FABRICA_DATABASE_URL", "").strip()
    )
    if not target:
        raise RuntimeError("FABRICA_CHECKPOINTER=postgres exige FABRICA_CHECKPOINTER_URL.")
    dsn = target.replace("postgresql+psycopg://", "postgresql://", 1).replace(
        "postgres+psycopg://", "postgresql://", 1
    )
    pool = ConnectionPool(
        conninfo=dsn,
        min_size=1,
        max_size=10,
        open=True,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    saver = PostgresSaver(pool)
    saver.setup()
    _HELD.append(pool)
    return saver
