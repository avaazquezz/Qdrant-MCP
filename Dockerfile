FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra embeddings --no-install-project

COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra embeddings --no-editable

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app/.venv ./.venv

ENV PATH="/app/.venv/bin:$PATH"
# Text-embedding models are downloaded here on first use; mount a volume to keep them.
ENV FASTEMBED_CACHE_PATH=/models

EXPOSE 8000

ENTRYPOINT ["mcp-qdrant"]
