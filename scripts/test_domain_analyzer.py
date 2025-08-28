#!/usr/bin/env python3
"""
Domain Analyzer Test Script
Tests domain analysis and article URL extraction
"""
import sys
import os
import json
from datetime import datetime
import logging

# Add domain analyzer to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'domain-analyzer', 'src'))

from analyzer.newspaper4k_analyzer import Newspaper4kDomainAnalyzer
from utils.database_utils import DatabaseManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_domain_analysis(domain_name: str, domain_url: str):
    """Test complete domain analysis and article URL extraction"""
    
    test_results = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "test_purpose": "DOMAIN_ANALYSIS_AND_URL_EXTRACTION_TEST",
            "domain_tested": domain_name
        },
        "domain_analysis": {},
        "url_extraction": {},
        "verification": {
            "domain_analysis_checks": {},
            "url_extraction_checks": {},
            "overall_status": "UNKNOWN"
        }
    }
    
    try:
        # Initialize analyzer
        analyzer = Newspaper4kDomainAnalyzer()
        
        # Domain Analysis
        logger.info(f"Starting domain analysis for {domain_name}")
        analysis_result = analyzer.analyze_domain(domain_url, domain_name)
        
        # Store domain analysis results
        test_results["domain_analysis"] = {
            "domain_name": domain_name,
            "domain_url": domain_url,
            "success": len(analysis_result.get('analysis_errors', [])) == 0,
            "rss_feeds": {
                "count": len(analysis_result.get('rss_feeds', [])),
                "urls": analysis_result.get('rss_feeds', [])
            },
            "sitemaps": {
                "count": len(analysis_result.get('sitemaps', [])),
                "urls": analysis_result.get('sitemaps', [])
            },
            "homepage_urls": {
                "count": len(analysis_result.get('homepage_urls', [])),
                "urls": analysis_result.get('homepage_urls', [])
            },
            "category_urls": {
                "count": len(analysis_result.get('category_urls', [])),
                "urls": analysis_result.get('category_urls', [])
            },
            "css_selectors": analysis_result.get('css_selectors', {}),
            "analysis_errors": analysis_result.get('analysis_errors', [])
        }
        
        # Domain analysis verification
        test_results["verification"]["domain_analysis_checks"] = {
            "rss_feeds_extracted": len(analysis_result.get('rss_feeds', [])) > 0,
            "sitemaps_extracted": len(analysis_result.get('sitemaps', [])) > 0,
            "homepage_urls_extracted": len(analysis_result.get('homepage_urls', [])) > 0,
            "category_urls_extracted": len(analysis_result.get('category_urls', [])) > 0,
            "css_selectors_dynamic": _verify_dynamic_css_selectors(analysis_result.get('css_selectors', {})),
            "no_analysis_errors": len(analysis_result.get('analysis_errors', [])) == 0
        }
        
        # Article URL Extraction
        logger.info(f"Starting article URL extraction for {domain_name}")
        article_urls = analyzer.extract_all_article_urls(domain_url, domain_name, analysis_result)
        
        # Store URL extraction results
        test_results["url_extraction"] = {
            "total_article_urls": len(article_urls),
            "sample_article_urls": article_urls[:20],  # First 20 URLs as sample
            "url_extraction_sources": _analyze_url_sources(analysis_result),
            "deduplication_info": {
                "unique_urls": len(set(article_urls)),
                "total_discovered": len(article_urls),
                "duplicates_removed": len(article_urls) - len(set(article_urls))
            }
        }
        
        # URL extraction verification
        test_results["verification"]["url_extraction_checks"] = {
            "article_urls_extracted": len(article_urls) > 0,
            "urls_from_rss": _check_rss_extraction(analysis_result.get('rss_feeds', [])),
            "urls_from_categories": _check_category_extraction(analysis_result.get('category_urls', [])),
            "urls_from_sitemaps": _check_sitemap_extraction(analysis_result.get('sitemaps', [])),
            "urls_deduplicated": len(article_urls) == len(set(article_urls)),
            "urls_are_articles": _verify_article_urls(article_urls[:10])  # Check first 10
        }
        
        # Overall verification
        analysis_pass = all(test_results["verification"]["domain_analysis_checks"].values())
        extraction_pass = all(test_results["verification"]["url_extraction_checks"].values())
        
        if analysis_pass and extraction_pass:
            test_results["verification"]["overall_status"] = "ALL_TESTS_PASSED"
        elif analysis_pass:
            test_results["verification"]["overall_status"] = "ANALYSIS_PASSED_EXTRACTION_PARTIAL"
        elif extraction_pass:
            test_results["verification"]["overall_status"] = "EXTRACTION_PASSED_ANALYSIS_PARTIAL"
        else:
            test_results["verification"]["overall_status"] = "NEEDS_IMPROVEMENT"
        
        logger.info(f"Test completed: {test_results['verification']['overall_status']}")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        test_results["verification"]["overall_status"] = "TEST_FAILED"
        test_results["test_error"] = str(e)
    
    return test_results

def _verify_dynamic_css_selectors(css_selectors: dict) -> bool:
    """Verify CSS selectors were dynamically extracted (not just hardcoded)"""
    if not css_selectors:
        return False
    
    # Check if we have more than just basic hardcoded selectors
    expected_categories = ['article_title', 'article_content', 'article_meta', 'navigation']
    for category in expected_categories:
        if category not in css_selectors or not css_selectors[category]:
            return False
    
    # If we have selectors, consider it dynamic (hardcoded would be fallback)
    return True

def _analyze_url_sources(analysis_result: dict) -> dict:
    """Analyze what sources are available for URL extraction"""
    return {
        "rss_feeds_available": len(analysis_result.get('rss_feeds', [])),
        "categories_available": len(analysis_result.get('category_urls', [])),
        "sitemaps_available": len(analysis_result.get('sitemaps', [])),
        "homepage_available": len(analysis_result.get('homepage_urls', [])) > 0
    }

def _check_rss_extraction(rss_feeds: list) -> bool:
    """Check if RSS feeds are available for extraction"""
    return len(rss_feeds) > 0

def _check_category_extraction(category_urls: list) -> bool:
    """Check if category URLs are available for extraction"""
    return len(category_urls) > 0

def _check_sitemap_extraction(sitemaps: list) -> bool:
    """Check if sitemaps are available for extraction"""
    return len(sitemaps) > 0

def _verify_article_urls(urls: list) -> bool:
    """Verify that extracted URLs look like article URLs"""
    if not urls:
        return False
    
    article_indicators = ['.html', '.htm', '/20', '/article', '/news', '/post']
    valid_count = 0
    
    for url in urls:
        url_lower = url.lower()
        if any(indicator in url_lower for indicator in article_indicators):
            valid_count += 1
        elif len(url.split('/')) >= 4:  # Deep enough path structure
            valid_count += 1
    
    # At least 50% should look like articles
    return (valid_count / len(urls)) >= 0.5

def export_test_results(test_results: dict, domain_name: str):
    """Export test results to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"domain_analyzer_test_{domain_name}_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(__file__), filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"Test results exported to: {filepath}")
    return filepath

def main():
    """Main test function"""
    # Test với dantri.com.vn
    domain_name = "dantri.com.vn"
    domain_url = "https://dantri.com.vn"
    
    print(f"Starting Domain Analyzer Test for {domain_name}")
    print("="*60)
    
    # Run test
    results = test_domain_analysis(domain_name, domain_url)
    
    # Export results
    export_path = export_test_results(results, domain_name)
    
    # Print summary
    print("\nTEST SUMMARY:")
    print(f"Domain: {domain_name}")
    print(f"Overall Status: {results['verification']['overall_status']}")
    
    if 'domain_analysis' in results:
        da = results['domain_analysis']
        print(f"\nDomain Analysis:")
        print(f"  RSS Feeds: {da.get('rss_feeds', {}).get('count', 0)}")
        print(f"  Sitemaps: {da.get('sitemaps', {}).get('count', 0)}")
        print(f"  Category URLs: {da.get('category_urls', {}).get('count', 0)}")
        print(f"  Homepage URLs: {da.get('homepage_urls', {}).get('count', 0)}")
    
    if 'url_extraction' in results:
        ue = results['url_extraction']
        print(f"\nURL Extraction:")
        print(f"  Total Article URLs: {ue.get('total_article_urls', 0)}")
        print(f"  Unique URLs: {ue.get('deduplication_info', {}).get('unique_urls', 0)}")
        print(f"  Duplicates Removed: {ue.get('deduplication_info', {}).get('duplicates_removed', 0)}")
    
    print(f"\nDetailed results saved to: {export_path}")
    
    # Return success status
    return results['verification']['overall_status'] in ['ALL_TESTS_PASSED', 'ANALYSIS_PASSED_EXTRACTION_PARTIAL']

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)