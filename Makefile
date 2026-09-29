.PHONY: install test lint run-api run-mcp evals up mypy

install:
	pip install -e ".[dev]"

test:
	FABRICA_OFFLINE=1 pytest

lint:
	ruff check .

run-api:
	FABRICA_OFFLINE=1 uvicorn fabrica.api.app:app --host 127.0.0.1 --port 8000

run-mcp:
	python -m fabrica.mcp_server

evals:
	FABRICA_OFFLINE=1 python -m fabrica evals

up:
	docker compose up --build

mypy:
	mypy src
