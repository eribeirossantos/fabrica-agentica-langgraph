"""Cliente MCP via langchain-mcp-adapters.

O agente recebe tools LangChain carregadas de um servidor MCP externo.
O padrão aponta para esta própria fábrica em stdio.
"""

from __future__ import annotations

import sys
from typing import Any

from langchain_core.tools import BaseTool


def conexao_padrao() -> dict[str, Any]:
    """Servidor local ``python -m fabrica.mcp_server`` no transporte stdio."""
    return {
        "fabrica": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "fabrica.mcp_server"],
        }
    }


async def carregar_tools(conexoes: dict[str, Any] | None = None) -> list[BaseTool]:
    """Abre o cliente e devolve as tools no formato do LangChain."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(conexoes or conexao_padrao())
    return await client.get_tools()
