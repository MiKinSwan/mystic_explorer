# Production Dockerfile - runs the FastAPI app on any Docker-capable host
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager for blazing fast builds
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency specifications and lockfiles
COPY pyproject.toml .

# Install production dependencies
RUN uv pip compile pyproject.toml -o requirements.txt && \
    uv pip install --system -r requirements.txt

# Copy application source code
COPY . .

# Expose production port
EXPOSE 8080

# Launch production FastAPI server
CMD ["uvicorn", "fast_api_app:fastapi_app", "--host", "0.0.0.0", "--port", "8080"]
