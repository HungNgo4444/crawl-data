#!/usr/bin/env python3
import asyncio
import json
import sys
from pathlib import Path

# Add path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "enhanced-crawler-worker" / "src"))

from workers.ai_content_extractor import AIContentExtractor

async def main():
    # Load URLs từ RSS file
    with open("scripts/rss_urls_20250822_164852.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Lấy 3 URLs mỗi domain
    test_urls = []
    domain_counts = {}
    
    for feed_key, feed_data in data["results"].items():
        domain = feed_data["domain"]
        if domain_counts.get(domain, 0) < 3:
            for item in feed_data["items"]:
                if domain_counts.get(domain, 0) >= 3:
                    break
                test_urls.append(item["url"])
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
    
    print(f"Testing {len(test_urls)} URLs")
    
    # Extract content
    extractor = AIContentExtractor()
    results = []
    
    for url in test_urls:
        print(f"Extracting: {url}")
        result = await extractor.extract(url)
        result["url"] = url
        results.append(result)
    
    # Export JSON
    output_file = f"scripts/ai_extraction_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main())