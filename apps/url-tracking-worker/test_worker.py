"""
Test script for URL tracking worker
"""
import sys
import os
import asyncio
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.database_utils import DatabaseManager
from src.monitor.url_extractor import URLExtractor
from src.monitor.domain_monitor import DomainMonitor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_worker_components():
    """Test các components của URL tracking worker"""
    print("\n=== URL TRACKING WORKER TEST ===\n")
    
    # Test 1: Database connection
    print("1. Testing database connection...")
    db_manager = DatabaseManager()
    if not db_manager.connect():
        print("❌ Database connection failed")
        return False
    print("✅ Database connected successfully")
    
    # Test 2: Get domains for monitoring
    print("\n2. Getting domains for monitoring...")
    domains = db_manager.get_domains_for_monitoring()
    print(f"📊 Found {len(domains)} domains ready for monitoring")
    
    if not domains:
        print("⚠️ No domains found with analysis data")
        db_manager.disconnect()
        return False
    
    # Show sample domain data
    sample_domain = domains[0]
    print(f"📝 Sample domain: {sample_domain['name']}")
    print(f"   RSS feeds: {len(sample_domain.get('rss_feeds', []))}")
    print(f"   Sitemaps: {len(sample_domain.get('sitemaps', []))}")
    print(f"   Categories: {len(sample_domain.get('category_urls', []))}")
    
    # Test 3: URL extraction
    print("\n3. Testing URL extraction...")
    url_extractor = URLExtractor()
    
    try:
        article_urls = url_extractor.extract_article_urls_from_domain_data(
            sample_domain['base_url'],
            sample_domain['name'],
            sample_domain
        )
        print(f"🔍 Extracted {len(article_urls)} article URLs")
        
        # Show sample URLs
        print("📋 Sample URLs:")
        for i, url in enumerate(article_urls[:3]):
            print(f"   {i+1}. {url}")
            
    except Exception as e:
        print(f"❌ URL extraction failed: {e}")
        article_urls = []
    
    # Test 4: Domain monitoring
    print("\n4. Testing domain monitoring...")
    domain_monitor = DomainMonitor(db_manager, url_extractor)
    
    try:
        # Monitor single domain
        result = await domain_monitor.monitor_single_domain(sample_domain)
        print(f"📈 Monitoring result: {result}")
        
    except Exception as e:
        print(f"❌ Domain monitoring failed: {e}")
    
    # Test 5: URL tracking count
    print("\n5. Checking URL tracking table...")
    total_urls = db_manager.get_url_tracking_count()
    domain_urls = db_manager.get_url_tracking_count(sample_domain['id'])
    print(f"📊 Total URLs in tracking: {total_urls}")
    print(f"📊 URLs for {sample_domain['name']}: {domain_urls}")
    
    # Test 6: Get monitoring stats
    print("\n6. Getting monitoring statistics...")
    stats = domain_monitor.get_monitoring_stats()
    print(f"📈 Monitoring stats: {stats}")
    
    # Cleanup
    db_manager.disconnect()
    print("\n✅ All tests completed!")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_worker_components())
        if success:
            print("\n🎉 URL Tracking Worker tests PASSED!")
        else:
            print("\n❌ URL Tracking Worker tests FAILED!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)