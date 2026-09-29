"""Embeddings determinísticos para o modo offline.

O truque de hashing agrupa tokens iguais na mesma dimensão. Dois textos que
compartilham palavras raras ficam mais próximos no cosseno. Não é um modelo
semântico: é estável, local e não pede chave.
"""

from __future__ import annotations

import hashlib
import math
import os
import re

_TOKEN = re.compile(r"\w+", re.UNICODE)
_STOP = {
    "a",
    "o",
    "e",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "que",
    "para",
    "com",
    "uma",
    "um",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "se",
    "por",
    "ao",
    "os",
    "as",
    "ou",
    "não",
    "nao",
}


class HashingEmbedder:
    """Vetor esparso normalizado, sempre com a mesma dimensão."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in _TOKEN.findall(text.lower()):
            if token in _STOP or len(token) < 2:
                continue
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


def build_embedder() -> HashingEmbedder:
    """O padrão é o embedder falso. Outro valor pede implementação explícita."""
    choice = os.getenv("FABRICA_EMBEDDINGS", "fake").strip().lower()
    if choice in {"", "fake", "hash", "hashing"}:
        return HashingEmbedder()
    raise RuntimeError(
        f"Embeddings '{choice}' não estão disponíveis neste processo. "
        "Use FABRICA_EMBEDDINGS=fake para o modo offline."
    )
