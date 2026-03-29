# Docker Configuration for GMNAP v7.0

This directory contains Docker configuration files for the GMNAP v7.0 deployment.

## Files

### `docker-compose.yml`
Docker Compose configuration for local development and testing. Includes:
- GMNAP application container
- Memgraph CE 2.12 graph database
- DuckDB analytics layer
- Nginx reverse proxy

### `Dockerfile`
Main application Dockerfile for building the GMNAP v7.0 container.
- Based on Python 3.11 slim
- Includes all required dependencies
- Configures runtime environment

### `init_memgraph.cypher`
Initialization script for Memgraph database:
- Creates required indexes
- Sets up constraints
- Initializes graph schema

## Usage

### Local Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Building Images
```bash
# Build main application image
docker build -t gmnap:v7.0 -f Dockerfile ../..

# Build with specific profile
docker build --build-arg PROFILE=extreme -t gmnap:v7.0-extreme -f Dockerfile ../..
```

### Environment Variables
- `GMNAP_PROFILE`: Runtime profile (quick/full/extreme)
- `MEMGRAPH_HOST`: Memgraph database host
- `MEMGRAPH_PORT`: Memgraph database port
- `DUCKDB_PATH`: Path to DuckDB database file

## v7.0 Compliance
These Docker configurations implement the deployment architecture specified in the v7.0 specifications section 10.