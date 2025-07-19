#!/bin/bash
# GMNAP Development Environment Setup

echo "Setting up GMNAP development environment..."

# Install Python dependencies
pip install -r requirements.txt

# Download FastText model if missing
if [ ! -f "cache/config/lid.176.bin" ]; then
    echo "Downloading FastText language detection model..."
    mkdir -p cache/config
    wget -O cache/config/lid.176.bin.gz https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
    gunzip cache/config/lid.176.bin.gz
fi

# Set up pre-commit hooks
pip install pre-commit
pre-commit install

# Create necessary directories
mkdir -p cache/output cache/bad_json logs data

echo "✅ Development environment setup complete!"
