"""Canal de status: lista em memória ou Redis com pub-sub."""

from __future__ import annotations

import json
import os


class InMemoryStatusBus:
    """Histórico do canal no processo. Os testes usam esta implementação."""

    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, str]]] = {}

    def publish(self, issue_id: str, event: dict[str, str]) -> None:
        self._events.setdefault(issue_id, []).append(dict(event))

    def history(self, issue_id: str) -> list[dict[str, str]]:
        return list(self._events.get(issue_id, []))


class RedisStatusBus:
    """Grava a lista e publica no mesmo canal, para outro processo acompanhar."""

    def __init__(self, url: str) -> None:
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("Redis pede o pacote redis. Instale com: pip install -e '.[infra]'") from exc
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._client.ping()

    def publish(self, issue_id: str, event: dict[str, str]) -> None:
        payload = json.dumps(event, ensure_ascii=False)
        channel = f"fabrica:status:{issue_id}"
        self._client.rpush(channel, payload)
        self._client.publish(channel, payload)

    def history(self, issue_id: str) -> list[dict[str, str]]:
        raw = self._client.lrange(f"fabrica:status:{issue_id}", 0, -1)
        return [json.loads(item) for item in raw]


def build_status_bus(url: str | None = None) -> InMemoryStatusBus | RedisStatusBus:
    """Sem URL, o canal fica na memória. Com URL, usa Redis."""
    selected = url if url is not None else os.getenv("FABRICA_REDIS_URL", "").strip()
    if not selected:
        return InMemoryStatusBus()
    return RedisStatusBus(selected)
