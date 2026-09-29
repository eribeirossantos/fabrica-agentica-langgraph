# Issue: Aumentar o contraste do texto de confirmação da doação

> Publicada após aprovação e revisão.

- **Pedido original:** melhoria: aumentar o contraste do texto de confirmação da doação
- **Tipo:** melhoria
- **Área:** acessibilidade
- **Prioridade:** P3 — acessibilidade
- **Labels:** `tipo:melhoria` `área:acessibilidade` `prioridade:P3`

## Resumo

O texto da confirmação da doação fica abaixo do contraste mínimo. O corte seguro é ajustar só essa cor.

## Problema

O texto da tela de confirmação da doação tem contraste insuficiente. Parte das pessoas não consegue ler o comprovante.

## Resultado esperado

O texto principal da confirmação atinge contraste de pelo menos 4,5:1 com o fundo, e o restante da tela permanece igual.

## Menor incremento seguro

Trocar apenas a cor do texto de confirmação, e do fundo se isso for indispensável para o contraste, sem redesenhar a tela.

## Fora de escopo

- Redesenhar a tela de confirmação.
- Incluir campos novos no comprovante.
- Alterar o fluxo de pagamento ou o botão Pagar.

## Riscos

- Escurecer o texto pode colidir com um fundo de sucesso que também seja escuro.
- Mudar um token de cor global afetaria telas fora do perímetro.

## Critérios de aceite

- [ ] CA1. Dado a tela de confirmação, quando o texto principal é medido sobre o fundo, então a razão de contraste é de pelo menos 4,5:1.
- [ ] CA2. Dado um leitor de tela, quando a confirmação abre, então o texto continua sendo anunciado com o mesmo conteúdo.
- [ ] CA3. Dado o restante do aplicativo, quando a correção é aplicada, então botões e telas fora da confirmação permanecem iguais.

## Especificação de design

### Perímetro (não tocar)

- Fluxo de pagamento e botão Pagar.
- Ordem e estrutura dos elementos da confirmação.
- Textos cujo contraste já atende 4,5:1.

### Mudanças de UI

- Ajustar a cor do texto principal da confirmação para um token com contraste de pelo menos 4,5:1.
- Não usar a cor como única indicação de sucesso.

### Copy (pt-BR)

- **Título da confirmação:** Doação confirmada
- **Corpo:** Sua doação foi registrada. Guarde este comprovante.
- **Ação secundária:** Voltar ao início

### Acessibilidade (WCAG 2.1 AA)

- WCAG 2.1 AA — contraste mínimo de 4,5:1 para texto normal (critério 1.4.3).
- WCAG 2.1 AA — nome, função e estado disponíveis para tecnologia assistiva (critério 4.1.2).
- WCAG 2.1 AA — operação por teclado e foco visível (critérios 2.1.1 e 2.4.7).
- WCAG 2.1 AA — a informação não depende só de cor (critério 1.4.1).

## Plano de implementação

Plano para o aplicativo de doações de exemplo. Este agente não altera repositório nenhum; descreve o que o PR deveria conter.

### Arquivos e áreas

- app/confirmacao/Confirmacao.module.css — cor do texto principal.
- app/confirmacao/tokens.css — token de cor usado só na confirmação.
- app/confirmacao/contraste.test.ts — medição do contraste e regressão das outras telas.

### Plano de testes

- CA1. Dado a tela de confirmação, quando o texto principal é medido sobre o fundo, então a razão de contraste é de pelo menos 4,5:1.
- CA2. Dado um leitor de tela, quando a confirmação abre, então o texto continua sendo anunciado com o mesmo conteúdo.
- CA3. Dado o restante do aplicativo, quando a correção é aplicada, então botões e telas fora da confirmação permanecem iguais.

### Evidências esperadas no PR

- Testes automatizados dos critérios CA citados passando no CI.
- Captura ou log que mostre o comportamento novo dentro do perímetro.
- Nota no PR listando o que não foi alterado, alinhada ao perímetro de design.

## Revisão

- **Veredito:** aprovado
- **Destino:** nenhum

- Pacote cobre os critérios de aceite e respeita o perímetro.

## Registro de status

[produto] issue especificada — P3 · melhoria · acessibilidade — Aumentar o contraste do texto de confirmação da doação
[product owner] aprovado — Issue aprovada para design.
[design] especificação de design pronta — 3 itens no perímetro.
[dev] plano de implementação pronto — 3 testes planejados.
[revisão] revisão aprovada — Pacote cobre os critérios de aceite e respeita o perímetro.
[fábrica] publicado — Issue publicada em Markdown e JSON.
