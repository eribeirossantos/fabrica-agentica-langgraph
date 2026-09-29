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

## ADR 007 — API HTTP no mesmo grafo

**Situação.** Um processo seletivo de plataforma pede um serviço, não só um script. A aprovação humana precisa continuar sendo o `interrupt`, agora retomado por um cliente HTTP.

**Decisão.** FastAPI em `src/fabrica/api`. `POST /pedidos` inicia o grafo. `POST /pedidos/{id}/decisao` manda `Command(resume=...)`. O contrato é Pydantic e aparece no OpenAPI. A CLI e a API chamam o mesmo `FactoryService`.

**Consequência.** Sem `thread_id` estável e sem checkpointer, a decisão não tem fio para retomar. O teste usa `TestClient` e SQLite em memória (`tests/test_api.py`).

## ADR 008 — RAG com citação, sem mudar a aresta

**Situação.** Design e revisão precisam de um manual: copy em pt-BR, WCAG 2.1 AA, ADRs fictícios e o formato de critério de aceite. Esse contexto não pode reclassificar o pedido.

**Decisão.** A pasta `knowledge/` é cortada por título, embedada com um hashing determinístico e consultada por um `BaseRetriever`. O índice padrão é em memória. `FABRICA_VECTOR_STORE=pgvector` usa a extensão `vector` no Postgres. Os nós de design e revisão gravam `fontes` depois da resposta do modelo. A tool `buscar_conhecimento` é o mesmo índice, com `@tool`.

**Consequência.** O modo offline não pede chave de embedding. O teste de recuperação confere que contraste acha o checklist e que "dado quando então" acha o padrão de critérios. O diagrama do grafo não ganha nó novo.

## ADR 009 — MCP como outra porta do mesmo serviço

**Situação.** Clientes de agente falam MCP, não só HTTP. A fábrica precisa ser tool, e também saber consumir tool externa.

**Decisão.** `src/fabrica/mcp_server.py` usa o SDK oficial (`mcp`, `FastMCP`) e registra `criar_issue`, `consultar_status` e `buscar_conhecimento` no stdio. `src/fabrica/mcp_client.py` usa `MultiServerMCPClient` do `langchain-mcp-adapters` para carregar essas tools como tools do LangChain.

**Consequência.** API e MCP compartilham `FactoryService`. O teste de cliente sobe o servidor em subprocesso, sem rede e sem chave.

## ADR 010 — Um provedor por agente, inclusive Azure

**Situação.** Times misturam OpenAI, Azure OpenAI, Anthropic e Google. O padrão do repositório continua sendo o stub.

**Decisão.** `LLM_PROVIDER` vale para todos. `PRODUCT_LLM_PROVIDER`, `DESIGN_LLM_PROVIDER`, `DEV_LLM_PROVIDER` e `REVIEW_LLM_PROVIDER` cobrem um papel só. Azure usa `AzureChatOpenAI` com endpoint, versão e deployment no ambiente. `FABRICA_OFFLINE=1` ignora essa escolha.

**Consequência.** O teste do grafo injeta um único modelo falso e não lê provedor. Chave ausente gera erro em português e não chama a rede.

## ADR 011 — Trace por nó e avaliação offline

**Situação.** Quando o fluxo falha, "o modelo errou" não diz em qual nó. E a classificação precisa de uma nota que o CI consiga calcular sem LangSmith.

**Decisão.** OpenTelemetry abre um span por nó do grafo e por request da API. O exportador sai de `OTEL_TRACES_EXPORTER`: `none`, `console` ou `otlp`. O logger `fabrica` aceita JSON. `LANGSMITH_TRACING` liga o tracing do LangChain quando houver chave; o código não importa um cliente próprio. `src/fabrica/evals` roda um dataset fixo e mede acerto de tipo, acerto de prioridade, critérios presentes e perímetro respeitado.

**Consequência.** O pytest fica em silêncio com `OTEL_TRACES_EXPORTER=none`. `make evals` quebra se alguma métrica sair de 1 no stub.

## ADR 012 — Três memórias, três papéis

**Situação.** Checkpoint, issue consultável e canal de status não são a mesma coisa. Um restart não pode apagar a issue, e um assinante não precisa ler a tabela para saber que o status mudou.

**Decisão.** O checkpointer é memória, SQLite ou Postgres (`langgraph-checkpoint-postgres`), escolhido por `FABRICA_CHECKPOINTER`. SQLAlchemy guarda a issue e o histórico de status. Redis faz lista e pub-sub do canal; sem URL, o canal fica em memória. Testes de integração com esses serviços são marcados e o `pytest` padrão os ignora.

**Consequência.** A API de teste não sobe Docker. O `docker compose` sobe Postgres com pgvector, Redis e a API já apontando para eles, ainda em modo offline.

## ADR 013 — Imagem e compose sem chave

**Situação.** O CI precisa provar que a imagem constrói, e um recrutador precisa subir a API com um comando.

**Decisão.** Dockerfile em dois estágios, Python 3.12, extra `infra` na imagem. Compose com API, Postgres (`pgvector/pgvector:pg16`) e Redis. Jaeger e o coletor OTLP ficam no perfil `observability`, para o `up` padrão não depender deles. Embeddings na imagem são o hashing determinístico.

**Consequência.** O workflow gera a imagem no job `imagem` e continua rodando lint e pytest offline em 3.11 e 3.12.
