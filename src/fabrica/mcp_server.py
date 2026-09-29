"""Servidor MCP da fábrica.

Expõe três tools no transporte stdio: criar um pedido, consultar o status
e buscar a base de conhecimento. A API HTTP usa o mesmo serviço.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from fabrica.service import FactoryService, NotFoundError
from fabrica.tools import buscar_conhecimento

_service: FactoryService | None = None


def get_service() -> FactoryService:
    """Serviço do processo do servidor. Offline se o ambiente pedir."""
    global _service
    if _service is None:
        _service = FactoryService.create()
    return _service


def criar_issue(pedido: str, auto_aprovar: bool = True, service: FactoryService | None = None) -> str:
    """Cria o pedido e, se pedido, aprova até a issue sair do interrupt."""
    ativo = service or get_service()
    view = ativo.criar(pedido)
    if auto_aprovar:
        view = ativo.publicar_ate_o_fim(view.id)
    return _dump({"id": view.id, "fase": view.fase, "resultado": view.resultado, "titulo": view.titulo})


def consultar_status(issue_id: str, service: FactoryService | None = None) -> str:
    """Devolve fase, resultado e o registro de status."""
    ativo = service or get_service()
    try:
        view = ativo.obter(issue_id)
    except NotFoundError as exc:
        return _dump({"erro": str(exc)})
    return _dump(
        {
            "id": view.id,
            "fase": view.fase,
            "resultado": view.resultado,
            "registro_de_status": view.registro_de_status,
        }
    )


def buscar_conhecimento_texto(consulta: str) -> str:
    """Trechos citados da base de conhecimento."""
    return str(buscar_conhecimento.invoke({"consulta": consulta}))


def build_server() -> FastMCP:
    """Registra as tools no SDK oficial."""
    server = FastMCP("fabrica")

    @server.tool(name="criar_issue")
    def criar_issue_tool(pedido: str, auto_aprovar: bool = True) -> str:
        """Cria um pedido na fábrica e, por padrão, aprova até publicar a issue."""
        return criar_issue(pedido, auto_aprovar=auto_aprovar)

    @server.tool(name="consultar_status")
    def consultar_status_tool(issue_id: str) -> str:
        """Consulta a fase e o histórico de status de um pedido."""
        return consultar_status(issue_id)

    @server.tool(name="buscar_conhecimento")
    def buscar_conhecimento_tool(consulta: str) -> str:
        """Busca copy, checklist WCAG, ADRs e padrões de critérios de aceite."""
        return buscar_conhecimento_texto(consulta)

    return server


def main() -> None:
    """Sobe o servidor no stdio, para um cliente MCP local."""
    build_server().run(transport="stdio")


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    main()
