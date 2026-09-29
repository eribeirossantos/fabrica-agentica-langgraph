"""Escolha do modelo: stub offline ou chat model do provedor configurado.

Provedores aceitos: ``stub`` (padrão), ``openai``, ``azure``, ``anthropic`` e
``google``. Cada agente pode apontar para um provedor diferente. A chave fica
só no ambiente. Este módulo não registra nem imprime segredos.
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
    "azure": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "google": "gemini-2.0-flash",
}
_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "azure": "AZURE_OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}
_ROLE_PREFIX = {
    "product": "PRODUCT",
    "design": "DESIGN",
    "dev": "DEV",
    "review": "REVIEW",
}
ROLES = ("product", "design", "dev", "review")


@dataclass(frozen=True)
class Settings:
    """Configuração efetiva de uma execução, possivelmente de um agente só."""

    provider: str
    model: str
    offline: bool
    role: str = "default"
    azure_endpoint: str = ""
    azure_deployment: str = ""
    azure_api_version: str = ""


class LangChainModel:
    """Adapta um chat model do LangChain ao contrato ``invoke(schema, system, user)``."""

    def __init__(self, chat: object) -> None:
        self._chat = chat

    def invoke(self, schema: type[BaseModel], system: str, user: str) -> BaseModel:
        runnable = self._chat.with_structured_output(schema)  # type: ignore[attr-defined]
        result = runnable.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        if isinstance(result, schema):
            return result
        return schema.model_validate(result)


def load_settings(*, offline: bool | None = None, role: str | None = None) -> Settings:
    """Lê o ambiente. ``offline=True`` força o stub em todos os agentes."""
    load_dotenv()
    provider = _role_value(role, "LLM_PROVIDER").lower()
    flag = os.getenv("FABRICA_OFFLINE", "").strip().lower()
    if offline is True or (offline is None and (flag in _TRUE or provider in _STUB_PROVIDERS)):
        return Settings(provider="stub", model="stub", offline=True, role=role or "default")
    if provider not in _DEFAULT_MODELS:
        known = ", ".join(sorted(_DEFAULT_MODELS))
        raise RuntimeError(f"Provedor '{provider or 'vazio'}' não é suportado. Use stub, {known}.")
    model = _role_value(role, "LLM_MODEL") or _DEFAULT_MODELS[provider]
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip() or model
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "").strip() or "2024-10-21"
    return Settings(
        provider=provider,
        model=model,
        offline=False,
        role=role or "default",
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        azure_api_version=api_version,
    )


def build_model(*, offline: bool | None = None, role: str | None = None) -> StubModel | LangChainModel:
    """Devolve o stub ou o chat model do provedor pedido para o agente."""
    settings = load_settings(offline=offline, role=role)
    if settings.offline:
        return StubModel()
    return LangChainModel(_build_chat(settings))


def build_models(*, offline: bool | None = None) -> dict[str, StubModel | LangChainModel]:
    """Um modelo por agente. No modo offline, todos são o stub determinístico."""
    return {role: build_model(offline=offline, role=role) for role in ROLES}


def _role_value(role: str | None, suffix: str) -> str:
    if role:
        prefix = _ROLE_PREFIX.get(role)
        if prefix:
            specific = os.getenv(f"{prefix}_{suffix}", "").strip()
            if specific:
                return specific
    return os.getenv(suffix, "").strip()


def _build_chat(settings: Settings) -> object:
    key_name = _KEY_ENV[settings.provider]
    api_key = os.getenv(key_name, "").strip()
    if not api_key:
        raise RuntimeError(
            f"Para usar o provedor {settings.provider}, defina {key_name}. Sem chave, rode com --offline."
        )
    if settings.provider == "openai":
        chat_openai = _import_openai()
        return chat_openai(model=settings.model, api_key=api_key, temperature=0)
    if settings.provider == "azure":
        if not settings.azure_endpoint:
            raise RuntimeError(
                "Para usar o Azure OpenAI, defina AZURE_OPENAI_ENDPOINT. Sem endpoint, rode com --offline."
            )
        azure_chat = _import_azure()
        return azure_chat(
            azure_endpoint=settings.azure_endpoint,
            azure_deployment=settings.azure_deployment or settings.model,
            api_version=settings.azure_api_version or "2024-10-21",
            api_key=api_key,
            temperature=0,
        )
    if settings.provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise RuntimeError(
                "O pacote langchain-anthropic não está instalado. Instale com: pip install -e '.[llm]'"
            ) from exc
        return ChatAnthropic(model=settings.model, api_key=api_key, temperature=0)
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise RuntimeError(
            "O pacote langchain-google-genai não está instalado. Instale com: pip install -e '.[llm]'"
        ) from exc
    return ChatGoogleGenerativeAI(model=settings.model, google_api_key=api_key, temperature=0)


def _import_openai() -> type:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "O pacote langchain-openai não está instalado. Instale com: pip install -e '.[llm]'"
        ) from exc
    return ChatOpenAI


def _import_azure() -> type:
    try:
        from langchain_openai import AzureChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "O pacote langchain-openai não está instalado. Instale com: pip install -e '.[llm]'"
        ) from exc
    return AzureChatOpenAI
