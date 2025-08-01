"""
Intelligently route requests to optimal crawler
"""

from typing import Dict, Any, Optional
from urllib.parse import urlparse
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SiteProfile:
    """Site-specific configuration and metadata"""
    name: str
    is_spa: bool = False
    has_dynamic_content: bool = False
    requires_js: bool = False
    anti_bot_protection: bool = False
    crawl_delay: float = 1.0
    max_concurrent: int = 5
    selectors: Dict[str, str] = None
    custom_headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.selectors is None:
            self.selectors = {}
        if self.custom_headers is None:
            self.custom_headers = {}

class StrategyRouter:
    """Intelligently route requests to optimal crawler"""
    
    def __init__(self):
        self.site_profiles: Dict[str, SiteProfile] = {}
        self._load_default_profiles()
    
    def _load_default_profiles(self):
        """Load default site profiles for major Vietnamese news sites"""
        
        # VnExpress - static content, very fast with Scrapy
        self.site_profiles['vnexpress.net'] = SiteProfile(
            name='vnexpress',
            is_spa=False,
            has_dynamic_content=False,
            requires_js=False,
            crawl_delay=1.0,
            max_concurrent=5,
            selectors={
                'title': 'h1.title-detail',
                'content': '.fck_detail',
                'author': '.author_mail',
                'publish_time': '.date',
                'description': '.description'
            }
        )
        
        # CafeF - mostly static with some dynamic elements
        self.site_profiles['cafef.vn'] = SiteProfile(
            name='cafef',
            is_spa=False,
            has_dynamic_content=True,
            requires_js=False,
            crawl_delay=2.0,
            max_concurrent=3,
            selectors={
                'title': 'h1',
                'content': '.detail-content',
                'author': '.author',
                'publish_time': '.pdate'
            }
        )
        
        # Dantri - hybrid approach needed
        self.site_profiles['dantri.com.vn'] = SiteProfile(
            name='dantri',
            is_spa=False,
            has_dynamic_content=True,
            requires_js=True,
            crawl_delay=1.5,
            max_concurrent=4,
            selectors={
                'title': 'h1.title-page',
                'content': '.singular-content',
                'author': '.author-name',
                'publish_time': '.news-time'
            }
        )
        
        # VietnamNet - modern site with some JS
        self.site_profiles['vietnamnet.vn'] = SiteProfile(
            name='vietnamnet',
            is_spa=False,
            has_dynamic_content=True,
            requires_js=False,
            crawl_delay=1.0,
            max_concurrent=4,
            selectors={
                'title': 'h1.title',
                'content': '.ArticleContent',
                'author': '.author',
                'publish_time': '.time'
            }
        )
        
        # Generic profile for unknown sites
        self.site_profiles['_default'] = SiteProfile(
            name='generic',
            is_spa=False,
            has_dynamic_content=True,
            requires_js=True,  # Be safe with unknown sites
            crawl_delay=2.0,
            max_concurrent=2,
            selectors={
                'title': 'h1, .title, .headline',
                'content': '.content, .article-content, .post-content, .entry-content',
                'author': '.author, .byline',
                'publish_time': '.date, .time, .published'
            }
        )
    
    def select_strategy(self, url: str, site_profile: Optional[SiteProfile] = None) -> str:
        """
        Decision logic:
        - Static news sites → Scrapy (5x faster)
        - Dynamic content → Playwright  
        - Mixed content → Hybrid approach
        """
        if site_profile is None:
            site_profile = self.get_site_profile(url)
        
        logger.debug(f"Selecting strategy for {url} with profile {site_profile.name}")
        
        # If site has anti-bot protection, use Playwright
        if site_profile.anti_bot_protection:
            logger.debug(f"Using playwright for {url} (anti-bot protection)")
            return 'playwright'
        
        # If site is SPA, must use Playwright
        if site_profile.is_spa:
            logger.debug(f"Using playwright for {url} (SPA)")
            return 'playwright'
        
        # If site requires JS for content loading, use Playwright
        if site_profile.requires_js:
            logger.debug(f"Using playwright for {url} (requires JS)")
            return 'playwright'
        
        # If site has dynamic content but doesn't require JS, use hybrid
        if site_profile.has_dynamic_content and not site_profile.requires_js:
            logger.debug(f"Using hybrid for {url} (dynamic content, no JS required)")
            return 'hybrid'
        
        # Default to Scrapy for static content (fastest)
        logger.debug(f"Using scrapy for {url} (static content)")
        return 'scrapy'
    
    def get_site_profile(self, url: str) -> SiteProfile:
        """Get site profile for a given URL"""
        try:
            domain = urlparse(url).netloc.lower()
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Find matching profile
            for profile_domain, profile in self.site_profiles.items():
                if profile_domain != '_default' and profile_domain in domain:
                    return profile
            
            # Return default profile if no match found
            return self.site_profiles['_default']
            
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return self.site_profiles['_default']
    
    def add_site_profile(self, domain: str, profile: SiteProfile):
        """Add or update a site profile"""
        self.site_profiles[domain] = profile
        logger.info(f"Added site profile for {domain}")
    
    def get_crawl_config(self, url: str) -> Dict[str, Any]:
        """Get complete crawl configuration for a URL"""
        site_profile = self.get_site_profile(url)
        strategy = self.select_strategy(url, site_profile)
        
        return {
            'strategy': strategy,
            'site_profile': site_profile,
            'crawl_delay': site_profile.crawl_delay,
            'max_concurrent': site_profile.max_concurrent,
            'selectors': site_profile.selectors,
            'custom_headers': site_profile.custom_headers,
            'requires_js': site_profile.requires_js
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        return {
            'total_profiles': len(self.site_profiles),
            'profile_domains': list(self.site_profiles.keys())
        }