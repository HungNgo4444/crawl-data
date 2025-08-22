"""URL manipulation and validation utilities"""

import re
from urllib.parse import urljoin, urlparse, parse_qs
from typing import List, Optional, Set


class URLUtils:
    """URL manipulation utilities"""
    
    # Common article URL patterns for Vietnamese news sites
    ARTICLE_PATTERNS = [
        r'/\d{4}/\d{2}/\d{2}/',  # Date-based URLs
        r'-\d+\.html?$',        # Ending with ID and .html
        r'-\d+\.htm$',          # Ending with ID and .htm
        r'/[a-z-]+/\d+/',       # Category with ID
        r'/tin-tuc/',           # News section
        r'/bai-viet/',          # Article section
    ]
    
    # Patterns to exclude (not articles)
    EXCLUDE_PATTERNS = [
        r'/tag/',
        r'/search',
        r'/login',
        r'/register',
        r'/contact',
        r'/about',
        r'/rss',
        r'\.rss$',
        r'\.xml$',
        r'\.(jpg|jpeg|png|gif|pdf|doc)$',
        r'/page/\d+',
        r'/trang-\d+',
        r'#comment',
    ]
    
    @staticmethod
    def normalize_url(url: str, base_url: str = None) -> str:
        """Normalize URL"""
        if not url:
            return ""
        
        # Join with base URL if relative
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
        
        # Parse and rebuild URL
        parsed = urlparse(url)
        
        # Remove common tracking parameters
        query_params = parse_qs(parsed.query)
        clean_params = {
            k: v for k, v in query_params.items() 
            if k not in ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'ref']
        }
        
        # Rebuild query string
        clean_query = '&'.join([f"{k}={v[0]}" for k, v in clean_params.items()])
        
        # Rebuild URL
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_query:
            clean_url += f"?{clean_query}"
        
        return clean_url
    
    @staticmethod
    def is_article_url(url: str) -> bool:
        """Check if URL is likely an article URL"""
        if not url:
            return False
        
        # Check exclude patterns first
        for pattern in URLUtils.EXCLUDE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Check article patterns
        for pattern in URLUtils.ARTICLE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        # Default check for Vietnamese news URL structure
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Common Vietnamese article indicators
        vietnamese_indicators = [
            'tin-tuc', 'bai-viet', 'thoi-su', 'the-gioi', 'kinh-te',
            'giai-tri', 'the-thao', 'phap-luat', 'giao-duc', 'suc-khoe',
            'doi-song', 'khoa-hoc', 'cong-nghe', 'du-lich'
        ]
        
        return any(indicator in path for indicator in vietnamese_indicators)
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract domain from URL"""
        if not url:
            return ""
        
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    @staticmethod
    def get_base_url(url: str) -> str:
        """Get base URL"""
        if not url:
            return ""
        
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    @staticmethod
    def find_sitemap_urls(domain: str) -> List[str]:
        """Generate common sitemap URLs for a domain"""
        if not domain:
            return []
        
        if not domain.startswith(('http://', 'https://')):
            domain = f"https://{domain}"
        
        base_url = URLUtils.get_base_url(domain)
        
        sitemap_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemaps.xml',
            '/robots.txt',  # Often contains sitemap references
            '/rss.xml',
            '/feed.xml',
        ]
        
        return [urljoin(base_url, path) for path in sitemap_paths]
    
    @staticmethod
    def find_rss_urls(domain: str) -> List[str]:
        """Generate common RSS feed URLs for Vietnamese news sites"""
        if not domain:
            return []
        
        if not domain.startswith(('http://', 'https://')):
            domain = f"https://{domain}"
        
        base_url = URLUtils.get_base_url(domain)
        
        rss_paths = [
            '/rss',
            '/rss.xml',
            '/feed',
            '/feed.xml',
            '/feeds',
            '/rss/thoi-su.rss',
            '/rss/the-gioi.rss',
            '/rss/kinh-te.rss',
            '/rss/giai-tri.rss',
            '/rss/the-thao.rss',
            '/thoi-su.rss',
            '/the-gioi.rss',
            '/kinh-te.rss',
            '/giai-tri.rss',
            '/the-thao.rss',
        ]
        
        return [urljoin(base_url, path) for path in rss_paths]
    
    @staticmethod
    def deduplicate_urls(urls: List[str]) -> List[str]:
        """Remove duplicate URLs"""
        if not urls:
            return []
        
        seen = set()
        unique_urls = []
        
        for url in urls:
            normalized = URLUtils.normalize_url(url)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_urls.append(normalized)
        
        return unique_urls
    
    @staticmethod
    def filter_by_date_range(urls: List[str], start_date: str = None, end_date: str = None) -> List[str]:
        """Filter URLs by date range (if URL contains date)"""
        if not urls or (not start_date and not end_date):
            return urls
        
        filtered_urls = []
        
        for url in urls:
            # Try to extract date from URL
            date_match = re.search(r'(\d{4})/(\d{2})/(\d{2})', url)
            if date_match:
                url_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                
                # Check date range
                include_url = True
                if start_date and url_date < start_date:
                    include_url = False
                if end_date and url_date > end_date:
                    include_url = False
                
                if include_url:
                    filtered_urls.append(url)
            else:
                # If no date found, include by default
                filtered_urls.append(url)
        
        return filtered_urls
