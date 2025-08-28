#!/usr/bin/env python3
"""Test VnExpress domain with improved newspaper4k analysis"""
import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'domain-analyzer', 'src'))

from analyzer.newspaper4k_analyzer import Newspaper4kDomainAnalyzer

def test_vnexpress_improved():
    analyzer = Newspaper4kDomainAnalyzer()
    
    domain_name = "vnexpress.net"
    domain_url = "https://vnexpress.net"
    
    print(f"Testing {domain_name} with improved analysis...")
    print(f"URL: {domain_url}")
    print("=" * 50)
    
    # Test với improved analysis
    result = analyzer.analyze_domain(domain_url, domain_name)
    
    print(f"\n=== RESULTS ===")
    print(f"RSS Feeds: {len(result.get('rss_feeds', []))}")
    for i, rss in enumerate(result.get('rss_feeds', [])[:5], 1):
        print(f"  {i}. {rss}")
    
    print(f"\nSitemaps: {len(result.get('sitemaps', []))}")
    for i, sitemap in enumerate(result.get('sitemaps', [])[:3], 1):
        print(f"  {i}. {sitemap}")
    
    print(f"\nCategories: {len(result.get('category_urls', []))}")
    for i, cat in enumerate(result.get('category_urls', [])[:10], 1):
        print(f"  {i}. {cat}")
    
    print(f"\nHomepage: {len(result.get('homepage_urls', []))}")
    for i, home in enumerate(result.get('homepage_urls', []), 1):
        print(f"  {i}. {home}")
    
    print(f"\nCSS Selectors: {len(result.get('css_selectors', {}))}")
    for key, selectors in result.get('css_selectors', {}).items():
        print(f"  {key}: {len(selectors)} selectors")
    
    if result.get('analysis_errors'):
        print(f"\n=== ERRORS ===")
        for error in result['analysis_errors']:
            print(f"Error: {error}")
    
    # Save detailed results to file
    output_file = f"scripts/vnexpress_improved_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to: {output_file}")
    return result

if __name__ == "__main__":
    test_vnexpress_improved()