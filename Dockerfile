FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install runtime dependencies only
RUN uv sync --no-dev --frozen

# Copy application code
COPY config.py models.py api.py mcp_server.py main.py ./
COPY core/ core/
COPY commands/ commands/
COPY utils/ utils/

# Data directory for SQLite database
RUN mkdir -p /data
ENV FORGEOPS_DB_PATH=/data/forgeops.db

EXPOSE 8002

CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8002"]
