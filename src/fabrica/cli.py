"""Linha de comando da fábrica."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fabrica.graph import readable_mermaid
from fabrica.render import format_status_line
from fabrica.runner import execute


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada. Devolve o código de saída do processo."""
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list[:1] == ["evals"]:
        from fabrica.evals.runner import run_cli

        return run_cli(args_list[1:])
    parser = argparse.ArgumentParser(
        prog="fabrica",
        description="Transforma um pedido em uma issue priorizada e especificada.",
    )
    parser.add_argument(
        "pedido",
        nargs="?",
        help="Pedido com prefixo bug:, melhoria: ou dúvida:.",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Aprova a issue sem perguntar ao product owner.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--offline",
        action="store_true",
        help="Usa o modelo determinístico, sem chave de API.",
    )
    mode.add_argument(
        "--online",
        action="store_true",
        help="Usa o provedor definido em LLM_PROVIDER. Exige a chave correspondente.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        help="Pasta para gravar o Markdown e o JSON da issue.",
    )
    parser.add_argument(
        "--diagrama",
        action="store_true",
        help="Imprime o diagrama Mermaid do grafo e encerra.",
    )
    args = parser.parse_args(args_list)
    if args.diagrama:
        print(readable_mermaid(), end="")
        return 0
    if not args.pedido or not args.pedido.strip():
        parser.error("informe o pedido, por exemplo: bug: botão de pagar não responde no celular")

    offline = True if args.offline else False if args.online else None
    try:
        state = execute(
            args.pedido,
            auto_approve=args.auto_approve,
            offline=offline,
            on_status=lambda event: print(format_status_line(event)),
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print()
    print(state.get("final_markdown", ""))
    if args.saida:
        markdown_path, json_path = write_outputs(args.saida, "issue", state)
        print(f"Markdown: {markdown_path}")
        print(f"JSON: {json_path}")
    if state.get("outcome") == "cancelado":
        return 2
    return 0


def write_outputs(directory: Path, stem: str, state: dict) -> tuple[Path, Path]:
    """Grava a issue em Markdown e JSON."""
    directory.mkdir(parents=True, exist_ok=True)
    markdown_path = directory / f"{stem}.md"
    json_path = directory / f"{stem}.json"
    markdown_path.write_text(state.get("final_markdown", ""), encoding="utf-8")
    document = state.get("final_document") or {}
    json_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return markdown_path, json_path


def cli() -> None:
    """Entrada do console script. Propaga o código de saída."""
    raise SystemExit(main())
