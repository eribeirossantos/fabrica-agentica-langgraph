# Issue: O que acontece com a doação se o pagamento falhar?

> Publicada após aprovação e revisão.

- **Pedido original:** dúvida: o que acontece com a doação se o pagamento falhar?
- **Tipo:** dúvida
- **Área:** checkout
- **Prioridade:** P4 — clareza para o usuário
- **Labels:** `tipo:duvida` `área:checkout` `prioridade:P4`

## Resumo

A falha de pagamento não explica se a doação foi registrada. O corte seguro é uma frase nesse estado de erro.

## Problema

Quando o pagamento falha, a pessoa não sabe se a doação foi registrada nem se o valor será cobrado de novo.

## Resultado esperado

A tela de falha diz, em uma frase, que a doação não foi registrada e que nenhuma cobrança extra foi feita, e oferece tentar de novo.

## Menor incremento seguro

Incluir somente a mensagem de falha no estado de erro do pagamento, sem mudar a regra de cobrança.

## Fora de escopo

- Retentativa automática do pagamento.
- Troca de meio de pagamento ou de regra de cobrança.
- Fluxo novo de estorno.

## Riscos

- A frase 'nenhuma cobrança extra' precisa ser verdadeira para os meios já existentes.
- Um texto longo demais empurra a ação de tentar de novo para fora da primeira dobra no celular.

## Critérios de aceite

- [ ] CA1. Dado um pagamento recusado, quando a falha é exibida, então a pessoa lê que a doação não foi registrada.
- [ ] CA2. Dado a mesma falha, quando a mensagem aparece, então ela informa que não houve cobrança extra.
- [ ] CA3. Dado a mensagem de falha, quando a pessoa aciona Tentar de novo, então o checkout reabre sem criar uma segunda doação.

## Especificação de design

### Perímetro (não tocar)

- Regra de cobrança e meios de pagamento.
- Tela de sucesso da doação.
- Navegação global.

### Mudanças de UI

- No estado de falha do pagamento, mostrar a explicação antes da ação de tentar de novo.
- Manter a ação Tentar de novo visível sem rolagem no celular.

### Copy (pt-BR)

- **Mensagem de falha:** A doação não foi registrada. Nenhuma cobrança extra foi feita.
- **Ação:** Tentar de novo

### Acessibilidade (WCAG 2.1 AA)

- WCAG 2.1 AA — contraste mínimo de 4,5:1 para texto normal (critério 1.4.3).
- WCAG 2.1 AA — nome, função e estado disponíveis para tecnologia assistiva (critério 4.1.2).
- WCAG 2.1 AA — operação por teclado e foco visível (critérios 2.1.1 e 2.4.7).
- WCAG 2.1 AA — a informação não depende só de cor (critério 1.4.1).

### Fontes

- guia_de_copy.md#estados-do-pagamento
- guia_de_copy.md#tom-da-interface
- padroes_de_criterios.md#formato-dado-quando-entao

## Plano de implementação

Plano para o aplicativo de doações de exemplo. Este agente não altera repositório nenhum; descreve o que o PR deveria conter.

### Arquivos e áreas

- app/checkout/PaymentFailure.tsx — mensagem do estado de erro.
- app/checkout/mensagens.ts — copy final da falha.
- app/checkout/PaymentFailure.test.tsx — testes dos critérios de aceite.

### Plano de testes

- CA1. Dado um pagamento recusado, quando a falha é exibida, então a pessoa lê que a doação não foi registrada.
- CA2. Dado a mesma falha, quando a mensagem aparece, então ela informa que não houve cobrança extra.
- CA3. Dado a mensagem de falha, quando a pessoa aciona Tentar de novo, então o checkout reabre sem criar uma segunda doação.

### Evidências esperadas no PR

- Testes automatizados dos critérios CA citados passando no CI.
- Captura ou log que mostre o comportamento novo dentro do perímetro.
- Nota no PR listando o que não foi alterado, alinhada ao perímetro de design.

## Revisão

- **Veredito:** aprovado
- **Destino:** nenhum

- Pacote cobre os critérios de aceite e respeita o perímetro.

### Fontes

- padroes_de_criterios.md#formato-dado-quando-entao
- guia_de_copy.md#estados-do-pagamento
- padroes_de_criterios.md#perimetro-no-criterio

## Registro de status

[produto] issue especificada — P4 · dúvida · checkout — O que acontece com a doação se o pagamento falhar?
[product owner] aprovado — Issue aprovada para design.
[design] especificação de design pronta — 3 itens no perímetro.
[dev] plano de implementação pronto — 3 testes planejados.
[revisão] revisão aprovada — Pacote cobre os critérios de aceite e respeita o perímetro.
[fábrica] publicado — Issue publicada em Markdown e JSON.
