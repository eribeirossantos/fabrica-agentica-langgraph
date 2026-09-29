"""Garante que a suíte não chame provedor nenhum e não escreva fora do processo."""

from __future__ import annotations

import os

os.environ["FABRICA_OFFLINE"] = "1"
os.environ["FABRICA_DATABASE_URL"] = "sqlite://"
os.environ["FABRICA_CHECKPOINTER"] = "memory"
os.environ["FABRICA_VECTOR_STORE"] = "memory"
os.environ["FABRICA_EMBEDDINGS"] = "fake"
os.environ["OTEL_TRACES_EXPORTER"] = "none"
os.environ.pop("FABRICA_REDIS_URL", None)
os.environ.pop("LANGSMITH_TRACING", None)
os.environ.pop("LANGCHAIN_TRACING_V2", None)
for _key in (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
):
    os.environ.pop(_key, None)
