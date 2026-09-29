"""Índice vetorial em memória e, quando configurado, em pgvector."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from fabrica.rag.chunking import Chunk, knowledge_dir, load_chunks
from fabrica.rag.embeddings import HashingEmbedder, build_embedder


@dataclass(frozen=True)
class Hit:
    """Trecho ordenado pela proximidade com a consulta."""

    citation: str
    text: str
    score: float


class MemoryVectorStore:
    """Busca por cosseno num processo só. Serve aos testes e ao modo local."""

    def __init__(self, embedder: HashingEmbedder) -> None:
        self.embedder = embedder
        self._rows: list[tuple[Chunk, list[float]]] = []

    def add(self, chunks: list[Chunk]) -> None:
        self._rows = [(chunk, self.embedder.embed(chunk.text)) for chunk in chunks]

    def search(self, query: str, k: int = 3) -> list[Hit]:
        if not self._rows or k <= 0:
            return []
        query_vector = self.embedder.embed(query)
        scored = [
            Hit(citation=chunk.citation, text=chunk.text, score=_cosine(query_vector, vector))
            for chunk, vector in self._rows
        ]
        scored.sort(key=lambda hit: (-hit.score, hit.citation))
        return [hit for hit in scored if hit.score > 0][:k]


class PgVectorStore:
    """Mesmo contrato da memória, com a extensão vector no PostgreSQL."""

    def __init__(self, dsn: str, embedder: HashingEmbedder) -> None:
        self.embedder = embedder
        self.dsn = _psycopg_dsn(dsn)
        self._ensure_schema()

    def add(self, chunks: list[Chunk]) -> None:
        import psycopg

        with psycopg.connect(self.dsn) as conn:
            _register(conn)
            for chunk in chunks:
                vector = _literal(self.embedder.embed(chunk.text))
                conn.execute(
                    """
                    INSERT INTO knowledge_chunks (citation, content, embedding)
                    VALUES (%s, %s, %s::vector)
                    ON CONFLICT (citation) DO UPDATE
                    SET content = EXCLUDED.content, embedding = EXCLUDED.embedding
                    """,
                    (chunk.citation, chunk.text, vector),
                )
            conn.commit()

    def search(self, query: str, k: int = 3) -> list[Hit]:
        import psycopg

        vector = _literal(self.embedder.embed(query))
        with psycopg.connect(self.dsn) as conn:
            _register(conn)
            rows = conn.execute(
                """
                SELECT citation, content, 1 - (embedding <=> %s::vector) AS score
                FROM knowledge_chunks
                ORDER BY embedding <=> %s::vector, citation
                LIMIT %s
                """,
                (vector, vector, k),
            ).fetchall()
        return [Hit(citation=row[0], text=row[1], score=float(row[2])) for row in rows if float(row[2]) > 0]

    def _ensure_schema(self) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "pgvector pede o pacote psycopg. Instale com: pip install -e '.[infra]'"
            ) from exc
        dim = self.embedder.dim
        with psycopg.connect(self.dsn) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    citation TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({dim}) NOT NULL
                )
                """
            )
            conn.commit()


def build_store(directory: Path | None = None) -> MemoryVectorStore | PgVectorStore:
    """Monta o índice pedido pelo ambiente e ingere ``knowledge/``."""
    embedder = build_embedder()
    chunks = load_chunks(directory or knowledge_dir())
    kind = os.getenv("FABRICA_VECTOR_STORE", "memory").strip().lower()
    if kind in {"", "memory", "local"}:
        store = MemoryVectorStore(embedder)
        store.add(chunks)
        return store
    if kind == "pgvector":
        dsn = os.getenv("FABRICA_VECTOR_DATABASE_URL", "").strip() or os.getenv("FABRICA_DATABASE_URL", "").strip()
        if not dsn:
            raise RuntimeError("FABRICA_VECTOR_STORE=pgvector exige FABRICA_DATABASE_URL.")
        store = PgVectorStore(dsn, embedder)
        store.add(chunks)
        return store
    raise RuntimeError("FABRICA_VECTOR_STORE aceita memory ou pgvector.")


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def _psycopg_dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1).replace("postgres+psycopg://", "postgresql://", 1)


def _register(conn: object) -> None:
    try:
        from pgvector.psycopg import register_vector
    except ImportError:
        return
    register_vector(conn)
