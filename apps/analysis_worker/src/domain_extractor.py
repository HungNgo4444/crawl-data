#!/usr/bin/env python3
"""
Simple Domain Data Extractor
Replaces complex AI processing with straightforward scraping
Author: James (Dev Agent)
Date: 2025-08-18
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse, parse_qs
import json
from datetime import datetime
import time
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional, Tuple
import logging
from dataclasses import dataclass
from pathlib import Path
import random

@dataclass
class ExtractionResult:
    """Result of domain extraction"""
    domain: str
    success: bool
    rss_feeds: List[str]
    sitemaps: List[str] 
    category_urls: List[str]
    total_sitemap_urls: int
    extraction_time: str
    error: Optional[str] = None

class DomainDataExtractor:
    """
    Complete domain data extractor for RSS, Sitemaps, and Categories
    Simple, fast, and reliable alternative to AI processing
    """
    
    def __init__(self, domain: str):
        self.domain = domain.rstrip('/')
        self.base_domain = urlparse(self.domain).netloc
        
        # Results
        self.rss_feeds: Set[str] = set()
        self.sitemaps: Set[str] = set()
        self.category_urls: Set[str] = set()
        
        # Rate limiting
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit_delay = 1.0  # Base delay between requests
        self.max_retries = 3
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _rate_limited_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make rate-limited HTTP request with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                # Apply rate limiting delay
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                
                if time_since_last < self.rate_limit_delay:
                    delay = self.rate_limit_delay - time_since_last
                    # Add jitter to avoid thundering herd
                    delay += random.uniform(0.1, 0.5)
                    time.sleep(delay)
                
                # Make request
                response = getattr(self.session, method.lower())(url, **kwargs)
                self.last_request_time = time.time()
                self.request_count += 1
                
                # Handle rate limiting response
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        delay = int(retry_after) + random.uniform(1, 3)
                    else:
                        # Exponential backoff
                        delay = (2 ** attempt) + random.uniform(0.5, 2.0)
                    
                    self.logger.warning(f"Rate limited (429), waiting {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                
                # Success or other non-retry status
                return response
                
            except requests.exceptions.Timeout:
                delay = (2 ** attempt) + random.uniform(0.5, 1.5)
                self.logger.warning(f"Timeout, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                time.sleep(delay)
                continue
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Request failed after {self.max_retries} attempts: {e}")
                    return None
                else:
                    delay = random.uniform(0.5, 1.5)
                    time.sleep(delay)
                    continue
        
        return None
    
    def _handle_domain_redirects(self):
        """Handle domain redirects and update working domain"""
        try:
            response = self._rate_limited_request('head', self.domain, timeout=10, allow_redirects=True)
            
            if response and response.url != self.domain:
                original_domain = self.domain
                self.domain = response.url.rstrip('/')
                self.base_domain = urlparse(self.domain).netloc
                
                self.logger.info(f"  Domain redirected: {original_domain} → {self.domain}")
            
        except Exception as e:
            self.logger.warning(f"Error checking domain redirects: {e}")
    
    def extract_all_data(self) -> ExtractionResult:
        """Extract all domain data: RSS, Sitemaps, Categories"""
        start_time = time.time()
        
        self.logger.info(f"🔍 Starting extraction for: {self.domain}")
        
        try:
            # 0. Handle domain redirects first
            self._handle_domain_redirects()
            
            # 1. Extract homepage for RSS and Category discovery
            self._extract_from_homepage()
            
            # 2. Extract sitemaps
            self._extract_sitemaps()
            
            # 3. Extract categories from common paths
            self._extract_categories()
            
            duration = time.time() - start_time
            
            result = ExtractionResult(
                domain=self.domain,
                success=True,
                rss_feeds=list(self.rss_feeds),
                sitemaps=list(self.sitemaps),
                category_urls=list(self.category_urls),
                total_sitemap_urls=len(self.sitemaps),
                extraction_time=f"{duration:.2f}s"
            )
            
            self.logger.info(f"✅ Extraction completed: RSS({len(result.rss_feeds)}), Sitemaps({len(result.sitemaps)}), Categories({len(result.category_urls)})")
            return result
            
        except Exception as e:
            error_msg = f"Extraction failed: {e}"
            self.logger.error(error_msg)
            
            return ExtractionResult(
                domain=self.domain,
                success=False,
                rss_feeds=[],
                sitemaps=[],
                category_urls=[],
                total_sitemap_urls=0,
                extraction_time=f"{time.time() - start_time:.2f}s",
                error=error_msg
            )
    
    def _extract_from_homepage(self):
        """Extract RSS feeds and categories from homepage"""
        try:
            self.logger.info("📄 Analyzing homepage...")
            response = self._rate_limited_request('get', self.domain, timeout=15)
            
            if not response or response.status_code != 200:
                self.logger.warning(f"Homepage returned {response.status_code if response else 'No response'}")
                return
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract RSS feeds from <link> tags
            self._find_rss_feeds_in_html(soup)
            
            # Extract categories from navigation
            self._find_categories_in_navigation(soup)
            
        except Exception as e:
            self.logger.warning(f"Homepage analysis failed: {e}")
    
    def _find_rss_feeds_in_html(self, soup: BeautifulSoup):
        """Find RSS feeds in HTML <link> tags"""
        # RSS/Atom feed links in <head>
        rss_links = soup.find_all('link', {
            'type': ['application/rss+xml', 'application/atom+xml', 'application/rdf+xml']
        })
        
        for link in rss_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.domain, href)
                if self._is_valid_rss_url(full_url):
                    self.rss_feeds.add(full_url)
        
        # Look for RSS links in content
        rss_patterns = [
            r'href=["\']([^"\']*(?:rss|feed|atom)[^"\']*)["\']',
            r'href=["\']([^"\']*\.(?:rss|xml|atom))["\']'
        ]
        
        content = str(soup)
        for pattern in rss_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                full_url = urljoin(self.domain, match)
                if self._is_valid_rss_url(full_url):
                    self.rss_feeds.add(full_url)
        
        # Common RSS paths
        common_rss_paths = [
            '/rss.xml', '/feed.xml', '/feeds/all.rss', '/rss/',
            '/feed/', '/atom.xml', '/index.xml', '/rss/news.xml'
        ]
        
        for path in common_rss_paths:
            rss_url = f"{self.domain}{path}"
            if self._verify_rss_feed(rss_url):
                self.rss_feeds.add(rss_url)
    
    def _find_categories_in_navigation(self, soup: BeautifulSoup):
        """Find category URLs in navigation elements"""
        # Look in nav elements
        nav_elements = soup.find_all(['nav', 'menu'])
        
        # Also check common navigation classes/ids
        nav_selectors = [
            '[class*="nav"]', '[class*="menu"]', '[class*="category"]',
            '[id*="nav"]', '[id*="menu"]', '[class*="section"]'
        ]
        
        for selector in nav_selectors:
            nav_elements.extend(soup.select(selector))
        
        vietnamese_category_keywords = [
            'thời sự', 'kinh tế', 'xã hội', 'thể thao', 'giải trí', 'công nghệ',
            'sức khỏe', 'giáo dục', 'pháp luật', 'quốc tế', 'địa phương', 'văn hóa',
            'chuyên mục', 'danh mục', 'tin tức', 'bài viết', 'chủ đề'
        ]
        
        for nav_element in nav_elements:
            links = nav_element.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                text = link.get_text().strip().lower()
                
                if href and text:
                    # Check if this looks like a category
                    is_category = (
                        any(keyword in text for keyword in vietnamese_category_keywords) or
                        any(keyword in href.lower() for keyword in ['category', 'chuyen-muc', 'tin-tuc', 'section']) or
                        (len(text) > 2 and len(text) < 30 and '/' in href)
                    )
                    
                    if is_category:
                        full_url = urljoin(self.domain, href)
                        if self._is_valid_category_url(full_url):
                            self.category_urls.add(full_url)
    
    def _extract_sitemaps(self):
        """Extract sitemap URLs only (no parsing content)"""
        self.logger.info("🗺️ Extracting sitemap URLs...")
        
        # 1. Find from robots.txt
        robots_sitemaps = self._find_sitemaps_from_robots()
        
        # 2. Try common sitemap URLs
        common_sitemaps = self._try_common_sitemap_urls()
        
        # 3. Find from HTML meta tags and links
        html_sitemaps = self._find_sitemaps_from_html()
        
        # 4. Collect and deduplicate sitemap URLs
        all_sitemap_urls = robots_sitemaps + common_sitemaps + html_sitemaps
        
        # Advanced deduplication and validation
        deduplicated_sitemaps = self._deduplicate_and_validate_sitemaps(all_sitemap_urls)
        
        for sitemap_url in deduplicated_sitemaps:
            self.sitemaps.add(sitemap_url)
        
        self.logger.info(f"  Found {len(self.sitemaps)} sitemap URLs total (after deduplication)")
    
    def _find_sitemaps_from_robots(self) -> List[str]:
        """Enhanced sitemap discovery from robots.txt"""
        robots_url = f"{self.domain}/robots.txt"
        sitemaps = []
        
        try:
            response = self.session.get(robots_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                lines = content.split('\n')
                
                for line in lines:
                    line = line.strip()
                    # Standard sitemap declarations (case insensitive)
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        # Handle protocol-relative URLs
                        if sitemap_url.startswith('//'):
                            sitemap_url = f"https:{sitemap_url}"
                        elif not sitemap_url.startswith(('http://', 'https://')):
                            sitemap_url = urljoin(self.domain, sitemap_url)
                        sitemaps.append(sitemap_url)
                        self.logger.info(f"  Found in robots.txt: {sitemap_url}")
                
                # Also look for sitemap mentions in comments
                for line in lines:
                    if 'sitemap' in line.lower() and ('http' in line or '.xml' in line):
                        # Extract URLs from comments like "# Sitemap: https://..."
                        urls = re.findall(r'https?://[^\s]+\.xml', line)
                        for url in urls:
                            if url not in sitemaps:
                                sitemaps.append(url)
                                self.logger.info(f"  Found in robots comment: {url}")
                        
        except Exception as e:
            self.logger.warning(f"Error reading robots.txt: {e}")
            
        return sitemaps
    
    def _find_sitemaps_from_html(self) -> List[str]:
        """Find sitemap URLs from HTML content"""
        sitemaps = []
        
        try:
            response = self.session.get(self.domain, timeout=10)
            if response.status_code != 200:
                return sitemaps
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Look for sitemap links in <head>
            sitemap_links = soup.find_all('link', attrs={'rel': 'sitemap'})
            for link in sitemap_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.domain, href)
                    sitemaps.append(full_url)
                    self.logger.info(f"  Found in HTML link: {full_url}")
            
            # 2. Look for sitemap mentions in HTML content
            content = str(soup).lower()
            sitemap_urls = re.findall(r'https?://[^\s"\'<>]+sitemap[^\s"\'<>]*\.xml', content)
            for url in sitemap_urls:
                if self.base_domain in url and url not in sitemaps:
                    sitemaps.append(url)
                    self.logger.info(f"  Found in HTML content: {url}")
            
            # 3. Look for footer sitemap links
            footer_elements = soup.find_all(['footer', 'div'], attrs={'class': re.compile(r'footer|bottom', re.I)})
            for footer in footer_elements:
                links = footer.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '').lower()
                    if 'sitemap' in href or 'site-map' in href:
                        full_url = urljoin(self.domain, link.get('href'))
                        if full_url not in sitemaps:
                            sitemaps.append(full_url)
                            self.logger.info(f"  Found in footer: {full_url}")
            
        except Exception as e:
            self.logger.warning(f"Error extracting sitemaps from HTML: {e}")
        
        return sitemaps
    
    def _try_common_sitemap_urls(self) -> List[str]:
        """Try comprehensive sitemap URL patterns for Vietnamese sites"""
        common_paths = [
            # Standard sitemap patterns
            '/sitemap.xml', '/sitemap_index.xml', '/sitemaps.xml',
            '/sitemap/sitemap.xml', '/sitemaps/sitemap.xml',
            '/wp-sitemap.xml', '/post-sitemap.xml', '/sitemap/index.xml',
            
            # Vietnamese news site patterns
            '/site-map.xml', '/sitemap-index.xml', '/sitemap_main.xml',
            '/sitemaps/index.xml', '/sitemaps/main.xml', '/maps/sitemap.xml',
            '/feed/sitemap.xml', '/rss/sitemap.xml',
            
            # CMS specific patterns
            '/sitemap-articles.xml', '/sitemap-news.xml', '/sitemap-posts.xml',
            '/sitemaps/articles.xml', '/sitemaps/news.xml', '/sitemaps/posts.xml',
            
            # Government/official site patterns (for baochinhphu.vn)
            '/sitemap-content.xml', '/sitemap-pages.xml', '/maps/site-map.xml',
            '/content/sitemap.xml', '/pages/sitemap.xml',
            
            # Alternative extensions
            '/sitemap.php', '/sitemap.aspx', '/sitemap.htm', '/sitemap.html'
        ]
        
        sitemaps = []
        for path in common_paths:
            url = f"{self.domain}{path}"
            try:
                response = self.session.head(url, timeout=8)
                if response.status_code == 200:
                    # Additional check for content-type
                    content_type = response.headers.get('content-type', '').lower()
                    if any(ct in content_type for ct in ['xml', 'text', 'html']):
                        sitemaps.append(url)
                        self.logger.info(f"  Found sitemap: {url}")
            except Exception as e:
                continue
                
        return sitemaps
    
    def _extract_categories(self):
        """Extract categories from common URL patterns"""
        self.logger.info("📂 Extracting category patterns...")
        
        # Common Vietnamese news category patterns
        common_category_patterns = [
            '/thoi-su', '/kinh-te', '/xa-hoi', '/the-thao', '/giai-tri',
            '/cong-nghe', '/suc-khoe', '/giao-duc', '/phap-luat', '/quoc-te',
            '/dia-phuong', '/van-hoa', '/du-lich', '/oto-xe-may', '/nha-dat',
            '/tai-chinh', '/chung-khoan', '/doanh-nghiep', '/startup',
            '/chuyen-muc', '/tin-tuc', '/bao-chi', '/news', '/category'
        ]
        
        extensions = ['', '.html', '.htm', '.php', '/']
        
        for pattern in common_category_patterns:
            for ext in extensions:
                test_url = f"{self.domain}{pattern}{ext}"
                
                try:
                    response = self.session.head(test_url, timeout=5)
                    if response.status_code == 200:
                        self.category_urls.add(test_url)
                        break  # Found working variant
                except:
                    continue
    
    def _is_valid_rss_url(self, url: str) -> bool:
        """Check if URL looks like a valid RSS feed"""
        if not url or not url.startswith(('http://', 'https://')):
            return False
        
        parsed = urlparse(url)
        if parsed.netloc != self.base_domain:
            return False
        
        # RSS indicators
        rss_indicators = ['rss', 'feed', 'atom', 'xml']
        return any(indicator in url.lower() for indicator in rss_indicators)
    
    def _is_valid_category_url(self, url: str) -> bool:
        """Check if URL looks like a valid category page"""
        if not url or not url.startswith(('http://', 'https://')):
            return False
        
        parsed = urlparse(url)
        if parsed.netloc != self.base_domain:
            return False
        
        # Avoid files, admin pages, search pages
        avoid_patterns = [
            '.jpg', '.png', '.gif', '.css', '.js', '.pdf',
            'admin', 'login', 'search', 'api', 'ajax'
        ]
        
        return not any(pattern in url.lower() for pattern in avoid_patterns)
    
    def _looks_like_category_page(self, url: str) -> bool:
        """Check if sitemap URL looks like category page"""
        category_indicators = [
            'category', 'chuyen-muc', 'danh-muc', 'section',
            'thoi-su', 'kinh-te', 'xa-hoi', 'the-thao', 'giai-tri'
        ]
        
        return any(indicator in url.lower() for indicator in category_indicators)
    
    def _verify_rss_feed(self, url: str) -> bool:
        """Verify if URL is actually an RSS feed"""
        try:
            response = self.session.head(url, timeout=5)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                return any(rss_type in content_type for rss_type in [
                    'application/rss+xml', 'application/atom+xml', 
                    'application/xml', 'text/xml'
                ])
        except:
            pass
        return False
    
    def _deduplicate_and_validate_sitemaps(self, sitemap_urls: List[str]) -> List[str]:
        """Advanced deduplication and validation of sitemap URLs"""
        if not sitemap_urls:
            return []
        
        # Step 1: Basic deduplication by URL
        unique_urls = list(set(sitemap_urls))
        
        # Step 2: Normalize URLs for better deduplication
        normalized_urls = {}
        for url in unique_urls:
            normalized = self._normalize_sitemap_url(url)
            if normalized not in normalized_urls:
                normalized_urls[normalized] = url
        
        # Step 3: Validate and prioritize sitemaps
        validated_sitemaps = []
        for normalized_url, original_url in normalized_urls.items():
            if self._validate_sitemap_url(original_url):
                validated_sitemaps.append(original_url)
        
        # Step 4: Limit excessive sitemaps (max 15 per domain)
        if len(validated_sitemaps) > 15:
            self.logger.warning(f"  Too many sitemaps ({len(validated_sitemaps)}), limiting to 15 most relevant")
            # Prioritize: robots.txt > common paths > HTML discovered
            prioritized = self._prioritize_sitemaps(validated_sitemaps)
            validated_sitemaps = prioritized[:15]
        
        self.logger.info(f"  Deduplication: {len(sitemap_urls)} -> {len(validated_sitemaps)} sitemaps")
        return validated_sitemaps
    
    def _normalize_sitemap_url(self, url: str) -> str:
        """Normalize sitemap URL for deduplication"""
        # Remove trailing slashes, fragments, and query params for comparison
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url.lower())
        # Remove query and fragment
        normalized = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path.rstrip('/'),
            '', '', ''
        ))
        return normalized
    
    def _validate_sitemap_url(self, url: str) -> bool:
        """Validate if sitemap URL is accessible and valid"""
        try:
            if not url or not url.startswith(('http://', 'https://')):
                return False
            
            # Quick HEAD request to check accessibility
            response = self.session.head(url, timeout=5)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                # Accept XML, HTML, or text content types for sitemaps
                if any(ct in content_type for ct in ['xml', 'text', 'html', 'application']):
                    return True
            
            return False
        except Exception:
            return False
    
    def _prioritize_sitemaps(self, sitemaps: List[str]) -> List[str]:
        """Prioritize sitemaps by source and importance"""
        prioritized = []
        
        # Priority 1: Main sitemap files
        main_patterns = ['sitemap.xml', 'sitemap_index.xml', 'sitemaps.xml']
        for pattern in main_patterns:
            for sitemap in sitemaps:
                if pattern in sitemap.lower() and sitemap not in prioritized:
                    prioritized.append(sitemap)
        
        # Priority 2: Robots.txt discovered sitemaps
        for sitemap in sitemaps:
            if 'robots' not in sitemap.lower() and sitemap not in prioritized:
                prioritized.append(sitemap)
        
        # Priority 3: Remaining sitemaps
        for sitemap in sitemaps:
            if sitemap not in prioritized:
                prioritized.append(sitemap)
        
        return prioritized

class DomainProcessingManager:
    """Manages domain processing using simple extraction"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def process_domain(self, domain_data: Dict) -> bool:
        """Process a single domain"""
        domain_id = domain_data['id']
        domain_name = domain_data['name']
        base_url = domain_data['base_url']
        
        self.logger.info(f"🔄 Processing domain: {domain_name}")
        
        try:
            # Extract data
            extractor = DomainDataExtractor(base_url)
            result = extractor.extract_all_data()
            
            if not result.success:
                self.logger.error(f"❌ Failed to extract data for {domain_name}: {result.error}")
                return False
            
            # Store in database
            success = self._store_extraction_results(domain_id, result)
            
            if success:
                self.logger.info(f"✅ Successfully processed {domain_name}")
                return True
            else:
                self.logger.error(f"❌ Failed to store results for {domain_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error processing {domain_name}: {e}")
            return False
    
    def _store_extraction_results(self, domain_id: int, result: ExtractionResult) -> bool:
        """Store extraction results in database"""
        try:
            # Update domain record
            update_data = {
                'rss_feeds': json.dumps(result.rss_feeds),
                'sitemaps': json.dumps(result.sitemaps), 
                'css_selectors': json.dumps(result.category_urls),  # Store categories in css_selectors
                'last_analyzed_at': datetime.now(),
                'analysis_model': 'simple-extractor-v1'
            }
            
            return self.db_manager.update_domain_analysis(domain_id, update_data)
            
        except Exception as e:
            self.logger.error(f"Database storage error: {e}")
            return False
    
    def process_all_domains(self) -> Dict:
        """Process all active domains"""
        self.logger.info("🚀 Starting domain processing...")
        
        # Get active domains
        domains = self.db_manager.get_domains()
        if not domains:
            return {'success': False, 'error': 'No active domains found'}
        
        results = {
            'total_domains': len(domains),
            'successful': 0,
            'failed': 0,
            'processed_domains': []
        }
        
        for domain in domains:
            domain_name = domain['name']
            success = self.process_domain(domain)
            
            results['processed_domains'].append({
                'name': domain_name,
                'success': success
            })
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        self.logger.info(f"🏁 Processing completed: {results['successful']}/{results['total_domains']} successful")
        return results