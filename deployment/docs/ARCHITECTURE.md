# 🏗️ System Architecture Documentation

## 📋 Overview

AI-Powered Multi-Domain News Crawler System - Complete containerized architecture cho Stories 1.1-1.3.

## 🎯 Design Principles

- **Containerization**: Mọi component chạy trong Docker containers
- **Service Isolation**: Mỗi service có container riêng biệt
- **Vietnamese Focus**: Optimized cho Vietnamese news content analysis
- **Scalability**: Ready để scale horizontally
- **Observability**: Built-in monitoring và logging

## 🧩 Component Architecture

### Story 1.1: Database Schema Foundation

```
┌─────────────────────────────────────────────┐
│            PostgreSQL Container             │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │        Domain Management            │   │
│  │                                     │   │
│  │  • domain_configurations           │   │
│  │  • domain_parsing_templates        │   │
│  │  • crawler_strategy_stats          │   │
│  │  • analysis_queue_entries          │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Vietnamese News Domains:                  │
│  • VNExpress.net                          │
│  • DanTri.com.vn                          │
│  • CafeF.vn                              │
│  • TuoiTre.vn                            │
└─────────────────────────────────────────────┘
```

**Technical Stack:**
- PostgreSQL 15 Alpine
- UTF-8 encoding với Vietnamese collation
- Automated schema migrations
- Health checks với pg_isready

### Story 1.2: GWEN-3 Model Deployment

```
┌─────────────────────────────────────────────┐
│             Ollama Container                │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         qwen2.5:3b Model            │   │
│  │                                     │   │
│  │  • Vietnamese language optimized   │   │
│  │  • 3B parameters                   │   │
│  │  • GPU acceleration (GTX 1650)     │   │
│  │  • Memory efficient                │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  API Endpoints:                            │
│  • /api/generate - Content analysis       │
│  • /api/tags - Model management           │
│  • /api/show - Model info                 │
└─────────────────────────────────────────────┘
```

**Technical Stack:**
- Ollama latest image
- NVIDIA GPU support (GTX 1650 optimized)
- Memory limits: 6GB
- Model persistence với volumes
- Health checks với API endpoints

### Story 1.3: Domain Analysis Worker

```
┌─────────────────────────────────────────────┐
│           Analysis Worker Container          │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         FastAPI Service             │   │
│  │                                     │   │
│  │  • Vietnamese content analysis     │   │
│  │  • Template generation             │   │
│  │  • Queue job processing            │   │
│  │  • Health monitoring               │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  Worker Components:                        │
│  • DomainAnalysisTrigger               │
│  • RedisQueueManager                   │
│  • RealDatabaseClient                 │
│  • GWEN3Client                        │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│              Redis Container                │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         Queue Management            │   │
│  │                                     │   │
│  │  • Analysis job queue              │   │
│  │  • Job status tracking             │   │
│  │  • Worker coordination             │   │
│  │  • Persistence với AOF             │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**Technical Stack:**
- Python 3.11 với FastAPI
- Redis 7 Alpine với persistence
- Async/await pattern
- Real-time job processing
- Comprehensive health checks

## 🔄 Data Flow Architecture

### Analysis Request Flow

```
1. API Request
   ↓
2. DomainAnalysisTrigger
   ↓
3. Domain Validation
   ↓
4. Redis Queue Enqueue
   ↓
5. Analysis Worker Processing
   ↓
6. GWEN-3 Content Analysis
   ↓
7. Template Generation
   ↓
8. PostgreSQL Storage
   ↓
9. Response với Job ID
```

### Vietnamese Content Processing

```
1. URL Fetch
   ↓
2. Content Extraction
   ↓
3. Vietnamese Detection
   ↓
4. GWEN-3 Analysis
   ↓
5. Parsing Template Creation
   ↓
6. Confidence Scoring
   ↓
7. Database Persistence
```

## 🌐 Network Architecture

### Container Networking

```
crawler-system (bridge network)
│
├── crawler_postgres:5432
├── crawler_ollama:11434
├── crawler_analysis_worker:8080
├── crawler_redis:6379
├── crawler_pgadmin:80
├── crawler_redis_commander:8081
├── crawler_prometheus:9090
└── crawler_grafana:3000
```

### Service Communication

- **Sync Communication**: HTTP/REST APIs
- **Async Communication**: Redis pub/sub
- **Database Access**: PostgreSQL connections
- **Model Access**: Ollama API calls

### External Access Ports

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| PostgreSQL | 5432 | 5432 | Database access |
| Ollama | 11434 | 11434 | Model API |
| Analysis Worker | 8080 | 8082 | REST API |
| Redis | 6379 | 6379 | Queue access |
| pgAdmin | 80 | 8080 | DB management |
| Redis Commander | 8081 | 8081 | Queue management |

## 💾 Data Architecture

### Database Schema

```sql
-- Domain management
domain_configurations (
    id UUID PRIMARY KEY,
    domain_name VARCHAR(255),
    base_url TEXT,
    status VARCHAR(50),
    crawl_frequency_hours INTEGER
)

-- Parsing templates
domain_parsing_templates (
    id UUID PRIMARY KEY,
    domain_config_id UUID REFERENCES domain_configurations(id),
    template_data JSONB,
    confidence_score DECIMAL(5,4),
    is_active BOOLEAN
)

-- Analysis tracking
analysis_queue_entries (
    id UUID PRIMARY KEY,
    domain_config_id UUID,
    job_id VARCHAR(255),
    trigger_source VARCHAR(100),
    status VARCHAR(50)
)

-- Performance tracking
crawler_strategy_stats (
    id UUID PRIMARY KEY,
    domain_name VARCHAR(255),
    strategy_type VARCHAR(100),
    success_rate DECIMAL(5,4),
    avg_processing_time_ms INTEGER
)
```

### Redis Data Structures

```
# Job queue
analysis_jobs:{domain_id} → Job data (JSON)

# Job status tracking  
job_status:{job_id} → Status info (Hash)

# Queue statistics
queue_stats → Metrics data (Hash)

# Worker heartbeat
worker_heartbeat:{worker_id} → Timestamp
```

### Volume Persistence

```
postgres_data/       # PostgreSQL database files
ollama_models/       # GWEN-3 model files (3GB+)  
redis_data/          # Redis AOF persistence
pgadmin_data/        # pgAdmin configuration
prometheus_data/     # Metrics history
grafana_data/        # Dashboard settings
```

## ⚡ Performance Architecture

### Resource Allocation

```yaml
PostgreSQL:
  memory: 1GB
  cpu: 1.0
  storage: 10GB

Ollama (GTX 1650):
  memory: 6GB (GPU constraint)
  cpu: 4.0
  gpu: 1x GTX 1650

Analysis Worker:
  memory: 1GB
  cpu: 2.0
  concurrent_jobs: 3

Redis:
  memory: 512MB
  cpu: 0.5
  persistence: AOF
```

### Scalability Patterns

**Horizontal Scaling:**
- Multiple Analysis Worker instances
- Load balancing với nginx/traefik
- Database read replicas
- Redis clustering

**Vertical Scaling:**
- Increase memory/CPU limits
- GPU upgrades cho Ollama
- SSD storage cho database

### Caching Strategy

```
# Application Level
- Template caching trong Analysis Worker
- Domain configuration caching
- Model response caching

# Redis Level  
- Job result caching
- Frequently accessed domain configs
- Analysis statistics
```

## 🛡️ Security Architecture

### Network Security

```
External Traffic → Reverse Proxy → Internal Services
                     │
                     ├── Rate limiting
                     ├── SSL termination
                     └── Authentication
```

### Container Security

- Non-root user execution
- Minimal base images (Alpine)
- Security scanning với Docker Scout
- Regular image updates

### Data Security

- Encrypted database connections
- Secure credential management
- Environment variable secrets
- Volume encryption (production)

## 📊 Monitoring Architecture

### Health Checks

```python
# Service health endpoints
GET /health           # Overall system health
GET /health/live      # Kubernetes liveness
GET /health/ready     # Kubernetes readiness
GET /metrics          # Prometheus metrics
```

### Observability Stack

```
Application → Prometheus → Grafana → Dashboards
              │
              ├── System metrics
              ├── Business metrics  
              └── Performance metrics
```

### Logging Strategy

```
Container Logs → Docker logging driver → Log aggregation
                │
                ├── JSON structured logs
                ├── Log rotation (100MB, 3 files)
                └── Centralized collection
```

## 🔧 Configuration Architecture

### Environment-based Config

```bash
# Development
ENVIRONMENT=development
LOG_LEVEL=DEBUG
METRICS_ENABLED=true

# Production  
ENVIRONMENT=production
LOG_LEVEL=INFO
SECURITY_HARDENING=true
```

### Service Discovery

```yaml
# Internal DNS resolution
postgres:5432       # Database service
ollama:11434        # Model service  
redis:6379          # Queue service
analysis-worker:8080 # API service
```

### Configuration Management

- Docker Compose environment variables
- External `.env` files cho sensitive data
- ConfigMaps cho Kubernetes deployment
- Secrets management với external systems

---

**Architecture Version**: Stories 1.1-1.3 Complete
**Last Updated**: 2025-08-12
**Architecture Review**: Quarterly