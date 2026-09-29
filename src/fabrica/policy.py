"""Regras determinísticas de classificação, prioridade e área.

A escala de prioridade segue a ordem usada na fábrica:

1. não perder transação ou doação
2. não vazar dado
3. acessibilidade
4. clareza para o usuário
5. cosmético

O prefixo do pedido (``bug:``, ``melhoria:``, ``dúvida:``, e também ``dívida:``)
define o tipo, com uma exceção: relato de vazamento em bug ou melhoria vira
``risco``. Pergunta hipotética (``o que acontece se``) não conta como incidente
de perda de transação.
"""

from __future__ import annotations

import re
import unicodedata

TYPE_DISPLAY = {
    "bug": "bug",
    "risco": "risco",
    "melhoria": "melhoria",
    "divida": "dívida",
    "duvida": "dúvida",
}

PRIORITY_REASONS = {
    "P1": "não perder transação ou doação",
    "P2": "não vazar dado",
    "P3": "acessibilidade",
    "P4": "clareza para o usuário",
    "P5": "cosmético",
}

_PREFIX = re.compile(
    r"^\s*(bug|melhoria|d[uú]vida|d[ií]vida)\s*:\s*",
    re.IGNORECASE,
)

_TRANSACTION = (
    re.compile(r"nao (responde|funciona|conclui|registra|grava|processa|dispara)"),
    re.compile(r"nao (e |foi )?(registrad|gravad|processad|concluid)"),
    re.compile(
        r"(pagamento|doacao|transacao|pix|checkout|cobranca).{0,50}"
        r"(nao (responde|funciona|conclui|registra)|falhou|falha ao|se perde|perdid)"
    ),
    re.compile(
        r"(falhou|falha ao|se perde|perdid|nao conclui).{0,50}"
        r"(pagamento|doacao|transacao|checkout)"
    ),
    re.compile(r"botao de pagar"),
    re.compile(r"cobranca (duplicada|indevida|em dobro)"),
    re.compile(r"perder (a )?(doacao|transacao|pagamento)"),
    re.compile(r"doacao (duplicada|em dobro|nao registrada|perdida)"),
    re.compile(r"estamos perdendo"),
)

_LEAK = (
    re.compile(r"\bvazamento\b|\bvazar\b|\bvazou\b|\bvazando\b"),
    re.compile(r"\bdados? pessoais?\b"),
    re.compile(r"\bcpf\b"),
    re.compile(r"\bsenha\b"),
    re.compile(r"\btoken\b"),
    re.compile(r"\bprivacidade\b"),
    re.compile(r"\blgpd\b"),
    re.compile(r"aparece na url"),
    re.compile(r"aparece no log"),
    re.compile(r"log publico"),
)

_A11Y = (
    re.compile(r"acessibilidade"),
    re.compile(r"leitor de tela"),
    re.compile(r"contraste"),
    re.compile(r"\bteclado\b"),
    re.compile(r"\ba11y\b"),
    re.compile(r"\bwcag\b"),
    re.compile(r"\baria\b"),
    re.compile(r"foco visivel"),
)

_CLARITY = (
    re.compile(r"\bconfus"),
    re.compile(r"\bclareza\b"),
    re.compile(r"\bmensagem\b"),
    re.compile(r"\btexto\b"),
    re.compile(r"\brotulo\b"),
    re.compile(r"\bcopy\b"),
    re.compile(r"o que acontece"),
    re.compile(r"\bexplic"),
    re.compile(r"\binstruc"),
    re.compile(r"erro 500"),
    re.compile(r"nao fica claro"),
)

_COSMETIC = (
    re.compile(r"\bcor\b"),
    re.compile(r"\bfonte\b"),
    re.compile(r"\balinh"),
    re.compile(r"\bespacamento\b"),
    re.compile(r"\bicone\b"),
    re.compile(r"\bpixel\b"),
    re.compile(r"\bcosmetico\b"),
)

_FAILURE_HINT = re.compile(
    r"nao (responde|funciona|conclui|registra|grava|processa)|falhou|falha ao|se perde|\berro\b"
)

_DEBT = (
    re.compile(r"divida tecnica"),
    re.compile(r"debito tecnico"),
    re.compile(r"\blegado\b"),
    re.compile(r"\brefator"),
)

_INCIDENT = re.compile(
    r"estamos perdendo|ja perdemos|nao registra|nao responde|vazou|aparece na url|aparece no log"
)

_QUESTION = re.compile(r"(o que|como|por que|qual|quais|quando|onde|quem)\b")


def normalize(text: str) -> str:
    """Minúsculas, sem acento e com espaços simples, para comparar regras."""
    decomposed = unicodedata.normalize("NFD", text.strip().lower())
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", without_marks)


def split_prefix(text: str) -> tuple[str | None, str]:
    """Separa o prefixo do pedido e devolve o corpo original, com acentos."""
    match = _PREFIX.match(text or "")
    if not match:
        return None, (text or "").strip()
    return normalize(match.group(1)), text[match.end() :].strip()


def _any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _looks_like_question(body: str) -> bool:
    normalized = normalize(body)
    return normalized.endswith("?") or bool(_QUESTION.match(normalized))


def _hypothetical(normalized_body: str) -> bool:
    return bool(re.search(r"\b(se|caso|o que acontece)\b", normalized_body))


def classify_request(text: str) -> str:
    """Classifica o pedido em bug, risco, melhoria, dívida ou dúvida."""
    prefix, body = split_prefix(text)
    normalized = normalize(body)
    if prefix == "duvida":
        return "duvida"
    if _any(normalized, _LEAK) and prefix in {None, "bug", "melhoria"}:
        return "risco"
    if prefix in {"bug", "melhoria", "divida"}:
        return prefix
    if _any(normalized, _LEAK):
        return "risco"
    if _any(normalized, _DEBT):
        return "divida"
    if _looks_like_question(body):
        return "duvida"
    if _any(normalized, _TRANSACTION) or re.search(r"\berro\b|\bfalha\b|\bbug\b", normalized):
        return "bug"
    return "melhoria"


def prioritize_request(text: str, issue_type: str | None = None) -> tuple[str, str]:
    """Devolve o código de prioridade e o motivo na escala da fábrica."""
    if issue_type is None:
        issue_type = classify_request(text)
    _prefix, body = split_prefix(text)
    normalized = normalize(body)
    cosmetic_only = _any(normalized, _COSMETIC) and not _FAILURE_HINT.search(normalized)
    hypothetical_question = (
        issue_type == "duvida" and _hypothetical(normalized) and not _INCIDENT.search(normalized)
    )
    if _any(normalized, _TRANSACTION) and not cosmetic_only and not hypothetical_question:
        return "P1", PRIORITY_REASONS["P1"]
    if _any(normalized, _LEAK):
        return "P2", PRIORITY_REASONS["P2"]
    if _any(normalized, _A11Y):
        return "P3", PRIORITY_REASONS["P3"]
    if issue_type == "duvida" or _any(normalized, _CLARITY):
        return "P4", PRIORITY_REASONS["P4"]
    return "P5", PRIORITY_REASONS["P5"]


def infer_area(text: str) -> str:
    """Escolhe a área da label na mesma ordem da escala de prioridade."""
    normalized = normalize(text)
    cosmetic_only = _any(normalized, _COSMETIC) and not _FAILURE_HINT.search(normalized)
    if _any(normalized, _TRANSACTION) and not cosmetic_only:
        return "checkout"
    if _any(normalized, _LEAK) or re.search(r"\blog\b", normalized):
        return "privacidade"
    if _any(normalized, _A11Y):
        return "acessibilidade"
    if "confirm" in normalized:
        return "confirmacao"
    if re.search(r"pagar|pagamento|pix|checkout|cartao|cobranca", normalized):
        return "checkout"
    if _any(normalized, _DEBT):
        return "plataforma"
    return "produto"
