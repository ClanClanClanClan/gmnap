FROM python:3.12-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libicu-dev \
    pkg-config \
    zstd \
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
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create cache and data directories
RUN mkdir -p /app/cache/gs /app/cache/bad_json /app/data

# Set Python path
ENV PYTHONPATH=/app

# Create non-root user for security
RUN useradd -m -u 1000 gmnap && chown -R gmnap:gmnap /app
USER gmnap

# Expose API port
EXPOSE 8080

# Default command — start API server
CMD ["python", "-m", "uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8080"]
