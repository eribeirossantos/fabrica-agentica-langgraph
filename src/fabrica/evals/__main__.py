"""Permite rodar ``python -m fabrica.evals``."""

from fabrica.evals.runner import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli())
