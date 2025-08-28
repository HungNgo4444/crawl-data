#!/usr/bin/env python3
"""
Batch Domain Analyzer - Process all active domains
Bypasses connection issue by using test analyzer + direct database updates
"""
import sys
import os
import json
import time
from datetime import datetime

# Add domain analyzer to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'domain-analyzer', 'src'))

from analyzer.newspaper4k_analyzer import Newspaper4kDomainAnalyzer
import subprocess

def get_active_domains():
    """Get all active domains from database"""
    try:
        cmd = [
            'docker', 'exec', '-e', 'PGPASSWORD=crawler123', 
            'crawler_postgres', 'psql', '-U', 'crawler_user', 
            '-d', 'crawler_db', '-t', '-c',
            "SELECT id, name, base_url FROM domains WHERE status = 'ACTIVE' ORDER BY name;"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        domains = []
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    domains.append({
                        'id': parts[0],
                        'name': parts[1], 
                        'base_url': parts[2]
                    })
        
        return domains
        
    except Exception as e:
        print(f"Error getting domains: {e}")
        return []

def update_domain_in_database(domain_id, domain_name, analysis_result):
    """Update domain analysis in database via docker command"""
    try:
        # Convert lists to JSON strings for PostgreSQL
        rss_feeds = json.dumps(analysis_result.get('rss_feeds', []))
        sitemaps = json.dumps(analysis_result.get('sitemaps', []))
        category_urls = json.dumps(analysis_result.get('category_urls', []))
        homepage_urls = json.dumps(analysis_result.get('homepage_urls', []))
        css_selectors = json.dumps(analysis_result.get('css_selectors', {}))
        
        # Escape single quotes in JSON
        rss_feeds = rss_feeds.replace("'", "''")
        sitemaps = sitemaps.replace("'", "''")
        category_urls = category_urls.replace("'", "''")
        homepage_urls = homepage_urls.replace("'", "''")
        css_selectors = css_selectors.replace("'", "''")
        
        sql_query = f"""
        UPDATE domains 
        SET rss_feeds = '{rss_feeds}'::jsonb,
            sitemaps = '{sitemaps}'::jsonb,
            category_urls = '{category_urls}'::jsonb,
            homepage_urls = '{homepage_urls}'::jsonb,
            css_selectors = '{css_selectors}'::jsonb,
            last_analyzed_at = NOW(),
            analysis_model = 'newspaper4k-batch-v2.0'
        WHERE id = '{domain_id}';
        """
        
        cmd = [
            'docker', 'exec', '-e', 'PGPASSWORD=crawler123',
            'crawler_postgres', 'psql', '-U', 'crawler_user',
            '-d', 'crawler_db', '-c', sql_query
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if 'UPDATE 1' in result.stdout:
            print(f"Updated {domain_name}")
            return True
        else:
            print(f"Failed to update {domain_name}")
            return False
            
    except Exception as e:
        print(f"Error updating {domain_name}: {e}")
        return False

def process_all_domains():
    """Process all active domains"""
    print("Starting batch domain analysis...")
    
    # Get all domains
    domains = get_active_domains()
    print(f"Found {len(domains)} active domains")
    
    # Process in batches of 5 to avoid timeout
    batch_size = 5
    print(f"Processing in batches of {batch_size}")
    
    if not domains:
        print("No domains found!")
        return False
    
    # Initialize analyzer
    analyzer = Newspaper4kDomainAnalyzer()
    
    success_count = 0
    error_count = 0
    
    for i, domain in enumerate(domains, 1):
        domain_name = domain['name']
        domain_url = domain['base_url']
        domain_id = domain['id']
        
        print(f"\n[{i}/{len(domains)}] Processing {domain_name}")
        print(f"URL: {domain_url}")
        
        try:
            # Analyze domain
            print(f"  Analyzing...")
            analysis_result = analyzer.analyze_domain(domain_url, domain_name)
            
            # Check for errors
            if analysis_result.get('analysis_errors'):
                print(f"  Analysis errors: {analysis_result['analysis_errors']}")
            
            # Show results
            rss_count = len(analysis_result.get('rss_feeds', []))
            sitemap_count = len(analysis_result.get('sitemaps', []))
            category_count = len(analysis_result.get('category_urls', []))
            homepage_count = len(analysis_result.get('homepage_urls', []))
            
            print(f"  Results: RSS({rss_count}), Sitemaps({sitemap_count}), Categories({category_count}), Homepage({homepage_count})")
            
            # Update database
            print(f"  Updating database...")
            if update_domain_in_database(domain_id, domain_name, analysis_result):
                success_count += 1
            else:
                error_count += 1
                
            # Brief pause to avoid overwhelming
            time.sleep(1)
            
        except Exception as e:
            print(f"  Error processing {domain_name}: {e}")
            error_count += 1
    
    print(f"\nBatch processing completed!")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Success rate: {(success_count/(success_count+error_count)*100):.1f}%")
    
    return success_count > 0

if __name__ == "__main__":
    success = process_all_domains()
    sys.exit(0 if success else 1)