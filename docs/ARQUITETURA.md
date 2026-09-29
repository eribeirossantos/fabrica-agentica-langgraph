# Arquitetura

Decisões curtas sobre o desenho desta fábrica. O contexto é um fluxo de entrada que já existe como orquestração de agentes numa plataforma sem código e que aqui foi reescrito em LangGraph para ficar legível, testável e portável.

## ADR 001 — LangGraph, não uma corrente linear

**Situação.** O fluxo tem volta: o product owner rejeita e o produto reescreve; a revisão devolve para design ou para dev. Uma cadeia `prompt | modelo | próximo prompt` não representa isso sem um `while` por fora.

**Decisão.** Um `StateGraph` com nós nomeados e arestas condicionais. O próximo passo é função do estado, não uma escolha livre do modelo.

**Consequência.** O diagrama em `docs/grafo.mmd` é o processo. Dá para apontar para uma aresta numa entrevista e mostrar o teste que a cobre (`tests/test_routing.py`).

## ADR 002 — Estado tipado e saídas estruturadas

**Situação.** Cada agente precisa ler o que o anterior decidiu e devolver um pacote com campos estáveis: issue, spec, plano, revisão.

**Decisão.** O estado é um `TypedDict` (`src/fabrica/state.py`). A saída de cada agente é um modelo Pydantic (`src/fabrica/schemas.py`). O registro de status usa um redutor que soma listas, para a volta no grafo não apagar o histórico.

**Consequência.** Markdown e JSON saem dos mesmos campos. O modo com API usa `with_structured_output` no mesmo schema que o stub preenche offline.

## ADR 003 — Classificação e prioridade em código

**Situação.** A escala é regra de negócio: não perder transação ou doação, não vazar dado, acessibilidade, clareza, cosmético. Um modelo pode inverter essa ordem num dia ruim.

**Decisão.** `src/fabrica/policy.py` classifica, prioriza e escolhe a área. O nó de produto chama o modelo para a narrativa e em seguida grava tipo, área e prioridade por cima de qualquer texto.

**Consequência.** Os testes da escala não dependem de API. Uma pergunta hipotética (`o que acontece se`) não vira incidente de pagamento. Relato de vazamento em um `bug:` sobe para `risco`.

## ADR 004 — Aprovação com interrupt e checkpointer

**Situação.** A plataforma sem código tem um passo humano no meio do fluxo. Em código, o equivalente útil é pausar o grafo e retomar depois, não bloquear uma função com `input()` sem estado persistido.

**Decisão.** O nó `approval` chama `interrupt`. O grafo só compila com checkpointer. A CLI usa `MemorySaver` e um `thread_id`. Retomar manda `Command(resume=...)`. O nó reexecuta do início; a decisão só é registrada depois que `interrupt` devolve o valor.

**Consequência.** Três rejeições seguem para publicação com resultado `cancelado`, para o laço não ser infinito. O limite está em `MAX_APPROVAL_ROUNDS`.

## ADR 005 — Modo offline como caminho padrão

**Situação.** Processo seletivo, CI e leitura do repositório não podem depender de chave. O contrato com o modelo, porém, precisa ser o mesmo do modo online.

**Decisão.** `StubModel` implementa `invoke(schema, system, user)` e devolve os modelos Pydantic. `LLM_PROVIDER=stub` ou `FABRICA_OFFLINE=1` seleciona esse caminho. OpenAI, Anthropic e Google entram por variável de ambiente, com as bibliotecas no extra `llm`. Chave só no ambiente, nunca no git.

**Consequência.** `pytest` e o workflow de CI rodam o grafo inteiro sem rede. Os arquivos em `examples/saidas/` são essa execução, versionada.

## ADR 006 — Revisão determinística com teto

**Situação.** A revisão precisa poder devolver o pacote, mas um modelo que sempre pede mais uma volta impede o fluxo de terminar.

**Decisão.** `evaluate_package` confere perímetro, copy, menção a WCAG 2.1 AA e a presença de `CA1`, `CA2`, ... no plano de testes. Achado de design volta para Design (e o Dev roda de novo em seguida, porque a aresta é design → dev). Achado só de dev volta para Dev. Na terceira revisão sem aprovação, a aresta vai para publicação com resultado `encerrado_no_limite`.

**Consequência.** O laço é testável com um modelo falso que entrega spec ou plano incompleto (`tests/test_graph_flow.py`). O veredito não muda se o modelo narrativo discordar.
