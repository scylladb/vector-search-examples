# Use Python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml ./
COPY config.py ./
COPY scylladb.py ./
COPY migrate.py ./
COPY schema.cql ./
COPY scylla_semantic_cache.py ./

# Install Python dependencies
RUN uv sync --no-dev

# Keep the container running
CMD ["tail", "-f", "/dev/null"]