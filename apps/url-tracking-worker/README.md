# URL Tracking Worker

Automated service for monitoring domains and populating the url_tracking table.

## Features

- **Automated Monitoring**: Scheduled monitoring of active domains
- **URL Extraction**: Extract article URLs from RSS feeds, sitemaps, category pages, homepage
- **Deduplication**: Multi-level URL deduplication (in-memory + database)
- **Scalable**: Configurable batch processing and worker threads
- **Docker Ready**: Full containerization with health checks

## Architecture

```
DatabaseManager → get_domains_for_monitoring()
       ↓
URLExtractor → extract_article_urls_from_domain_data()
       ↓
DomainMonitor → monitor_all_domains()
       ↓  
MonitoringScheduler → schedule jobs every X minutes
       ↓
url_tracking table ← bulk_add_urls_to_tracking()
```

## Configuration

Environment variables:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=crawler_user
DB_PASSWORD=crawler123
DB_NAME=crawler_db

# Monitoring
MONITORING_INTERVAL_MINUTES=15
BATCH_SIZE=10
MAX_WORKERS=4
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3

# Logging
LOG_LEVEL=INFO
ENABLE_LOGGING=true
```

## Deployment

### Docker Compose (Recommended)

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f url-tracking-worker

# Stop
docker-compose down
```

### Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Run worker
python -m src.main
```

## Monitoring

The worker provides:

- **Health checks**: Container health monitoring
- **Logging**: Detailed monitoring logs
- **Statistics**: Domain and URL tracking stats
- **Manual triggers**: On-demand monitoring runs

## Integration

Integrates with:

- **domains table**: Reads analysis data (rss_feeds, sitemaps, etc.)
- **url_tracking table**: Writes discovered URLs
- **newspaper4k**: Article URL extraction
- **APScheduler**: Automated scheduling

## Flow

1. **Scheduler** triggers monitoring every X minutes
2. **DatabaseManager** gets domains with analysis data
3. **URLExtractor** extracts URLs from RSS/sitemaps/categories/homepage
4. **DomainMonitor** processes all domains in batch
5. **URLs** are deduplicated and inserted into url_tracking table
6. **Timestamps** updated for tracking last monitoring

## Example Output

```
2025-08-28 10:00:01 - INFO - Starting scheduled domain monitoring job
2025-08-28 10:00:02 - INFO - Found 25 domains for monitoring
2025-08-28 10:00:05 - INFO - Domain vnexpress.net: found 47 URLs, added 12 new URLs
2025-08-28 10:00:08 - INFO - Domain dantri.com.vn: found 33 URLs, added 8 new URLs
2025-08-28 10:02:15 - INFO - Monitoring cycle completed: 25/25 domains processed
```