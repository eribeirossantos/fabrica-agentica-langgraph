"""Tools MCP da fábrica, em processo e pelo cliente stdio."""

from __future__ import annotations

import asyncio
import json

from fabrica.api.app import create_app
from fabrica.mcp_client import carregar_tools
from fabrica.mcp_server import build_server, buscar_conhecimento_texto, consultar_status, criar_issue


def test_tools_em_processo() -> None:
    app = create_app(database_url="sqlite://", offline=True)
    service = app.state.service
    created = json.loads(
        criar_issue("bug: botão de pagar não responde no celular", auto_aprovar=False, service=service)
    )
    assert created["fase"] == "aguardando_aprovacao"
    status = json.loads(consultar_status(created["id"], service=service))
    assert status["fase"] == "aguardando_aprovacao"
    published = json.loads(
        criar_issue("dúvida: o que acontece com a doação se o pagamento falhar?", service=service)
    )
    assert published["fase"] == "publicado"
    texto = buscar_conhecimento_texto("contraste WCAG 1.4.3")
    assert "checklist_wcag.md" in texto


def test_servidor_registra_os_nomes_publicos() -> None:
    server = build_server()
    tools = server._tool_manager.list_tools()
    nomes = sorted(tool.name for tool in tools)
    assert nomes == ["buscar_conhecimento", "consultar_status", "criar_issue"]


def _texto(resultado: object) -> str:
    if isinstance(resultado, str):
        return resultado
    if isinstance(resultado, list):
        partes: list[str] = []
        for bloco in resultado:
            if isinstance(bloco, dict):
                partes.append(str(bloco.get("text") or ""))
            else:
                partes.append(str(getattr(bloco, "text", bloco)))
        return "\n".join(partes)
    return str(resultado)


def test_cliente_mcp_carrega_e_chama_a_busca() -> None:
    async def _run() -> None:
        tools = await carregar_tools()
        nomes = {tool.name for tool in tools}
        assert {"criar_issue", "consultar_status", "buscar_conhecimento"} <= nomes
        busca = next(tool for tool in tools if tool.name == "buscar_conhecimento")
        texto = await busca.ainvoke({"consulta": "contraste texto WCAG 1.4.3"})
        assert "checklist_wcag.md" in _texto(texto)

    asyncio.run(_run())
