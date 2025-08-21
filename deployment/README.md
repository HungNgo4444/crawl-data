# Production Deployment Guide

🚀 **Complete Containerized System for Stories 1.1-1.3**
AI-Powered Multi-Domain News Crawler System

## Quick Start

```bash
# Start complete system
cd deployment
deploy.bat start

# Check system health
deploy.bat health

# Stop system
deploy.bat stop
```

## System Architecture

- **Story 1.1**: PostgreSQL Database với Vietnamese domain management schema
- **Story 1.2**: Ollama GWEN-3 Model (qwen2.5:3b) cho Vietnamese content analysis
- **Story 1.3**: Domain Analysis Worker với Redis queue management

## Files Structure

- `docker-compose.yml` - Main containerization configuration
- `deploy.bat` - Deployment management script
- `init/01-init.sql` - Database initialization with Vietnamese news domains
- `migrate.sh` - Database migration script

## Access URLs

- 🔧 Analysis Worker API: http://localhost:8082/health
- 🤖 Ollama API: http://localhost:11434/api/tags
- 📊 pgAdmin: http://localhost:8080 (admin@crawler.dev / admin123)
- 🔄 Redis Commander: http://localhost:8081 (with --profile dev)

## Environment Variables

All configuration is handled through docker-compose.yml environment variables:

- `GWEN3_MODEL=qwen2.5:3b` - Vietnamese AI model
- `DB_USER=crawler_user` / `DB_PASSWORD=crawler123`
- `REDIS_URL=redis://redis:6379`

## Available Commands

```bash
deploy.bat help       # Show help menu
deploy.bat start      # Start complete containerized system
deploy.bat stop       # Stop all containers
deploy.bat health     # Check all service health status
deploy.bat logs       # Show recent logs from all services
deploy.bat setup-db   # Setup database with Vietnamese domains
deploy.bat clean      # Clean up containers and volumes
```

## Testing the System

### 1. Trigger Vietnamese Content Analysis

```bash
# Test VNExpress.net analysis
curl -X POST "http://localhost:8082/trigger/5ca6f1b9-ee1a-4df7-89d7-e3a3d04e4faf"
```

### 2. Check Job Status

```bash
# Get job status
curl "http://localhost:8082/jobs/{job_id}/status"
```

### 3. Monitor System Health

```bash
# Analysis Worker health
curl "http://localhost:8082/health"

# Service statistics
curl "http://localhost:8082/stats"
```

## Troubleshooting

### Container Issues
- Wait for all services to be healthy: `deploy.bat health`
- Check logs: `deploy.bat logs`

### Model Issues
- Ensure qwen2.5:3b model is downloaded: `docker exec crawler_ollama ollama list`
- Download model if missing: `docker exec crawler_ollama ollama pull qwen2.5:3b`

### Database Issues
- Reset database: `deploy.bat setup-db`
- Check PostgreSQL logs: `docker-compose logs postgres`

## Development Mode

```bash
# Include Redis Commander for queue management
docker-compose --profile dev up -d

# Include monitoring (Prometheus + Grafana)
docker-compose --profile monitoring up -d

# Include admin tools (pgAdmin)
docker-compose --profile admin up -d
```