#!/usr/bin/env python3
"""
Populate url_example column trong domains table từ rss_urls JSON file
Mỗi domain sẽ có 1 URL mẫu để phân tích structure
"""

import json
import psycopg2
from urllib.parse import urlparse

def extract_domain_from_url(url):
    """Extract domain từ URL"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    return domain.replace('www.', '') if domain.startswith('www.') else domain

def get_sample_urls_by_domain(json_file_path):
    """
    Extract sample URLs grouped by domain từ JSON file
    Trả về dict: {domain: sample_url}
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    domain_urls = {}
    
    # Duyệt qua tất cả results
    for feed_name, feed_data in data.get('results', {}).items():
        domain = feed_data.get('domain', '')
        urls = feed_data.get('urls', [])
        
        if domain and urls:
            # Chuẩn hóa domain name
            normalized_domain = domain.lower().replace('www.', '')
            
            # Lấy URL đầu tiên làm sample nếu chưa có
            if normalized_domain not in domain_urls:
                # Tìm URL có content (không phải homepage)
                sample_url = None
                for url in urls[:5]:  # Chỉ check 5 URLs đầu
                    if any(keyword in url.lower() for keyword in ['-', '_', '/', 'html', 'php']):
                        if not url.endswith('/'):  # Không phải homepage
                            sample_url = url
                            break
                
                # Nếu không tìm được URL có content, lấy URL đầu tiên
                if not sample_url and urls:
                    sample_url = urls[0]
                
                if sample_url:
                    domain_urls[normalized_domain] = sample_url
    
    return domain_urls

def update_domains_with_url_examples(domain_urls, db_config):
    """
    Update domains table với url_example
    """
    try:
        # Kết nối database
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Lấy danh sách domains hiện tại
        cur.execute("SELECT id, name FROM domains WHERE status = 'ACTIVE';")
        existing_domains = cur.fetchall()
        
        updated_count = 0
        
        for domain_id, domain_name in existing_domains:
            # Chuẩn hóa domain name để match
            normalized_name = domain_name.lower().replace('www.', '')
            
            # Tìm URL mẫu cho domain này
            sample_url = domain_urls.get(normalized_name)
            
            if sample_url:
                # Update url_example
                cur.execute(
                    "UPDATE domains SET url_example = %s WHERE id = %s;",
                    (sample_url, domain_id)
                )
                updated_count += 1
                print(f"Updated {domain_name}: {sample_url}")
            else:
                print(f"No sample URL found for domain: {domain_name}")
        
        conn.commit()
        print(f"\nSuccessfully updated {updated_count} domains with sample URLs")
        
        # Hiển thị kết quả
        cur.execute("""
            SELECT name, url_example 
            FROM domains 
            WHERE url_example IS NOT NULL 
            ORDER BY name;
        """)
        
        print("\nDomains with sample URLs:")
        for name, url in cur.fetchall():
            print(f"  {name}: {url}")
        
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def main():
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'crawler_db',
        'user': 'crawler_user',
        'password': 'crawler123'
    }
    
    # Paths
    json_file_path = r'F:\Crawl data\scripts\rss_urls_20250821_202405.json'
    
    print("Extracting sample URLs by domain from JSON file...")
    domain_urls = get_sample_urls_by_domain(json_file_path)
    
    print(f"Found sample URLs for {len(domain_urls)} domains:")
    for domain, url in domain_urls.items():
        print(f"  {domain}: {url}")
    
    print("\nUpdating domains table...")
    update_domains_with_url_examples(domain_urls, db_config)

if __name__ == "__main__":
    main()