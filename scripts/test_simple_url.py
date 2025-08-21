import asyncio
import os
import json
from datetime import datetime
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

async def main():
    # Configure browser and crawler settings
    browser_config = BrowserConfig(headless=True)
    
    # Schema for content extraction (sử dụng schema đã fix)
    extraction_schema = {
        "name": "article_extractor",
        "baseSelector": "body",
        "fields": [
            {
                "name": "title",
                "selector": "h1.title-detail, h1.title-news, h1.detail-title, .title-detail, h1, meta[property='og:title']",
                "type": "text",
                "transform": "strip"
            },
            {
                "name": "content", 
                "selector": "article, .article-content, .entry-content, .post-content, main, .fck_detail",
                "type": "text",
                "transform": "strip"
            },
            {
                "name": "author",
                "selector": ".author, .by-author, .article-author, [rel='author'], meta[name='author']",
                "type": "text",
                "transform": "strip"
            },
            {
                "name": "publish_date",
                "selector": "time[datetime], .publish-date, .entry-date, meta[property='article:published_time']",
                "type": "attribute",
                "attribute": "datetime"
            },
            {
                "name": "category",
                "selector": ".category, .article-category, .breadcrumb li:last-child",
                "type": "text", 
                "transform": "strip"
            },
            {
                "name": "image_url",
                "selector": "meta[property='og:image'], article img, .featured-image img",
                "type": "attribute",
                "attribute": "content"
            }
        ]
    }
    
    run_config = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(schema=extraction_schema)
    )
    
    # Initialize the crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Set the URL you want to crawl
        url = "https://vnexpress.net/muong-thanh-se-day-nhanh-tien-do-du-an-tai-huyen-thanh-oai-cu-4929824.html"
        
        print(f"Testing extraction for: {url}")
        print("=" * 80)
        
        # Run the crawler
        result = await crawler.arun(url=url, config=run_config)
        
        # Display results
        print(f"Crawl successful: {result.success}")
        print(f"Status code: {result.status_code}")
        
        # Parse extracted content
        if result.extracted_content:
            try:
                extracted_data = json.loads(result.extracted_content)
                if isinstance(extracted_data, list) and extracted_data:
                    extracted_data = extracted_data[0]
                
                print("\n=== EXTRACTED DATA ===")
                print(f"Title: {extracted_data.get('title', 'None')}")
                print(f"Author: {extracted_data.get('author', 'None')}")
                print(f"Date: {extracted_data.get('publish_date', 'None')}")
                print(f"Category: {extracted_data.get('category', 'None')}")
                print(f"Image: {extracted_data.get('image_url', 'None')}")
                print(f"Content length: {len(extracted_data.get('content', ''))} chars")
                
                # Create output directory
                os.makedirs("output", exist_ok=True)
                
                # Save extracted data as JSON
                with open("output/extracted_data.json", "w", encoding='utf-8') as f:
                    json.dump(extracted_data, f, ensure_ascii=False, indent=2)
                
                print(f"\nExtracted data saved to: output/extracted_data.json")
                
            except json.JSONDecodeError as e:
                print(f"Error parsing extracted content: {e}")
                print(f"Raw extracted content: {result.extracted_content}")
        else:
            print("No extracted content found")
        
        # Save markdown
        with open("output/crawl_result.md", "w", encoding='utf-8') as f:
            f.write(result.markdown or "No markdown content")
        
        print(f"Markdown saved to: output/crawl_result.md")
        
        # Show metadata
        if result.metadata:
            print(f"\nMetadata title: {result.metadata.get('title', 'None')}")
            print(f"Metadata description: {result.metadata.get('description', 'None')[:100]}...")
        
        print(f"\nTotal processing time: {result.extraction_time if hasattr(result, 'extraction_time') else 'N/A'}")
        print("Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 