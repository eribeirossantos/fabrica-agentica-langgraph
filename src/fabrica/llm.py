"""Escolha do modelo: stub offline ou chat model do provedor configurado.

Provedores aceitos: ``stub`` (padrão), ``openai``, ``anthropic`` e ``google``.
A chave fica só no ambiente. Este módulo não registra nem imprime segredos.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from fabrica.stub import StubModel

_TRUE = {"1", "true", "sim", "yes", "on"}
_STUB_PROVIDERS = {"", "stub", "offline", "fake"}
_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "google": "gemini-2.0-flash",
}
_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}


@dataclass(frozen=True)
class Settings:
    """Configuração efetiva de uma execução."""

    provider: str
    model: str
    offline: bool


class LangChainModel:
    """Adapta um chat model do LangChain ao contrato ``invoke(schema, system, user)``."""

    def __init__(self, chat: object) -> None:
        self._chat = chat

    def invoke(self, schema: type[BaseModel], system: str, user: str) -> BaseModel:
        runnable = self._chat.with_structured_output(schema)  # type: ignore[attr-defined]
        result = runnable.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        if isinstance(result, schema):
            return result
        return schema.model_validate(result)


def load_settings(*, offline: bool | None = None) -> Settings:
    """Lê o ambiente. ``offline=True`` força o stub; ``False`` força o provedor."""
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    flag = os.getenv("FABRICA_OFFLINE", "").strip().lower()
    if offline is True or (offline is None and (flag in _TRUE or provider in _STUB_PROVIDERS)):
        return Settings(provider="stub", model="stub", offline=True)
    if provider not in _DEFAULT_MODELS:
        known = ", ".join(sorted(_DEFAULT_MODELS))
        raise RuntimeError(
            f"Provedor '{provider or 'vazio'}' não é suportado. Use stub, {known}."
        )
    model = os.getenv("LLM_MODEL", "").strip() or _DEFAULT_MODELS[provider]
    return Settings(provider=provider, model=model, offline=False)


def build_model(*, offline: bool | None = None) -> StubModel | LangChainModel:
    """Devolve o stub ou o chat model do provedor pedido."""
    settings = load_settings(offline=offline)
    if settings.offline:
        return StubModel()
    return LangChainModel(_build_chat(settings))


def _build_chat(settings: Settings) -> object:
    key_name = _KEY_ENV[settings.provider]
    api_key = os.getenv(key_name, "").strip()
    if not api_key:
        raise RuntimeError(
            f"Para usar o provedor {settings.provider}, defina {key_name}. "
            "Sem chave, rode com --offline."
        )
    if settings.provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "O pacote langchain-openai não está instalado. Instale com: pip install -e '.[llm]'"
            ) from exc
        return ChatOpenAI(model=settings.model, api_key=api_key, temperature=0)
    if settings.provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise RuntimeError(
                "O pacote langchain-anthropic não está instalado. "
                "Instale com: pip install -e '.[llm]'"
            ) from exc
        return ChatAnthropic(model=settings.model, api_key=api_key, temperature=0)
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise RuntimeError(
            "O pacote langchain-google-genai não está instalado. "
            "Instale com: pip install -e '.[llm]'"
        ) from exc
    return ChatGoogleGenerativeAI(model=settings.model, google_api_key=api_key, temperature=0)
