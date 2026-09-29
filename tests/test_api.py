"""API REST offline, com SQLite em memória e o stub."""

from __future__ import annotations

from fastapi.testclient import TestClient

from fabrica.api.app import create_app

PEDIDO = "bug: botão de pagar não responde no celular"


def test_health_e_fluxo_de_aprovacao() -> None:
    app = create_app(database_url="sqlite://", offline=True)
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["offline"] is True

        created = client.post("/pedidos", json={"pedido": PEDIDO})
        assert created.status_code == 201
        body = created.json()
        issue_id = body["id"]
        assert body["fase"] == "aguardando_aprovacao"
        assert body["prioridade"] == "P1"
        assert body["registro_de_status"][0]["agent"] == "produto"

        waiting = client.get(f"/pedidos/{issue_id}/issue")
        assert waiting.status_code == 409
        assert waiting.json()["detalhe"]

        rejected = client.post(
            f"/pedidos/{issue_id}/decisao",
            json={"decision": "reject", "feedback": "Recorte só o toque no celular."},
        )
        assert rejected.status_code == 200
        assert rejected.json()["fase"] == "aguardando_aprovacao"
        assert any(item["status"] == "rejeitado" for item in rejected.json()["registro_de_status"])

        approved = client.post(
            f"/pedidos/{issue_id}/decisao",
            json={"decision": "approve"},
        )
        assert approved.status_code == 200
        assert approved.json()["fase"] == "publicado"

        issue = client.get(f"/pedidos/{issue_id}/issue")
        assert issue.status_code == 200
        documento = issue.json()["documento"]
        assert documento["resultado"] == "publicado"
        assert "WCAG" in issue.json()["markdown"]

        markdown = client.get(f"/pedidos/{issue_id}/issue.md")
        assert markdown.status_code == 200
        assert "text/markdown" in markdown.headers["content-type"]
        assert "Botão de pagar não responde no celular" in markdown.text

        again = client.post(f"/pedidos/{issue_id}/decisao", json={"decision": "approve"})
        assert again.status_code == 409

        missing = client.get("/pedidos/nao-existe")
        assert missing.status_code == 404
        assert missing.json()["detalhe"] == "Pedido não encontrado."


def test_openapi_documenta_os_caminhos() -> None:
    app = create_app(database_url="sqlite://", offline=True)
    with TestClient(app) as client:
        spec = client.get("/openapi.json")
        assert spec.status_code == 200
        paths = spec.json()["paths"]
        assert "/health" in paths
        assert "/pedidos" in paths
        assert "/pedidos/{issue_id}/decisao" in paths
        assert "/pedidos/{issue_id}/issue.md" in paths
        assert spec.json()["info"]["title"] == "Fábrica agêntica"


def test_pedido_vazio_nao_entra() -> None:
    app = create_app(database_url="sqlite://", offline=True)
    with TestClient(app) as client:
        response = client.post("/pedidos", json={"pedido": ""})
        assert response.status_code == 422
