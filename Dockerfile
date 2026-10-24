
FROM python:3.14.7-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Provide a version when Git metadata is unavailable in Docker
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0

COPY . .

RUN uv --version
RUN uv sync --locked --no-dev

CMD ["uv", "run", "fcc-server"]
