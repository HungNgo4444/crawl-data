#!/usr/bin/env python3
"""Test single domain analysis"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'domain-analyzer', 'src'))

from analyzer.newspaper4k_analyzer import Newspaper4kDomainAnalyzer

def test_single_domain():
    analyzer = Newspaper4kDomainAnalyzer()
    
    # Test với 24h.com.vn
    domain_name = "24h.com.vn"
    domain_url = "https://24h.com.vn"
    
    print(f"Testing {domain_name}...")
    result = analyzer.analyze_domain(domain_url, domain_name)
    
    print(f"RSS: {len(result.get('rss_feeds', []))}")
    print(f"Sitemaps: {len(result.get('sitemaps', []))}")
    print(f"Categories: {len(result.get('category_urls', []))}")
    print(f"Errors: {result.get('analysis_errors', [])}")
    
    return result

if __name__ == "__main__":
    test_single_domain()