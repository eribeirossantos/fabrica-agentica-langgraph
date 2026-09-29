FROM python:3.12-slim AS build

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY knowledge ./knowledge
RUN pip install --no-cache-dir ".[infra]"

FROM python:3.12-slim

WORKDIR /app
COPY --from=build /usr/local /usr/local
COPY knowledge ./knowledge
ENV FABRICA_OFFLINE=1 \
    FABRICA_KNOWLEDGE_DIR=/app/knowledge \
    FABRICA_EMBEDDINGS=fake \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "fabrica.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
