"""
Test script để kiểm tra flow url_tracking từ domain-analyzer
"""
import sys
import os
import logging
import json
from pprint import pprint

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from analyzer.newspaper4k_analyzer import Newspaper4kDomainAnalyzer
from utils.database_utils import DatabaseManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_domain_flow(domain_name: str = None):
    """
    Test toàn bộ flow từ domains table -> extract URLs -> lưu url_tracking
    """
    print(f"\nTESTING URL TRACKING FLOW")
    print("=" * 50)
    
    analyzer = Newspaper4kDomainAnalyzer()
    db_manager = DatabaseManager()
    
    # 1. Kết nối database
    print("\n1️⃣ Connecting to database...")
    if not db_manager.connect():
        print("❌ Cannot connect to database")
        return
    print("✅ Database connected")
    
    try:
        # 2. Lấy domain từ database
        print(f"\n2️⃣ Getting domain data from database...")
        if domain_name:
            domain = db_manager.get_domain_by_name(domain_name)
            domains = [domain] if domain else []
        else:
            domains = db_manager.get_active_domains()
            # Lấy chỉ 1 domain để test
            domains = domains[:1] if domains else []
            
        if not domains:
            print("❌ No domains found")
            return
            
        domain = domains[0]
        print(f"✅ Testing with domain: {domain['name']}")
        print(f"   Base URL: {domain['base_url']}")
        print(f"   Analysis Model: {domain.get('analysis_model', 'None')}")
        
        # 3. Hiển thị dữ liệu hiện có của domain
        print(f"\n3️⃣ Current domain data:")
        print(f"   RSS Feeds: {len(domain.get('rss_feeds', []))} items")
        print(f"   Sitemaps: {len(domain.get('sitemaps', []))} items") 
        print(f"   Homepage URLs: {len(domain.get('homepage_urls', []))} items")
        print(f"   Category URLs: {len(domain.get('category_urls', []))} items")
        
        if domain.get('rss_feeds'):
            print(f"   Sample RSS: {domain['rss_feeds'][:2]}")
        if domain.get('category_urls'):
            print(f"   Sample Categories: {domain['category_urls'][:3]}")
        
        # 4. Extract article URLs sử dụng newspaper4k
        print(f"\n4️⃣ Extracting article URLs using newspaper4k...")
        
        # Simulate analysis result từ phase 1 
        analysis_result = {
            'rss_feeds': domain.get('rss_feeds', []),
            'sitemaps': domain.get('sitemaps', []),
            'homepage_urls': domain.get('homepage_urls', []),
            'category_urls': domain.get('category_urls', []),
            'css_selectors': domain.get('css_selectors', {})
        }
        
        # Phase 2: Extract all article URLs
        article_urls = analyzer.extract_all_article_urls(
            domain['base_url'], 
            domain['name'], 
            analysis_result
        )
        
        print(f"✅ Extracted {len(article_urls)} article URLs")
        print(f"   Sample URLs:")
        for i, url in enumerate(article_urls[:5]):
            print(f"   {i+1}. {url}")
        
        # 5. Deduplicate URLs
        print(f"\n5️⃣ Deduplication process:")
        print(f"   Input URLs: {len(article_urls)}")
        
        # The deduplication đã được thực hiện trong extract_all_article_urls
        print(f"   Final URLs (after dedup): {len(article_urls)}")
        
        # 6. Lưu vào url_tracking table
        print(f"\n6️⃣ Saving URLs to url_tracking table...")
        
        # Check số lượng URLs hiện tại trong url_tracking cho domain này
        current_count = get_current_url_count(db_manager, domain['id'])
        print(f"   Current URLs in tracking: {current_count}")
        
        # Bulk insert URLs
        success_count = db_manager.bulk_add_urls_to_tracking(
            article_urls, 
            domain['id'], 
            'newspaper4k-phase2-test'
        )
        
        # Check số lượng sau insert
        new_count = get_current_url_count(db_manager, domain['id'])
        print(f"   URLs after insert: {new_count}")
        print(f"   Successfully added: {success_count}/{len(article_urls)} URLs")
        print(f"   Net increase: {new_count - current_count}")
        
        # 7. Show sample data in url_tracking
        print(f"\n7️⃣ Sample url_tracking records:")
        show_sample_tracking_data(db_manager, domain['id'])
        
        print(f"\n✅ URL TRACKING FLOW TEST COMPLETED!")
        
    except Exception as e:
        print(f"❌ Error in flow test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db_manager.disconnect()

def get_current_url_count(db_manager, domain_id: str) -> int:
    """Get current URL count for domain"""
    try:
        with db_manager.connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM url_tracking WHERE domain_id = %s
            """, (domain_id,))
            return cursor.fetchone()[0]
    except:
        return 0

def show_sample_tracking_data(db_manager, domain_id: str):
    """Show sample url_tracking data"""
    try:
        import psycopg2.extras
        with db_manager.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT url_hash, original_url, status, metadata, created_at 
                FROM url_tracking 
                WHERE domain_id = %s 
                ORDER BY created_at DESC 
                LIMIT 5
            """, (domain_id,))
            
            records = cursor.fetchall()
            for i, record in enumerate(records):
                print(f"   {i+1}. {record['original_url'][:60]}...")
                print(f"      Hash: {record['url_hash'][:16]}...")
                print(f"      Status: {record['status']}")
                print(f"      Metadata: {record['metadata']}")
                print(f"      Created: {record['created_at']}")
                print()
                
    except Exception as e:
        print(f"   Error showing sample data: {e}")

def analyze_deduplication_mechanisms():
    """Phân tích các cơ chế deduplicate"""
    print(f"\nDEDUPLICATION MECHANISMS ANALYSIS")
    print("=" * 50)
    
    print("\n1. In-memory deduplication (newspaper4k_analyzer.py:516-542):")
    print("   - Sử dụng set() để remove duplicates trong memory")
    print("   - Normalize URLs bằng urlparse (remove fragments)")
    print("   - Chỉ keep URLs từ cùng domain")
    print("   - Filter theo domain_parsed.netloc")
    
    print("\n2. Database-level deduplication (database_utils.py:99-129):")
    print("   - Sử dụng SHA256 hash của URL làm unique key")
    print("   - UNIQUE constraint trên url_hash column")
    print("   - ON CONFLICT DO UPDATE để handle duplicates")
    print("   - Metadata được update nếu URL đã tồn tại")
    
    print("\n3. URL normalization process:")
    print("   - Remove fragments (#anchor)")
    print("   - Keep query parameters (?param=value)")
    print("   - Lowercase scheme và netloc")
    print("   - Path normalization")

def show_domain_data_columns():
    """Show which columns are extracted from domains table"""
    print(f"\nDOMAIN DATA EXTRACTION")
    print("=" * 50)
    
    print("\nColumns extracted from domains table (database_utils.py:48-50):")
    columns = [
        "id", "name", "display_name", "base_url", 
        "rss_feeds", "sitemaps", "css_selectors",
        "last_analyzed_at", "analysis_model", 
        "url_example", "generated_schema"
    ]
    
    for col in columns:
        print(f"   + {col}")
    
    print(f"\nAdditional columns used for URL extraction:")
    additional = ["homepage_urls", "category_urls"]
    for col in additional:
        print(f"   + {col}")

if __name__ == "__main__":
    print("URL TRACKING FLOW TEST SUITE")
    print("=" * 60)
    
    # 1. Show các columns được lấy từ domains table
    show_domain_data_columns()
    
    # 2. Analyze deduplication mechanisms
    analyze_deduplication_mechanisms()
    
    # 3. Test actual flow
    domain_to_test = sys.argv[1] if len(sys.argv) > 1 else None
    test_domain_flow(domain_to_test)