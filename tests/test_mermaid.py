"""O diagrama lido no README sai do grafo compilado."""

from __future__ import annotations

from fabrica.graph import build_graph, graph_edges, readable_mermaid


def test_draw_mermaid_lista_os_agentes() -> None:
    raw = build_graph().get_graph().draw_mermaid()
    for node in ("product", "approval", "design", "dev", "review", "publish"):
        assert node in raw


def test_mermaid_legivel_cobre_cada_aresta() -> None:
    diagram = readable_mermaid()
    for source, target in graph_edges():
        assert f"{source} " in diagram or diagram.startswith(f"{source} ") or f"\n    {source} " in diagram
        assert target in diagram
