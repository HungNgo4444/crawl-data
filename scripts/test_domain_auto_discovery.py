#!/usr/bin/env python3
"""
Test script for Domain Auto-Discovery System
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
import json

# Add the project path to Python path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'apps', 'crawl4ai-domain-monitor', 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from utils.database import DatabaseManager
from monitor.domain_auto_discovery import DomainAutoDiscovery

async def test_single_domain(domain_name: str):
    """Test auto-discovery for a single domain"""
    
    # Database connection
    db_manager = DatabaseManager(
        host="localhost",
        port=5432,
        database="crawler_db", 
        user="crawler_user",
        password="crawler123"
    )
    
    # Test connection
    if not db_manager.test_connection():
        logger.error("Database connection failed!")
        return
    
    logger.info(f"Starting auto-discovery for domain: {domain_name}")
    
    # Initialize discovery service
    discovery = DomainAutoDiscovery(db_manager)
    
    try:
        # Run discovery
        result = await discovery.discover_and_save_domain(domain_name)
        
        # Print results
        print(f"\n{'='*80}")
        print(f"AUTO-DISCOVERY RESULTS FOR: {domain_name}")
        print(f"{'='*80}")
        print(f"Base URL: {result.base_url}")
        print(f"Homepage Title: {result.homepage_title}")
        print(f"Confidence Score: {result.confidence_score:.2f}")
        print(f"Discovery Method: {result.discovery_method}")
        print(f"Analysis Time: {result.analysis_timestamp}")
        
        print(f"\n📡 RSS FEEDS ({len(result.rss_feeds)}):")
        for i, rss in enumerate(result.rss_feeds, 1):
            print(f"  {i}. {rss}")
        
        print(f"\n🗺️ SITEMAPS ({len(result.sitemaps)}):")
        for i, sitemap in enumerate(result.sitemaps, 1):
            print(f"  {i}. {sitemap}")
        
        print(f"\n📂 CATEGORIES ({len(result.category_pages)}):")
        for i, category in enumerate(result.category_pages, 1):
            print(f"  {i}. {category}")
        
        if result.analysis_errors:
            print(f"\n❌ ERRORS ({len(result.analysis_errors)}):")
            for i, error in enumerate(result.analysis_errors, 1):
                print(f"  {i}. {error}")
        
        print(f"\n{'='*80}")
        
        # Save results to JSON file for reference
        result_dict = {
            'domain_name': result.domain_name,
            'base_url': result.base_url,
            'homepage_title': result.homepage_title,
            'rss_feeds': result.rss_feeds,
            'sitemaps': result.sitemaps,
            'category_pages': result.category_pages,
            'url_patterns': result.url_patterns,
            'css_selectors': result.css_selectors,
            'confidence_score': result.confidence_score,
            'analysis_timestamp': result.analysis_timestamp,
            'discovery_method': result.discovery_method,
            'analysis_errors': result.analysis_errors
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"scripts/domain_discovery_{domain_name.replace('.', '_')}_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Auto-discovery failed: {e}")
        raise

async def test_all_domains():
    """Test auto-discovery for all active domains in database"""
    
    # Database connection
    db_manager = DatabaseManager(
        host="localhost",
        port=5432,
        database="crawler_db", 
        user="crawler_user",
        password="crawler123"
    )
    
    # Test connection
    if not db_manager.test_connection():
        logger.error("Database connection failed!")
        return
    
    logger.info("Starting auto-discovery for all active domains")
    
    # Initialize discovery service
    discovery = DomainAutoDiscovery(db_manager)
    
    try:
        # Run discovery for all domains
        results = await discovery.discover_all_active_domains()
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"AUTO-DISCOVERY SUMMARY - ALL DOMAINS")
        print(f"{'='*80}")
        print(f"Total domains processed: {len(results)}")
        
        total_rss = sum(len(r.rss_feeds) for r in results.values())
        total_sitemaps = sum(len(r.sitemaps) for r in results.values())  
        total_categories = sum(len(r.category_pages) for r in results.values())
        avg_confidence = sum(r.confidence_score for r in results.values()) / len(results) if results else 0
        
        print(f"Total RSS feeds found: {total_rss}")
        print(f"Total sitemaps found: {total_sitemaps}")
        print(f"Total categories found: {total_categories}")
        print(f"Average confidence: {avg_confidence:.2f}")
        
        print(f"\n📊 DOMAIN BREAKDOWN:")
        for domain_name, result in results.items():
            status = "✅" if result.confidence_score > 0.5 else "⚠️" if result.confidence_score > 0.2 else "❌"
            print(f"  {status} {domain_name}: RSS({len(result.rss_feeds)}) | Sitemaps({len(result.sitemaps)}) | Categories({len(result.category_pages)}) | Confidence({result.confidence_score:.2f})")
        
        # Save comprehensive results
        all_results = {
            domain_name: {
                'domain_name': result.domain_name,
                'base_url': result.base_url,
                'homepage_title': result.homepage_title,
                'rss_feeds': result.rss_feeds,
                'sitemaps': result.sitemaps,
                'category_pages': result.category_pages,
                'confidence_score': result.confidence_score,
                'analysis_timestamp': result.analysis_timestamp,
                'discovery_method': result.discovery_method,
                'analysis_errors': result.analysis_errors
            }
            for domain_name, result in results.items()
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"scripts/all_domains_auto_discovery_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\nAll results saved to: {output_file}")
        print(f"{'='*80}")
        
    except Exception as e:
        logger.error(f"Auto-discovery failed: {e}")
        raise

async def main():
    """Main test function"""
    if len(sys.argv) > 1:
        # Test single domain
        domain_name = sys.argv[1]
        await test_single_domain(domain_name)
    else:
        # Test all domains
        await test_all_domains()

if __name__ == "__main__":
    asyncio.run(main())