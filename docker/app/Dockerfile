FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

# Copy application code
COPY . .

# Set environment for container
ENV POSTGRES_DSN=postgresql://user:password@postgres:5432/app_db
ENV PYTHONPATH=/app

# Add health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "from storage_layer.database.database_manager import get_db_manager; get_db_manager().health_check()" || exit 1

# Default command - can be overridden  
CMD ["python", "scripts/continuous_crawler.py", "run", "--interval", "60"]