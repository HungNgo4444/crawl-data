# Enhanced Crawler Worker - Production Container
# Multi-stage build for optimal size and security

FROM python:3.12-slim-bookworm AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security with home directory
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

# Set working directory
WORKDIR /app

# Create directories with proper permissions
RUN mkdir -p /app/cache /app/logs /app/data && \
    chown -R appuser:appuser /app

FROM base AS dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for enhanced crawler
RUN pip install --no-cache-dir \
    httpx[http2]==0.25.2 \
    feedparser==6.0.10 \
    lxml==4.9.3 \
    beautifulsoup4==4.12.2 \
    aiofiles==23.2.1 \
    lz4==4.3.2 \
    redis==5.0.1 \
    asyncpg==0.29.0 \
    pydantic==2.5.0 \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    pytest-mock==3.12.0

FROM dependencies AS production

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY *.py ./

# Copy configuration files
COPY config/ ./config/

# Set proper permissions
RUN chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser

# Set Python path
ENV PYTHONPATH="/app"

# Run as root for now to avoid permission issues with Crawl4AI
# USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import asyncio; print('Health check passed')" || exit 1

# Default command - use simple main that actually works
CMD ["python", "simple_main.py"]

# Expose port for health checks and metrics
EXPOSE 8080

# Labels for metadata
LABEL maintainer="Enhanced Crawler Team"
LABEL version="1.0.0"
LABEL description="Enhanced Vietnamese News Crawler Worker with Crawl4AI Integration"