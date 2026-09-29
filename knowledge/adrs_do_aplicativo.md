# Decisões de arquitetura do aplicativo de doações

ADRs fictícios. Servem de contexto para design e revisão. Não citam empresa, cliente ou produto real.

## ADR 1 — Cobrança idempotente

O checkout não inicia uma segunda cobrança enquanto a primeira não termina. Toques repetidos no botão Pagar durante o carregamento não criam outra doação.

Consequência para a issue: o plano de implementação inclui o cliente de pagamento e o estado do botão. O contrato da API de cobrança permanece no perímetro do que não se mexe, salvo quando a issue for explicitamente sobre esse contrato.

## ADR 2 — Dado pessoal fora da URL

CPF, e-mail e identificadores do doador não aparecem em URL compartilhada nem em log público. Vazamento sobe na escala de prioridade, à frente de contraste e de ajuste visual.

## ADR 3 — Confirmação separada do checkout

A tela de confirmação só mostra a doação já registrada. Mudança de copy na confirmação não altera o cálculo do valor nem a navegação global.

## ADR 4 — Legado isolado

Cliente HTTP duplicado e módulo de recibo são área de plataforma. Extraí-los é dívida técnica e não entra no mesmo incremento de um bug de pagamento.
