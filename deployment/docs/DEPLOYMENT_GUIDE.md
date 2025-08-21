# 🚀 AI-Powered Multi-Domain News Crawler - Production Deployment Guide

## 📋 System Overview

Complete containerized deployment for Stories 1.1-1.3:

- **Story 1.1**: PostgreSQL Database Foundation với Vietnamese domain management
- **Story 1.2**: GWEN-3 Model Deployment (qwen2.5:3b) cho Vietnamese content analysis  
- **Story 1.3**: Domain Analysis Worker với Redis queue management

## 🏗️ Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   PostgreSQL    │    │   Ollama GWEN-3  │    │  Analysis Worker    │
│   (Story 1.1)   │◄──►│   (Story 1.2)    │◄──►│   (Story 1.3)       │
│   Port: 5432    │    │   Port: 11434    │    │   Port: 8082        │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         ▲                                                ▲
         │                                                │
         ▼                                                ▼
┌─────────────────┐                            ┌─────────────────────┐
│     pgAdmin     │                            │       Redis         │
│   Port: 8080    │                            │     Port: 6379      │
└─────────────────┘                            └─────────────────────┘
```

## 🚦 Quick Start

### 1. Prerequisites

```bash
# Ensure Docker và Docker Compose installed
docker --version
docker-compose --version

# Ensure ports available: 5432, 6379, 8080, 8082, 11434
netstat -an | findstr ":5432 :6379 :8080 :8082 :11434"
```

### 2. Deploy System

```bash
# Navigate to deployment directory
cd deployment

# Start complete system
deploy.bat start

# Verify all services healthy
deploy.bat health
```

### 3. First-time Setup

```bash
# Setup database với Vietnamese domains
deploy.bat setup-db

# Download GWEN-3 model (if not auto-downloaded)
docker exec crawler_ollama ollama pull qwen2.5:3b
```

## 🔧 Configuration Management

### Environment Variables

All configuration managed through `docker-compose.yml`:

```yaml
# Database Configuration
POSTGRES_DB: crawler_db
POSTGRES_USER: crawler_user  
POSTGRES_PASSWORD: crawler123

# GWEN-3 Model Configuration
GWEN3_URL: http://ollama:11434
GWEN3_MODEL: qwen2.5:3b
OLLAMA_KEEP_ALIVE: 600s

# Analysis Worker Configuration  
WORKER_ID: worker-001
REDIS_URL: redis://redis:6379
MAX_CONCURRENT_ANALYSES: 3
LOG_LEVEL: INFO
```

### Volume Management

```yaml
volumes:
  postgres_data:     # PostgreSQL database files
  pgadmin_data:      # pgAdmin configuration
  ollama_models:     # GWEN-3 model files (large!)
  redis_data:        # Redis persistence
  prometheus_data:   # Metrics storage
  grafana_data:      # Dashboard configuration
```

## 🌐 Service Endpoints

| Service | URL | Purpose | Credentials |
|---------|-----|---------|-------------|
| Analysis Worker | http://localhost:8082/health | API Health Check | None |
| Analysis Worker | http://localhost:8082/trigger/{id} | Trigger Analysis | None |
| Ollama API | http://localhost:11434/api/tags | Model Management | None |
| pgAdmin | http://localhost:8080 | Database Management | admin@crawler.dev / admin123 |
| Redis Commander | http://localhost:8081 | Queue Management | None (dev profile) |

## 🧪 Testing & Verification

### 1. System Health Check

```bash
# Complete health check
deploy.bat health

# Individual service checks
curl http://localhost:8082/health          # Analysis Worker
curl http://localhost:11434/api/tags       # Ollama API
curl http://localhost:8082/stats           # Worker Statistics
```

### 2. Vietnamese Content Analysis Test

```bash
# Trigger VNExpress.net analysis
curl -X POST "http://localhost:8082/trigger/5ca6f1b9-ee1a-4df7-89d7-e3a3d04e4faf"

# Expected response:
# {"success": true, "message": "Analysis started immediately (job ID: ...)", "job_id": "..."}

# Check job status
curl "http://localhost:8082/jobs/{job_id}/status"
```

### 3. Database Verification

```bash
# Connect to database
docker exec -it crawler_postgres psql -U crawler_user -d crawler_db

# Check Vietnamese domains
SELECT domain_name, base_url, status FROM domain_configurations;

# Should show VNExpress, Dân Trí, CafeF, etc.
```

## 📊 Monitoring & Observability

### Development Profile (Optional)

```bash
# Include Redis Commander
docker-compose --profile dev up -d

# Access queue management: http://localhost:8081
```

### Monitoring Profile (Optional)  

```bash
# Include Prometheus + Grafana
docker-compose --profile monitoring up -d

# Access dashboards:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

### Log Management

```bash
# View all service logs
deploy.bat logs

# Individual service logs
docker-compose logs postgres
docker-compose logs ollama  
docker-compose logs analysis-worker
docker-compose logs redis
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Container Startup Failures

```bash
# Check container status
docker-compose ps

# Common solutions
docker-compose down
docker-compose up -d
deploy.bat health
```

#### 2. Model Loading Issues

```bash
# Check Ollama container health
docker exec crawler_ollama ollama list

# If qwen2.5:3b missing:
docker exec crawler_ollama ollama pull qwen2.5:3b

# Monitor download progress
docker-compose logs ollama -f
```

#### 3. Database Connection Errors

```bash
# Reset database
deploy.bat setup-db

# Check PostgreSQL status
docker-compose logs postgres

# Manual database reset
docker-compose down -v
docker-compose up -d postgres
```

#### 4. Analysis Worker Errors

```bash
# Check worker logs
docker-compose logs analysis-worker

# Common fixes:
# - Ensure database is healthy
# - Ensure Redis is healthy  
# - Ensure Ollama model loaded
# - Restart worker: docker-compose restart analysis-worker
```

#### 5. Port Conflicts

```bash
# Check port usage
netstat -an | findstr ":5432 :6379 :8080 :8082 :11434"

# Edit docker-compose.yml to use different ports if needed
```

## 🔄 Maintenance Operations

### Backup & Restore

```bash
# Backup database
docker exec crawler_postgres pg_dump -U crawler_user crawler_db > backup_$(date +%Y%m%d).sql

# Restore database
docker exec -i crawler_postgres psql -U crawler_user crawler_db < backup_file.sql

# Backup Ollama models (large files!)
docker run --rm -v deployment_ollama_models:/data -v $(pwd):/backup alpine tar czf /backup/ollama_models_backup.tar.gz /data
```

### Updates & Upgrades

```bash
# Update container images
docker-compose pull

# Rebuild and restart
deploy.bat stop
deploy.bat start

# Verify after update
deploy.bat health
```

### Performance Tuning

```bash
# Monitor resource usage
docker stats

# Adjust in docker-compose.yml:
# - Memory limits for Ollama (GTX 1650 constraint)
# - CPU limits for Analysis Worker
# - Redis memory configuration
```

## 🔒 Security Considerations

### Production Hardening

1. **Change default passwords** trong docker-compose.yml
2. **Use environment files** thay vì hardcode credentials  
3. **Configure firewall** để restrict port access
4. **Enable SSL/TLS** cho external access
5. **Regular security updates** cho container images

### Credential Management

```bash
# Create .env file (not in git!)
echo "DB_PASSWORD=your_secure_password" > .env
echo "PGADMIN_PASSWORD=your_admin_password" >> .env

# Reference trong docker-compose.yml:
# POSTGRES_PASSWORD: ${DB_PASSWORD}
```

## 📈 Scaling Considerations

### Horizontal Scaling

```bash
# Scale analysis workers
docker-compose up -d --scale analysis-worker=3

# Load balancer configuration needed for multiple workers
# Consider using nginx or traefik
```

### Vertical Scaling

- **Database**: Increase PostgreSQL memory/CPU limits
- **Ollama**: Requires GPU scaling (multiple GPUs)
- **Redis**: Increase memory limits for larger queues
- **Analysis Worker**: Increase concurrent analysis limits

## 📞 Support & Maintenance

### Health Monitoring Script

Create automated health check:

```bash
# Save as health_monitor.bat
@echo off
cd deployment
deploy.bat health
if %errorlevel% neq 0 (
    echo ALERT: System unhealthy, restarting...
    deploy.bat stop
    timeout /t 10
    deploy.bat start
)
```

### Log Rotation

```bash
# Configure log rotation trong docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "3"
```

---

**Deployment Version**: Stories 1.1-1.3 Complete
**Last Updated**: 2025-08-12
**Maintained by**: System Architecture Team