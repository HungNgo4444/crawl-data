#!/usr/bin/env python3
import asyncio
import json
import sys
from pathlib import Path

# Add path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "enhanced-crawler-worker" / "src"))

from workers.ai_content_extractor import AIContentExtractor

async def test_single_url():
    """Test với 1 URL để verify fix"""
    test_url = "https://vnexpress.net/roddick-alcaraz-sai-lam-khi-an-ui-sinner-4929954.html"
    
    print(f"Testing URL: {test_url}")
    
    try:
        extractor = AIContentExtractor()
        result = await extractor.extract(test_url)
        
        print("Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_single_url())