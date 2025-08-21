# GWEN-3 Ollama Deployment Guide

Complete setup and deployment guide for GWEN-3 8B model with Ollama container for Vietnamese content analysis.

## Overview

This guide covers the deployment of GWEN-3 (8B model) using Ollama in a Docker container optimized for Vietnamese news content analysis. The system provides automated parsing template generation for Vietnamese news websites.

## Prerequisites

### System Requirements
- **RAM**: Minimum 16GB (8GB allocated to GWEN-3 model)
- **Storage**: 10GB free space for model files
- **CPU**: 4+ cores recommended
- **OS**: Windows 10/11, Linux, or macOS with Docker support

### Software Requirements
- Docker Desktop 4.0+
- Docker Compose 2.0+
- Git (for repository management)
- PowerShell/Bash terminal access

### Network Requirements
- Internet access for model download (initial setup only)
- Port 11434 available for Ollama API
- Internal Docker network connectivity

## Quick Start

### 1. Repository Setup
```bash
# Navigate to project directory
cd "F:\Crawl data"

# Verify directory structure
ls infrastructure/docker/ollama/
ls deployment/
```

### 2. Environment Configuration
```bash
# Navigate to deployment directory
cd deployment

# Verify environment file exists
cat .env
```

Expected `.env` content:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crawler_db
DB_USER=crawler_user
DB_PASSWORD=crawler123
```

### 3. Deploy GWEN-3 Container
```bash
# Option A: Using deployment script (recommended)
cd infrastructure/scripts
chmod +x deploy_gwen3.sh
./deploy_gwen3.sh deploy

# Option B: Manual Docker Compose
cd deployment
docker-compose up -d ollama-gwen3
```

### 4. Verify Deployment
```bash
# Check container status
docker-compose ps ollama-gwen3

# Wait for model loading (5-10 minutes)
docker-compose logs -f ollama-gwen3

# Test health check
curl http://localhost:11434/api/version
```

## Detailed Deployment Steps

### Step 1: Container Configuration

The GWEN-3 container is configured with:
- **Memory limit**: 8GB hard limit
- **CPU allocation**: 4 cores (2 reserved, 4 limit)
- **Model**: gwen-3:8b specialized for Vietnamese
- **API port**: 11434
- **Health checks**: 30-second intervals

```yaml
# Docker Compose configuration
services:
  ollama-gwen3:
    build:
      context: ../infrastructure/docker/ollama
      dockerfile: Dockerfile
    container_name: ollama_gwen3
    restart: unless-stopped
    
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
        reservations:
          memory: 6G
          cpus: '2.0'
```

### Step 2: Model Download and Setup

The container automatically downloads GWEN-3 model on first startup:

```bash
# Monitor download progress
docker-compose logs -f ollama-gwen3

# Expected output:
# Starting Ollama server...
# Ollama server started (PID: xxx)
# Downloading gwen-3:8b model...
# Model download completed successfully
```

**Download specifications:**
- Model size: ~4.5GB
- Download time: 10-15 minutes (depending on connection)
- Storage location: Docker volume `ollama_models`

### Step 3: Health Verification

#### Automatic Health Checks
```bash
# Check Docker health status
docker inspect ollama_gwen3 --format='{{.State.Health.Status}}'

# Expected output: "healthy"
```

#### Manual Health Verification
```bash
# 1. API connectivity
curl -s http://localhost:11434/api/version

# 2. Model availability  
curl -s http://localhost:11434/api/tags | grep "gwen-3:8b"

# 3. Inference test
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"gwen-3:8b","prompt":"Test Vietnamese: Xin chào","stream":false}'
```

#### Comprehensive Health Check
```bash
# Using integrated health check script
cd infrastructure/scripts
chmod +x health_check.sh
./health_check.sh
```

## Configuration Management

### Model Parameters
Configuration file: `config/gwen3/model-config.yml`

```yaml
# Key parameters for Vietnamese analysis
performance:
  inference:
    temperature: 0.1          # Deterministic output
    top_p: 0.9               # Token probability filtering
    num_predict: 4096        # Max output tokens
    num_ctx: 8192            # Context window
    
vietnamese_analysis:
  language_detection:
    threshold: 0.8           # Vietnamese detection confidence
  content:
    min_confidence_score: 0.7 # Minimum template confidence
```

### Memory Management
```yaml
# Memory allocation settings
resources:
  memory:
    limit_gb: 8              # Hard limit
    warning_threshold_percent: 85
    critical_threshold_percent: 95
    
monitoring:
  health_check:
    interval_seconds: 30     # Check frequency
    start_period_seconds: 300 # Allow 5min for loading
```

## API Usage

### Basic Client Example
```python
from apps.gwen3_client import OllamaGWEN3Client

async with OllamaGWEN3Client() as client:
    # Verify model availability
    is_available, message = await client.verify_model_availability()
    print(f"Model available: {is_available} - {message}")
    
    # Analyze Vietnamese content
    result = await client.analyze_domain_structure(
        "vnexpress.net",
        vietnamese_html_content
    )
    
    print(f"Confidence: {result.confidence_score}")
    print(f"Headline selectors: {result.headline_selectors}")
```

### Advanced Wrapper Usage
```python
from apps.gwen3_client import GWEN3ModelWrapper

wrapper = GWEN3ModelWrapper(cache_ttl_hours=24)

async with wrapper:
    # Batch analysis with caching
    domains_content = [
        ("vnexpress.net", vnexpress_html),
        ("tuoitre.vn", tuoitre_html),
        ("thanhnien.vn", thanhnien_html)
    ]
    
    results = await wrapper.analyze_batch(domains_content)
    
    # Check cache statistics
    cache_stats = wrapper.get_cache_statistics()
    print(f"Cache hit rate: {cache_stats['cache_hit_rate']:.1f}%")
```

## Monitoring and Maintenance

### Performance Monitoring
```bash
# Resource usage monitoring
docker stats ollama_gwen3

# Memory usage check
docker exec ollama_gwen3 free -h

# API response time test
time curl -s http://localhost:11434/api/version
```

### Log Management
```bash
# View container logs
docker-compose logs ollama-gwen3

# Follow log stream
docker-compose logs -f ollama-gwen3

# Log rotation (automatic via Docker)
# Logs are rotated at 100MB with 3 backup files
```

### Health Monitoring
```bash
# Scheduled health checks (every 5 minutes)
*/5 * * * * /path/to/infrastructure/scripts/health_check.sh

# Performance metrics collection
docker stats ollama_gwen3 --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## Troubleshooting

### Common Issues

#### 1. Container Won't Start
```bash
# Check container logs
docker-compose logs ollama-gwen3

# Common causes:
# - Insufficient memory (need 8GB+ available)
# - Port 11434 already in use
# - Docker resource limits too low
```

**Solutions:**
```bash
# Increase Docker memory limit to 12GB+
# Check port usage: netstat -tulpn | grep 11434
# Free up system memory before starting
```

#### 2. Model Download Fails
```bash
# Symptoms: Container restarts repeatedly
# Check download progress
docker-compose logs ollama-gwen3 | grep -i download

# Common causes:
# - Network connectivity issues
# - Insufficient disk space
# - Docker hub rate limits
```

**Solutions:**
```bash
# Check disk space: df -h
# Test network: curl -s https://registry.ollama.ai
# Manual model download: docker exec ollama_gwen3 ollama pull gwen-3:8b
```

#### 3. High Memory Usage
```bash
# Monitor memory usage
watch -n 5 'docker stats ollama_gwen3 --no-stream'

# Check for memory leaks
docker exec ollama_gwen3 cat /proc/meminfo
```

**Solutions:**
```bash
# Restart container if memory > 90%
docker-compose restart ollama-gwen3

# Clear analysis cache
curl -X POST http://localhost:11434/api/clear-cache
```

#### 4. Slow Inference Performance
```bash
# Test response time
time curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"gwen-3:8b","prompt":"Quick test","stream":false}'

# Should complete within 30 seconds for small prompts
```

**Solutions:**
```bash
# Check CPU allocation
docker inspect ollama_gwen3 | grep -i cpu

# Increase CPU limits in docker-compose.yml
# Reduce concurrent requests
# Optimize prompt length
```

### Recovery Procedures

#### Container Recovery
```bash
# Stop and restart container
docker-compose stop ollama-gwen3
docker-compose start ollama-gwen3

# Force recreation
docker-compose up --force-recreate -d ollama-gwen3
```

#### Model Recovery
```bash
# Reload model manually
docker exec ollama_gwen3 ollama pull gwen-3:8b

# Clear model cache
docker exec ollama_gwen3 rm -rf /root/.ollama/models/gwen-3*
docker-compose restart ollama-gwen3
```

#### Complete Reset
```bash
# WARNING: This removes all cached data
docker-compose down ollama-gwen3
docker volume rm deployment_ollama_models
docker-compose up -d ollama-gwen3
```

## Performance Optimization

### Memory Optimization
```bash
# Enable memory cleanup
export OLLAMA_MAX_VRAM=8388608  # 8GB in KB
export OLLAMA_FLASH_ATTENTION=1
```

### CPU Optimization
```yaml
# docker-compose.yml optimization
deploy:
  resources:
    limits:
      cpus: '4.0'
    reservations:
      cpus: '2.0'
```

### Network Optimization
```bash
# Enable connection keep-alive
export OLLAMA_KEEP_ALIVE=300s
export OLLAMA_NUM_PARALLEL=1
```

## Security Considerations

### Network Security
- Ollama API exposed only on localhost (127.0.0.1:11434)
- Internal Docker network isolation
- No external API endpoints
- Container runs with limited privileges

### Data Security  
- No persistent data logging of analyzed content
- Model parameters stored in encrypted Docker volumes
- Analysis results cached temporarily only
- No external data transmission

### Access Control
```bash
# Container user restrictions
USER ollama
WORKDIR /app

# Read-only filesystem where possible
--read-only --tmpfs /tmp
```

## Backup and Recovery

### Model Backup
```bash
# Backup model data
docker run --rm -v deployment_ollama_models:/data -v $(pwd):/backup \
  alpine tar czf /backup/ollama-models-$(date +%Y%m%d).tar.gz -C /data .
```

### Configuration Backup
```bash
# Backup configuration files
tar czf gwen3-config-$(date +%Y%m%d).tar.gz \
  config/gwen3/ \
  infrastructure/docker/ollama/ \
  deployment/docker-compose.yml
```

### Restore Procedures
```bash
# Restore model data
docker volume create deployment_ollama_models
docker run --rm -v deployment_ollama_models:/data -v $(pwd):/backup \
  alpine tar xzf /backup/ollama-models-backup.tar.gz -C /data

# Restart container
docker-compose restart ollama-gwen3
```

## Production Deployment

### Scaling Considerations
- Single container deployment (no horizontal scaling)
- Vertical scaling: increase memory/CPU allocation
- Load balancing: implement at application layer
- Concurrent request limiting: max 2 simultaneous analyses

### Monitoring Setup
```yaml
# Prometheus metrics (if available)
prometheus_metrics:
  enabled: true
  port: 9090
  metrics:
    - ollama_inference_duration
    - ollama_memory_usage
    - ollama_request_count
```

### Alerting Rules
```yaml
# Alert conditions
alerts:
  high_memory_usage:
    condition: memory_usage > 85%
    duration: 5m
    action: restart_container
    
  slow_response:
    condition: avg_response_time > 60s
    duration: 3m
    action: log_warning
```

## Support and Maintenance

### Regular Maintenance Tasks
```bash
# Weekly tasks
- Check container health status
- Review performance metrics
- Update model if new version available
- Clean up old log files

# Monthly tasks  
- Backup model data
- Review resource usage trends
- Update container base images
- Security audit
```

### Getting Support
- Review troubleshooting section first
- Check container logs for error details  
- Monitor system resources (RAM, CPU, disk)
- Test with minimal Vietnamese content samples

### Useful Commands Reference
```bash
# Status checks
docker-compose ps ollama-gwen3
docker inspect ollama_gwen3 --format='{{.State.Health.Status}}'
curl -s http://localhost:11434/api/version

# Performance monitoring
docker stats ollama_gwen3 --no-stream
docker exec ollama_gwen3 free -h
docker exec ollama_gwen3 top -bn1

# Maintenance
docker-compose restart ollama-gwen3
docker-compose logs --tail=50 ollama-gwen3
docker system prune
```

---

**Last Updated**: 2025-08-11  
**Version**: 1.0.0  
**Author**: James (Dev Agent)  
**Contact**: See project documentation for support channels