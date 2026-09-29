"""Serviços externos. Pulado no pytest padrão e no CI."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


def test_postgres_checkpointer_e_redis() -> None:
    database = os.getenv("FABRICA_DATABASE_URL", "")
    redis_url = os.getenv("FABRICA_REDIS_URL", "")
    if not database or not redis_url:
        pytest.skip("defina FABRICA_DATABASE_URL e FABRICA_REDIS_URL")
    from fabrica.persistence.bus import build_status_bus
    from fabrica.persistence.checkpointer import build_checkpointer

    saver = build_checkpointer("postgres", url=database)
    assert saver is not None
    bus = build_status_bus(redis_url)
    bus.publish("integracao", {"agent": "fábrica", "status": "ok", "detail": "redis"})
    assert bus.history("integracao")[0]["status"] == "ok"
