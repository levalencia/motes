# Backend Dockerfile for Motes
FROM python:3.12-slim AS base

RUN pip install uv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --no-dev

COPY backend/app ./app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
