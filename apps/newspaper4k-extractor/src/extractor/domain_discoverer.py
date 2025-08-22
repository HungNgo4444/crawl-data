"""Domain discovery for RSS feeds and sitemaps"""

import requests
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

from ..utils.url_utils import URLUtils
from ..config.settings import get_settings


class DomainDiscoverer:
    """Discover RSS feeds and sitemaps for domains"""
    
    def __init__(self):
        self.settings = get_settings()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.settings.user_agent
        })
    
    def discover_feeds(self, domain: str) -> List[str]:
        """Discover RSS feeds for a domain"""
        if not domain.startswith(('http://', 'https://')):
            domain = f"https://{domain}"
        
        feeds = []
        
        # Try common RSS paths
        common_paths = URLUtils.find_rss_urls(domain)
        for rss_url in common_paths:
            if self._is_valid_rss(rss_url):
                feeds.append(rss_url)
        
        # Try to find RSS links in homepage
        try:
            homepage_feeds = self._find_rss_in_page(domain)
            feeds.extend(homepage_feeds)
        except Exception as e:
            print(f"Homepage RSS discovery failed for {domain}: {e}")
        
        return list(set(feeds))  # Remove duplicates
    
    def discover_sitemaps(self, domain: str) -> List[str]:
        """Discover sitemaps for a domain"""
        if not domain.startswith(('http://', 'https://')):
            domain = f"https://{domain}"
        
        sitemaps = []
        
        # Try common sitemap paths
        common_paths = URLUtils.find_sitemap_urls(domain)
        for sitemap_url in common_paths:
            if self._is_valid_sitemap(sitemap_url):
                sitemaps.append(sitemap_url)
        
        # Try to find sitemaps in robots.txt
        try:
            robots_sitemaps = self._find_sitemaps_in_robots(domain)
            sitemaps.extend(robots_sitemaps)
        except Exception as e:
            print(f"Robots.txt sitemap discovery failed for {domain}: {e}")
        
        return list(set(sitemaps))  # Remove duplicates
    
    def get_articles_from_rss(self, rss_url: str, limit: int = 20) -> List[str]:
        """Get article URLs from RSS feed"""
        try:
            feed = feedparser.parse(rss_url)
            urls = []
            
            for entry in feed.entries[:limit]:
                if hasattr(entry, 'link') and entry.link:
                    url = entry.link.strip()
                    if URLUtils.is_article_url(url):
                        urls.append(url)
            
            return urls
        except Exception as e:
            print(f"RSS parsing failed for {rss_url}: {e}")
            return []
    
    def get_articles_from_sitemap(self, sitemap_url: str, limit: int = 50) -> List[str]:
        """Get article URLs from sitemap"""
        try:
            response = self.session.get(sitemap_url, timeout=self.settings.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            urls = []
            
            # Handle sitemap index
            sitemap_tags = soup.find_all('sitemap')
            if sitemap_tags:
                for sitemap in sitemap_tags[:5]:  # Limit to first 5 sitemaps
                    loc = sitemap.find('loc')
                    if loc and loc.text:
                        sub_urls = self.get_articles_from_sitemap(loc.text, limit//5)
                        urls.extend(sub_urls)
            else:
                # Handle regular sitemap
                for loc in soup.find_all('loc'):
                    if loc.text and URLUtils.is_article_url(loc.text):
                        urls.append(loc.text.strip())
                        if len(urls) >= limit:
                            break
            
            return urls[:limit]
            
        except Exception as e:
            print(f"Sitemap parsing failed for {sitemap_url}: {e}")
            return []
    
    def _is_valid_rss(self, rss_url: str) -> bool:
        """Check if URL is a valid RSS feed"""
        try:
            response = self.session.get(rss_url, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if 'xml' in content_type or 'rss' in content_type:
                    return True
                
                # Try to parse as feed
                feed = feedparser.parse(response.content)
                return len(feed.entries) > 0
        except:
            pass
        return False
    
    def _is_valid_sitemap(self, sitemap_url: str) -> bool:
        """Check if URL is a valid sitemap"""
        try:
            response = self.session.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if 'xml' in content_type:
                    # Try to parse as XML
                    soup = BeautifulSoup(response.content, 'xml')
                    return bool(soup.find_all('loc') or soup.find_all('sitemap'))
        except:
            pass
        return False
    
    def _find_rss_in_page(self, page_url: str) -> List[str]:
        """Find RSS feeds linked in a webpage"""
        try:
            response = self.session.get(page_url, timeout=self.settings.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            feeds = []
            
            # Look for RSS link tags
            rss_links = soup.find_all('link', {'type': 'application/rss+xml'})
            for link in rss_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(page_url, href)
                    feeds.append(full_url)
            
            # Look for Atom feeds
            atom_links = soup.find_all('link', {'type': 'application/atom+xml'})
            for link in atom_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(page_url, href)
                    feeds.append(full_url)
            
            return feeds
            
        except Exception as e:
            print(f"Page RSS discovery failed: {e}")
            return []
    
    def _find_sitemaps_in_robots(self, domain: str) -> List[str]:
        """Find sitemap URLs in robots.txt"""
        robots_url = urljoin(domain, '/robots.txt')
        sitemaps = []
        
        try:
            response = self.session.get(robots_url, timeout=10)
            response.raise_for_status()
            
            for line in response.text.splitlines():
                line = line.strip()
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    if sitemap_url:
                        sitemaps.append(sitemap_url)
            
            return sitemaps
            
        except Exception as e:
            print(f"Robots.txt parsing failed: {e}")
            return []
