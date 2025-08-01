# 🏛️ FINTECH CRAWLER - DOCKER WORKFLOW RULES

## 📋 **BẮT BUỘC TUÂN THỦ**

### **RULE 1: DEVELOPMENT & TESTING**
```bash
# ❌ KHÔNG BAO GIỜ chạy trực tiếp từ Windows host
python scripts/test_refactored_system.py  # ❌ FAIL

# ✅ LUÔN LUÔN deploy lên Docker trước
docker-compose up -d app
docker logs fintech_app_refactored  # ✅ SUCCESS
```

### **RULE 2: DATABASE CONNECTION**
```yaml
Windows Host Connection: ❌ KHÔNG RELIABLE
  - pg_hba.conf conflicts  
  - Authentication issues
  - Python version compatibility problems

Docker Internal Connection: ✅ PERFECT & STABLE
  - Direct network access
  - Consistent authentication  
  - Isolated environment
```

### **RULE 3: DEPLOYMENT PROCESS**
```bash
# Bước 1: Build app container
docker-compose build app

# Bước 2: Deploy services  
docker-compose up -d postgres redis app

# Bước 3: Verify logs
docker logs fintech_app_refactored

# Bước 4: Check success rate
# Target: >90% success rate trong Docker
```

### **RULE 4: DEBUGGING WORKFLOW**
```bash
# Khi có lỗi:
1. Không debug trên Windows host
2. Luôn check Docker logs first:
   docker logs fintech_app_refactored
3. Enter container để debug:
   docker exec -it fintech_app_refactored bash
4. Test commands inside container
```

### **RULE 5: PRODUCTION READINESS**
```yaml
Database: ✅ PostgreSQL trong Docker
Crawler: ✅ Playwright trong Docker  
Network: ✅ Internal Docker network
Authentication: ✅ Trust auth for containers
Monitoring: ✅ Docker logs + health checks
```

## 🎯 **CURRENT STATUS**

```yaml
Phase 1 & 2 Completion: 75% ACHIEVED
- ✅ PostgreSQL connection & storage
- ✅ Docker containerization  
- ✅ Automated table creation
- ⚠️ Minor crawler model fixes needed

Next Priority: Fix remaining 25% cho 100% success rate
```

## 🚨 **CRITICAL WARNINGS**

1. **NEVER** phát triển trực tiếp trên Windows host
2. **ALWAYS** test trong Docker environment first  
3. **MUST** use Docker logs để troubleshoot
4. **REQUIRED** 90%+ success rate trước khi deploy production

## 📞 **EMERGENCY COMMANDS**

```bash
# Reset everything nếu có vấn đề:
docker-compose down
docker-compose up -d postgres
docker exec fintech_postgres psql -U user -d app_db -c "CREATE SCHEMA IF NOT EXISTS raw_data; CREATE SCHEMA IF NOT EXISTS processed_data; CREATE SCHEMA IF NOT EXISTS system_logs;"
docker-compose up -d app
docker logs fintech_app_refactored
```