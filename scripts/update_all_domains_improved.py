#!/usr/bin/env python3
"""Update all domains with improved newspaper4k analysis"""
import sys
import os
import subprocess
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'domain-analyzer', 'src'))
from analyzer.newspaper4k_analyzer import Newspaper4kDomainAnalyzer

def get_all_domains():
    """Get all active domains"""
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
            if '|' in line and line.strip():
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3 and parts[0] and parts[1]:
                    domains.append({
                        'id': parts[0],
                        'name': parts[1], 
                        'base_url': parts[2]
                    })
        
        return domains
        
    except Exception as e:
        print(f"Error getting domains: {e}")
        return []

def update_domain_sql(domain_id, domain_name, analysis_result):
    """Generate SQL update statement"""
    rss_feeds = json.dumps(analysis_result.get('rss_feeds', []))
    sitemaps = json.dumps(analysis_result.get('sitemaps', []))
    category_urls = json.dumps(analysis_result.get('category_urls', []))
    homepage_urls = json.dumps(analysis_result.get('homepage_urls', []))
    css_selectors = json.dumps(analysis_result.get('css_selectors', {}))
    
    # Escape single quotes
    rss_feeds = rss_feeds.replace("'", "''")
    sitemaps = sitemaps.replace("'", "''")
    category_urls = category_urls.replace("'", "''")
    homepage_urls = homepage_urls.replace("'", "''")
    css_selectors = css_selectors.replace("'", "''")
    
    sql = f"""
UPDATE domains 
SET rss_feeds = '{rss_feeds}'::jsonb,
    sitemaps = '{sitemaps}'::jsonb,
    category_urls = '{category_urls}'::jsonb,
    homepage_urls = '{homepage_urls}'::jsonb,
    css_selectors = '{css_selectors}'::jsonb,
    last_analyzed_at = NOW(),
    analysis_model = 'newspaper4k-improved'
WHERE id = '{domain_id}';
"""
    return sql

def main():
    print("Improved batch analysis for ALL 25 domains...")
    
    domains = get_all_domains()
    print(f"Found {len(domains)} domains to process")
    
    if not domains:
        return False
    
    analyzer = Newspaper4kDomainAnalyzer()
    sql_statements = []
    
    for i, domain in enumerate(domains, 1):
        domain_name = domain['name']
        domain_url = domain['base_url']
        domain_id = domain['id']
        
        print(f"[{i}/{len(domains)}] Processing {domain_name}...")
        
        try:
            # Analyze with improved method
            result = analyzer.analyze_domain(domain_url, domain_name)
            
            # Show results
            rss_count = len(result.get('rss_feeds', []))
            sitemap_count = len(result.get('sitemaps', []))
            category_count = len(result.get('category_urls', []))
            
            print(f"  Results: RSS({rss_count}), Sitemaps({sitemap_count}), Categories({category_count})")
            
            # Generate SQL
            sql = update_domain_sql(domain_id, domain_name, result)
            sql_statements.append(sql)
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # Execute SQL statements one by one
    print(f"\nExecuting {len(sql_statements)} updates...")
    
    success_count = 0
    
    for i, sql in enumerate(sql_statements, 1):
        try:
            cmd = [
                'docker', 'exec', '-e', 'PGPASSWORD=crawler123',
                'crawler_postgres', 'psql', '-U', 'crawler_user',
                '-d', 'crawler_db', '-c', sql
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if 'UPDATE 1' in result.stdout:
                success_count += 1
                print(f"  [{i}/{len(sql_statements)}] Updated successfully")
            else:
                print(f"  [{i}/{len(sql_statements)}] Update failed")
                
        except Exception as e:
            print(f"  [{i}/{len(sql_statements)}] SQL error: {e}")
    
    print(f"\nSuccessfully updated {success_count}/{len(sql_statements)} domains!")
    return success_count > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)