# ─────────────────────────────────────────────────────────────────────────────
# Multi-stage Dockerfile for FastAPI + Celery workers
# ─────────────────────────────────────────────────────────────────────────────

# -- Stage 1: Builder --
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Copy project files
COPY pyproject.toml .

# Create a virtual environment and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install production dependencies only (no dev)
RUN uv pip install --no-cache-dir .

# -- Stage 2: Runtime --
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies (PostgreSQL client for wait-for-it / healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app

# Copy application code
COPY . /app

# Create a non-root user and change ownership
RUN useradd -m devpulse && chown -R devpulse:devpulse /app
USER devpulse

# Default command (will be overridden by docker-compose for celery workers)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
