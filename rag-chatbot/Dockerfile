# Use Python 3.10 base image
FROM python:3.10.18-trixie

# Set working directory
WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download docs files
RUN chmod +x download_docs.sh && ./download_docs.sh

# Keep the container running
CMD ["tail", "-f", "/dev/null"]