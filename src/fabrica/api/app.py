"""Aplicação FastAPI da fábrica.

``POST /pedidos`` inicia o grafo. A aprovação humana pausa em interrupt;
``POST /pedidos/{id}/decisao`` retoma o mesmo fio.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from fabrica import __version__
from fabrica.api.schemas import DecisaoIn, ErroOut, HealthOut, IssueOut, PedidoIn, PedidoOut, StatusItem
from fabrica.llm import load_settings
from fabrica.records import IssueView
from fabrica.service import ConflictError, FactoryService, NotFoundError
from fabrica.telemetry import configure_observability, span

_FINAL = {"publicado", "cancelado", "encerrado_no_limite"}


def create_app(
    *,
    database_url: str | None = None,
    offline: bool | None = None,
    model: Any = None,
    checkpointer: Any = None,
    status_bus: Any = None,
) -> FastAPI:
    """Constrói a API. Os testes passam SQLite em memória e o stub."""
    configure_observability()
    service = FactoryService.create(
        database_url=database_url,
        offline=offline,
        model=model,
        checkpointer=checkpointer,
        status_bus=status_bus,
    )
    app = FastAPI(
        title="Fábrica agêntica",
        version=__version__,
        description=(
            "Cria um pedido, consulta o estado do grafo, aprova ou rejeita a issue "
            "e devolve o Markdown e o JSON publicados."
        ),
    )
    app.state.service = service

    @app.middleware("http")
    async def rastrear_request(request: Any, call_next: Any) -> Any:
        with span(
            f"http {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
        ):
            return await call_next(request)

    @app.exception_handler(NotFoundError)
    async def nao_encontrado(_request: Any, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content=ErroOut(detalhe=str(exc)).model_dump())

    @app.exception_handler(ConflictError)
    async def conflito(_request: Any, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content=ErroOut(detalhe=str(exc)).model_dump())

    @app.get("/health", response_model=HealthOut, tags=["saúde"])
    def health() -> HealthOut:
        """Diz se o processo está no ar e se o modo offline está ligado."""
        settings = load_settings()
        return HealthOut(
            status="ok",
            offline=settings.offline,
            vector_store=os.getenv("FABRICA_VECTOR_STORE", "memory"),
            checkpointer=os.getenv("FABRICA_CHECKPOINTER", "memory"),
        )

    @app.post("/pedidos", response_model=PedidoOut, status_code=201, tags=["pedidos"])
    def criar_pedido(body: PedidoIn) -> PedidoOut:
        """Inicia o grafo e para na aprovação humana."""
        return _pedido(service.criar(body.pedido))

    @app.get("/pedidos/{issue_id}", response_model=PedidoOut, tags=["pedidos"])
    def consultar_pedido(issue_id: str) -> PedidoOut:
        """Devolve a fase e o registro de status."""
        return _pedido(service.obter(issue_id))

    @app.post("/pedidos/{issue_id}/decisao", response_model=PedidoOut, tags=["pedidos"])
    def decidir(issue_id: str, body: DecisaoIn) -> PedidoOut:
        """Aprova ou rejeita. Rejeição com feedback devolve o texto ao produto."""
        return _pedido(service.decidir(issue_id, body.decision, body.feedback))

    @app.get(
        "/pedidos/{issue_id}/issue",
        response_model=IssueOut,
        tags=["issue"],
        responses={409: {"model": ErroOut}},
    )
    def obter_issue(issue_id: str) -> IssueOut:
        """JSON da issue final, com o Markdown dentro."""
        view = _final(service, issue_id)
        return IssueOut(id=view.id, markdown=view.markdown, documento=view.documento)

    @app.get(
        "/pedidos/{issue_id}/issue.md",
        tags=["issue"],
        response_class=PlainTextResponse,
        responses={409: {"model": ErroOut}},
    )
    def obter_issue_markdown(issue_id: str) -> PlainTextResponse:
        """Markdown da issue final."""
        view = _final(service, issue_id)
        return PlainTextResponse(view.markdown, media_type="text/markdown; charset=utf-8")

    return app


def _final(service: FactoryService, issue_id: str) -> IssueView:
    view = service.obter(issue_id)
    if view.fase not in _FINAL or not view.markdown:
        raise ConflictError("A issue ainda não foi publicada.")
    return view


def _pedido(view: IssueView) -> PedidoOut:
    return PedidoOut(
        id=view.id,
        pedido=view.pedido,
        fase=view.fase,
        resultado=view.resultado,
        titulo=view.titulo,
        prioridade=view.prioridade,
        registro_de_status=[StatusItem(**event) for event in view.registro_de_status],
    )


app = create_app()
