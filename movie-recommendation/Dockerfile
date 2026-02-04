FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for scylla-driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libev-dev \
    && rm -rf /var/lib/apt/lists/*

# copy requirements file
COPY requirements.txt .

# Install PyTorch CPU-only first (avoids NVIDIA/CUDA packages)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu


# Install remaining Python dependencies (excluding torch and nvidia packages)
RUN grep -v -E '^(torch|nvidia|triton)' requirements.txt > requirements-filtered.txt && \
    pip install --no-cache-dir -r requirements-filtered.txt

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Run migration then start the application
CMD ["sh", "-c", "python src/migrate.py && uvicorn src.main:app --forwarded-allow-ips '*' --host 0.0.0.0 --port 8000"]
