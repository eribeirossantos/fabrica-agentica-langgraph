"""CLI offline, da aprovação interativa até os arquivos gravados."""

from __future__ import annotations

import json

from fabrica.cli import main
from fabrica.graph import readable_mermaid


def test_auto_approve_imprime_a_issue(capsys) -> None:
    code = main(
        ["--auto-approve", "--offline", "bug: botão de pagar não responde no celular"]
    )
    assert code == 0
    saida = capsys.readouterr().out
    assert "P1 — não perder transação ou doação" in saida
    assert "[fábrica] publicado" in saida
    assert "Botão de pagar não responde no celular" in saida
    assert "WCAG 2.1 AA" in saida


def test_rejeitar_e_aprovar_pelo_terminal(monkeypatch, capsys) -> None:
    respostas = iter(["n", "Recorte só o toque no celular.", "s"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(respostas))
    code = main(["--offline", "dúvida: o que acontece com a doação se o pagamento falhar?"])
    assert code == 0
    saida = capsys.readouterr().out
    assert "[product owner] rejeitado" in saida
    assert "Recorte só o toque no celular." in saida
    assert "[fábrica] publicado" in saida


def test_grava_markdown_e_json(tmp_path) -> None:
    code = main(
        [
            "--auto-approve",
            "--offline",
            "--saida",
            str(tmp_path),
            "melhoria: aumentar o contraste do texto de confirmação da doação",
        ]
    )
    assert code == 0
    markdown = (tmp_path / "issue.md").read_text(encoding="utf-8")
    document = json.loads((tmp_path / "issue.json").read_text(encoding="utf-8"))
    assert "Critérios de aceite" in markdown
    assert document["resultado"] == "publicado"
    assert document["issue"]["priority"] == "P3"
    assert document["issue"]["type_label"] == "melhoria"


def test_diagrama(capsys) -> None:
    assert main(["--diagrama"]) == 0
    assert capsys.readouterr().out == readable_mermaid()
