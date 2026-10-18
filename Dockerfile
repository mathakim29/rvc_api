# not working, incomplete do not use
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

ARG version=3.11
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml /app/pyproject.toml
COPY /src /app/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --only-binary :all:

EXPOSE 7000
USER root

RUN uv run rvc_api:main