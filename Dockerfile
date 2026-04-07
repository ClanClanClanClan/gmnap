FROM python:3.12-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libicu-dev \
    zstd \
    sqlite3 \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Compile FastText CLI binary (346KB, needed for surname classification)
RUN git clone --depth 1 https://github.com/facebookresearch/fastText.git /tmp/fasttext-build \
    && cd /tmp/fasttext-build && make -j$(nproc) \
    && cp /tmp/fasttext-build/fasttext /usr/local/bin/fasttext \
    && rm -rf /tmp/fasttext-build

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create cache and data directories
RUN mkdir -p /app/cache/gs /app/cache/bad_json /app/data

# Set Python path
ENV PYTHONPATH=/app/src:/app

# Default command
CMD ["python3", "-m", "uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8080"]