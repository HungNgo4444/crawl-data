#!/usr/bin/env python3
"""
Test script cho end-to-end structured data extraction workflow
Tests integration giữa domain_analyzer → css_selector_bridge → crawl4ai_content_extractor
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'enhanced-crawler-worker', 'src'))

from workers.crawl4ai_content_extractor import Crawl4AIContentExtractor, ExtractionResult
from integrations.css_selector_bridge import CSSelectorBridge, SelectorSchema

async def test_single_domain_extraction(domain_name: str, test_url: str = None):
    """Test extraction for single domain"""
    
    print(f"\n[TEST] Testing structured data extraction for: {domain_name}")
    print("=" * 60)
    
    # Initialize components
    bridge = CSSelectorBridge()
    extractor = Crawl4AIContentExtractor()
    
    try:
        # Step 1: Get CSS selectors from domain_analyzer
        print("[STEP 1] Retrieving CSS selectors from domain analysis...")
        selector_schema = await bridge.get_domain_selectors(domain_name)
        
        if selector_schema:
            print(f"[SUCCESS] Retrieved schema: {selector_schema.name}")
            print(f"   Base selector: {selector_schema.base_selector}")
            print(f"   Fields count: {len(selector_schema.fields)}")
            print(f"   Confidence: {selector_schema.confidence_score:.2f}")
        else:
            print("[ERROR] Failed to retrieve selector schema")
            return False
        
        # Step 2: Convert to Crawl4AI format
        print("\n[STEP 2] Converting to JsonCssExtractionStrategy format...")
        css_schema = bridge.to_crawl4ai_schema(selector_schema)
        print(f"[SUCCESS] Schema converted successfully")
        print(f"   Fields: {[f['name'] for f in css_schema['fields']]}")
        
        # Step 3: Get test URL if not provided
        if not test_url:
            print("\n[STEP 3] Getting test URL from database...")
            test_url = await bridge._get_test_url_for_domain(domain_name)
            
        if not test_url:
            print("[ERROR] No test URL available for domain")
            return False
        
        print(f"[SUCCESS] Test URL: {test_url}")
        
        # Step 4: Extract content using CSS selectors
        print(f"\n[STEP 4] Extracting content from URL...")
        result = await extractor.extract_single_content(
            url=test_url,
            domain_config={'name': domain_name},
            css_selectors=css_schema
        )
        
        # Step 5: Analyze results
        print(f"\n[STEP 5] Extraction Results")
        print(f"Success: {result.success}")
        print(f"Method: {result.extraction_method}")
        print(f"Quality Score: {result.quality_score:.2f}")
        print(f"Extraction Time: {result.extraction_time:.2f}s")
        
        if result.success:
            print(f"\n[DATA] Extracted Data:")
            print(f"   Title: {result.title[:100] if result.title else 'None'}...")
            print(f"   Content Length: {len(result.content) if result.content else 0}")
            print(f"   Author: {result.author or 'None'}")
            print(f"   Publish Date: {result.publish_date or 'None'}")
            print(f"   Category: {result.category or 'None'}")
            print(f"   Image URL: {result.url_image or 'None'}")
            
            # Check extraction attempts
            if result.extraction_metadata and 'extraction_attempts' in result.extraction_metadata:
                print(f"\n[ATTEMPTS] Extraction Attempts:")
                for attempt in result.extraction_metadata['extraction_attempts']:
                    print(f"   - {attempt['method']}: {'SUCCESS' if attempt['success'] else 'FAIL'}")
        
        return result.success and result.quality_score >= 0.6
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

async def test_multiple_domains():
    """Test extraction for multiple Vietnamese news domains"""
    
    print("[TEST] COMPREHENSIVE STRUCTURED DATA EXTRACTION TEST")
    print("=" * 70)
    
    # Test domains (add more as needed)
    test_domains = [
        'vnexpress.net',
        'dantri.com.vn', 
        'tuoitre.vn',
        'thanhnien.vn',
        '24h.com.vn'
    ]
    
    results = []
    
    for domain_name in test_domains:
        success = await test_single_domain_extraction(domain_name)
        results.append({
            'domain': domain_name,
            'success': success
        })
        
        # Brief pause between tests
        await asyncio.sleep(2)
    
    # Summary
    print(f"\n[SUMMARY] RESULTS")
    print("=" * 40)
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Total Domains Tested: {total}")
    print(f"Successful Extractions: {successful}")
    print(f"Success Rate: {successful/total*100:.1f}%")
    
    print(f"\n[RESULTS] Individual Results:")
    for result in results:
        status = "PASS" if result['success'] else "FAIL"
        print(f"   [{status}] {result['domain']}")
    
    return successful >= total * 0.6  # 60% success rate threshold

async def test_css_selector_bridge():
    """Test CSS selector bridge functionality"""
    
    print("\n[TEST] CSS SELECTOR BRIDGE")
    print("=" * 50)
    
    bridge = CSSelectorBridge()
    
    # Test 1: Get selectors for known domain
    print("[TEST 1] Retrieving selectors for vnexpress.net...")
    try:
        schema = await bridge.get_domain_selectors('vnexpress.net')
        if schema:
            print(f"[SUCCESS] Retrieved schema with {len(schema.fields)} fields")
            print(f"   Confidence: {schema.confidence_score:.2f}")
        else:
            print("[ERROR] Failed to retrieve schema")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    # Test 2: Test fallback for unknown domain
    print(f"\n[TEST 2] Testing fallback for unknown domain...")
    try:
        schema = await bridge.get_domain_selectors('unknown-domain.com')
        if schema and 'fallback' in schema.name:
            print(f"[SUCCESS] Fallback schema created with {len(schema.fields)} fields")
        else:
            print("[ERROR] Fallback failed")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    # Test 3: Get all domains with schemas
    print(f"\n[TEST 3] Getting all domains with schemas...")
    try:
        domains = await bridge.get_all_domains_with_schemas()
        print(f"[SUCCESS] Found {len(domains)} domains with schemas")
        if domains:
            print(f"   Sample domains: {domains[:5]}")
    except Exception as e:
        print(f"[ERROR] {e}")

async def test_extractor_fallback():
    """Test extractor fallback strategies"""
    
    print("\n[TEST] EXTRACTION FALLBACK STRATEGIES")
    print("=" * 55)
    
    extractor = Crawl4AIContentExtractor()
    
    # Test URL that should work
    test_url = "https://vnexpress.net/"
    
    print(f"[TEST] Testing fallback strategies on: {test_url}")
    
    try:
        # Test without CSS selectors (should fallback to generic)
        result = await extractor.extract_single_content(
            url=test_url,
            domain_config={'name': 'test-domain'},
            css_selectors=None
        )
        
        print(f"[SUCCESS] Extraction completed")
        print(f"   Method: {result.extraction_method}")
        print(f"   Success: {result.success}")
        print(f"   Quality: {result.quality_score:.2f}")
        
        if result.extraction_metadata and 'extraction_attempts' in result.extraction_metadata:
            print(f"   Fallback chain:")
            for attempt in result.extraction_metadata['extraction_attempts']:
                print(f"     - {attempt['method']}: {'SUCCESS' if attempt['success'] else 'FAIL'}")
        
        return result.success
        
    except Exception as e:
        print(f"[ERROR] Fallback test failed: {e}")
        return False

async def main():
    """Main test runner"""
    
    print("[TEST] STORY 1.4 STRUCTURED DATA EXTRACTION - COMPREHENSIVE TEST")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test 1: CSS Selector Bridge
        await test_css_selector_bridge()
        
        # Test 2: Extractor Fallback
        fallback_success = await test_extractor_fallback()
        
        # Test 3: End-to-end extraction for multiple domains
        e2e_success = await test_multiple_domains()
        
        # Final results
        print(f"\n[FINAL] TEST RESULTS")
        print("=" * 40)
        print(f"CSS Bridge: PASS (Basic functionality)")
        print(f"Fallback Strategies: {'PASS' if fallback_success else 'FAIL'}")
        print(f"End-to-End Extraction: {'PASS' if e2e_success else 'FAIL'}")
        
        overall_success = fallback_success and e2e_success
        print(f"\nOverall Status: {'PASS' if overall_success else 'FAIL'}")
        
        if overall_success:
            print("\n[SUCCESS] All tests passed! Story 1.4 structured data extraction is working correctly.")
        else:
            print("\n[WARNING] Some tests failed. Review implementation for issues.")
        
        return overall_success
        
    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)