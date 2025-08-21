# Analysis Worker Service Container
# Optimized for Vietnamese content analysis with GWEN-3
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN groupadd -r worker && useradd -r -g worker -d /app -s /bin/bash worker

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data && \
    chown -R worker:worker /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV WORKER_ID=worker-container
ENV LOG_LEVEL=INFO
ENV HEALTH_CHECK_PORT=8080

# Health check configuration
ENV MAX_CONCURRENT_ANALYSES=3
ENV ANALYSIS_TIMEOUT=300
ENV POLLING_INTERVAL=10

# Redis configuration
ENV REDIS_URL=redis://redis:6379

# Database configuration
ENV DB_HOST=postgres
ENV DB_PORT=5432
ENV DB_NAME=crawler_db
ENV DB_USER=crawler_user
ENV DB_PASSWORD=

# GWEN-3 configuration
ENV GWEN3_URL=http://ollama:11434
ENV GWEN3_MODEL=gwen-3:8b

# Monitoring configuration
ENV METRICS_ENABLED=true

# Expose health check port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Switch to non-root user
USER worker

# Default command
CMD ["python", "-m", "src.main"]