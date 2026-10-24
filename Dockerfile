
FROM python:3.14.7-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md LICENSE ./

RUN uv --version
RUN uv sync --locked --no-dev --no-install-project

COPY . .

RUN uv sync --locked --no-dev --no-editable

CMD ["uv", "run", "fcc-server"]
