#!/usr/bin/env python3
"""
Domain Data Extractor - Clean and Simple
Extracts RSS feeds, sitemaps, and categories from domains
Author: James (Dev Agent)
Date: 2025-08-22
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime
import time
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass

@dataclass
class ExtractionResult:
    """Result of domain extraction"""
    domain: str
    success: bool
    rss_feeds: List[str]
    sitemaps: List[str] 
    category_urls: List[str]
    extraction_time: str
    error: Optional[str] = None

class DomainDataExtractor:
    """Simple and reliable domain data extractor"""
    
    def __init__(self, domain: str):
        self.domain = domain.rstrip('/')
        self.base_domain = urlparse(self.domain).netloc
        
        # Results
        self.rss_feeds = set()
        self.sitemaps = set()
        self.category_urls = set()
        
        # Session setup
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.logger = logging.getLogger(__name__)
    
    def extract_all_data(self) -> ExtractionResult:
        """Extract all domain data: RSS, Sitemaps, Categories"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Extracting data for: {self.domain}")
            
            # Extract homepage for initial data
            self._extract_from_homepage()
            
            # Extract sitemaps from robots.txt and common paths
            self._extract_sitemaps()
            
            # Extract common category patterns
            self._extract_categories()
            
            return ExtractionResult(
                domain=self.domain,
                success=True,
                rss_feeds=list(self.rss_feeds),
                sitemaps=list(self.sitemaps),
                category_urls=list(self.category_urls),
                extraction_time=f"{time.time() - start_time:.2f}s"
            )
            
        except Exception as e:
            return ExtractionResult(
                domain=self.domain,
                success=False,
                rss_feeds=[],
                sitemaps=[],
                category_urls=[],
                extraction_time=f"{time.time() - start_time:.2f}s",
                error=str(e)
            )
    
    def _extract_from_homepage(self):
        """Extract RSS feeds and categories from homepage"""
        try:
            response = self.session.get(self.domain, timeout=10)
            if response.status_code != 200:
                return
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find RSS feeds in <link> tags
            rss_links = soup.find_all('link', {
                'type': ['application/rss+xml', 'application/atom+xml']
            })
            
            for link in rss_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.domain, href)
                    if self._is_valid_url(full_url):
                        self.rss_feeds.add(full_url)
            
            # Find categories in navigation
            nav_elements = soup.find_all(['nav', 'menu'])
            nav_elements.extend(soup.select('[class*="nav"], [class*="menu"], [class*="category"]'))
            
            vietnamese_keywords = [
                'thời sự', 'kinh tế', 'xã hội', 'thể thao', 'giải trí', 'công nghệ',
                'sức khỏe', 'giáo dục', 'pháp luật', 'quốc tế', 'địa phương'
            ]
            
            for nav in nav_elements:
                links = nav.find_all('a', href=True)
                for link in links:
                    href = link.get('href')
                    text = link.get_text().strip().lower()
                    
                    if href and text:
                        is_category = (
                            any(keyword in text for keyword in vietnamese_keywords) or
                            any(keyword in href.lower() for keyword in ['category', 'chuyen-muc', 'section'])
                        )
                        
                        if is_category:
                            full_url = urljoin(self.domain, href)
                            if self._is_valid_url(full_url):
                                self.category_urls.add(full_url)
            
        except Exception as e:
            self.logger.warning(f"Homepage extraction failed: {e}")
    
    def _extract_sitemaps(self):
        """Extract sitemap URLs from robots.txt and common paths"""
        # Check robots.txt
        try:
            robots_url = f"{self.domain}/robots.txt"
            response = self.session.get(robots_url, timeout=5)
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        if sitemap_url.startswith('//'):
                            sitemap_url = f"https:{sitemap_url}"
                        elif not sitemap_url.startswith(('http://', 'https://')):
                            sitemap_url = urljoin(self.domain, sitemap_url)
                        self.sitemaps.add(sitemap_url)
        except:
            pass
        
        # Check common sitemap paths
        common_paths = [
            '/sitemap.xml', '/sitemap_index.xml', '/sitemaps.xml',
            '/wp-sitemap.xml', '/site-map.xml'
        ]
        
        for path in common_paths:
            try:
                url = f"{self.domain}{path}"
                response = self.session.head(url, timeout=5)
                if response.status_code == 200:
                    self.sitemaps.add(url)
            except:
                continue
    
    def _extract_categories(self):
        """Extract categories from common Vietnamese news patterns"""
        common_patterns = [
            '/thoi-su', '/kinh-te', '/xa-hoi', '/the-thao', '/giai-tri',
            '/cong-nghe', '/suc-khoe', '/giao-duc', '/phap-luat', '/quoc-te',
            '/chuyen-muc', '/tin-tuc', '/category'
        ]
        
        for pattern in common_patterns:
            for ext in ['', '/', '.html']:
                try:
                    url = f"{self.domain}{pattern}{ext}"
                    response = self.session.head(url, timeout=3)
                    if response.status_code == 200:
                        self.category_urls.add(url)
                        break
                except:
                    continue
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for this domain"""
        if not url or not url.startswith(('http://', 'https://')):
            return False
        
        parsed = urlparse(url)
        if parsed.netloc != self.base_domain:
            return False
        
        # Avoid non-content URLs
        avoid_patterns = [
            '.jpg', '.png', '.gif', '.css', '.js', '.pdf',
            'admin', 'login', 'search', 'api'
        ]
        
        return not any(pattern in url.lower() for pattern in avoid_patterns)

class DomainProcessingManager:
    """Manages domain processing"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def process_domain(self, domain_data: Dict) -> bool:
        """Process a single domain"""
        domain_id = domain_data['id']
        domain_name = domain_data['name']
        base_url = domain_data['base_url']
        
        self.logger.info(f"Processing domain: {domain_name}")
        
        try:
            # Extract data
            extractor = DomainDataExtractor(base_url)
            result = extractor.extract_all_data()
            
            if not result.success:
                self.logger.error(f"Failed to extract data for {domain_name}: {result.error}")
                return False
            
            # Store in database
            update_data = {
                'rss_feeds': json.dumps(result.rss_feeds),
                'sitemaps': json.dumps(result.sitemaps), 
                'css_selectors': json.dumps(result.category_urls),
                'last_analyzed_at': datetime.now(),
                'analysis_model': 'simple-extractor-v1'
            }
            
            success = self.db_manager.update_domain_analysis(domain_id, update_data)
            
            if success:
                self.logger.info(f"Successfully processed {domain_name}")
                return True
            else:
                self.logger.error(f"Failed to store results for {domain_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing {domain_name}: {e}")
            return False
    
    def process_all_domains(self) -> Dict:
        """Process all active domains"""
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
            success = self.process_domain(domain)
            
            results['processed_domains'].append({
                'name': domain['name'],
                'success': success
            })
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        self.logger.info(f"Processing completed: {results['successful']}/{results['total_domains']} successful")
        return results