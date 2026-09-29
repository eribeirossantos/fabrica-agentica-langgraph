"""O span do nó existe e o log estruturado serializa em JSON."""

from __future__ import annotations

import json

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from fabrica.telemetry import _JsonFormatter


def test_formatter_json_inclui_o_no() -> None:
    formatter = _JsonFormatter()
    record = __import__("logging").LogRecord(
        name="fabrica",
        level=20,
        pathname=__file__,
        lineno=1,
        msg="fabrica.graph.product",
        args=(),
        exc_info=None,
    )
    record.node = "product"
    record.event = "fabrica.graph.product"
    payload = json.loads(formatter.format(record))
    assert payload["node"] == "product"
    assert payload["message"] == "fabrica.graph.product"


def test_no_do_grafo_abre_span(monkeypatch) -> None:
    from opentelemetry import trace

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")

    from fabrica.runner import execute

    execute("bug: botão de pagar não responde no celular", auto_approve=True, offline=True)
    nomes = {span.name for span in exporter.get_finished_spans()}
    assert "fabrica.graph.product" in nomes
    assert "fabrica.graph.review" in nomes
    assert "fabrica.graph.publish" in nomes
