# Developer Tooling

This directory contains development tools and configurations for GMNAP v7.0.

## Structure

### `/cli`
Command-line interface tools and scripts for development tasks.

### `/containers`
Container-related files including specialized Dockerfiles.
- `Dockerfile.korea` - Specialized container for Korean language processing

### `/docker`
Main Docker configuration for the project.
- `docker-compose.yml` - Docker Compose configuration for multi-container setup
- `Dockerfile` - Main application Dockerfile

### `/pre-commit`
Pre-commit hooks and configurations for code quality enforcement.

### `/vscode`
Visual Studio Code workspace settings and recommended extensions.

## v7.0 Development Environment

According to the v7.0 specifications, the development environment includes:
- Docker Compose for containerized development
- Pre-commit hooks for code quality
- CLI tools for common development tasks
- VSCode configurations for consistent development experience

## Quick Start

1. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

2. Start development environment:
   ```bash
   docker-compose -f developer_tooling/docker/docker-compose.yml up
   ```

3. Use CLI tools:
   ```bash
   python developer_tooling/cli/<tool_name>.py
   ```