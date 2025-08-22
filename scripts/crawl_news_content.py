#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import asyncio
import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import traceback

# Fix Windows console encoding
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator



def clean_content(content):
    """Clean content by removing javascript links, images, and duplicate text"""
    import re
    
    lines = content.split('\n')
    cleaned_lines = []
    seen_lines = set()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip javascript links
        if re.search(r'\[\]\(javascript:', line):
            continue
            
        # Skip image markdown
        if re.search(r'!\[.*\]\(https?://', line):
            continue
            
        # Skip author info patterns
        if re.search(r'\*\*[A-Za-z\s]+\*\*\s*\(theo\s+_.*_\)', line):
            continue
            
        # Remove duplicate lines
        if line not in seen_lines:
            seen_lines.add(line)
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def get_content_selector(domain):
    """Get specific content selector for each domain to avoid navigation/ads"""
    selectors = {
        'vnexpress.net': '.fck_detail, .Normal, .content_detail, article .content-detail',
        'dantri.com.vn': '.dt-news__content, .news-content, .article-content, #ctl00_IDContent_ctl00_divContent',
        'tuoitre.vn': '.detail-content, .article-content, #main-detail-body, .content',
        'thanhnien.vn': '.details__content, .article-body, .pswp-content, .content',
        'www.24h.com.vn': '.ArticleContent, .cate-24h-foot-arti-deta, .article-content',
        '24h.com.vn': '.ArticleContent, .cate-24h-foot-arti-deta, .article-content'
    }
    return selectors.get(domain, 'article, .content, .article-content, .news-content, main')


def load_rss_urls(file_path):
    """Load RSS URLs from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading RSS URLs file: {e}")
        return None


def group_urls_by_domain(rss_data):
    """Group URLs by domain and limit to 3 URLs per domain"""
    domain_urls = defaultdict(list)
    
    if 'results' not in rss_data:
        return domain_urls
        
    for feed_key, feed_data in rss_data['results'].items():
        if 'urls' in feed_data and 'domain' in feed_data:
            domain = feed_data['domain']
            urls = feed_data['urls'][:3]  # Limit to 3 URLs per domain
            domain_urls[domain].extend(urls)
    
    # Ensure max 3 URLs per domain
    for domain in domain_urls:
        domain_urls[domain] = domain_urls[domain][:3]
    
    return dict(domain_urls)


def get_css_schema_for_domain(domain):
    """Get CSS schema for different news domains"""
    
    # Common Vietnamese news site schemas
    schemas = {
        'vnexpress.net': {
            'name': 'vnexpress_article',
            'baseSelector': 'body',
            'fields': [
                {
                    'name': 'title',
                    'selector': 'h1.title-detail, h1.title_news_detail, .title-detail',
                    'type': 'text'
                },
                {
                    'name': 'content',
                    'selector': '.fck_detail, .Normal, article .content-detail, .content_detail',
                    'type': 'text'
                },
                {
                    'name': 'description',
                    'selector': '.description, .lead, .sapo',
                    'type': 'text'
                },
                {
                    'name': 'publish_time',
                    'selector': '.date, .time, .publish_time',
                    'type': 'text'
                }
            ]
        },
        'dantri.com.vn': {
            'name': 'dantri_article',
            'baseSelector': 'body',
            'fields': [
                {
                    'name': 'title',
                    'selector': 'h1, .article-title, .news-title',
                    'type': 'text'
                },
                {
                    'name': 'content',
                    'selector': '.news-content, .article-content, .dt-news__content',
                    'type': 'text'
                },
                {
                    'name': 'description',
                    'selector': '.news-sapo, .article-sapo, .dt-news__sapo',
                    'type': 'text'
                }
            ]
        },
        'tuoitre.vn': {
            'name': 'tuoitre_article',
            'baseSelector': 'body',
            'fields': [
                {
                    'name': 'title',
                    'selector': 'h1, .article-title, .detail-title',
                    'type': 'text'
                },
                {
                    'name': 'content',
                    'selector': '.detail-content, .article-content, #main-detail-body',
                    'type': 'text'
                },
                {
                    'name': 'description',
                    'selector': '.sapo, .detail-sapo',
                    'type': 'text'
                }
            ]
        },
        'thanhnien.vn': {
            'name': 'thanhnien_article',
            'baseSelector': 'body',
            'fields': [
                {
                    'name': 'title',
                    'selector': 'h1, .article-title, .details__headline',
                    'type': 'text'
                },
                {
                    'name': 'content',
                    'selector': '.details__content, .article-body, .pswp-content',
                    'type': 'text'
                },
                {
                    'name': 'description',
                    'selector': '.details__summary, .sapo',
                    'type': 'text'
                }
            ]
        },
        '24h.com.vn': {
            'name': '24h_article',
            'baseSelector': 'body',
            'fields': [
                {
                    'name': 'title',
                    'selector': 'h1, .article-title, .cate-24h-foot-arti-title',
                    'type': 'text'
                },
                {
                    'name': 'content',
                    'selector': '.article-content, .cate-24h-foot-arti-deta, .ArticleContent',
                    'type': 'text'
                },
                {
                    'name': 'description',
                    'selector': '.article-sapo, .sapo',
                    'type': 'text'
                }
            ]
        }
    }
    
    # Default generic schema if domain not found
    default_schema = {
        'name': 'generic_article',
        'baseSelector': 'body',
        'fields': [
            {
                'name': 'title',
                'selector': 'h1, title, .title, .article-title, .news-title, .post-title',
                'type': 'text'
            },
            {
                'name': 'content',
                'selector': 'article, .article, .content, .article-content, .news-content, .post-content, main p',
                'type': 'text'
            },
            {
                'name': 'description',
                'selector': '.description, .sapo, .lead, .excerpt, .summary',
                'type': 'text'
            }
        ]
    }
    
    return schemas.get(domain, default_schema)


async def crawl_urls(domain_urls):
    """Crawl URLs using AsyncWebCrawler with JsonCssExtractionStrategy"""
    results = {}
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        for domain, urls in domain_urls.items():
            print(f"\nCrawling domain: {domain}")
            results[domain] = []
            
            # Get CSS schema for this domain
            schema = get_css_schema_for_domain(domain)
            extraction_strategy = JsonCssExtractionStrategy(schema)
            
            for i, url in enumerate(urls, 1):
                print(f"  Crawling URL {i}/3: {url}")
                try:
                    # Configure crawler run with content filtering
                    config = CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        extraction_strategy=extraction_strategy,
                        word_count_threshold=10,
                        markdown_generator=DefaultMarkdownGenerator(
                            content_filter=PruningContentFilter()
                        ),
                        css_selector=get_content_selector(domain)
                    )
                    
                    result = await crawler.arun(url=url, config=config)
                    
                    if result.success:
                        # Parse extracted data
                        extracted_data = {}
                        if result.extracted_content:
                            try:
                                content_data = json.loads(result.extracted_content)
                                if isinstance(content_data, list) and len(content_data) > 0:
                                    extracted_data = content_data[0]
                                elif isinstance(content_data, dict):
                                    extracted_data = content_data
                            except json.JSONDecodeError:
                                print(f"    Failed to parse extracted JSON for {url}")
                        
                        article_data = {
                            'url': url,
                            'success': True,
                            'domain': domain,
                            'title': extracted_data.get('title', '').strip(),
                            'content': extracted_data.get('content', '').strip(),
                            'description': extracted_data.get('description', '').strip(),
                            'publish_time': extracted_data.get('publish_time', '').strip(),
                            'raw_content': result.markdown.strip() if result.markdown else '',
                            'crawled_at': datetime.now().isoformat(),
                            'word_count': len(result.markdown.split()) if result.markdown else 0
                        }
                        
                        results[domain].append(article_data)
                        print(f"    Success - Title: {article_data['title'][:100]}...")
                        
                    else:
                        error_data = {
                            'url': url,
                            'success': False,
                            'domain': domain,
                            'error': result.error_message if hasattr(result, 'error_message') else 'Unknown error',
                            'crawled_at': datetime.now().isoformat()
                        }
                        results[domain].append(error_data)
                        print(f"    Failed: {error_data['error']}")
                        
                except Exception as e:
                    error_data = {
                        'url': url,
                        'success': False,
                        'domain': domain,
                        'error': str(e),
                        'crawled_at': datetime.now().isoformat()
                    }
                    results[domain].append(error_data)
                    print(f"    Exception: {str(e)}")
                
                # Small delay between requests
                await asyncio.sleep(1)
    
    return results


def save_results_md(results, output_file):
    """Save crawl results to Markdown file"""
    md_content = []
    md_content.append(f"# News Content Crawl Results")
    md_content.append(f"\nCrawled at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    total_success = 0
    total_failed = 0
    
    for domain, domain_results in results.items():
        if not domain_results:  # Skip empty domains
            continue
            
        success_count = sum(1 for r in domain_results if r.get('success', False))
        failed_count = len(domain_results) - success_count
        total_success += success_count
        total_failed += failed_count
        
        md_content.append(f"## {domain}")
        md_content.append(f"Success: {success_count}, Failed: {failed_count}\n")
        
        for i, article in enumerate(domain_results, 1):
            if article.get('success', False):
                title = article.get('title', 'No title').strip() or 'No title extracted'
                content = article.get('content', '').strip()
                description = article.get('description', '').strip()
                
                md_content.append(f"### Article {i}")
                md_content.append(f"**URL:** {article['url']}")
                md_content.append(f"**Title:** {title}")
                
                if description:
                    md_content.append(f"**Description:** {description}")
                
                # Show cleaned raw content
                raw_content = article.get('raw_content', '').strip()
                if raw_content:
                    cleaned_content = clean_content(raw_content)
                    md_content.append(f"**Content:**")
                    md_content.append(f"```")
                    md_content.append(cleaned_content)
                    md_content.append(f"```")
                else:
                    md_content.append(f"**Content:** [No raw content available]")
                
                md_content.append(f"**Word Count:** {article.get('word_count', 0)}")
                md_content.append("")
            else:
                md_content.append(f"### Article {i} (FAILED)")
                md_content.append(f"**URL:** {article['url']}")
                md_content.append(f"**Error:** {article.get('error', 'Unknown error')}")
                md_content.append("")
    
    md_content.append(f"---")
    md_content.append(f"**Overall Summary:** {total_success} successful, {total_failed} failed")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))
        print(f"\nResults saved to: {output_file}")
        return True
    except Exception as e:
        print(f"\nError saving results: {e}")
        return False


async def main():
    """Main function"""
    print("Starting News Content Crawler using Crawl4AI")
    
    # File paths
    rss_file = Path("F:/Crawl data/scripts/rss_urls_20250821_202405.json")
    output_file = Path("F:/Crawl data/scripts/crawled_news_content.md")
    
    # Load RSS URLs
    print(f"Loading RSS URLs from: {rss_file}")
    rss_data = load_rss_urls(rss_file)
    if not rss_data:
        return
    
    # Group URLs by domain (3 per domain) and skip empty ones
    domain_urls = group_urls_by_domain(rss_data)
    domain_urls = {k: v for k, v in domain_urls.items() if v}  # Skip empty domains
    print(f"Found {len(domain_urls)} domains with URLs to crawl:")
    for domain, urls in domain_urls.items():
        print(f"  - {domain}: {len(urls)} URLs")
    
    # Crawl URLs
    print("\nStarting crawl process...")
    results = await crawl_urls(domain_urls)
    
    # Save results to markdown
    if save_results_md(results, output_file):
        # Print summary
        print("\nCrawl Summary:")
        total_success = 0
        total_failed = 0
        
        for domain, domain_results in results.items():
            success_count = sum(1 for r in domain_results if r.get('success', False))
            failed_count = len(domain_results) - success_count
            total_success += success_count
            total_failed += failed_count
            print(f"  {domain}: {success_count} success, {failed_count} failed")
        
        print(f"\nOverall: {total_success} successful, {total_failed} failed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        traceback.print_exc()