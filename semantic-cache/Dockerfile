# Use Python 3.10 base image
FROM python:3.10.18-trixie

# Set working directory
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY scylla_semantic_cache.py ./
COPY config.py ./
COPY requirements.txt ./
COPY scylladb.py ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Keep the container running
CMD ["tail", "-f", "/dev/null"]