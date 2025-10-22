FROM python:3.13-slim

WORKDIR /app

# Install system dependencies, PostgreSQL client libraries, Stockfish, and uv
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    bash -lc 'set -euo pipefail \
    && apt-get update \
    && apt-get install -y curl wget libpq-dev gcc stockfish \
    && ln -sf /usr/games/stockfish /usr/local/bin/stockfish \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*'
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Copy source code before syncing (workspace resolution)
COPY libs/ ./libs/
COPY backend/ ./backend/

# Install dependencies (prod)
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Install dev dependencies and sync again (separate layer for better caching)
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen

CMD ["uv", "run", "--package", "backend", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9998", "--reload"]