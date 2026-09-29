"""Retriever do LangChain sobre o índice da fábrica."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from fabrica.rag.store import Hit, build_store

_store: Any = None


class KnowledgeRetriever(BaseRetriever):
    """Busca os trechos mais próximos e devolve documentos com a citação."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    store: Any
    k: int = 3

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        del run_manager
        hits: list[Hit] = self.store.search(query, k=self.k)
        return [
            Document(page_content=hit.text, metadata={"citation": hit.citation, "score": hit.score}) for hit in hits
        ]


def get_store() -> Any:
    """Índice único do processo. Os testes usam o store em memória."""
    global _store
    if _store is None:
        _store = build_store()
    return _store


def get_retriever(k: int = 3) -> KnowledgeRetriever:
    return KnowledgeRetriever(store=get_store(), k=k)


def search(query: str, k: int = 3) -> list[Hit]:
    return get_store().search(query, k=k)


def reset_store() -> None:
    """Limpa o índice cacheado. Útil quando o teste troca a pasta."""
    global _store
    _store = None
