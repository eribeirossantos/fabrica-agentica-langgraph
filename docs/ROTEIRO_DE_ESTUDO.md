# Roteiro de estudo — LangChain e LangGraph em 4 semanas

Para quem já desenha fluxos de agentes numa plataforma sem código e quer o mesmo vocabulário em Python. Cada semana usa este repositório como laboratório. A carga cabe ao lado de um trabalho: leia a página, reproduza um pedaço da fábrica, faça o exercício.

Os links abaixo são a documentação oficial. Vários endereços antigos redirecionam para a página atual; isso foi conferido em setembro de 2026. Não incluí URL antiga que hoje cai só na visão geral, porque ela não abre o assunto.

Mapa mental, da plataforma para o código:

| Na plataforma | Neste repositório |
| --- | --- |
| Nó de agente com prompt | Nó do grafo + prompt em `src/fabrica/prompts.py` |
| Saída com campos fixos | Modelo Pydantic e structured output |
| Roteador | `route_after_approval` e `route_after_review` |
| Aprovação humana | `interrupt` no nó `approval` |
| Memória da execução | Estado do grafo + checkpointer + `thread_id` |
| Canal de status | `status_log` com redutor de lista |
| Ferramenta | `@tool buscar_conhecimento` em `src/fabrica/tools.py` |

## Semana 1 — modelo, mensagem, tool e saída estruturada

**Meta.** Chamar um chat model por trás do contrato que a fábrica já usa, e entender por que a saída estruturada importa mais do que um parágrafo livre.

**Conceitos.**

- Visão geral do LangChain: [introdução](https://python.langchain.com/docs/introduction/).
- Chat model e provedores: [modelos](https://python.langchain.com/docs/concepts/chat_models/), [índice de integrações](https://python.langchain.com/docs/integrations/chat/), [OpenAI](https://python.langchain.com/docs/integrations/chat/openai/), [Anthropic](https://python.langchain.com/docs/integrations/chat/anthropic/), [Google](https://python.langchain.com/docs/integrations/chat/google_generative_ai/).
- Mensagens: a página de [entrada multimodal](https://python.langchain.com/docs/how_to/multimodal_inputs/) abre o guia atual de messages. `SystemMessage` e `HumanMessage` já estão em `src/fabrica/llm.py`.
- Saída estruturada: [structured output](https://python.langchain.com/docs/how_to/structured_output/).
- Tools no guia de agentes: [configuração básica de agente](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/) e [saída estruturada no agente](https://langchain-ai.github.io/langgraph/how-tos/react-agent-structured-output/).
- Runnable. A documentação antiga de LCEL foi reorganizada e o endereço antigo não abre mais uma página própria. O que continua valendo: um runnable é uma unidade com `invoke`. Na fábrica, esse contrato é `invoke(schema, system, user)`, implementado pelo stub e por `LangChainModel`. A composição com estado e desvio fica no grafo, não numa corrente de pipes.

**No repositório.** Leia `src/fabrica/schemas.py`, `src/fabrica/llm.py`, `src/fabrica/prompts.py` e `src/fabrica/stub.py`. Os prompts são `ChatPromptTemplate`. O modo com API usa `with_structured_output` no mesmo schema que o stub preenche. A tool visível é `buscar_conhecimento`. Rode `python -m fabrica --auto-approve "bug: botão de pagar não responde no celular"` e compare com `examples/saidas/01-bug-pagar.md`.

**Exercício.** Crie uma tool `normalize_request` que devolve prefixo e corpo (`split_prefix` já existe). No modo online, faça o nó de produto chamá-la antes do structured output. Mantenha o stub capaz de responder sem rede, e acrescente um teste que não usa chave. Não mova a prioridade para dentro da tool: a semana 1 não afrouxa a política. Compare com `buscar_conhecimento`: ela devolve trecho e citação, e o nó é quem grava `fontes`.

## Semana 2 — grafo de estado, aresta condicional e checkpointer

**Meta.** Ler um fluxo da plataforma e reescrever a parte "se rejeitar, volta" como aresta, com o estado sobrevivendo à pausa.

**Conceitos.**

- [Visão geral do LangGraph](https://langchain-ai.github.io/langgraph/) e [quickstart](https://langchain-ai.github.io/langgraph/tutorials/get-started/1-build-basic-chatbot/).
- [Graph API](https://langchain-ai.github.io/langgraph/concepts/low_level/): estado, nós, arestas, compilação.
- [Desvios condicionais](https://langchain-ai.github.io/langgraph/how-tos/branching/).
- [Persistência](https://langchain-ai.github.io/langgraph/concepts/persistence/) e o how-to de [memória no grafo](https://langchain-ai.github.io/langgraph/how-tos/persistence/).
- Referência de [checkpoints](https://langchain-ai.github.io/langgraph/reference/checkpoints/).
- [Pregel](https://langchain-ai.github.io/langgraph/concepts/pregel/), se quiser ver o motor por baixo do `StateGraph`. O uso diário continua sendo a Graph API.
- [Streaming](https://langchain-ai.github.io/langgraph/concepts/streaming/), para o canal de status sair enquanto o grafo anda, não só no final.

**No repositório.** `src/fabrica/state.py`, `src/fabrica/graph.py` e `tests/test_routing.py`. Gere o diagrama com `python -m fabrica --diagrama` e confira que `docs/grafo.mmd` mudou se você acrescentar um nó.

**Exercício.** Adicione um nó `triage` antes de `product` que só normaliza o pedido e publica uma linha no `status_log`. A aresta seguinte continua indo para produto. Atualize o teste das arestas e regenere `docs/grafo.mmd`. Como segundo passo, troque o checkpointer. `src/fabrica/persistence/checkpointer.py` já escolhe memória, SQLite ou Postgres por `FABRICA_CHECKPOINTER`. Rode duas vezes com o mesmo `thread_id` num saver que grave em disco. Comece pela página de persistência; não invente um formato paralelo de histórico. A issue consultável pela API fica no SQLAlchemy, separada do checkpoint.

## Semana 3 — humano no laço, memória e vários agentes

**Meta.** Explicar, sem hesitar, por que a aprovação está dentro do grafo e qual a diferença entre este grafo fixo e um supervisor que escolhe o próximo agente.

**Conceitos.**

- [Interrupts](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/) e o how-to [human-in-the-loop](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/add-human-in-the-loop/).
- [Execução durável](https://langchain-ai.github.io/langgraph/concepts/durable_execution/): por que o nó recomeça e o que isso exige do código antes do `interrupt`.
- [Memória](https://langchain-ai.github.io/langgraph/concepts/memory/): o fio curto da execução (estado + checkpoint) versus memória entre conversas.
- [Workflows e agentes](https://langchain-ai.github.io/langgraph/concepts/agentic_concepts/). O antigo tutorial de supervisor abre essa mesma página: [agent supervisor](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/).
- [Subgrafos](https://langchain-ai.github.io/langgraph/how-tos/subgraph/), quando um agente precisar de um fluxo interno.
- [Functional API](https://langchain-ai.github.io/langgraph/concepts/functional_api/), para saber que existe outro estilo e quando ele não substitui o grafo explícito. Esta fábrica fica na Graph API de propósito.

**No repositório.** O comentário no nó `approval` em `src/fabrica/graph.py` e os testes `test_rejeicao_volta_ao_produto_e_aprovacao_publica` e `test_tres_rejeicoes_cancelam`. Rode sem `--auto-approve` e rejeite uma vez com um feedback curto. Procure a frase no problema da issue publicada.

**Exercício.** Inclua um segundo `interrupt` no nó `publish`, antes de gravar a issue, para a pessoa aceitar ou pedir ajuste de design. Reaproveite o checkpointer; não abra um `input()` paralelo. Escreva o teste do novo laço no mesmo estilo de `tests/test_graph_flow.py`: uma rejeição volta, a aprovação seguinte termina, e um limite impede o giro infinito.

Compare, por escrito, em dez linhas: por que esta fábrica não usa um supervisor. A resposta esperada está na seção de entrevista, mais abaixo. Escreva a sua antes de ler.

## Semana 4 — RAG, avaliação, rastreio e deploy

**Meta.** Saber o que falta para esta fábrica sair do notebook mental e ir para um processo de time: medida, rastreio e um processo que sobe o grafo.

**Conceitos.**

- RAG com grafo: [agentic RAG](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_agentic_rag/). O básico continua sendo retriever, contexto e resposta com fonte. O tutorial mostra a versão em que o grafo decide buscar de novo.
- Observabilidade: [LangSmith](https://docs.smith.langchain.com/observability), [início rápido de tracing](https://docs.smith.langchain.com/tracing) e o guia que abre em [trace com LangChain](https://docs.smith.langchain.com/observability/how_to_guides). As variáveis usuais são `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` e `LANGSMITH_PROJECT`. Elas estão comentadas no `.env.example`. Não commite a chave.
- Avaliação: [conceitos](https://docs.smith.langchain.com/evaluation), [visão de avaliação](https://docs.smith.langchain.com/evaluation/concepts), [avaliar uma aplicação](https://docs.smith.langchain.com/evaluation/how_to_guides), [quickstart](https://docs.smith.langchain.com/evaluation/tutorials) e [pytest](https://docs.smith.langchain.com/cookbook/testing-examples/pytest).
- Subir o grafo: [deployment](https://langchain-ai.github.io/langgraph/tutorials/deployment/), [estrutura da aplicação](https://langchain-ai.github.io/langgraph/concepts/application_structure/), [CLI](https://langchain-ai.github.io/langgraph/concepts/langgraph_cli/), [Agent Server](https://langchain-ai.github.io/langgraph/concepts/langgraph_server/) e [Studio](https://langchain-ai.github.io/langgraph/cloud/how-tos/studio/quick_start/).

**No repositório.** `knowledge/` é o manual. `src/fabrica/rag` ingere, corta e busca. Design e revisão citam a fonte. `make evals` roda `src/fabrica/evals`. A API está em `src/fabrica/api`, o servidor MCP em `src/fabrica/mcp_server.py`, o trace em `src/fabrica/telemetry.py`. O CI faz lint, teste offline e build da imagem em Python 3.11 e 3.12.

**Exercício.** Rode `make evals` e leia as quatro métricas. Acrescente um pedido ao `dataset.json` com tipo e prioridade que a política já cobre, e veja a nota cair se você errar o esperado. Se tiver chave do LangSmith, rode uma corrida `--online` com `LANGSMITH_TRACING=true` e anote o `thread_id`. Sem chave, `OTEL_TRACES_EXPORTER=console` mostra o span de cada nó. Suba a API com `make run-api` ou `docker compose up --build` e aprove um pedido com os `curl` do README.

O RAG desta fábrica busca antes de design e de revisão, não antes do produto, de propósito: a prioridade continua na política. A issue cita o arquivo e a seção. Não use o trecho recuperado para furar essa regra.

## Perguntas de entrevista

Respostas curtas, amarradas a este código. Use-as para treinar em voz alta.

**LangChain e LangGraph são a mesma coisa?**
São camadas diferentes. LangChain é o modelo, a mensagem, a tool e a saída estruturada. LangGraph é o fluxo com estado, aresta e pausa. Aqui, `llm.py` é LangChain; `graph.py` é LangGraph.

**Por que não deixar o modelo escolher o próximo agente?**
Porque o processo é conhecido: produto, aprovação, design, dev, revisão. Um supervisor livre esconde a regra e dificulta o teste. Aresta condicional deixa a regra em função pura, coberta por `tests/test_routing.py`. Supervisor passa a fazer sentido quando o conjunto de especialistas muda a cada pedido e a rota não cabe numa tabela.

**O que o checkpointer guarda, e para que serve o `thread_id`?**
O checkpoint é o estado no meio da execução, inclusive a pausa do `interrupt`. O `thread_id` escolhe qual execução retomar. Sem os dois, a aprovação humana não tem de onde continuar. Veja `execute` em `src/fabrica/runner.py`.

**Por que o código antes do `interrupt` não pode ter efeito colateral?**
Na retomada o nó roda de novo desde a primeira linha. `interrupt` devolve o valor enviado em `Command(resume=...)` e não pausa outra vez. Se o status "aguardando aprovação" fosse gravado antes do `interrupt`, ele duplicaria. Por isso a decisão só entra no `status_log` depois.

**Por que a prioridade não sai do structured output?**
Porque é regra, não redação. O modelo preenche problema, critério e incremento. `classify_request` e `prioritize_request` sobrescrevem tipo, área e prioridade. O teste `test_politica_vence_o_titulo_do_modelo` mostra um modelo que mente no título e ainda assim não muda o P1.

**Como você testa um grafo de agentes sem pagar API?**
O stub implementa o mesmo método do chat model e devolve os schemas. O CI exporta `FABRICA_OFFLINE=1`. Laços que o stub sozinho não provoca usam `tests/fakes.py`: design incompleto uma vez, plano de dev sempre sem teste. O limite de revisão é `MAX_REVIEW_ITERATIONS`.

**O que impede o ciclo de revisão de nunca acabar?**
A aresta. Se o veredito não é `aprovado` e `review_iterations` chegou ao teto, o destino é `publish`, com resultado `encerrado_no_limite` e os achados no Markdown. O teste `test_revisao_para_no_limite` conta as chamadas ao dev e exige que seja exatamente o teto, não mais.

**Onde está o RAG, e por que ele não escolhe a prioridade?**
Em `knowledge/` e no retriever usado por design e revisão. A citação fica em `fontes`. Tipo e prioridade continuam em `policy.py`. O tutorial de referência é o de agentic RAG linkado na semana 4. O embedding padrão é determinístico, para o teste rodar sem chave. Pgvector é a opção quando o compose sobe o Postgres.

**Como você provaria que a classificação não regrediu?**
Com a tabela de `tests/test_policy.py` no CI e com `make evals`, que mede tipo, prioridade, critérios presentes e perímetro respeitado. Estilo de redação não entra nessa nota. LangSmith entra quando houver chave; o dataset offline já existe.

**O que você colocaria em produção primeiro?**
Checkpointer Postgres, issue no SQLAlchemy, canal de status no Redis, segredo só em ambiente, trace por nó sem gravar a chave, e o mesmo modo offline para o teste de regressão. A API e o servidor MCP já sobem esse grafo. O que ainda falta está nos próximos passos.

**Por que a API e o MCP chamam o mesmo serviço?**
Porque o fio do grafo é um só. `FactoryService` inicia o pedido, lê a fase e retoma o `interrupt`. HTTP e MCP são portas. Duplicar o grafo em cada porta faria a aprovação divergir.

**Como você troca o modelo de um agente sem mexer no outro?**
Com `DESIGN_LLM_PROVIDER` e o par de modelo, caindo em `LLM_PROVIDER` quando o específico está vazio. Azure é mais um provedor, com endpoint e deployment no ambiente. `FABRICA_OFFLINE=1` devolve o stub para todos.

## Próximos passos

- **Kubernetes e Helm.** Chart com API, Postgres e Redis, probe em `/health`, segredo fora da imagem e volume ou serviço gerenciado para o checkpointer.
- **CrewAI ou AutoGen.** Úteis quando os especialistas negociam a rota. Nesta fábrica a rota é conhecida; o exercício é explicar em voz alta quando o grafo fixo deixa de ser a melhor escolha.
- **Arquitetura orientada a eventos.** O Redis já publica o status. O passo seguinte é um consumidor para notificação e auditoria, e um pedido que não precise segurar a conexão HTTP até o fim do grafo.
