#!/usr/bin/env python3
"""
Test script for deep crawling functionality
"""

import sys
import os
import logging
import time
from pathlib import Path

# Add domain-analyzer src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "domain-analyzer" / "src"))

from analyzer.newspaper4k_analyzer import Newspaper4kDomainAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_deep_crawling():
    """Test deep crawling on Vietnamese news site"""
    
    # Initialize analyzer
    analyzer = Newspaper4kDomainAnalyzer()
    
    # Test with a Vietnamese news site
    domain_url = "https://thanhnien.vn"
    domain_name = "thanhnien.vn"
    
    logger.info(f"🚀 Testing deep crawling on {domain_name}")
    
    # Phase 1: Basic domain analysis
    logger.info("📊 Phase 1: Domain analysis...")
    start_time = time.time()
    
    analysis_result = analyzer.analyze_domain(domain_url, domain_name)
    
    phase1_time = time.time() - start_time
    logger.info(f"✅ Phase 1 completed in {phase1_time:.2f}s")
    logger.info(f"📈 Results: RSS({len(analysis_result['rss_feeds'])}), "
               f"Sitemaps({len(analysis_result['sitemaps'])}), "
               f"Categories({len(analysis_result['category_urls'])})")
    
    # Phase 2: Deep crawling test
    logger.info("🕳️ Phase 2: Deep crawling test...")
    start_time = time.time()
    
    # Test with subset of categories to avoid timeout
    test_categories = analysis_result['category_urls'][:3]  # Test with 3 categories
    logger.info(f"Testing deep crawling with {len(test_categories)} categories")
    
    deep_urls = analyzer._extract_urls_from_categories(test_categories)
    
    phase2_time = time.time() - start_time
    logger.info(f"✅ Phase 2 completed in {phase2_time:.2f}s")
    logger.info(f"🎯 Deep crawling found {len(deep_urls)} unique URLs")
    
    # Show sample URLs
    logger.info("📋 Sample URLs discovered:")
    for i, url in enumerate(deep_urls[:10]):  # Show first 10
        logger.info(f"  {i+1}. {url}")
    
    # Statistics
    logger.info(f"📊 Deep Crawling Statistics:")
    logger.info(f"  • Total URLs found: {len(deep_urls)}")
    logger.info(f"  • Time taken: {phase2_time:.2f}s")
    logger.info(f"  • URLs per second: {len(deep_urls)/phase2_time:.2f}")
    
    # Test duplicate removal
    logger.info("🧹 Testing duplicate removal...")
    original_count = len(deep_urls)
    deduplicated_urls = analyzer._clean_and_deduplicate_urls(deep_urls + deep_urls)  # Add duplicates
    logger.info(f"  • Original: {original_count}")
    logger.info(f"  • With duplicates: {len(deep_urls + deep_urls)}")
    logger.info(f"  • After deduplication: {len(deduplicated_urls)}")
    
    return analysis_result, deep_urls

if __name__ == "__main__":
    try:
        analysis, urls = test_deep_crawling()
        print(f"\n🎉 Deep crawling test completed successfully!")
        print(f"   Found {len(urls)} unique URLs with 3-level deep crawling")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)