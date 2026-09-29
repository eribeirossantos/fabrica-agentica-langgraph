# Issue: Botão de pagar não responde no celular

> Publicada após aprovação e revisão.

- **Pedido original:** bug: botão de pagar não responde no celular
- **Tipo:** bug
- **Área:** checkout
- **Prioridade:** P1 — não perder transação ou doação
- **Labels:** `tipo:bug` `área:checkout` `prioridade:P1`

## Resumo

O toque em Pagar no celular não inicia a doação. O corte seguro é corrigir só esse disparo.

## Problema

No celular, o botão de pagar da tela de checkout não inicia o pagamento. A pessoa toca e nada acontece, então a doação não é registrada.

## Resultado esperado

Ao tocar uma vez em Pagar no celular, o pagamento inicia, o botão mostra carregamento e a doação segue para a confirmação, sem cobrança duplicada.

## Menor incremento seguro

Corrigir apenas o disparo do pagamento no toque móvel, sem redesenhar o checkout nem incluir meio de pagamento novo.

## Fora de escopo

- Redesenhar o layout do checkout.
- Adicionar ou remover meios de pagamento.
- Alterar valor, recibo ou mensagens posteriores à confirmação.

## Riscos

- Trocar o evento de clique em vez de complementar o toque pode quebrar o desktop.
- Sem idempotência, toques repetidos durante o carregamento criam doações duplicadas.

## Critérios de aceite

- [ ] CA1. Dado um celular com o checkout aberto, quando a pessoa toca uma vez em Pagar, então o pagamento inicia e o botão entra em carregamento em até um segundo.
- [ ] CA2. Dado o pagamento confirmado, quando a resposta de sucesso chega, então a doação aparece registrada e a tela de confirmação é exibida.
- [ ] CA3. Dado um toque extra enquanto o botão está em carregamento, quando o primeiro toque já foi aceito, então só uma doação é criada.

## Especificação de design

### Perímetro (não tocar)

- Meios de pagamento e o contrato da API de cobrança.
- Cálculo do valor da doação.
- Navegação global, cabeçalho e rodapé.
- Conteúdo da tela de confirmação, fora o estado que o botão dispara.

### Mudanças de UI

- O botão Pagar ganha estado de carregamento no toque, com indicação visível.
- Toques adicionais durante o carregamento não disparam outra cobrança.
- O foco permanece no botão até a ida para a confirmação.

### Copy (pt-BR)

- **Botão principal:** Pagar doação
- **Estado de carregamento:** Pagamento em andamento
- **Erro recuperável:** Não foi possível pagar. Tente de novo. Nenhuma cobrança extra foi feita.
- **Confirmação:** Doação registrada

### Acessibilidade (WCAG 2.1 AA)

- WCAG 2.1 AA — contraste mínimo de 4,5:1 para texto normal (critério 1.4.3).
- WCAG 2.1 AA — nome, função e estado disponíveis para tecnologia assistiva (critério 4.1.2).
- WCAG 2.1 AA — operação por teclado e foco visível (critérios 2.1.1 e 2.4.7).
- WCAG 2.1 AA — a informação não depende só de cor (critério 1.4.1).

## Plano de implementação

Plano para o aplicativo de doações de exemplo. Este agente não altera repositório nenhum; descreve o que o PR deveria conter.

### Arquivos e áreas

- app/checkout/PayButton.tsx — toque e estado de carregamento.
- app/checkout/payment-client.ts — não iniciar segunda cobrança enquanto a primeira não termina.
- app/checkout/PayButton.test.tsx — testes dos critérios de aceite.

### Plano de testes

- CA1. Dado um celular com o checkout aberto, quando a pessoa toca uma vez em Pagar, então o pagamento inicia e o botão entra em carregamento em até um segundo.
- CA2. Dado o pagamento confirmado, quando a resposta de sucesso chega, então a doação aparece registrada e a tela de confirmação é exibida.
- CA3. Dado um toque extra enquanto o botão está em carregamento, quando o primeiro toque já foi aceito, então só uma doação é criada.

### Evidências esperadas no PR

- Testes automatizados dos critérios CA citados passando no CI.
- Captura ou log que mostre o comportamento novo dentro do perímetro.
- Nota no PR listando o que não foi alterado, alinhada ao perímetro de design.

## Revisão

- **Veredito:** aprovado
- **Destino:** nenhum

- Pacote cobre os critérios de aceite e respeita o perímetro.

## Registro de status

[produto] issue especificada — P1 · bug · checkout — Botão de pagar não responde no celular
[product owner] aprovado — Issue aprovada para design.
[design] especificação de design pronta — 4 itens no perímetro.
[dev] plano de implementação pronto — 3 testes planejados.
[revisão] revisão aprovada — Pacote cobre os critérios de aceite e respeita o perímetro.
[fábrica] publicado — Issue publicada em Markdown e JSON.
