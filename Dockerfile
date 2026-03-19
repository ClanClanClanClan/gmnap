FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    python3-pip \
    build-essential \
    libicu-dev \
    zstd \
    duckdb \
    sqlite3 \
    git \
    curl \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install FastText language identification model
RUN mkdir -p /app/config && \
    wget -q https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O /app/config/lid.176.bin

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create cache and data directories
RUN mkdir -p /app/cache/gs /app/cache/bad_json /app/data

# Set Python path
ENV PYTHONPATH=/app/src:/app

# Default command
CMD ["python3.12", "-m", "uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8080"]