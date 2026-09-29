"""Seleção de modelo: o padrão dos testes é o stub, sem rede."""

from __future__ import annotations

import importlib.util

import pytest

from fabrica.llm import build_model, load_settings
from fabrica.stub import StubModel


def test_flag_offline_ignora_provedor(monkeypatch) -> None:
    monkeypatch.setenv("FABRICA_OFFLINE", "1")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    assert isinstance(build_model(), StubModel)


def test_sem_provedor_usa_stub(monkeypatch) -> None:
    monkeypatch.delenv("FABRICA_OFFLINE", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert isinstance(build_model(), StubModel)


def test_online_sem_chave_explica_em_portugues(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_model(offline=False)


def test_offline_ignora_provedor_do_agente(monkeypatch) -> None:
    monkeypatch.setenv("FABRICA_OFFLINE", "1")
    monkeypatch.setenv("PRODUCT_LLM_PROVIDER", "azure")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "chave")
    assert isinstance(build_model(role="product"), StubModel)


def test_provedor_diferente_por_agente(monkeypatch) -> None:
    monkeypatch.delenv("FABRICA_OFFLINE", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("DESIGN_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("DEV_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("DEV_LLM_MODEL", "claude-3-5-haiku-latest")
    produto = load_settings(role="product", offline=False)
    design = load_settings(role="design", offline=False)
    dev = load_settings(role="dev", offline=False)
    assert produto.provider == "openai"
    assert design.provider == "anthropic"
    assert dev.provider == "anthropic"
    assert dev.model == "claude-3-5-haiku-latest"


def test_azure_sem_chave_explica_em_portugues(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "azure")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="AZURE_OPENAI_API_KEY"):
        build_model(offline=False)


def test_azure_sem_endpoint_explica_em_portugues(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "azure")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "chave")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    with pytest.raises(RuntimeError, match="AZURE_OPENAI_ENDPOINT"):
        build_model(offline=False)


def test_online_sem_pacote_explica_o_extra(monkeypatch) -> None:
    if importlib.util.find_spec("langchain_openai") is not None:
        pytest.skip("langchain-openai está instalado neste ambiente")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    with pytest.raises(RuntimeError, match="langchain-openai"):
        build_model(offline=False)
