# 🗄️ Database Access Guide

## 📊 pgAdmin Web Interface

### Access URL
**http://localhost:8080**

### Login Credentials
- **Email**: `admin@crawler.dev`
- **Password**: `admin123`

### First-time Setup

1. **Access pgAdmin**
   ```
   Browser → http://localhost:8080
   Login với credentials trên
   ```

2. **Add Server Connection**
   ```
   Right-click "Servers" → Create → Server
   
   General Tab:
   - Name: "Crawler Database"
   
   Connection Tab:
   - Host name: "postgres" (internal Docker network)
   - Port: 5432
   - Maintenance database: "crawler_db"
   - Username: "crawler_user" 
   - Password: "crawler123"
   
   Click "Save"
   ```

3. **Browse Database**
   ```
   Servers → Crawler Database → Databases → crawler_db
   
   Tables:
   ├── domain_configurations (Vietnamese news sites)
   ├── domain_parsing_templates (AI analysis results)  
   ├── analysis_queue_entries (Job tracking)
   └── crawler_strategy_stats (Performance metrics)
   ```

## 🖥️ Command Line Access

### Direct PostgreSQL Connection

```bash
# From host machine
psql -h localhost -p 5432 -U crawler_user -d crawler_db

# From inside container
docker exec -it crawler_postgres psql -U crawler_user -d crawler_db
```

### Quick Database Queries

```sql
-- Check Vietnamese news domains
SELECT domain_name, base_url, status, created_at 
FROM domain_configurations 
ORDER BY created_at DESC;

-- Check analysis results
SELECT 
    dc.domain_name,
    dpt.confidence_score,
    dpt.created_at,
    dpt.template_data->>'language_detected' as language
FROM domain_parsing_templates dpt
JOIN domain_configurations dc ON dpt.domain_config_id = dc.id
ORDER BY dpt.created_at DESC
LIMIT 10;

-- Check queue status
SELECT 
    aqe.job_id,
    dc.domain_name,
    aqe.status,
    aqe.trigger_source,
    aqe.created_at
FROM analysis_queue_entries aqe
JOIN domain_configurations dc ON aqe.domain_config_id = dc.id
ORDER BY aqe.created_at DESC
LIMIT 10;
```

## 🔍 Database Schema Details

### Vietnamese News Domains

```sql
-- VNExpress.net
SELECT * FROM domain_configurations 
WHERE domain_name = 'vnexpress.net';

-- Expected result:
-- id: 5ca6f1b9-ee1a-4df7-89d7-e3a3d04e4faf
-- domain_name: vnexpress.net
-- base_url: https://vnexpress.net
-- status: ACTIVE
```

### Analysis Templates

```sql
-- Latest analysis templates
SELECT 
    dc.domain_name,
    dpt.template_data->>'headline_selectors' as headlines,
    dpt.template_data->>'content_selectors' as content,
    dpt.confidence_score
FROM domain_parsing_templates dpt
JOIN domain_configurations dc ON dpt.domain_config_id = dc.id
WHERE dpt.is_active = true;
```

## 🚨 pgAdmin Troubleshooting

### Issue: pgAdmin not accessible

**Solution 1: Check container status**
```bash
docker-compose ps pgadmin
# Should show "Up" status

# If not running:
docker-compose up -d pgadmin
```

**Solution 2: Check port binding**
```bash
netstat -an | findstr :8080
# Should show port 8080 listening

# If port conflict, edit docker-compose.yml:
# ports: - "8081:80"  # Change external port
```

**Solution 3: Reset pgAdmin container**
```bash
docker-compose stop pgadmin
docker-compose rm -f pgadmin
docker-compose up -d pgadmin
```

### Issue: Cannot connect to database from pgAdmin

**Solution 1: Use correct host name**
- ❌ Wrong: `localhost` or `127.0.0.1`  
- ✅ Correct: `postgres` (Docker internal network)

**Solution 2: Check database container**
```bash
docker exec -it crawler_postgres psql -U crawler_user -d crawler_db
# If this works, pgAdmin connection should work
```

**Solution 3: Check network connectivity**
```bash
# From pgAdmin container
docker exec -it crawler_pgadmin ping postgres
# Should be able to ping postgres container
```

## 📋 Database Backup & Restore

### Backup Database

```bash
# Complete backup
docker exec crawler_postgres pg_dump -U crawler_user crawler_db > backup_$(date +%Y%m%d).sql

# Schema only  
docker exec crawler_postgres pg_dump -U crawler_user -s crawler_db > schema_backup.sql

# Data only
docker exec crawler_postgres pg_dump -U crawler_user -a crawler_db > data_backup.sql
```

### Restore Database

```bash
# Restore complete backup
docker exec -i crawler_postgres psql -U crawler_user crawler_db < backup_file.sql

# Restore schema only
docker exec -i crawler_postgres psql -U crawler_user crawler_db < schema_backup.sql
```

## 🔒 Security Notes

### Production Hardening

```bash
# Change default passwords trong docker-compose.yml
POSTGRES_PASSWORD: ${DB_PASSWORD}
PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}

# Use .env file
echo "DB_PASSWORD=your_secure_password" > .env  
echo "PGADMIN_PASSWORD=your_admin_password" >> .env
```

### Access Control

```sql
-- Check current user permissions
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole 
FROM pg_roles 
WHERE rolname = 'crawler_user';

-- Grant specific permissions only
GRANT SELECT, INSERT, UPDATE ON domain_configurations TO crawler_user;
```

## 📊 Database Monitoring

### Performance Queries

```sql
-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Active connections
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start
FROM pg_stat_activity 
WHERE state = 'active';

-- Database statistics
SELECT 
    datname,
    numbackends,
    xact_commit,
    xact_rollback,
    blks_read,
    blks_hit
FROM pg_stat_database 
WHERE datname = 'crawler_db';
```

---

**Database Access**: PostgreSQL 15 với pgAdmin 4
**Last Updated**: 2025-08-12