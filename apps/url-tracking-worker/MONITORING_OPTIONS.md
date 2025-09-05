# URL Tracking Worker - Monitoring Options

## ⚡ Fix for Monitoring Gaps

This implementation provides **2 solutions** to fix the monitoring gaps issue where domains weren't being monitored every 15 minutes consistently.

## 🎯 Root Cause of Gaps

The original issue was caused by:
1. **APScheduler blocking**: `max_instances=1` caused cycles > 15min to skip next cycle
2. **Database lock contention**: All domains waited sequentially for database writes
3. **Event loop complexity**: ThreadPoolExecutor + async mixing caused overhead

## 🚀 Option 1: Timeout-based Scheduling (Default)

**Pros:**
- ✅ Minimal code changes
- ✅ Prevents gaps with timeout protection
- ✅ Backward compatible
- ✅ Ready to deploy

**How it works:**
- Uses `asyncio.wait_for()` with 14-minute timeout
- `max_instances=2` allows backup instance
- `misfire_grace_time=300` handles delayed starts
- `coalesce=True` merges missed runs

**Configuration:**
```env
# Use Option 1 (default)
USE_PURE_ASYNC=false
MONITORING_TIMEOUT_SECONDS=840  # 14 minutes
```

## ⚡ Option 2: Pure Async Monitoring

**Pros:**
- 🚀 Maximum performance
- 🚀 True concurrent processing (15 domains at once)
- 🚀 Batch database operations
- 🚀 No threading overhead

**How it works:**
- Pure `asyncio` with `Semaphore(15)`
- Batched URL inserts (500 URLs/batch)
- `run_in_executor()` for sync operations
- Eliminates ThreadPoolExecutor completely

**Configuration:**
```env
# Use Option 2 (high performance)
USE_PURE_ASYNC=true
MAX_CONCURRENT_DOMAINS=15
BATCH_SIZE=500
```

## ⚙️ Environment Variables

```env
# === Core Scheduling ===
MONITORING_INTERVAL_MINUTES=15      # How often to run monitoring
MONITORING_TIMEOUT_SECONDS=840      # Timeout for each cycle (14 minutes)

# === Processing Method ===
USE_PURE_ASYNC=false               # false=Option1, true=Option2

# === Option 2 Settings ===
MAX_CONCURRENT_DOMAINS=15          # Concurrent domains (Option 2)
BATCH_SIZE=500                     # URLs per batch insert (Option 2)

# === Features ===
ENABLE_GAP_DETECTION=true          # Log gap detection warnings
LOG_LEVEL=INFO                     # Detailed monitoring logs
```

## 📊 Performance Comparison

| Metric | Original | Option 1 | Option 2 |
|--------|----------|----------|----------|
| **Gap Risk** | ❌ High | ✅ Low | ✅ None |
| **Concurrent Domains** | 10 | 10 | 15 |
| **Processing Mode** | Thread | Thread+Timeout | Pure Async |
| **Database Ops** | Sequential | Sequential | Batched |
| **Memory Usage** | High | High | Lower |
| **CPU Efficiency** | Low | Medium | High |

## 🔧 Implementation Details

### Option 1 Changes:
- `scheduler.py`: Added `_monitoring_job_with_timeout()`
- APScheduler: `max_instances=2`, `misfire_grace_time=300`
- Timeout protection with `asyncio.wait_for()`

### Option 2 Changes:
- `domain_monitor_async.py`: New pure async implementation
- `database_utils.py`: Added `bulk_add_url_objects_to_tracking()`
- Semaphore-based concurrency control

## 🚀 Quick Start

**For immediate gap fix (Option 1):**
```bash
# No environment changes needed - it's the default
docker-compose up -d --build
```

**For maximum performance (Option 2):**
```bash
# Set environment variable
echo "USE_PURE_ASYNC=true" >> .env
docker-compose up -d --build
```

## 📈 Monitoring Success

**Watch for these log messages:**

**Option 1:**
```
🚀 Starting timeout-protected monitoring job (timeout: 840s)
✅ Timeout-protected monitoring completed in 180.5s
```

**Option 2:**
```
🚀 Starting pure async monitoring cycle for all domains
✅ SUCCESS vnexpress.net: 47 URLs found, 12 added
🎉 Pure async monitoring completed: 25 successful
📦 Flushed batch: 150 URLs inserted to database
```

## 🛟 Rollback Plan

If issues occur, rollback by:
1. Set `USE_PURE_ASYNC=false`
2. Restart containers: `docker-compose restart`
3. Monitor logs for "Thread-based Domain Monitor" message

## 💡 Recommendations

- **Production**: Start with **Option 1** for safety
- **High-load**: Upgrade to **Option 2** after testing
- **Monitoring**: Watch logs for gap warnings
- **Performance**: Monitor CPU/memory usage during peak times