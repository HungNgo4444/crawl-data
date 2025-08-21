# 🚀 Quick Start - Vietnamese Domain Analysis Worker

Cách nhanh nhất để test Analysis Worker với database có sẵn 20+ Vietnamese news domains.

## ⚡ Quick Setup (5 phút)

### 1. Chạy database và services
```bash
cd "F:\Crawl data\apps\analysis_worker"

# Chạy toàn bộ stack
docker-compose up -d

# Chờ services khởi động (2-3 phút)
docker-compose logs -f analysis-worker
```

### 2. Setup database với Vietnamese domains
```bash
# Tạo database với 23 Vietnamese news domains
python scripts/setup_test_database.py

# Xem database stats
python scripts/setup_test_database.py stats
```

### 3. Test phân tích domains
```bash
# Test toàn bộ Vietnamese domains
python scripts/test_analysis_worker.py

# Test domain cụ thể
python scripts/test_analysis_worker.py domain vnexpress.net https://vnexpress.net
```

## 📊 Database có sẵn

### 23 Vietnamese News Domains:
1. **VnExpress** (vnexpress.net) - Priority 1
2. **Dân Trí** (dantri.com.vn) - Priority 1  
3. **Tuổi Trẻ** (tuoitre.vn) - Priority 1
4. **Thanh Niên** (thanhnien.vn) - Priority 1
5. **VietnamNet** (vietnamnet.vn) - Priority 2
6. **VTV News** (vtv.vn) - Priority 2
7. **CafeF** (cafef.vn) - Business
8. **Người Dua Tin** (nguoiduatin.vn) - Business
9. **Tiền Phong** (tienphong.vn) - General
10. **Lao Động** (laodong.vn) - Labor
11. **24H News** (24h.com.vn) - General
12. **Soha** (soha.vn) - Entertainment
13. **Người Lao Động** (nld.com.vn) - Labor
14. **Báo Mới** (baomoi.com) - Aggregator
15. **Zing News** (zing.vn) - Tech/Lifestyle
16. **Thể Thao 247** (thethao247.vn) - Sports
17. **Bóng Đá 24H** (bongda24h.vn) - Football
18. **Genk** (genk.vn) - Technology
19. **ICTNews** (ictnews.vn) - Technology
20. **Sức Khỏe Đời Sống** (suckhoedoisong.vn) - Health
21. **Giáo Dục VN** (giaoduc.net.vn) - Education
22. **Kênh 14** (kenh14.vn) - Entertainment
23. **Eva.vn** (eva.vn) - Women/Lifestyle

### Sample Data có sẵn:
- ✅ **50+ discovered URLs** (RSS, sitemap, categories)
- ✅ **15+ analysis results** với GWEN-2.5:3b
- ✅ **50+ crawled articles** với Vietnamese content
- ✅ **Vietnamese selectors** cho từng domain
- ✅ **Real-world confidence scores** và metrics

## 🎯 Test Cases sẵn có

### 1. Test Analysis API
```bash
# Trigger analysis VnExpress
curl -X POST http://localhost:8080/api/v1/analysis/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "domain_name": "vnexpress.net",
    "base_url": "https://vnexpress.net",
    "trigger_source": "manual"
  }'

# Check results
curl http://localhost:8080/api/v1/analysis/recent?limit=5
```

### 2. Test Vietnamese Content Processing
```bash
# Test Dantri
curl -X POST http://localhost:8080/api/v1/analysis/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "domain_name": "dantri.com.vn", 
    "base_url": "https://dantri.com.vn",
    "trigger_source": "test"
  }'
```

### 3. Test Business News (CafeF)
```bash
curl -X POST http://localhost:8080/api/v1/analysis/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "domain_name": "cafef.vn",
    "base_url": "https://cafef.vn", 
    "trigger_source": "test"
  }'
```

## 📊 Monitoring Dashboards

| Service | URL | Login |
|---------|-----|-------|
| **Analysis Worker API** | http://localhost:8080/health | - |
| **Redis Queue UI** | http://localhost:8081 | - |
| **Grafana Dashboard** | http://localhost:3000 | admin/admin |
| **Prometheus Metrics** | http://localhost:9090 | - |

## 🔍 Check Results

### 1. Via API
```bash
# Health check
curl http://localhost:8080/health

# Queue stats
curl http://localhost:8080/api/v1/queue/stats

# Worker stats  
curl http://localhost:8080/api/v1/worker/stats

# Recent analyses
curl http://localhost:8080/api/v1/analysis/recent
```

### 2. Via Database
```bash
# Connect to PostgreSQL
docker exec -it analysis-postgres psql -U crawler_user -d crawler_db

# Check domains
SELECT domain_name, display_name, category FROM domain_configurations;

# Check analyses
SELECT domain_name, status, overall_confidence_score, analysis_timestamp 
FROM domain_analysis_results ORDER BY analysis_timestamp DESC LIMIT 10;

# Check discovered URLs
SELECT domain_name, url_type, COUNT(*) 
FROM discovered_urls GROUP BY domain_name, url_type;
```

### 3. Via Redis Commander
1. Mở http://localhost:8081
2. Xem queues:
   - `domain_analysis_queue` - Main queue
   - `domain_analysis_retry_queue` - Retry jobs
   - `domain_analysis_failed_queue` - Failed jobs

## 🧪 Performance Benchmarks

Với database có sẵn, bạn có thể test:

### Expected Performance:
- **Single Analysis:** < 10 seconds
- **Confidence Score:** > 0.8 cho major Vietnamese sites
- **Vietnamese Content Ratio:** > 0.9 cho Vietnamese domains
- **Queue Throughput:** > 10 analyses/minute
- **Success Rate:** > 95% cho established domains

### Test Commands:
```bash
# Performance test
python scripts/test_analysis_worker.py

# Load test 
python scripts/load_test.py --domains 5 --concurrent 3

# Database stats
python scripts/setup_test_database.py stats
```

## ⚡ Troubleshooting

### GWEN-2.5:3b Model
```bash
# Verify model exists
docker exec -it analysis-ollama ollama list

# If not, pull it
docker exec -it analysis-ollama ollama pull gwen-2.5:3b
```

### Database Issues
```bash
# Reset database
python scripts/setup_test_database.py reset

# Check connection
docker exec -it analysis-postgres pg_isready -U crawler_user
```

### Service Health
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs analysis-worker
docker-compose logs redis
docker-compose logs postgres
```

---

## 🎉 Ready to Test!

Database đã sẵn sàng với 23 Vietnamese news domains và sample data. Bạn có thể:

1. ✅ **Test real Vietnamese content analysis** với GWEN-2.5:3b
2. ✅ **Verify CSS selector generation** cho Vietnamese news sites  
3. ✅ **Monitor performance** với comprehensive metrics
4. ✅ **Check crawl data quality** với real articles
5. ✅ **Test queue management** với retry logic

**Bắt đầu ngay:** `docker-compose up -d && python scripts/setup_test_database.py`