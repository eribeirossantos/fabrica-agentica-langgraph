"""Laços de aprovação e de revisão no grafo compilado, em modo offline."""

from __future__ import annotations

from fabrica.graph import MAX_REVIEW_ITERATIONS
from fabrica.runner import execute
from fabrica.schemas import ProductDraft
from fabrica.stub import StubModel
from tests.fakes import ScriptedModel

PEDIDO = "bug: botão de pagar não responde no celular"


def test_rejeicao_volta_ao_produto_e_aprovacao_publica() -> None:
    respostas = [
        {"decision": "reject", "feedback": "Recorte só o toque no celular."},
        {"decision": "approve", "feedback": ""},
    ]

    def approver(payload: dict) -> dict[str, str]:
        del payload
        return respostas.pop(0)

    state = execute(PEDIDO, approver=approver, offline=True)
    assert state["outcome"] == "publicado"
    assert state["approval_rounds"] == 1
    assert "Recorte só o toque no celular." in state["issue"]["problem"]
    status = [event["status"] for event in state["status_log"]]
    assert status.count("rejeitado") == 1
    assert "aprovado" in status
    assert status[-1] == "publicado"
    assert "Pagar doação" in state["final_markdown"]


def test_tres_rejeicoes_cancelam() -> None:
    def approver(payload: dict) -> dict[str, str]:
        return {"decision": "reject", "feedback": f"ainda não na rodada {payload['round']}"}

    state = execute(PEDIDO, approver=approver, offline=True)
    assert state["outcome"] == "cancelado"
    assert state["approval_rounds"] == 3
    assert [event["status"] for event in state["status_log"]].count("rejeitado") == 3
    assert state["status_log"][-1]["status"] == "cancelado sem aprovação"
    assert state["design_spec"] == {}


def test_revisao_devolve_para_design_uma_vez() -> None:
    model = ScriptedModel(break_design_once=True)
    state = execute(PEDIDO, auto_approve=True, model=model)
    assert state["outcome"] == "publicado"
    assert model.design_calls == 2
    assert "devolvido para design" in [event["status"] for event in state["status_log"]]
    assert state["review"]["verdict"] == "aprovado"


def test_revisao_para_no_limite() -> None:
    model = ScriptedModel(always_bad_dev=True)
    state = execute(PEDIDO, auto_approve=True, model=model)
    assert state["outcome"] == "encerrado_no_limite"
    assert state["review_iterations"] == MAX_REVIEW_ITERATIONS
    assert model.dev_calls == MAX_REVIEW_ITERATIONS
    assert state["status_log"][-1]["status"] == "encerrado no limite de revisão"
    assert state["review"]["target"] == "dev"


def test_politica_vence_o_titulo_do_modelo() -> None:
    class Mentiroso(StubModel):
        def invoke(self, schema, system, user):
            draft = super().invoke(schema, system, user)
            if schema is ProductDraft:
                draft.title = "Título mentiroso"
            return draft

    state = execute(PEDIDO, auto_approve=True, model=Mentiroso())
    assert state["issue"]["title"] == "Título mentiroso"
    assert state["issue"]["type_label"] == "bug"
    assert state["issue"]["priority"] == "P1"
    assert state["issue"]["area_label"] == "checkout"


def test_auto_approve_registra_o_canal() -> None:
    state = execute(PEDIDO, auto_approve=True, offline=True)
    linhas = [f"[{event['agent']}] {event['status']}" for event in state["status_log"]]
    assert linhas == [
        "[produto] issue especificada",
        "[product owner] aprovado",
        "[design] especificação de design pronta",
        "[dev] plano de implementação pronto",
        "[revisão] revisão aprovada",
        "[fábrica] publicado",
    ]
