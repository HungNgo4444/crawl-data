# GWEN-3 Troubleshooting Guide

Comprehensive troubleshooting guide for GWEN-3 Ollama deployment and Vietnamese content analysis issues.

## Quick Diagnosis Commands

### System Status Check
```bash
# Container status
docker-compose ps ollama-gwen3

# Health status
docker inspect ollama_gwen3 --format='{{.State.Health.Status}}'

# Resource usage
docker stats ollama_gwen3 --no-stream

# API connectivity
curl -s http://localhost:11434/api/version

# Model availability
curl -s http://localhost:11434/api/tags | grep -i gwen
```

### Log Analysis
```bash
# Recent logs
docker-compose logs --tail=50 ollama-gwen3

# Follow live logs
docker-compose logs -f ollama-gwen3

# Search for errors
docker-compose logs ollama-gwen3 | grep -i error

# Filter by timestamp
docker-compose logs --since="1h" ollama-gwen3
```

## Container Issues

### Issue: Container Won't Start

#### Symptoms
- Container exits immediately after starting
- `docker-compose ps` shows container as "Exited"
- Error messages in startup logs

#### Diagnosis
```bash
# Check exit code
docker-compose ps ollama-gwen3

# View startup logs
docker-compose logs ollama-gwen3

# Check system resources
free -h
df -h
```

#### Common Causes & Solutions

**1. Insufficient Memory**
```bash
# Symptoms:
# - "OOM killed" in logs
# - Container exits with code 137
# - System has < 10GB available RAM

# Solution: Free up memory
sudo systemctl stop unnecessary-services
docker system prune -f
# Or increase system RAM
```

**2. Port Already in Use**
```bash
# Check port usage
netstat -tulpn | grep 11434
lsof -i :11434

# Solution: Kill process using port
sudo kill -9 $(lsof -t -i:11434)
# Or change port in docker-compose.yml
```

**3. Docker Resource Limits**
```bash
# Check Docker settings
docker system info | grep -E "Memory|CPUs"

# Solution: Increase Docker resources
# Docker Desktop → Settings → Resources
# Set Memory to 12GB+, CPUs to 4+
```

**4. Corrupted Docker Image**
```bash
# Symptoms: Image build failures
# Solution: Rebuild from scratch
docker-compose down
docker image rm deployment_ollama-gwen3:latest
docker-compose build --no-cache ollama-gwen3
docker-compose up -d ollama-gwen3
```

### Issue: Container Starts but Health Check Fails

#### Symptoms
- Container status is "running" but health is "unhealthy"
- Health check timeout errors
- API endpoints not responding

#### Diagnosis
```bash
# Manual health check
docker exec ollama_gwen3 /app/health-check.sh

# Check Ollama service
docker exec ollama_gwen3 ps aux | grep ollama

# Test API manually
docker exec ollama_gwen3 curl -s http://localhost:11434/api/version
```

#### Solutions

**1. Ollama Service Not Started**
```bash
# Restart Ollama inside container
docker exec ollama_gwen3 pkill ollama
docker-compose restart ollama-gwen3
```

**2. Health Check Timeout**
```bash
# Increase health check timeout in docker-compose.yml
healthcheck:
  test: ["/app/health-check.sh"]
  timeout: 60s        # Increased from 30s
  start_period: 600s  # Increased from 300s
```

## Model Loading Issues

### Issue: GWEN-3 Model Not Found

#### Symptoms
- "Model not found" errors in API responses
- `curl http://localhost:11434/api/tags` doesn't show gwen-3:8b
- Analysis requests fail with model errors

#### Diagnosis
```bash
# Check loaded models
curl -s http://localhost:11434/api/tags | jq '.models[].name'

# Check model files
docker exec ollama_gwen3 ls -la /root/.ollama/models/

# Check disk space
docker exec ollama_gwen3 df -h
```

#### Solutions

**1. Manual Model Download**
```bash
# Download model manually
docker exec ollama_gwen3 ollama pull gwen-3:8b

# Monitor download progress
docker-compose logs -f ollama-gwen3 | grep -i download
```

**2. Network Issues During Download**
```bash
# Test connectivity
docker exec ollama_gwen3 curl -s https://registry.ollama.ai

# Check proxy settings if behind corporate firewall
# Add to docker-compose.yml:
environment:
  - HTTP_PROXY=http://proxy:8080
  - HTTPS_PROXY=http://proxy:8080
```

**3. Insufficient Disk Space**
```bash
# Free up space
docker system prune -a -f
docker volume prune -f

# Check available space (need 10GB+)
df -h /var/lib/docker
```

### Issue: Model Loading Timeout

#### Symptoms
- Container health check fails during model loading
- Very long startup times (>10 minutes)
- "Model loading in progress" messages

#### Solutions
```bash
# 1. Increase startup timeout
# In docker-compose.yml:
healthcheck:
  start_period: 900s  # 15 minutes

# 2. Monitor loading progress
docker-compose logs -f ollama-gwen3 | grep -i "loading\|download"

# 3. Restart if stuck
docker-compose restart ollama-gwen3
```

## Performance Issues

### Issue: Very Slow Analysis Response Times

#### Symptoms
- Analysis takes >60 seconds for small content
- High CPU usage but low memory usage
- Timeout errors in API responses

#### Diagnosis
```bash
# Test simple inference
time curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"gwen-3:8b","prompt":"Test","stream":false,"options":{"num_predict":10}}'

# Check resource usage during analysis
docker stats ollama_gwen3

# Monitor system load
top -p $(docker exec ollama_gwen3 pgrep ollama)
```

#### Solutions

**1. CPU Resource Constraints**
```yaml
# Increase CPU allocation in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '6.0'    # Increase from 4.0
```

**2. Memory Swapping**
```bash
# Check swap usage
free -h
# If swap is being used, add more RAM or reduce memory usage

# Disable swap temporarily
sudo swapoff -a
```

**3. Model Parameter Optimization**
```bash
# Use faster parameters for testing
curl -X POST http://localhost:11434/api/generate \
  -d '{
    "model":"gwen-3:8b",
    "prompt":"Test",
    "options":{
      "temperature":0.1,
      "num_predict":100,
      "top_k":10
    }
  }'
```

### Issue: High Memory Usage / Out of Memory

#### Symptoms
- Container killed with exit code 137
- Memory usage consistently >90%
- System becomes unresponsive

#### Diagnosis
```bash
# Monitor memory usage over time
watch -n 5 'docker stats ollama_gwen3 --no-stream'

# Check memory inside container
docker exec ollama_gwen3 free -h

# Check for memory leaks
docker exec ollama_gwen3 cat /proc/meminfo
```

#### Solutions

**1. Increase Memory Allocation**
```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      memory: 10G    # Increase from 8G
```

**2. Enable Memory Cleanup**
```bash
# Set environment variables for memory management
environment:
  - OLLAMA_MAX_VRAM=6442450944  # 6GB in bytes
  - OLLAMA_FLASH_ATTENTION=1
  - OLLAMA_GC_INTERVAL=30
```

**3. Clear Analysis Cache**
```python
# Using Python client
from apps.gwen3_client import GWEN3ModelWrapper

async with GWEN3ModelWrapper() as wrapper:
    await wrapper.clear_cache()
```

## Vietnamese Analysis Issues

### Issue: Language Detection Failures

#### Symptoms
- Vietnamese content detected as "unknown" or "english"
- Low confidence scores for clearly Vietnamese content
- Missing Vietnamese-specific selectors

#### Diagnosis
```bash
# Test with known Vietnamese content
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model":"gwen-3:8b",
    "prompt":"Phân tích văn bản tiếng Việt: Xin chào, đây là tin tức."
  }'
```

#### Solutions

**1. Update Vietnamese Keywords**
```yaml
# In config/gwen3/model-config.yml
vietnamese_analysis:
  language_detection:
    threshold: 0.7        # Lower threshold
    keywords:
      - "tin tức"
      - "báo chí"
      - "thông tin"
      - "bài viết"
      - "và"
      - "của"
      - "được"
```

**2. Improve Content Preprocessing**
```python
# Better content preparation
def prepare_vietnamese_content(html_content):
    # Preserve Vietnamese characters
    import unicodedata
    normalized = unicodedata.normalize('NFC', html_content)
    
    # Keep essential HTML structure
    return normalized
```

### Issue: Poor CSS Selector Quality

#### Symptoms
- Generic selectors like "div", "span" without classes
- Very low confidence scores (<0.5)
- Selectors don't work on actual content

#### Solutions

**1. Improve Analysis Prompts**
```yaml
# Update analysis-prompts.yml
analysis_prompts:
  domain_structure_analysis: |
    YÊU CẦU CỤ THỂ:
    - Tránh selector generic như "div", "span"
    - Ưu tiên class names có ý nghĩa semantic
    - Cung cấp ít nhất 2 backup selectors
    - Đánh giá confidence score thật tế
```

**2. Domain-Specific Training**
```python
# Add domain-specific patterns
VIETNAMESE_PATTERNS = {
    "vnexpress.net": {
        "headline": ["h1.title_news_detail", ".article-title"],
        "content": [".fck_detail", ".article-body"]
    },
    "tuoitre.vn": {
        "headline": [".article-title", "h1.title"],
        "content": [".article-content", ".content-main"]
    }
}
```

## API and Network Issues

### Issue: API Connection Refused

#### Symptoms
- "Connection refused" errors
- Timeouts when accessing http://localhost:11434
- API endpoints return 404 or 500 errors

#### Diagnosis
```bash
# Check if service is listening
netstat -tlnp | grep 11434

# Test from inside container
docker exec ollama_gwen3 curl -s http://localhost:11434/api/version

# Check firewall rules
sudo iptables -L | grep 11434
```

#### Solutions

**1. Service Not Started**
```bash
# Restart Ollama service
docker exec ollama_gwen3 pkill -f ollama
docker exec ollama_gwen3 ollama serve &
```

**2. Port Binding Issues**
```yaml
# Ensure correct port mapping in docker-compose.yml
ports:
  - "11434:11434"    # host:container
```

**3. Network Configuration**
```bash
# Check Docker network
docker network ls
docker network inspect deployment_crawler
```

### Issue: API Timeout Errors

#### Symptoms
- Requests timeout after 30-60 seconds
- "Request timeout" errors in client
- Partial responses or connection drops

#### Solutions

**1. Increase Client Timeouts**
```python
# In Python client configuration
config.ollama.timeout = 600  # 10 minutes
config.ollama.max_retries = 5
```

**2. Server-side Timeout Configuration**
```bash
# Set Ollama server timeouts
environment:
  - OLLAMA_REQUEST_TIMEOUT=600s
  - OLLAMA_KEEP_ALIVE=300s
```

## Data and Content Issues

### Issue: Analysis Returns Empty Results

#### Symptoms
- Empty parsing templates
- Zero confidence scores
- No selectors generated

#### Diagnosis
```bash
# Test with minimal content
curl -X POST http://localhost:11434/api/generate \
  -d '{
    "model":"gwen-3:8b",
    "prompt":"Analyze: <h1>Test Title</h1><div>Content</div>",
    "stream":false
  }'
```

#### Solutions

**1. Content Too Short**
```python
# Ensure minimum content length
if len(html_content) < 500:  # 500 characters minimum
    # Add context or use fallback analysis
```

**2. HTML Structure Issues**
```python
# Clean HTML before analysis
from bs4 import BeautifulSoup

def clean_html_for_analysis(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style tags
    for tag in soup(['script', 'style']):
        tag.decompose()
        
    return str(soup)
```

### Issue: Inconsistent Analysis Results

#### Symptoms
- Different results for same content
- Confidence scores vary widely
- Selectors change between runs

#### Solutions

**1. Use Deterministic Settings**
```json
{
  "model": "gwen-3:8b",
  "options": {
    "temperature": 0.0,    // Maximum determinism
    "top_k": 1,            // Most probable token only
    "seed": 12345          // Fixed seed
  }
}
```

**2. Cache Results**
```python
# Enable result caching
wrapper = GWEN3ModelWrapper(
    cache_ttl_hours=24,
    max_cache_size=1000
)
```

## Recovery Procedures

### Complete System Recovery

#### 1. Soft Recovery (Data Preserved)
```bash
# Restart container
docker-compose restart ollama-gwen3

# Wait for startup
sleep 60

# Verify health
curl -s http://localhost:11434/api/version
```

#### 2. Hard Recovery (Rebuild Container)
```bash
# Stop and remove container
docker-compose down ollama-gwen3

# Remove image
docker image rm deployment_ollama-gwen3

# Rebuild and start
docker-compose build --no-cache ollama-gwen3
docker-compose up -d ollama-gwen3
```

#### 3. Complete Reset (All Data Lost)
```bash
# WARNING: This removes all cached data and models
docker-compose down
docker volume rm deployment_ollama_models
docker system prune -a -f
docker-compose up -d
```

### Model Recovery

#### Reload Model Only
```bash
# Remove model from memory
docker exec ollama_gwen3 ollama rm gwen-3:8b

# Download fresh copy
docker exec ollama_gwen3 ollama pull gwen-3:8b

# Verify loading
curl -s http://localhost:11434/api/tags | grep gwen-3
```

### Configuration Recovery

#### Restore Default Configuration
```bash
# Backup current config
cp config/gwen3/model-config.yml config/gwen3/model-config.yml.backup

# Reset to defaults
git checkout config/gwen3/model-config.yml

# Restart to apply changes
docker-compose restart ollama-gwen3
```

## Monitoring and Prevention

### Proactive Monitoring Setup

#### Health Check Script
```bash
#!/bin/bash
# Add to crontab: */5 * * * *
/path/to/infrastructure/scripts/health_check.sh

# Alert if health check fails
if [ $? -ne 0 ]; then
    echo "GWEN-3 health check failed" | mail -s "Alert" admin@company.com
fi
```

#### Resource Monitoring
```bash
# Monitor resource usage
watch -n 30 'docker stats ollama_gwen3 --no-stream'

# Alert on high memory usage
MEMORY_USAGE=$(docker stats ollama_gwen3 --no-stream --format "{{.MemPerc}}" | sed 's/%//')
if (( $(echo "$MEMORY_USAGE > 85" | bc -l) )); then
    echo "High memory usage: $MEMORY_USAGE%" | mail -s "Memory Alert" admin@company.com
fi
```

### Log Management

#### Log Rotation
```bash
# Configure log rotation
# /etc/logrotate.d/docker-gwen3
/var/lib/docker/containers/*/gwen3*-json.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

#### Log Analysis
```bash
# Search for common issues
docker-compose logs ollama-gwen3 | grep -E "(error|Error|ERROR|timeout|Timeout|failed|Failed)"

# Monitor performance patterns
docker-compose logs ollama-gwen3 | grep "analysis completed" | tail -50
```

## Support and Documentation

### Collecting Debug Information

When reporting issues, collect the following information:

#### System Information
```bash
# System specs
uname -a
free -h
df -h
docker version
docker-compose version

# Container information
docker-compose ps
docker inspect ollama_gwen3

# Recent logs
docker-compose logs --tail=100 ollama-gwen3 > gwen3-logs.txt
```

#### Configuration Files
```bash
# Configuration backup
tar -czf gwen3-config-$(date +%Y%m%d).tar.gz \
  config/gwen3/ \
  deployment/docker-compose.yml \
  infrastructure/docker/ollama/
```

### Common Error Codes

| Exit Code | Meaning | Common Causes |
|-----------|---------|---------------|
| 0 | Success | Normal operation |
| 1 | General error | Configuration issues, file not found |
| 125 | Docker run error | Invalid Docker command |
| 126 | Permission denied | File permission issues |
| 127 | Command not found | Missing executable |
| 137 | SIGKILL | Out of memory, killed by system |
| 143 | SIGTERM | Graceful shutdown |

### Getting Help

1. **Check this troubleshooting guide first**
2. **Review container logs for specific error messages**
3. **Test with minimal Vietnamese content samples**
4. **Verify system requirements (RAM, disk space)**
5. **Check Docker and system resource limits**

---

**Troubleshooting Guide Version**: 1.0.0  
**Last Updated**: 2025-08-11  
**Author**: James (Dev Agent)  
**Next Review**: Monthly update recommended