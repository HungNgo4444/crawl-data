# 🚀 AI-Powered Vietnamese News Crawler System

> **Complete containerized system for Stories 1.1-1.3: Database Foundation, GWEN-3 Model Deployment, and Domain Analysis Worker**

[![Container Status](https://img.shields.io/badge/containers-ready-green.svg)](http://localhost:8082/health)
[![GWEN-3 Model](https://img.shields.io/badge/gwen--3-qwen2.5:3b-blue.svg)](http://localhost:11434/api/tags)
[![Stories Complete](https://img.shields.io/badge/stories-1.1--1.3-success.svg)](#development-status)

## 🎯 **Quick Start - Complete System**

### Windows:
```bash
# Start complete AI crawler system (Stories 1.1-1.3)
./dev-commands.bat dev-start

# Check system health
./dev-commands.bat health

# Setup database với Vietnamese domains
./dev-commands.bat setup-db

# Run tests
./dev-commands.bat test

# Stop system
./dev-commands.bat dev-stop
```

### Unix/Linux:
```bash
# Start complete system
docker-compose up -d

# Check health
docker-compose ps

# View logs
docker-compose logs -f
```

## 🏗️ **Complete Container Architecture (Stories 1.1-1.3)**

### ✅ **Story 1.1: Database Schema Foundation**
- **PostgreSQL** (`crawler_postgres`): Port 5432
- **pgAdmin** (optional): Port 8080 - Database management interface

### ✅ **Story 1.2: GWEN-3 Model Deployment**  
- **Ollama** (`crawler_ollama`): Port 11434 - Vietnamese AI analysis model
- **GPU Support**: GTX 1650 4GB optimized

### ✅ **Story 1.3: Domain Analysis Worker**
- **Analysis Worker** (`crawler_analysis_worker`): Port 8082 - Main analysis service
- **Redis** (`crawler_redis`): Port 6379 - Queue management

### 🛠️ **Development Tools**
- **Redis Commander**: Port 8081 (`--profile dev`)
- **Prometheus**: Port 9090 (`--profile monitoring`)
- **Grafana**: Port 3000 (`--profile monitoring`)

## 📊 **Service URLs**

| Service | URL | Purpose |
|---------|-----|---------|
| Analysis Worker API | http://localhost:8082/health | Health check & API |
| GWEN-3 Ollama | http://localhost:11434/api/version | AI model API |
| pgAdmin | http://localhost:8080 | Database management |
| Redis Commander | http://localhost:8081 | Queue management |
| Prometheus | http://localhost:9090 | Metrics collection |
| Grafana | http://localhost:3000 | Visualization |

**Login Credentials:**
- pgAdmin: `admin@crawler.dev` / `admin123`
- Grafana: `admin` / `admin`

## 📁 **Project Structure (Organized)**

```
📦 AI-Powered Multi-Domain News Crawler
├── 🐳 docker-compose.yml          # Complete system container orchestration
├── ⚡ dev-commands.bat           # Windows development commands
├── ⚡ Makefile                  # Unix/Linux development commands  
├── 📖 README.md                 # This file
├── 
├── 🚀 apps/
│   ├── analysis_worker/         ✅ Story 1.3 - Analysis Worker
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml   # Individual service compose (legacy)
│   │   ├── src/                 # Analysis worker source code
│   │   └── tests/               # Comprehensive test suite
│   └── _future/                 📋 Future stories (1.4-1.8)
│       ├── domain_api/          📝 Story 1.5 (Domain Management API)
│       └── enhanced_crawler/    📝 Story 1.4 (Enhanced Crawler)
├── 
├── 🗄️ deployment/               ✅ Story 1.1 - Database deployment
│   ├── docker-compose.yml       # Legacy database compose
│   ├── migrations/              # Database schema migrations
│   └── init/                    # Database initialization
├── 
├── 📚 docs/                     📖 Complete system documentation
│   ├── stories/                 # Story specifications (1.1-1.3 ✅)
│   ├── architecture/            # System architecture docs
│   └── deployment/              # Deployment guides
├── 
├── ⚙️ config/                   🛠️ Configuration files
│   ├── database/                # Database configs
│   └── gwen3/                   # GWEN-3 model configs
├── 
└── 🗂️ archived/                📦 Cleaned up files (Phase 1)
    ├── moved-20250812/          # Duplicate files removed
    └── unused-gwen3_client/     # Old client implementation
```

## 🚧 **Development Status - Stories 1.1-1.3**

| Story | Title | Status | Container | Port | Notes |
|-------|-------|--------|-----------|------|-------|
| **1.1** | Database Schema Foundation | ✅ **COMPLETE** | crawler_postgres | 5432 | PostgreSQL với Vietnamese domains |
| **1.2** | GWEN-3 Model Deployment | ✅ **COMPLETE** | crawler_ollama | 11434 | Ollama với qwen2.5:3b |
| **1.3** | Domain Analysis Worker | ✅ **COMPLETE** | crawler_analysis_worker | 8082 | Redis queue + Analysis API |
| 1.4 | Enhanced Crawler | 📋 Ready for Dev | TBD | TBD | Template-based crawling |
| 1.5 | Domain Management API | 📋 Ready for Dev | TBD | 8000 | FastAPI với WebSocket |
| 1.6 | React Admin Interface | 📋 Ready for Dev | TBD | 3000 | TypeScript + Material-UI |
| 1.7 | Monitoring Stack | 📋 Ready for Dev | TBD | 9090 | Prometheus/Grafana |
| 1.8 | Integration Testing | 📋 Ready for Dev | TBD | - | E2E testing suite |

## 🧪 **Testing & Validation**

```bash
# Complete system health check
./dev-commands.bat health

# Run analysis worker tests
./dev-commands.bat test

# Test individual components
docker-compose exec analysis-worker pytest tests/unit/ -v
docker-compose exec analysis-worker pytest tests/integration/ -v
docker-compose exec analysis-worker pytest tests/performance/ -v

# Database validation
docker-compose exec postgres psql -U crawler_user -d crawler_db -c "\dt"
```

## 🔧 **Development Commands**

### Windows (dev-commands.bat):
| Command | Purpose |
|---------|---------|
| `./dev-commands.bat help` | Show all available commands |
| `./dev-commands.bat dev-start` | Start complete system (Stories 1.1-1.3) |
| `./dev-commands.bat health` | Health check all services |
| `./dev-commands.bat setup-db` | Setup Vietnamese domains database |
| `./dev-commands.bat logs` | View system logs |
| `./dev-commands.bat dev-stop` | Stop all containers |
| `./dev-commands.bat clean` | Clean containers và volumes |

### Unix/Linux (docker-compose):
```bash
# Basic operations
docker-compose up -d                    # Start all services
docker-compose down                     # Stop all services  
docker-compose ps                       # Show service status
docker-compose logs -f [service]        # View logs

# With profiles
docker-compose --profile dev up -d      # Include Redis Commander
docker-compose --profile monitoring up # Include Prometheus/Grafana
docker-compose --profile admin up      # Include pgAdmin
```

## 🗄️ **Database Management**

```bash
# Setup Vietnamese news domains
./dev-commands.bat setup-db

# Connect to database
docker-compose exec postgres psql -U crawler_user -d crawler_db

# Run specific migration
docker-compose exec postgres psql -U crawler_user -d crawler_db -f /docker-entrypoint-initdb.d/01-init.sql

# Check tables
docker-compose exec postgres psql -U crawler_user -d crawler_db -c "\dt"
```

## 📊 **System Monitoring**

### Health Checks:
- **System**: `./dev-commands.bat health`
- **Analysis Worker**: http://localhost:8082/health
- **Database**: `docker-compose exec postgres pg_isready -U crawler_user`
- **GWEN-3 Model**: http://localhost:11434/api/version
- **Redis Queue**: `docker-compose exec redis redis-cli ping`

### Logs:
```bash
# All services
./dev-commands.bat logs

# Individual services
docker-compose logs postgres
docker-compose logs ollama  
docker-compose logs analysis-worker
docker-compose logs redis
```

## 🎯 **Key Features Implemented**

### ✅ **Story 1.1 Features:**
- PostgreSQL 15+ với JSONB support
- Domain management schema (domain_configurations, domain_parsing_templates, domain_analysis_queue)
- Connection pooling optimized for 16GB RAM constraint
- Migration framework với rollback support
- Vietnamese news domain seed data (8 major sites)

### ✅ **Story 1.2 Features:**  
- Ollama container với GWEN-3 8B model (qwen2.5:3b)
- GPU support for GTX 1650 4GB
- Memory optimization (8GB constraint)
- Health checking và auto-restart
- Vietnamese content analysis capabilities

### ✅ **Story 1.3 Features:**
- Redis-based queue management
- Async analysis worker với FastAPI integration  
- GWEN-3 model integration
- Comprehensive error handling và retry logic
- Health check API endpoints
- Development hot reload support

## 🎉 **Containerization Complete**

**Stories 1.1-1.3 are fully containerized và functional!**

✅ **Database Schema Foundation** - PostgreSQL với Vietnamese domains  
✅ **GWEN-3 Model Deployment** - Ollama với AI analysis  
✅ **Domain Analysis Worker** - Redis queue + Analysis API  

**Next Phase:** Stories 1.4-1.8 containerization

## 🤝 **Contributing**

1. **Start system**: `./dev-commands.bat dev-start`
2. **Check health**: `./dev-commands.bat health`  
3. **Make changes** in respective `apps/` folders
4. **Test changes**: `./dev-commands.bat test`
5. **View logs**: `./dev-commands.bat logs`

---

**📧 Author:** James (Full Stack Developer) - Container System Architect  
**📅 Date:** 2025-08-12  
**🔗 Stories:** 1.1-1.3 Complete Container Implementation