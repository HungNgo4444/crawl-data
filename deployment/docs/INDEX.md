# 📚 AI-Powered Multi-Domain News Crawler - Documentation Index

## 🚀 Getting Started

| Document | Purpose | Audience |
|----------|---------|----------|
| [QUICK_START.md](QUICK_START.md) | 5-minute deployment guide | Everyone |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Complete deployment documentation | DevOps/Admins |
| [DATABASE_ACCESS.md](DATABASE_ACCESS.md) | pgAdmin and database access | Developers |

## 🏗️ Technical Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture và design | Architects/Engineers |

## 📋 System Overview

### Stories Implementation Status

✅ **Story 1.1**: Database Schema Foundation  
✅ **Story 1.2**: GWEN-3 Model Deployment (qwen2.5:3b)  
✅ **Story 1.3**: Domain Analysis Worker  

### Key Features

- 🇻🇳 **Vietnamese Content Analysis** với GWEN-3 AI model
- 📊 **PostgreSQL Database** với domain management schema
- ⚡ **Real-time Processing** với Redis queue management
- 🔧 **REST API** cho analysis triggers và monitoring
- 🐳 **Complete Containerization** với Docker Compose
- 📈 **Monitoring & Observability** với health checks

## 🌐 Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| Analysis Worker API | http://localhost:8082/health | System health & analysis triggers |
| pgAdmin Database | http://localhost:8080 | Database management interface |
| Ollama Model API | http://localhost:11434/api/tags | AI model management |

## 🛠️ Quick Commands

```bash
# Deployment management
deploy.bat start      # Start complete system  
deploy.bat health     # Comprehensive health check
deploy.bat stop       # Graceful shutdown
deploy.bat logs       # View service logs
deploy.bat clean      # Complete cleanup

# Testing & validation
scripts\test_system.bat    # Integration tests
scripts\health_check.bat   # Detailed health check
```

## 📊 File Structure

```
deployment/
├── docs/                          # Documentation
│   ├── INDEX.md                   # This file
│   ├── QUICK_START.md            # 5-minute setup  
│   ├── DEPLOYMENT_GUIDE.md       # Complete guide
│   ├── DATABASE_ACCESS.md        # pgAdmin usage
│   └── ARCHITECTURE.md           # Technical architecture
├── environments/                  # Environment configs
│   ├── development.yml           # Dev overrides
│   └── production.yml            # Production settings
├── scripts/                      # Management scripts  
│   ├── health_check.bat          # Health validation
│   └── test_system.bat           # Integration tests
├── init/                         # Database initialization
│   └── 01-init.sql              # Schema & Vietnamese domains
├── docker-compose.yml            # Main container config
├── deploy.bat                    # Deployment script
└── README.md                     # Quick overview
```

## 🎯 Common Use Cases

### 1. First-time Setup
1. Read [QUICK_START.md](QUICK_START.md) 
2. Run `deploy.bat start`
3. Verify with `deploy.bat health`

### 2. Development Work
1. Use development environment: `docker-compose -f docker-compose.yml -f environments/development.yml up -d`
2. Access [DATABASE_ACCESS.md](DATABASE_ACCESS.md) for pgAdmin
3. Review logs: `deploy.bat logs`

### 3. Production Deployment  
1. Review [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. Use production config: `docker-compose -f docker-compose.yml -f environments/production.yml up -d`  
3. Run integration tests: `scripts\test_system.bat`

### 4. Troubleshooting
1. Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) troubleshooting section
2. Run detailed health check: `scripts\health_check.bat`
3. View service-specific logs: `docker-compose logs [service]`

## 🔍 Vietnamese Content Analysis Testing

```bash
# Test VNExpress.net analysis
curl -X POST "http://localhost:8082/trigger/5ca6f1b9-ee1a-4df7-89d7-e3a3d04e4faf"

# Check job status  
curl "http://localhost:8082/jobs/{job_id}/status"

# View system statistics
curl "http://localhost:8082/stats"
```

## 🏷️ Version Information

- **System Version**: Stories 1.1-1.3 Complete
- **Database**: PostgreSQL 15 với Vietnamese domain schema
- **AI Model**: GWEN-3 (qwen2.5:3b) cho Vietnamese analysis
- **Queue**: Redis 7 với persistence
- **API Framework**: FastAPI với async processing
- **Containerization**: Docker Compose với health checks

## 📞 Support

### System Health Issues
- Run: `scripts\health_check.bat`
- Review: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) troubleshooting

### Database Issues  
- Guide: [DATABASE_ACCESS.md](DATABASE_ACCESS.md)
- Reset: `deploy.bat setup-db`

### Model Issues
- Check: `docker exec crawler_ollama ollama list`
- Download: `docker exec crawler_ollama ollama pull qwen2.5:3b`

### Integration Testing
- Full test suite: `scripts\test_system.bat`
- Individual service tests: `deploy.bat health`

---

**Documentation maintained by**: System Architecture Team  
**Last updated**: 2025-08-12  
**System status**: Production Ready ✅