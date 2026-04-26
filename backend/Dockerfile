FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install UV for faster pip operations
RUN pip install uv

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN uv pip install --system -e ".[dev]"

# Copy application code
COPY . .

# Default command: FastAPI dev server with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
