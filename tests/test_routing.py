"""Arestas condicionais, sem executar o modelo."""

from __future__ import annotations

import pytest

from fabrica.graph import (
    MAX_APPROVAL_ROUNDS,
    MAX_REVIEW_ITERATIONS,
    graph_edges,
    route_after_approval,
    route_after_review,
)


@pytest.mark.parametrize(
    ("state", "destino"),
    [
        ({"approval_decision": "approve", "approval_rounds": 0}, "design"),
        ({"approval_decision": "reject", "approval_rounds": 1}, "product"),
        ({"approval_decision": "reject", "approval_rounds": MAX_APPROVAL_ROUNDS}, "publish"),
    ],
)
def test_rota_da_aprovacao(state: dict, destino: str) -> None:
    assert route_after_approval(state) == destino


@pytest.mark.parametrize(
    ("state", "destino"),
    [
        ({"review": {"verdict": "aprovado", "target": "nenhum"}, "review_iterations": 1}, "publish"),
        (
            {"review": {"verdict": "devolver", "target": "dev"}, "review_iterations": 1},
            "dev",
        ),
        (
            {"review": {"verdict": "devolver", "target": "design"}, "review_iterations": 1},
            "design",
        ),
        (
            {
                "review": {"verdict": "devolver", "target": "dev"},
                "review_iterations": MAX_REVIEW_ITERATIONS,
            },
            "publish",
        ),
    ],
)
def test_rota_da_revisao(state: dict, destino: str) -> None:
    assert route_after_review(state) == destino


def test_grafo_tem_os_ciclos_de_devolucao() -> None:
    edges = graph_edges()
    assert ("approval", "product") in edges
    assert ("approval", "design") in edges
    assert ("approval", "publish") in edges
    assert ("review", "design") in edges
    assert ("review", "dev") in edges
    assert ("review", "publish") in edges
    assert ("design", "dev") in edges
    assert ("dev", "review") in edges
