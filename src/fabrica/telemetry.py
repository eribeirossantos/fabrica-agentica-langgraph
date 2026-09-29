"""Traces, logs estruturados e o gancho opcional do LangSmith.

O exportador padrão é nenhum, para a suíte e o CI ficarem em silêncio.
``console`` escreve o span na saída. ``otlp`` envia para o coletor configurado
em ``OTEL_EXPORTER_OTLP_ENDPOINT``.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Tracer

_TRUE = {"1", "true", "sim", "yes", "on"}
_CONFIGURED = False
_LOGGER = logging.getLogger("fabrica")


def configure_observability() -> None:
    """Liga o exportador de traces e, se pedido, o tracing do LangSmith."""
    global _CONFIGURED
    _configure_langsmith()
    configure_logging()
    if _CONFIGURED:
        return
    exporter_name = os.getenv("OTEL_TRACES_EXPORTER", "none").strip().lower()
    if exporter_name in {"", "none", "off"}:
        _CONFIGURED = True
        return
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": "fabrica-agentica"}))
    if exporter_name == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif exporter_name == "otlp":
        provider.add_span_processor(BatchSpanProcessor(_otlp_exporter()))
    else:
        raise RuntimeError("OTEL_TRACES_EXPORTER aceita none, console ou otlp.")
    trace.set_tracer_provider(provider)
    _CONFIGURED = True


def configure_logging() -> None:
    """JSON em ``fabrica`` quando ``FABRICA_LOG_FORMAT=json``. Não mexe no root."""
    if _LOGGER.handlers:
        return
    handler = logging.StreamHandler()
    if os.getenv("FABRICA_LOG_FORMAT", "").strip().lower() == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    _LOGGER.addHandler(handler)
    default_level = "INFO" if os.getenv("FABRICA_LOG_FORMAT", "").strip().lower() == "json" else "WARNING"
    _LOGGER.setLevel(os.getenv("FABRICA_LOG_LEVEL", default_level).upper())
    _LOGGER.propagate = False


def tracer() -> Tracer:
    return trace.get_tracer("fabrica")


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[Any]:
    """Abre um span e registra o nome em log estruturado."""
    with tracer().start_as_current_span(name) as current:
        for key, value in attributes.items():
            if value is not None:
                current.set_attribute(key, value)
        _LOGGER.info(name, extra={"event": name, **attributes})
        yield current


def langsmith_habilitado() -> bool:
    """Verdadeiro quando o ambiente pede rastreio no LangSmith."""
    tracing = os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "")).strip().lower()
    return tracing in _TRUE


def _configure_langsmith() -> None:
    if os.getenv("LANGSMITH_TRACING", "").strip().lower() in _TRUE:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    project = os.getenv("LANGSMITH_PROJECT", "").strip()
    if project:
        os.environ.setdefault("LANGCHAIN_PROJECT", project)


def _otlp_exporter() -> Any:
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    except ImportError as exc:
        raise RuntimeError(
            "O exportador OTLP não está instalado. Instale com: pip install -e '.[infra]'"
        ) from exc
    return OTLPSpanExporter()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in {"event", "node", "method", "path", "issue_id"}:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)
