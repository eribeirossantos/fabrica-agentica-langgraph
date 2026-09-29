"""Modelo determinístico para o modo offline.

Responde aos mesmos schemas do chat model, sem rede e sem chave. Os três
pedidos de exemplo têm narrativa própria; os demais caem num texto genérico
ainda assim completo, para o grafo e os testes fecharem.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from fabrica.policy import TYPE_DISPLAY, normalize
from fabrica.schemas import CopyBlock, DesignSpec, DevPlan, ProductDraft

_FEEDBACK_MARK = "Ajuste pedido pelo product owner: "


class StubModel:
    """Substitui o chat model quando não há API."""

    def invoke(self, schema: type[BaseModel], system: str, user: str) -> BaseModel:
        del system  # o stub segue o schema e o JSON do usuário, não o prompt livre
        payload = _load_payload(user)
        if schema is ProductDraft:
            return _product(payload)
        if schema is DesignSpec:
            return _design(payload)
        if schema is DevPlan:
            return _dev(payload)
        raise TypeError(f"Schema sem resposta offline: {schema.__name__}")


def _load_payload(user: str) -> dict[str, Any]:
    try:
        data = json.loads(user)
    except json.JSONDecodeError:
        data = {"request": user}
    if not isinstance(data, dict):
        return {"request": user}
    return data


def _scenario(text: str, issue_type: str) -> str:
    normalized = normalize(text)
    if "contraste" in normalized:
        return "contraste"
    if issue_type == "duvida":
        return "duvida"
    if issue_type == "risco":
        return "risco"
    if issue_type == "divida":
        return "divida"
    if any(token in normalized for token in ("pagar", "pagamento", "pix", "checkout", "doacao")):
        return "pagamento"
    return "generico"


def _title(body: str) -> str:
    clean = body.strip().rstrip(".")
    if not clean:
        return "Pedido sem título"
    return clean[0].upper() + clean[1:]


def _with_feedback(problem: str, feedback: str) -> str:
    feedback = (feedback or "").strip()
    if not feedback:
        return problem
    line = f"{_FEEDBACK_MARK}{feedback}"
    if line in problem:
        return problem
    return f"{problem.rstrip()}\n\n{line}"


def _product(payload: dict[str, Any]) -> ProductDraft:
    request = str(payload.get("request") or "")
    feedback = str(payload.get("feedback") or "")
    issue_type = str(payload.get("type_label") or "melhoria")
    body = str(payload.get("body") or request)
    scenario = _scenario(request or body, issue_type)
    title = _title(str(payload.get("body") or body))
    builders = {
        "pagamento": _product_payment,
        "contraste": _product_contrast,
        "duvida": _product_question,
        "risco": _product_risk,
        "divida": _product_debt,
    }
    draft = builders.get(scenario, _product_generic)(title, body, issue_type)
    draft.problem = _with_feedback(draft.problem, feedback)
    return draft


def _product_payment(title: str, body: str, issue_type: str) -> ProductDraft:
    del body, issue_type
    return ProductDraft(
        title=title,
        summary=(
            "O toque em Pagar no celular não inicia a doação. "
            "O corte seguro é corrigir só esse disparo."
        ),
        problem=(
            "No celular, o botão de pagar da tela de checkout não inicia o pagamento. "
            "A pessoa toca e nada acontece, então a doação não é registrada."
        ),
        expected_result=(
            "Ao tocar uma vez em Pagar no celular, o pagamento inicia, o botão mostra "
            "carregamento e a doação segue para a confirmação, sem cobrança duplicada."
        ),
        smallest_increment=(
            "Corrigir apenas o disparo do pagamento no toque móvel, sem redesenhar "
            "o checkout nem incluir meio de pagamento novo."
        ),
        out_of_scope=[
            "Redesenhar o layout do checkout.",
            "Adicionar ou remover meios de pagamento.",
            "Alterar valor, recibo ou mensagens posteriores à confirmação.",
        ],
        risks=[
            "Trocar o evento de clique em vez de complementar o toque pode quebrar o desktop.",
            "Sem idempotência, toques repetidos durante o carregamento criam doações duplicadas.",
        ],
        acceptance_criteria=[
            "Dado um celular com o checkout aberto, quando a pessoa toca uma vez em Pagar, "
            "então o pagamento inicia e o botão entra em carregamento em até um segundo.",
            "Dado o pagamento confirmado, quando a resposta de sucesso chega, então a doação "
            "aparece registrada e a tela de confirmação é exibida.",
            "Dado um toque extra enquanto o botão está em carregamento, quando o primeiro "
            "toque já foi aceito, então só uma doação é criada.",
        ],
    )


def _product_contrast(title: str, body: str, issue_type: str) -> ProductDraft:
    del body, issue_type
    return ProductDraft(
        title=title,
        summary=(
            "O texto da confirmação da doação fica abaixo do contraste mínimo. "
            "O corte seguro é ajustar só essa cor."
        ),
        problem=(
            "O texto da tela de confirmação da doação tem contraste insuficiente. "
            "Parte das pessoas não consegue ler o comprovante."
        ),
        expected_result=(
            "O texto principal da confirmação atinge contraste de pelo menos 4,5:1 "
            "com o fundo, e o restante da tela permanece igual."
        ),
        smallest_increment=(
            "Trocar apenas a cor do texto de confirmação, e do fundo se isso for "
            "indispensável para o contraste, sem redesenhar a tela."
        ),
        out_of_scope=[
            "Redesenhar a tela de confirmação.",
            "Incluir campos novos no comprovante.",
            "Alterar o fluxo de pagamento ou o botão Pagar.",
        ],
        risks=[
            "Escurecer o texto pode colidir com um fundo de sucesso que também seja escuro.",
            "Mudar um token de cor global afetaria telas fora do perímetro.",
        ],
        acceptance_criteria=[
            "Dado a tela de confirmação, quando o texto principal é medido sobre o fundo, "
            "então a razão de contraste é de pelo menos 4,5:1.",
            "Dado um leitor de tela, quando a confirmação abre, então o texto continua "
            "sendo anunciado com o mesmo conteúdo.",
            "Dado o restante do aplicativo, quando a correção é aplicada, então botões "
            "e telas fora da confirmação permanecem iguais.",
        ],
    )


def _product_question(title: str, body: str, issue_type: str) -> ProductDraft:
    del body, issue_type
    return ProductDraft(
        title=title,
        summary=(
            "A falha de pagamento não explica se a doação foi registrada. "
            "O corte seguro é uma frase nesse estado de erro."
        ),
        problem=(
            "Quando o pagamento falha, a pessoa não sabe se a doação foi registrada "
            "nem se o valor será cobrado de novo."
        ),
        expected_result=(
            "A tela de falha diz, em uma frase, que a doação não foi registrada e que "
            "nenhuma cobrança extra foi feita, e oferece tentar de novo."
        ),
        smallest_increment=(
            "Incluir somente a mensagem de falha no estado de erro do pagamento, "
            "sem mudar a regra de cobrança."
        ),
        out_of_scope=[
            "Retentativa automática do pagamento.",
            "Troca de meio de pagamento ou de regra de cobrança.",
            "Fluxo novo de estorno.",
        ],
        risks=[
            "A frase 'nenhuma cobrança extra' precisa ser verdadeira para os meios já existentes.",
            "Um texto longo demais empurra a ação de tentar de novo para fora da primeira dobra no celular.",
        ],
        acceptance_criteria=[
            "Dado um pagamento recusado, quando a falha é exibida, então a pessoa lê "
            "que a doação não foi registrada.",
            "Dado a mesma falha, quando a mensagem aparece, então ela informa que "
            "não houve cobrança extra.",
            "Dado a mensagem de falha, quando a pessoa aciona Tentar de novo, então "
            "o checkout reabre sem criar uma segunda doação.",
        ],
    )


def _product_risk(title: str, body: str, issue_type: str) -> ProductDraft:
    del issue_type
    return ProductDraft(
        title=title,
        summary="Há exposição de dado pessoal no fluxo de doação. O corte seguro fecha só esse vazamento.",
        problem=f"Dado pessoal aparece onde não deveria: {body}.",
        expected_result=(
            "O dado deixa de ser exibido ou registrado no lugar indevido, e o fluxo "
            "de doação continua concluindo para quem já estava autorizado."
        ),
        smallest_increment="Remover apenas a exposição descrita, sem redesenhar a conta nem o checkout.",
        out_of_scope=[
            "Revisão ampla de privacidade fora do ponto citado.",
            "Troca de provedor de pagamento.",
        ],
        risks=[
            "Esconder o campo na tela e mantê-lo na URL ou no log não resolve o vazamento.",
            "Uma correção apressada pode quebrar a confirmação de quem precisa ver o próprio comprovante.",
        ],
        acceptance_criteria=[
            "Dado o fluxo citado no pedido, quando a tela ou o log é inspecionado, "
            "então o dado pessoal não aparece para quem não é o titular.",
            "Dado a correção aplicada, quando a pessoa conclui a própria doação, "
            "então o comprovante dela continua acessível para ela.",
            "Dado um teste de regressão do checkout, quando o pagamento é aprovado, "
            "então a doação ainda é registrada.",
        ],
    )


def _product_debt(title: str, body: str, issue_type: str) -> ProductDraft:
    del issue_type
    return ProductDraft(
        title=title,
        summary="Dívida técnica localizada. O corte seguro é extrair só o trecho citado, sem mudar comportamento.",
        problem=f"Há duplicação ou acoplamento que dificulta mudança segura: {body}.",
        expected_result="O trecho citado fica num único lugar, com o comportamento observável igual ao de antes.",
        smallest_increment="Extrair apenas o módulo citado e cobrir o comportamento atual com teste.",
        out_of_scope=[
            "Reescrita do fluxo de doação.",
            "Mudança visual ou de copy.",
        ],
        risks=[
            "Mover código sem teste de caracterização pode alterar a cobrança sem que ninguém perceba.",
        ],
        acceptance_criteria=[
            "Dado o comportamento atual do fluxo tocado, quando a extração termina, "
            "então as respostas observáveis permanecem iguais.",
            "Dado o teste de caracterização, quando ele roda no CI, então passa sem ajuste de produção.",
            "Dado o restante do aplicativo, quando a extração é revisada, então nenhum arquivo fora do perímetro muda.",
        ],
    )


def _product_generic(title: str, body: str, issue_type: str) -> ProductDraft:
    label = TYPE_DISPLAY.get(issue_type, issue_type)
    return ProductDraft(
        title=title,
        summary=f"Pedido do tipo {label} reduzido ao menor incremento que muda o comportamento citado.",
        problem=f"Quem usa o aplicativo de doações encontra este pedido: {body}.",
        expected_result="O comportamento citado passa a corresponder ao que a pessoa espera, sem efeitos ao lado.",
        smallest_increment="Alterar só o ponto citado no pedido, com teste cobrindo o antes e o depois.",
        out_of_scope=[
            "Redesenho de telas que não foram citadas.",
            "Mudança de regra de cobrança.",
        ],
        risks=[
            "Ampliar o corte além do pedido aumenta a chance de regressão no checkout.",
        ],
        acceptance_criteria=[
            f"Dado o cenário descrito em '{body}', quando a pessoa repete a ação, "
            "então o resultado esperado deste incremento acontece.",
            "Dado a área não citada no pedido, quando o incremento é aplicado, então ela permanece igual.",
            "Dado o teste automatizado do critério principal, quando ele roda, então passa.",
        ],
    )


def _design(payload: dict[str, Any]) -> DesignSpec:
    issue = payload.get("issue") or {}
    feedback = str(payload.get("feedback") or "").strip()
    scenario = _scenario(str(issue.get("source_request") or ""), str(issue.get("type_label") or ""))
    specs = {
        "pagamento": _design_payment,
        "contraste": _design_contrast,
        "duvida": _design_question,
    }
    spec = specs.get(scenario, _design_generic)(issue)
    if feedback:
        spec.ui_changes.append(f"Ajuste após revisão: {feedback}")
    return spec


def _wcag_base() -> list[str]:
    return [
        "WCAG 2.1 AA — contraste mínimo de 4,5:1 para texto normal (critério 1.4.3).",
        "WCAG 2.1 AA — nome, função e estado disponíveis para tecnologia assistiva (critério 4.1.2).",
        "WCAG 2.1 AA — operação por teclado e foco visível (critérios 2.1.1 e 2.4.7).",
        "WCAG 2.1 AA — a informação não depende só de cor (critério 1.4.1).",
    ]


def _design_payment(issue: dict[str, Any]) -> DesignSpec:
    del issue
    return DesignSpec(
        do_not_touch=[
            "Meios de pagamento e o contrato da API de cobrança.",
            "Cálculo do valor da doação.",
            "Navegação global, cabeçalho e rodapé.",
            "Conteúdo da tela de confirmação, fora o estado que o botão dispara.",
        ],
        ui_changes=[
            "O botão Pagar ganha estado de carregamento no toque, com indicação visível.",
            "Toques adicionais durante o carregamento não disparam outra cobrança.",
            "O foco permanece no botão até a ida para a confirmação.",
        ],
        copy_pt_br=[
            CopyBlock(onde="Botão principal", texto="Pagar doação"),
            CopyBlock(onde="Estado de carregamento", texto="Pagamento em andamento"),
            CopyBlock(
                onde="Erro recuperável",
                texto="Não foi possível pagar. Tente de novo. Nenhuma cobrança extra foi feita.",
            ),
            CopyBlock(onde="Confirmação", texto="Doação registrada"),
        ],
        accessibility=_wcag_base(),
    )


def _design_contrast(issue: dict[str, Any]) -> DesignSpec:
    del issue
    return DesignSpec(
        do_not_touch=[
            "Fluxo de pagamento e botão Pagar.",
            "Ordem e estrutura dos elementos da confirmação.",
            "Textos cujo contraste já atende 4,5:1.",
        ],
        ui_changes=[
            "Ajustar a cor do texto principal da confirmação para um token com contraste de pelo menos 4,5:1.",
            "Não usar a cor como única indicação de sucesso.",
        ],
        copy_pt_br=[
            CopyBlock(onde="Título da confirmação", texto="Doação confirmada"),
            CopyBlock(onde="Corpo", texto="Sua doação foi registrada. Guarde este comprovante."),
            CopyBlock(onde="Ação secundária", texto="Voltar ao início"),
        ],
        accessibility=_wcag_base(),
    )


def _design_question(issue: dict[str, Any]) -> DesignSpec:
    del issue
    return DesignSpec(
        do_not_touch=[
            "Regra de cobrança e meios de pagamento.",
            "Tela de sucesso da doação.",
            "Navegação global.",
        ],
        ui_changes=[
            "No estado de falha do pagamento, mostrar a explicação antes da ação de tentar de novo.",
            "Manter a ação Tentar de novo visível sem rolagem no celular.",
        ],
        copy_pt_br=[
            CopyBlock(
                onde="Mensagem de falha",
                texto="A doação não foi registrada. Nenhuma cobrança extra foi feita.",
            ),
            CopyBlock(onde="Ação", texto="Tentar de novo"),
        ],
        accessibility=_wcag_base(),
    )


def _design_generic(issue: dict[str, Any]) -> DesignSpec:
    title = str(issue.get("title") or "a mudança")
    return DesignSpec(
        do_not_touch=[
            "Fluxo de cobrança que não foi citado na issue.",
            "Navegação global e telas fora da área da issue.",
        ],
        ui_changes=[f"Aplicar só o que a issue '{title}' descreve, dentro do perímetro."],
        copy_pt_br=[
            CopyBlock(onde="Texto afetado", texto="A doação segue o que esta tela promete."),
        ],
        accessibility=_wcag_base(),
    )


def _dev(payload: dict[str, Any]) -> DevPlan:
    issue = payload.get("issue") or {}
    feedback = str(payload.get("feedback") or "").strip()
    criteria = issue.get("acceptance_criteria") or []
    scenario = _scenario(str(issue.get("source_request") or ""), str(issue.get("type_label") or ""))
    areas = {
        "pagamento": [
            "app/checkout/PayButton.tsx — toque e estado de carregamento.",
            "app/checkout/payment-client.ts — não iniciar segunda cobrança enquanto a primeira não termina.",
            "app/checkout/PayButton.test.tsx — testes dos critérios de aceite.",
        ],
        "contraste": [
            "app/confirmacao/Confirmacao.module.css — cor do texto principal.",
            "app/confirmacao/tokens.css — token de cor usado só na confirmação.",
            "app/confirmacao/contraste.test.ts — medição do contraste e regressão das outras telas.",
        ],
        "duvida": [
            "app/checkout/PaymentFailure.tsx — mensagem do estado de erro.",
            "app/checkout/mensagens.ts — copy final da falha.",
            "app/checkout/PaymentFailure.test.tsx — testes dos critérios de aceite.",
        ],
    }.get(
        scenario,
        [
            "app/produto/area-da-issue — ponto citado no pedido.",
            "app/produto/area-da-issue.test.ts — testes dos critérios de aceite.",
        ],
    )
    test_plan = [
        f"CA{index}. {criterion}" for index, criterion in enumerate(criteria, start=1)
    ] or ["CA1. Cobrir o comportamento descrito no resultado esperado."]
    notes = (
        "Plano para o aplicativo de doações de exemplo. Este agente não altera "
        "repositório nenhum; descreve o que o PR deveria conter."
    )
    if feedback:
        notes = f"{notes} Plano ajustado após revisão: {feedback}"
    return DevPlan(
        files_and_areas=areas,
        test_plan=test_plan,
        pr_evidence=[
            "Testes automatizados dos critérios CA citados passando no CI.",
            "Captura ou log que mostre o comportamento novo dentro do perímetro.",
            "Nota no PR listando o que não foi alterado, alinhada ao perímetro de design.",
        ],
        notes=notes,
    )
