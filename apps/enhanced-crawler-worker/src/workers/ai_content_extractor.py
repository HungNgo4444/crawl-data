#!/usr/bin/env python3
"""
AI Content Extractor sử dụng Crawl4AI với LLMExtractionStrategy
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.types import LLMConfig, create_llm_config
from crawl4ai.async_configs import CrawlerRunConfig

class AIContentExtractor:
    def __init__(self):
        self.ollama_base_url = "http://crawler_ollama:11434"
        self.model_name = "qwen2.5:3b"
        
        # Load prompt từ file
        prompt_file = Path(__file__).parent.parent.parent.parent.parent / "prompts" / "vietnamese_news_extraction.txt"
        with open(prompt_file, "r", encoding="utf-8") as f:
            self.extraction_instruction = f.read()
        
        # Schema với nullable fields
        self.schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "author": {"type": ["string", "null"]},
                "publish_date": {"type": ["string", "null"]},
                "category": {"type": ["string", "null"]},
                "tags": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": ["string", "null"]},
                "url_image": {"type": ["string", "null"]}
            },
            "required": ["title", "content"]
        }
    
    async def extract(self, url: str) -> Dict[str, Any]:
        # Create proper LLMConfig object for Ollama
        llm_config = create_llm_config(
            provider=f"ollama/{self.model_name}",
            api_token="no-token",
            base_url=self.ollama_base_url
        )
        
        # Create extraction strategy với proper parameters
        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            instruction=self.extraction_instruction,
            schema=self.schema,
            extract_type="schema",  # FIXED: Correct parameter name
            verbose=False
        )
        
        # Create run config với all valid parameters
        run_config = CrawlerRunConfig(
            word_count_threshold=10,  # Lower threshold để capture more content
            extraction_strategy=extraction_strategy,
            # CSS selectors để target content chính
            css_selector="article, .post-content, .article-content, .content, .entry-content, [role='main'], main",
            # Đợi page load xong  
            wait_for="css:article, css:.content, css:main",
            # Timeout
            page_timeout=30000,
            verbose=False
        )
        
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            
            if result.success and result.extracted_content:
                try:
                    extracted_data = json.loads(result.extracted_content)
                    # Handle array response
                    if isinstance(extracted_data, list) and extracted_data:
                        extracted_data = extracted_data[0]
                    return extracted_data
                except json.JSONDecodeError as e:
                    return {
                        "error": "JSON parsing failed", 
                        "url": url,
                        "details": str(e)
                    }
            else:
                return {
                    "error": "Extraction failed", 
                    "url": url,
                    "details": getattr(result, 'error', 'Unknown error')
                }