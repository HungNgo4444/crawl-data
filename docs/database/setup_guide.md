# PostgreSQL Setup Guide

## 1. Install PostgreSQL

### Windows:
1. Download PostgreSQL từ https://www.postgresql.org/download/windows/
2. Install với default settings
3. Ghi nhớ password cho postgres user
4. Add PostgreSQL bin directory vào PATH

### Using Docker (Recommended):
```bash
# Pull PostgreSQL 15 image
docker pull postgres:15

# Run PostgreSQL container
docker run --name crawler_postgres \
  -e POSTGRES_DB=crawler_db \
  -e POSTGRES_USER=crawler_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  -d postgres:15

# Verify container is running
docker ps
```

## 2. Set Environment Variables

Tạo file `.env` trong project root:

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crawler_db
DB_USER=crawler_user
DB_PASSWORD=your_password
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

## 3. Test Connection

### Using psql command line:
```bash
psql -h localhost -p 5432 -U crawler_user -d crawler_db
```

### Using migration script:
```bash
cd "F:\Crawl data"
bash infrastructure/scripts/migrate.sh test
```

## 4. Run Migrations

```bash
# Run all migrations
bash infrastructure/scripts/migrate.sh up

# Check migration status
bash infrastructure/scripts/migrate.sh status
```

## 5. Connect with GUI Tools

### pgAdmin (Recommended):
1. Download từ https://www.pgadmin.org/
2. Add new server connection:
   - Host: localhost
   - Port: 5432
   - Database: crawler_db
   - Username: crawler_user

### DBeaver (Free):
1. Download từ https://dbeaver.io/
2. Create new PostgreSQL connection
3. Use same connection parameters

## 6. Verify Schema

After running migrations, check tables exist:

```sql
-- List all tables
\dt

-- Check domain_configurations structure
\d domain_configurations

-- View some sample data
SELECT * FROM domain_configurations LIMIT 5;

-- Check indexes
\di
```

## 7. Load Sample Data

```bash
# Migrations include seed data, but you can also run manually:
psql -h localhost -p 5432 -U crawler_user -d crawler_db \
  -f config/database/migrations/004_initial_seed_data.sql
```

## Troubleshooting

### Connection Issues:
- Check PostgreSQL service is running
- Verify firewall allows port 5432
- Check username/password correct

### Permission Issues:
```sql
-- Grant permissions if needed
GRANT ALL PRIVILEGES ON DATABASE crawler_db TO crawler_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO crawler_user;
```