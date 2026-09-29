"""Recuperação offline da base de conhecimento."""

from __future__ import annotations

from fabrica.rag.chunking import load_chunks
from fabrica.rag.embeddings import HashingEmbedder
from fabrica.rag.store import MemoryVectorStore
from fabrica.runner import execute
from fabrica.tools import buscar_conhecimento


def test_embeddings_iguais_para_o_mesmo_texto() -> None:
    embedder = HashingEmbedder()
    assert embedder.embed("contraste WCAG") == embedder.embed("contraste WCAG")


def test_contraste_recupera_o_checklist_wcag() -> None:
    hits = _store().search("contraste texto WCAG 1.4.3", k=3)
    assert hits
    assert hits[0].citation.startswith("checklist_wcag.md")


def test_criterios_recuperam_o_padrao_dado_quando_entao() -> None:
    hits = _store().search("Dado quando então critério de aceite verificável", k=3)
    assert hits[0].citation.startswith("padroes_de_criterios.md")


def test_copy_recupera_o_guia() -> None:
    hits = _store().search("tom de voz copy botão português", k=3)
    assert hits[0].citation.startswith("guia_de_copy.md")


def test_adr_recupera_decisao_de_arquitetura() -> None:
    hits = _store().search("ADR decisão cobrança idempotente checkout legado", k=3)
    assert any(hit.citation.startswith("adrs_do_aplicativo.md") for hit in hits)


def test_tool_devolve_a_citacao() -> None:
    texto = buscar_conhecimento.invoke({"consulta": "contraste WCAG 1.4.3"})
    assert "checklist_wcag.md" in texto
    assert "Fonte:" in texto


def test_design_e_revisao_citam_fontes() -> None:
    state = execute(
        "melhoria: aumentar o contraste do texto de confirmação da doação",
        auto_approve=True,
        offline=True,
    )
    design = state["design_spec"]["fontes"]
    review = state["review"]["fontes"]
    assert any(item.startswith("guia_de_copy.md") for item in design)
    assert any(item.startswith("checklist_wcag.md") for item in design)
    assert any(item.startswith("padroes_de_criterios.md") for item in review)
    assert "### Fontes" in state["final_markdown"]


def test_chunks_tem_citacao_estavel() -> None:
    citations = [chunk.citation for chunk in load_chunks()]
    assert "checklist_wcag.md#contraste" in citations
    assert "padroes_de_criterios.md#formato-dado-quando-entao" in citations


def _store() -> MemoryVectorStore:
    store = MemoryVectorStore(HashingEmbedder())
    store.add(load_chunks())
    return store
