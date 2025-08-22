#!/usr/bin/env python3
"""
Extract HTML using Crawl4AI
"""

import asyncio
import os
import sys


async def extract_html():
    # Tắt output để tránh encoding error
    old_stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    
    try:
        from crawl4ai import AsyncWebCrawler
        
        url = "https://thanhnien.vn/di-xe-bus-bat-tau-dien-tu-som-de-kip-xem-tong-hop-luyen-dieu-binh-185250821191947493.htm"
        
        # Crawler cơ bản
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url)
            
            if result.success:
                # Save HTML
                output_file = "F:/Crawl data/output/thanhnien.html"
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result.html)
                
                print(f"HTML extracted and saved to: {output_file}")
                print(f"HTML length: {len(result.html)} characters")
                
            else:
                print("Failed to extract HTML")
                
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        sys.stderr.close()
        sys.stderr = old_stderr


if __name__ == "__main__":
    asyncio.run(extract_html())