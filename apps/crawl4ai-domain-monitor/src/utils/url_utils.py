import re
import hashlib
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, urlunparse
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class URLNormalizer:
    """URL normalization utilities for deduplication"""
    
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
        "fbclid", "gclid", "ref", "source", "campaign", "mc_cid", "mc_eid"
    }
    
    def __init__(self, remove_tracking_params: bool = True, 
                 ignore_case: bool = True, ignore_fragments: bool = True):
        self.remove_tracking_params = remove_tracking_params
        self.ignore_case = ignore_case
        self.ignore_fragments = ignore_fragments
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for consistent deduplication"""
        try:
            # Parse URL
            parsed = urlparse(url.strip())
            
            # Normalize scheme and hostname
            scheme = parsed.scheme.lower() if parsed.scheme else 'https'
            hostname = parsed.hostname.lower() if parsed.hostname else ''
            
            # Handle www prefix consistently
            if hostname.startswith('www.'):
                hostname = hostname[4:]
            
            # Normalize path
            path = parsed.path
            if self.ignore_case:
                path = path.lower()
            
            # Remove trailing slash for consistency (except root)
            if path.endswith('/') and len(path) > 1:
                path = path[:-1]
            
            # Handle query parameters
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            
            # Remove tracking parameters if enabled
            if self.remove_tracking_params:
                query_params = {k: v for k, v in query_params.items() 
                              if k.lower() not in self.TRACKING_PARAMS}
            
            # Sort parameters for consistency
            sorted_params = []
            for key in sorted(query_params.keys()):
                for value in sorted(query_params[key]):
                    sorted_params.append((key, value))
            
            # Rebuild query string
            query = urlencode(sorted_params) if sorted_params else ''
            
            # Handle fragment
            fragment = '' if self.ignore_fragments else parsed.fragment
            
            # Reconstruct URL
            normalized = urlunparse((
                scheme,
                f"{hostname}:{parsed.port}" if parsed.port else hostname,
                path,
                parsed.params,
                query,
                fragment
            ))
            
            return normalized
            
        except Exception as e:
            logger.error(f"URL normalization error for '{url}': {e}")
            return url  # Return original if normalization fails


class URLValidator:
    """URL validation for Vietnamese news sites"""
    
    VIETNAMESE_NEWS_PATTERNS = [
        r'.*\.(vn|com\.vn)$',  # Vietnamese domains
        r'.*(vnexpress|dantri|tuoitre|thanhnien|24h|zing|kenh14|vietnamnet).*'
    ]
    
    ARTICLE_URL_PATTERNS = [
        r'.*-\d+\.html?$',  # Common Vietnamese news URL pattern
        r'.*/\d{4}/\d{2}/.*',  # Date-based URLs
        r'.*/tin-tuc/.*',  # News section URLs
        r'.*/bai-viet/.*'  # Article URLs
    ]
    
    EXCLUDE_PATTERNS = [
        r'.*(tag|category|search|login|register).*',
        r'.*\.(jpg|jpeg|png|gif|pdf|doc|docx)$',
        r'.*[?&](utm_|fbclid=|gclid=).*',
        r'.*/video/.*',  # Video pages (unless specifically wanted)
        r'.*/live-blog/.*'  # Live blogs
    ]
    
    def __init__(self):
        self.vietnamese_regex = [re.compile(pattern, re.IGNORECASE) 
                               for pattern in self.VIETNAMESE_NEWS_PATTERNS]
        self.article_regex = [re.compile(pattern, re.IGNORECASE) 
                             for pattern in self.ARTICLE_URL_PATTERNS]
        self.exclude_regex = [re.compile(pattern, re.IGNORECASE) 
                             for pattern in self.EXCLUDE_PATTERNS]
    
    def is_vietnamese_news_domain(self, url: str) -> bool:
        """Check if URL is from Vietnamese news domain"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return any(regex.match(domain) for regex in self.vietnamese_regex)
        except Exception:
            return False
    
    def is_likely_article_url(self, url: str) -> bool:
        """Check if URL is likely an article URL"""
        try:
            return any(regex.match(url) for regex in self.article_regex)
        except Exception:
            return False
    
    def should_exclude_url(self, url: str) -> bool:
        """Check if URL should be excluded"""
        try:
            return any(regex.search(url) for regex in self.exclude_regex)
        except Exception:
            return True  # Exclude if can't determine
    
    def filter_urls(self, urls: List[str], domain_patterns: Optional[List[str]] = None) -> List[str]:
        """Filter URLs based on validation rules"""
        filtered = []
        
        for url in urls:
            # Skip excluded URLs
            if self.should_exclude_url(url):
                continue
                
            # Check domain patterns if provided
            if domain_patterns:
                if not any(re.search(pattern, url, re.IGNORECASE) 
                          for pattern in domain_patterns):
                    continue
            
            # Must be Vietnamese news domain
            if not self.is_vietnamese_news_domain(url):
                continue
                
            # Prefer likely article URLs
            if self.is_likely_article_url(url):
                filtered.append(url)
                
        return filtered


class URLDeduplicator:
    """URL deduplication with SHA-256 fingerprinting"""
    
    def __init__(self, normalizer: Optional[URLNormalizer] = None):
        self.normalizer = normalizer or URLNormalizer()
        
    def generate_fingerprint(self, url: str) -> str:
        """Generate SHA-256 hash of normalized URL"""
        try:
            normalized_url = self.normalizer.normalize_url(url)
            return hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"Fingerprint generation error for '{url}': {e}")
            # Fallback to original URL hash
            return hashlib.sha256(url.encode('utf-8')).hexdigest()
    
    def generate_fingerprints_batch(self, urls: List[str]) -> List[Tuple[str, str]]:
        """Generate fingerprints for batch of URLs"""
        results = []
        for url in urls:
            fingerprint = self.generate_fingerprint(url)
            results.append((url, fingerprint))
        return results