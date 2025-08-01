# -----------------------------------------------------------------------------
# Dockerfile for the Fintech Crawler Project
# -----------------------------------------------------------------------------
# This Dockerfile uses a multi-stage build approach to create optimized
# and secure Docker images for different environments.
#
# Stages:
# 1. 'base': Installs Python and common dependencies.
# 2. 'builder': Installs all Python application dependencies.
# 3. 'development': A stage for local development with live reloading.
# 4. 'production': The final, lean production image.
#
# To build a specific stage:
#   docker build --target <stage_name> -t <image_name> .
# -----------------------------------------------------------------------------

# --- Stage 1: Base Image ---
# This stage sets up the Python environment and installs essential packages.
FROM python:3.11-slim as base
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Stage 2: Builder ---
# This stage installs all Python dependencies using pip.
# It copies only the requirements file to leverage Docker's layer caching.
FROM base as builder

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Download Playwright browsers
RUN playwright install --with-deps

# --- Stage 3: Development Image ---
# This stage is optimized for local development.
# It includes the full source code and is intended to be used with volumes
# for live code reloading.
FROM base as development

# Copy dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the application source code
COPY . .

# Default command can be overridden in docker-compose.yml
CMD ["tail", "-f", "/dev/null"]


# --- Stage 4: Production Image ---
# This is the final, lean image for production deployment.
# It copies only the necessary installed packages and source code.
FROM base as production

# Copy dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the application source code
COPY . .

# The entrypoint will be specified in the deployment configuration (e.g., Kubernetes)
# Example command:
# CMD ["python", "-m", "crawler_layer.orchestrator"] 