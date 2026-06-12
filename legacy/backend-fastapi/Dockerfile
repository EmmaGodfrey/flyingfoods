# Base image and install flow for local/CI API container builds.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 8000
