"""Leitura e corte da pasta ``knowledge/``."""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

_HEADING = re.compile(r"^##\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    """Trecho recuperável, com citação estável."""

    citation: str
    text: str


def knowledge_dir() -> Path:
    """Pasta da base. Ambiente, repositório ao lado de ``src`` ou diretório atual."""
    configured = os.getenv("FABRICA_KNOWLEDGE_DIR", "").strip()
    if configured:
        return Path(configured)
    bundled = Path(__file__).resolve().parents[3] / "knowledge"
    if bundled.is_dir():
        return bundled
    return Path.cwd() / "knowledge"


def load_chunks(directory: Path | None = None) -> list[Chunk]:
    """Corta cada Markdown pelos títulos ``##``. Sem título, o arquivo inteiro vale."""
    root = directory or knowledge_dir()
    if not root.is_dir():
        return []
    chunks: list[Chunk] = []
    for path in sorted(root.glob("*.md")):
        chunks.extend(_chunks_of(path))
    return chunks


def _chunks_of(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    matches = list(_HEADING.finditer(raw))
    if not matches:
        return [Chunk(citation=f"{path.name}#documento", text=raw)]
    chunks: list[Chunk] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        title = match.group(1).strip()
        body = raw[start:end].strip()
        chunks.append(Chunk(citation=f"{path.name}#{_slug(title)}", text=body))
    return chunks


def _slug(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "secao"
