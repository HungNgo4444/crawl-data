# ⚡ Quick Start Guide

## 🚀 5-Minute Deployment

### Step 1: Prerequisites Check
```bash
# Ensure Docker running
docker --version
docker-compose --version

# Check available ports
netstat -an | findstr ":5432 :6379 :8080 :8082 :11434"
```

### Step 2: Deploy System
```bash
# Navigate to deployment
cd F:\Crawl data\deployment

# Start all services  
deploy.bat start

# Wait 2-3 minutes for services to initialize
```

### Step 3: Verify Deployment
```bash
# Check all services healthy
deploy.bat health

# Expected output:
# ✅ PostgreSQL - Port 5432 (UP)
# ✅ Ollama GWEN-3 - Port 11434 (UP)  
# ✅ Analysis Worker - Port 8082 (UP)
# ✅ Redis Queue - Port 6379 (UP)
```

### Step 4: Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| 🔧 Analysis Worker | http://localhost:8082/health | None |
| 📊 Database Admin | http://localhost:8080 | admin@crawler.dev / admin123 |
| 🤖 AI Model API | http://localhost:11434/api/tags | None |

### Step 5: Test Vietnamese Analysis
```bash
# Test VNExpress analysis
curl -X POST "http://localhost:8082/trigger/5ca6f1b9-ee1a-4df7-89d7-e3a3d04e4faf"

# Expected: {"success": true, "job_id": "..."}
```

## 🎯 Common Use Cases

### Database Access
```bash
# pgAdmin Web Interface
Browser → http://localhost:8080
Login: admin@crawler.dev / admin123

# Add server connection:
Host: postgres
Port: 5432  
Database: crawler_db
User: crawler_user
Password: crawler123
```

### View Analysis Results
```bash
# Check job status
curl "http://localhost:8082/jobs/{job_id}/status"

# View system stats
curl "http://localhost:8082/stats"

# Monitor logs
deploy.bat logs
```

### Troubleshooting
```bash
# If any service fails:
deploy.bat stop
deploy.bat start
deploy.bat health

# Reset database:
deploy.bat setup-db

# View detailed logs:
docker-compose logs [service-name]
```

## 🛑 Stop System
```bash
# Graceful shutdown
deploy.bat stop

# Complete cleanup (removes data!)
deploy.bat clean
```

---

**Total setup time**: ~5 minutes
**System ready**: When all health checks pass ✅