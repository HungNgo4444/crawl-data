# 🚀 Analysis Worker Setup Guide - Story 1.3
## Cách chạy và tương tác với Vietnamese Domain Analysis Worker

---

## 📋 Yêu cầu hệ thống

### Minimum Requirements:
- **Docker:** >= 20.10
- **Docker Compose:** >= 2.0
- **RAM:** >= 8GB (cho GWEN-3 model)
- **Disk:** >= 10GB free space
- **CPU:** >= 4 cores (recommended)

### Recommended Requirements:
- **RAM:** >= 16GB
- **CPU:** >= 8 cores
- **SSD:** >= 20GB free space

---

## 🏗️ Cài đặt và chạy

### 1. Clone và setup môi trường

```bash
# Di chuyển vào thư mục analysis worker
cd "F:\Crawl data\apps\analysis_worker"

# Tạo file environment variables
cp .env.example .env

# Chỉnh sửa .env file nếu cần
notepad .env
```

### 2. Chạy toàn bộ stack (Production Mode)

```bash
# Chạy tất cả services cần thiết
docker-compose up -d

# Kiểm tra status
docker-compose ps

# Xem logs
docker-compose logs -f analysis-worker
```

### 3. Chạy với monitoring (Development Mode)

```bash
# Chạy với Prometheus và Grafana
docker-compose --profile monitoring up -d

# Chạy với Redis Commander
docker-compose --profile dev up -d
```

### 4. Setup GWEN-3 Model

```bash
# Vào container Ollama
docker exec -it analysis-ollama bash

# Download GWEN-3 model (có thể mất 10-20 phút)
ollama pull gwen-3:8b

# Verify model đã được tải
ollama list
```

---

## 🌐 Các service endpoints

| Service | URL | Mô tả |
|---------|-----|-------|
| **Analysis Worker API** | http://localhost:8080 | Main worker service |
| **Health Check** | http://localhost:8080/health | Worker health status |
| **Metrics** | http://localhost:8080/metrics | Prometheus metrics |
| **Redis Commander** | http://localhost:8081 | Queue management UI |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **Grafana** | http://localhost:3000 | Metrics visualization |
| **PostgreSQL** | localhost:5432 | Database access |
| **Redis** | localhost:6379 | Queue access |
| **Ollama/GWEN-3** | http://localhost:11434 | AI model API |

---

## 🎯 Cách tương tác với Analysis Worker

### 1. Kiểm tra health status

```bash
# Kiểm tra worker health
curl http://localhost:8080/health

# Kiểm tra component status
curl http://localhost:8080/health/detailed
```

### 2. Trigger phân tích domain

```bash
# Trigger phân tích domain VnExpress
curl -X POST http://localhost:8080/api/v1/analysis/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "domain_config_id": "vnexpress-config",
    "domain_name": "vnexpress.net",
    "base_url": "https://vnexpress.net",
    "trigger_source": "manual"
  }'

# Trigger phân tích domain Dantri
curl -X POST http://localhost:8080/api/v1/analysis/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "domain_config_id": "dantri-config", 
    "domain_name": "dantri.com.vn",
    "base_url": "https://dantri.com.vn",
    "trigger_source": "manual"
  }'
```

### 3. Kiểm tra queue status

```bash
# Xem queue statistics
curl http://localhost:8080/api/v1/queue/stats

# Xem worker statistics  
curl http://localhost:8080/api/v1/worker/stats
```

### 4. Xem kết quả phân tích

```bash
# Lấy kết quả phân tích theo job ID
curl http://localhost:8080/api/v1/analysis/result/{job_id}

# Lấy danh sách phân tích gần đây
curl http://localhost:8080/api/v1/analysis/recent?limit=10
```

---

## 📊 Monitoring và debugging

### 1. Xem logs realtime

```bash
# Worker logs
docker-compose logs -f analysis-worker

# Redis logs
docker-compose logs -f redis

# Database logs  
docker-compose logs -f postgres

# GWEN-3 logs
docker-compose logs -f ollama
```

### 2. Redis Commander (Queue Management)

1. Mở http://localhost:8081
2. Xem queues:
   - `domain_analysis_queue` - Main queue
   - `domain_analysis_retry_queue` - Retry queue
   - `domain_analysis_failed_queue` - Failed jobs
   - `domain_analysis_delayed_retry` - Scheduled retries

### 3. Grafana Dashboard

1. Mở http://localhost:3000
2. Login: admin/admin
3. Import dashboard: `config/grafana/dashboards/analysis-worker.json`

### 4. Database access

```bash
# Connect to PostgreSQL
docker exec -it analysis-postgres psql -U crawler_user -d crawler_db

# Xem tables
\dt

# Xem analysis results
SELECT * FROM domain_analysis_results ORDER BY created_at DESC LIMIT 10;

# Xem discovered URLs
SELECT * FROM discovered_urls WHERE domain_name = 'vnexpress.net';
```

---

## 🧪 Testing và validation

### 1. Chạy test suite

```bash
# Unit tests
docker-compose exec analysis-worker pytest tests/unit -v

# Integration tests  
docker-compose exec analysis-worker pytest tests/integration -v

# Performance tests
docker-compose exec analysis-worker pytest tests/performance -v -m "not slow"

# All tests
docker-compose exec analysis-worker pytest -v
```

### 2. Load testing

```bash
# Load test với 50 concurrent requests
docker-compose exec analysis-worker python scripts/load_test.py \
  --concurrent 50 \
  --duration 60 \
  --target-url http://localhost:8080

# Stress test memory usage
docker-compose exec analysis-worker python scripts/stress_test.py \
  --test-type memory \
  --iterations 100
```

### 3. Manual testing với Vietnamese sites

```bash
# Test VnExpress
curl -X POST http://localhost:8080/api/v1/analysis/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "domain_name": "vnexpress.net",
    "base_url": "https://vnexpress.net",
    "trigger_source": "test"
  }'

# Test Tuổi Trẻ  
curl -X POST http://localhost:8080/api/v1/analysis/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "domain_name": "tuoitre.vn", 
    "base_url": "https://tuoitre.vn",
    "trigger_source": "test"
  }'

# Test Thanh Niên
curl -X POST http://localhost:8080/api/v1/analysis/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "domain_name": "thanhnien.vn",
    "base_url": "https://thanhnien.vn", 
    "trigger_source": "test"
  }'
```

---

## 🔧 Configuration và customization

### 1. Environment variables

```bash
# Worker configuration
WORKER_ID=worker-custom-001
MAX_CONCURRENT_ANALYSES=5
ANALYSIS_TIMEOUT=600
POLLING_INTERVAL=5

# Performance tuning
REDIS_POOL_SIZE=20
DB_POOL_SIZE=10
HTTP_TIMEOUT=30

# Vietnamese content settings
VIETNAMESE_CONFIDENCE_THRESHOLD=0.7
CONTENT_ANALYSIS_DEPTH=deep
```

### 2. Custom Vietnamese domains

```bash
# Thêm domain configuration mới
curl -X POST http://localhost:8080/api/v1/domains/config \
  -H "Content-Type: application/json" \
  -d '{
    "domain_name": "custom-news.vn",
    "base_url": "https://custom-news.vn",
    "expected_selectors": {
      "headline": ["h1.title", ".news-title"],
      "content": [".article-content", ".news-body"],
      "category": [".category", ".section"]
    },
    "crawl_settings": {
      "max_depth": 3,
      "follow_external": false,
      "respect_robots": true
    }
  }'
```

### 3. Custom GWEN-3 prompts

```python
# File: config/gwen3/vietnamese_prompts.json
{
  "domain_analysis": {
    "system_prompt": "Bạn là chuyên gia phân tích cấu trúc website tin tức Việt Nam...",
    "analysis_prompt": "Phân tích website này và tìm các CSS selector cho...",
    "confidence_threshold": 0.8
  }
}
```

---

## 🚨 Troubleshooting

### Common Issues:

#### 1. GWEN-3 model không load được
```bash
# Kiểm tra Ollama status
docker exec -it analysis-ollama ollama list

# Re-download model
docker exec -it analysis-ollama ollama pull gwen-3:8b

# Restart Ollama
docker-compose restart ollama
```

#### 2. Redis connection errors
```bash
# Kiểm tra Redis status
docker exec -it analysis-redis redis-cli ping

# Clear Redis data
docker exec -it analysis-redis redis-cli FLUSHALL

# Restart Redis
docker-compose restart redis
```

#### 3. Database connection issues
```bash
# Kiểm tra PostgreSQL status  
docker exec -it analysis-postgres pg_isready -U crawler_user

# Reset database
docker-compose down postgres
docker volume rm analysis_postgres-data
docker-compose up -d postgres
```

#### 4. Memory issues
```bash
# Kiểm tra memory usage
docker stats

# Reduce concurrent analyses
export MAX_CONCURRENT_ANALYSES=1

# Restart with more memory
docker-compose down
docker-compose up -d
```

#### 5. Performance issues
```bash
# Enable performance profiling
export LOG_LEVEL=DEBUG
export METRICS_ENABLED=true

# Monitor với htop
docker exec -it analysis-worker htop

# Check network latency
docker exec -it analysis-worker ping redis
docker exec -it analysis-worker ping postgres
```

---

## 📈 Production deployment

### 1. Production docker-compose

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  analysis-worker:
    build: .
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
    environment:
      - LOG_LEVEL=INFO
      - METRICS_ENABLED=true
```

### 2. Scaling

```bash
# Scale workers
docker-compose up -d --scale analysis-worker=3

# Load balancer setup
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Backup và recovery

```bash
# Backup PostgreSQL
docker exec analysis-postgres pg_dump -U crawler_user crawler_db > backup.sql

# Backup Redis
docker exec analysis-redis redis-cli BGSAVE

# Restore
cat backup.sql | docker exec -i analysis-postgres psql -U crawler_user -d crawler_db
```

---

## 🎯 Kết luận

Analysis Worker Story 1.3 đã sẵn sàng cho production với:

- ✅ **Complete Docker stack** với all dependencies
- ✅ **Vietnamese content specialization** với GWEN-3
- ✅ **Comprehensive monitoring** với Prometheus/Grafana  
- ✅ **Production-ready** với health checks, scaling
- ✅ **Easy testing** với comprehensive test suite
- ✅ **Flexible configuration** cho various Vietnamese news sites

**Quick Start:**
```bash
cd "F:\Crawl data\apps\analysis_worker"
docker-compose up -d
# Wait for GWEN-3 model download (~10-20 minutes)
curl http://localhost:8080/health
```

🚀 **Ready to analyze Vietnamese news domains!**