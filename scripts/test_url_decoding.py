#!/usr/bin/env python3
"""
Test script for URL decoding functionality
"""

import sys
from pathlib import Path
from urllib.parse import unquote

def _clean_url_artifacts(url: str) -> str:
    """Clean XML artifacts, decode URL encoding and fix Vietnamese characters"""
    try:
        # Remove common XML artifacts
        artifacts = [']]></link>', ']]>', '</link>', '<![CDATA[', ']]']
        
        for artifact in artifacts:
            url = url.replace(artifact, '')
        
        # Remove CDATA prefix if exists
        if url.startswith('<![CDATA['):
            url = url[9:]  # Remove '<![CDATA['
        
        # FIX URL ENCODING: Decode Vietnamese characters from newspaper4k
        try:
            # Decode URL encoding like %C3%A1 -> á, %E1%BA%A5 -> ấ
            decoded_url = unquote(url)
            
            # Replace + with spaces (common in URL encoding)
            decoded_url = decoded_url.replace('+', ' ')
            
            # Only use decoded version if it looks better (has Vietnamese chars)
            if any(ord(c) > 127 for c in decoded_url) or ' ' in decoded_url:
                url = decoded_url
                print(f"URL decoded: {url[:100]}...")
                
        except Exception as e:
            print(f"URL decoding failed for {url[:100]}: {e}")
            
        return url.strip()
        
    except Exception as e:
        print(f"Error cleaning URL artifacts from {url}: {e}")
        return url

def test_url_decoding():
    """Test URL decoding with problematic URLs"""
    
    # Test URLs with encoding issues
    test_urls = [
        "https://english.vov.vn/tag/%C3%A1p+th%E1%BA%A5p+nhi%E1%BB%87t+%C4%91%E1%BB%9Bi+tr%C3%AAn+bi%E1%BB%83n+%C4%91%C3%B4ng",
        "https://vov4.vov.vn/tag/T%E1%BB%95ng+%C9%83%C3%AD+th%C6%B0+%E1%BB%93ng+T%C3%B4+L%C3%A2m",
        "https://english.vov.vn/en/tag/biofuel+E10",
        "https://vnexpress.net/tag/b%C3%A1o-c%C3%A1o",
        "https://thanhnien.vn/tag/gi%C3%A1-x%C4%83ng-d%E1%BA%A7u"
    ]
    
    print("Testing URL decoding functionality...")
    print("=" * 80)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Original URL:")
        print(f"   {url}")
        
        # Test URL cleaning
        cleaned_url = _clean_url_artifacts(url)
        print(f"   After cleaning: {cleaned_url}")
        
        # Manual decode test
        try:
            manual_decode = unquote(url).replace('+', ' ')
            print(f"   Manual decode: {manual_decode}")
        except Exception as e:
            print(f"   Manual decode failed: {e}")
        
        print(f"   Length diff: {len(url)} -> {len(cleaned_url)}")

if __name__ == "__main__":
    test_url_decoding()