"""Garante que a suíte não chame provedor nenhum."""

from __future__ import annotations

import os

os.environ["FABRICA_OFFLINE"] = "1"
for _key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
    os.environ.pop(_key, None)
