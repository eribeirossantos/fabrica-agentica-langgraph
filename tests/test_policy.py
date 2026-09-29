"""Regras de classificação e prioridade."""

from __future__ import annotations

import pytest

from fabrica.policy import classify_request, infer_area, prioritize_request

CASOS = [
    ("bug: botão de pagar não responde no celular", "bug", "P1", "checkout"),
    ("BUG: botão de pagar não responde", "bug", "P1", "checkout"),
    ("melhoria: aumentar o contraste do texto de confirmação da doação", "melhoria", "P3", "acessibilidade"),
    ("dúvida: o que acontece com a doação se o pagamento falhar?", "duvida", "P4", "checkout"),
    ("duvida: o que acontece se o pix falhar?", "duvida", "P4", "checkout"),
    ("dúvida: e se a doação se perde no pix?", "duvida", "P4", "checkout"),
    ("dúvida: estamos perdendo doações no pix", "duvida", "P1", "checkout"),
    ("dúvida: o cpf aparece na url compartilhada?", "duvida", "P2", "privacidade"),
    ("cpf do doador aparece na URL compartilhada", "risco", "P2", "privacidade"),
    ("bug: cpf do doador aparece no log público", "risco", "P2", "privacidade"),
    ("dívida: extrair o cliente HTTP duplicado do legado", "divida", "P5", "plataforma"),
    ("melhoria: alinhar o ícone da doação", "melhoria", "P5", "produto"),
    ("melhoria: mudar a cor do botão de pagar", "melhoria", "P5", "checkout"),
    ("melhoria: refatorar o módulo de recibo", "melhoria", "P5", "plataforma"),
    ("bug: mensagem de erro do pix é só erro 500", "bug", "P4", "checkout"),
    ("o botão de pagar não conclui a doação", "bug", "P1", "checkout"),
    (
        "bug: o botão de pagar não responde e o contraste está baixo",
        "bug",
        "P1",
        "checkout",
    ),
    (
        "melhoria: contraste baixo e o cpf aparece na url",
        "risco",
        "P2",
        "privacidade",
    ),
]


@pytest.mark.parametrize(("pedido", "tipo", "prioridade", "area"), CASOS)
def test_classificacao_e_prioridade(pedido: str, tipo: str, prioridade: str, area: str) -> None:
    assert classify_request(pedido) == tipo
    codigo, _motivo = prioritize_request(pedido, tipo)
    assert codigo == prioridade
    assert infer_area(pedido) == area


def test_prioridade_traz_o_motivo_da_escala() -> None:
    codigo, motivo = prioritize_request("bug: botão de pagar não responde no celular")
    assert codigo == "P1"
    assert motivo == "não perder transação ou doação"
