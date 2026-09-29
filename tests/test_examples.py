"""Os exemplos versionados são a saída real do modo offline."""

from __future__ import annotations

import json
from pathlib import Path

from fabrica.graph import readable_mermaid
from fabrica.runner import execute

ROOT = Path(__file__).resolve().parents[1]

SAMPLES = [
    ("01-bug-pagar", "bug: botão de pagar não responde no celular"),
    ("02-melhoria-contraste", "melhoria: aumentar o contraste do texto de confirmação da doação"),
    ("03-duvida-pagamento", "dúvida: o que acontece com a doação se o pagamento falhar?"),
]


def test_pedidos_e_saidas_batem_com_o_grafo() -> None:
    for stem, text in SAMPLES:
        pedido = (ROOT / "examples" / "pedidos" / f"{stem}.txt").read_text(encoding="utf-8")
        assert pedido.strip() == text
        state = execute(text, auto_approve=True, offline=True)
        markdown = (ROOT / "examples" / "saidas" / f"{stem}.md").read_text(encoding="utf-8")
        raw_json = (ROOT / "examples" / "saidas" / f"{stem}.json").read_text(encoding="utf-8")
        assert markdown == state["final_markdown"]
        assert raw_json == json.dumps(state["final_document"], ensure_ascii=False, indent=2) + "\n"
        assert state["outcome"] == "publicado"


def test_readme_e_arquivo_de_diagrama_saem_do_grafo() -> None:
    diagram = readable_mermaid()
    assert (ROOT / "docs" / "grafo.mmd").read_text(encoding="utf-8") == diagram
    assert diagram.strip() in (ROOT / "README.md").read_text(encoding="utf-8")
