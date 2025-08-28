"""
Domain analyzer using newspaper4k library - chỉ sử dụng built-in functions
"""
import logging
from typing import Dict, List, Any
from urllib.parse import urljoin
import requests
import time
import hashlib

# Import newspaper4k (pip install newspaper4k)
from newspaper import Source, Config

logger = logging.getLogger(__name__)

class Newspaper4kDomainAnalyzer:
    """Domain analyzer using newspaper4k library"""
    
    def __init__(self):
        self.config = Config()
        self.config.language = 'vi'  # Vietnamese language
        self.config.memoize_articles = False
        self.config.fetch_images = False
        self.config.number_threads = 1
        # Disable category caching để lấy fresh data
        self.config.disable_category_cache = True
        
    def analyze_domain(self, domain_url: str, domain_name: str) -> Dict[str, Any]:
        """
        Analyze a domain and discover RSS feeds, category pages, article URLs
        
        Args:
            domain_url: Base URL of the domain (e.g., https://vnexpress.net)
            domain_name: Domain name (e.g., vnexpress.net)
            
        Returns:
            Dict containing analysis results
        """
        logger.info(f"Starting analysis of domain: {domain_name}")
        
        analysis_result = {
            'rss_feeds': [],
            'sitemaps': [],
            'homepage_urls': [],
            'category_urls': [],
            'css_selectors': {},
            'analysis_timestamp': time.time(),
            'analysis_errors': []
        }
        
        try:
            # Create Source object
            source = Source(domain_url, config=self.config)
            
            # Download and parse homepage
            logger.info(f"Downloading and parsing {domain_url}")
            source.download()
            source.parse()
            
            # Extract homepage URLs (main domain URL)
            analysis_result['homepage_urls'] = [source.url]
            
            # Extract category URLs using ContentExtractor directly for better results
            if source.doc is not None:
                analysis_result['category_urls'] = source.extractor.get_category_urls(source.url, source.doc)
            else:
                logger.warning(f"No doc parsed for {domain_url}")
                analysis_result['category_urls'] = []
            
            # Extract RSS feeds - manual implementation để tránh lỗi xpath trong set_feeds()
            if source.doc is not None:
                analysis_result['rss_feeds'] = self._extract_rss_feeds_manual(source)
            else:
                analysis_result['rss_feeds'] = []
            
            # Dynamic CSS selectors extraction from the actual page - real data từ website
            try:
                analysis_result['css_selectors'] = self._extract_css_selectors(source)
            except Exception as e:
                logger.warning(f"CSS selector extraction failed: {e}")
                # Fallback to basic selectors nếu có lỗi
                analysis_result['css_selectors'] = {
                    'article_title': ['h1', 'h2'],
                    'article_content': ['article', '.content'],
                    'article_meta': ['.meta', '.byline'],
                    'navigation': ['nav', '.navigation']
                }
            
            # Extract sitemaps from robots.txt (newspaper4k doesn't have built-in)
            analysis_result['sitemaps'] = self._get_sitemaps_from_robots(domain_url)
            
            logger.info(f"Analysis completed for {domain_name}: "
                      f"RSS({len(analysis_result['rss_feeds'])}), "
                      f"Sitemaps({len(analysis_result['sitemaps'])}), "
                      f"Categories({len(analysis_result['category_urls'])}), "
                      f"Homepage({len(analysis_result['homepage_urls'])})")
            
        except Exception as e:
            error_msg = f"Error analyzing domain {domain_name}: {str(e)}"
            logger.error(error_msg)
            analysis_result['analysis_errors'].append(error_msg)
        
        return analysis_result
    
    def get_all_urls_for_domain(self, domain_url: str, domain_name: str) -> List[str]:
        """
        Get all URLs discovered by newspaper4k for a domain
        
        Args:
            domain_url: Base URL of the domain 
            domain_name: Domain name
            
        Returns:
            List of all discovered URLs
        """
        all_urls = []
        
        try:
            # Create Source object
            source = Source(domain_url, config=self.config)
            
            # Build the source
            logger.info(f"Building source for URL extraction: {domain_url}")
            source.build()
            
            # Get category URLs
            category_urls = source.category_urls()
            all_urls.extend(category_urls)
            
            # Get article URLs  
            article_urls = source.article_urls()
            all_urls.extend(article_urls)
            
            # Get RSS feed URLs
            rss_urls = source.feed_urls()
            all_urls.extend(rss_urls)
            
            # Add homepage
            all_urls.append(source.url)
            
            # Remove duplicates
            all_urls = list(set(all_urls))
            
            logger.info(f"Found total {len(all_urls)} URLs for {domain_name}")
            
        except Exception as e:
            logger.error(f"Error extracting URLs for {domain_name}: {e}")
        
        return all_urls
    
    def extract_all_article_urls(self, domain_url: str, domain_name: str, 
                                domain_data: Dict[str, Any]) -> List[str]:
        """
        Phase 2: Extract all article URLs from discovered sources
        
        Args:
            domain_url: Base URL of the domain
            domain_name: Domain name
            domain_data: Analysis data from Phase 1 containing rss_feeds, sitemaps, etc.
            
        Returns:
            List of deduplicated article URLs
        """
        logger.info(f"Phase 2: Extracting article URLs for {domain_name}")
        
        all_article_urls = set()
        
        try:
            # Create Source object
            source = Source(domain_url, config=self.config)
            source.build()
            
            # Extract from RSS feeds
            if domain_data.get('rss_feeds'):
                rss_articles = self._extract_urls_from_rss_feeds(domain_data['rss_feeds'])
                all_article_urls.update(rss_articles)
                logger.info(f"Extracted {len(rss_articles)} URLs from RSS feeds")
            
            # Extract from category pages
            if domain_data.get('category_urls'):
                category_articles = self._extract_urls_from_categories(domain_data['category_urls'])
                all_article_urls.update(category_articles)
                logger.info(f"Extracted {len(category_articles)} URLs from categories")
            
            # Extract from sitemaps
            if domain_data.get('sitemaps'):
                sitemap_articles = self._extract_urls_from_sitemaps(domain_data['sitemaps'])
                all_article_urls.update(sitemap_articles)
                logger.info(f"Extracted {len(sitemap_articles)} URLs from sitemaps")
            
            # Extract from homepage
            if domain_data.get('homepage_urls'):
                homepage_articles = self._extract_urls_from_homepage(domain_data['homepage_urls'][0])
                all_article_urls.update(homepage_articles)
                logger.info(f"Extracted {len(homepage_articles)} URLs from homepage")
            
            # Use newspaper4k built-in article discovery
            builtin_articles = source.article_urls()
            all_article_urls.update(builtin_articles)
            logger.info(f"Extracted {len(builtin_articles)} URLs from newspaper4k built-in")
            
        except Exception as e:
            logger.error(f"Error extracting article URLs for {domain_name}: {e}")
        
        # Deduplicate and filter
        final_urls = self._deduplicate_and_filter_urls(list(all_article_urls), domain_url)
        logger.info(f"Final count after deduplication: {len(final_urls)} URLs for {domain_name}")
        
        return final_urls
    
    def _get_sitemaps_from_robots(self, domain_url: str) -> List[str]:
        """Simple sitemap extraction from robots.txt"""
        sitemaps = []
        try:
            robots_url = urljoin(domain_url, '/robots.txt')
            response = requests.get(robots_url, timeout=10, headers={'User-Agent': 'DomainAnalyzer/1.0'})
            
            if response.status_code == 200:
                lines = response.text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        sitemaps.append(sitemap_url)
                            
        except Exception as e:
            logger.warning(f"Error parsing robots.txt: {e}")
        
        return sitemaps
    
    def _extract_rss_feeds_manual(self, source) -> List[str]:
        """Manual RSS feed extraction để tránh lỗi xpath trong newspaper4k"""
        feeds = []
        
        try:
            # Common RSS feed patterns
            common_feed_paths = ["/feed", "/feeds", "/rss", "/rss.xml", "/feed.xml", "/atom.xml"]
            
            for path in common_feed_paths:
                feed_url = urljoin(source.url, path)
                try:
                    response = requests.get(feed_url, timeout=10, headers={'User-Agent': 'DomainAnalyzer/1.0'})
                    if response.status_code == 200 and ('xml' in response.headers.get('content-type', '').lower() or 
                                                       'rss' in response.text[:200].lower() or
                                                       'atom' in response.text[:200].lower()):
                        feeds.append(feed_url)
                except:
                    continue
            
            # Look for RSS links in HTML
            if hasattr(source, 'doc') and source.doc is not None:
                try:
                    # Find RSS/feed links in HTML
                    rss_links = source.doc.cssselect('link[type="application/rss+xml"]')
                    for link in rss_links:
                        href = link.get('href')
                        if href:
                            full_url = urljoin(source.url, href)
                            if full_url not in feeds:
                                feeds.append(full_url)
                    
                    # Find atom links
                    atom_links = source.doc.cssselect('link[type="application/atom+xml"]')
                    for link in atom_links:
                        href = link.get('href')
                        if href:
                            full_url = urljoin(source.url, href)
                            if full_url not in feeds:
                                feeds.append(full_url)
                                
                    # Find feed URLs in href attributes
                    feed_hrefs = source.doc.cssselect('a[href*="rss"], a[href*="feed"], a[href*="atom"]')
                    for link in feed_hrefs:
                        href = link.get('href')
                        if href and ('rss' in href.lower() or 'feed' in href.lower() or 'atom' in href.lower()):
                            full_url = urljoin(source.url, href)
                            if full_url not in feeds:
                                feeds.append(full_url)
                                
                except Exception as e:
                    logger.warning(f"Error extracting RSS from HTML: {e}")
            
            # Discovery RSS feeds từ HTML page /rss (nhiều sites có RSS directory)
            rss_index_url = urljoin(source.url, '/rss')
            try:
                response = requests.get(rss_index_url, timeout=15, headers={'User-Agent': 'DomainAnalyzer/1.0'})
                if response.status_code == 200:
                    from lxml import html
                    doc = html.fromstring(response.content)
                    
                    # Find RSS links trong RSS index page
                    rss_link_selectors = [
                        'a[href*=".rss"]',           # Direct .rss files
                        'a[href*="/rss/"]',          # RSS directory paths  
                        'a[href*="feed"]',           # Feed links
                        'a[href*="xml"]'             # XML feeds
                    ]
                    
                    for selector in rss_link_selectors:
                        links = doc.cssselect(selector)
                        for link in links:
                            href = link.get('href')
                            if href:
                                full_url = urljoin(source.url, href)
                                # Validate đây có phải RSS feed thật không
                                if self._is_valid_rss_url(full_url) and full_url not in feeds:
                                    feeds.append(full_url)
                                    
            except Exception as e:
                logger.warning(f"Error parsing RSS index page: {e}")
            
        except Exception as e:
            logger.warning(f"Error in manual RSS extraction: {e}")
        
        return feeds
    
    def _is_valid_rss_url(self, url: str) -> bool:
        """Validate URL có phải RSS feed thật không"""
        try:
            # Quick validation based on URL pattern
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in ['.rss', '/rss/', 'feed', '.xml']):
                # Test actual RSS content
                response = requests.get(url, timeout=10, headers={'User-Agent': 'DomainAnalyzer/1.0'})
                if response.status_code == 200:
                    content_start = response.text[:200].lower()
                    return ('<?xml' in content_start or 'rss' in content_start or 'feed' in content_start)
        except:
            pass
        return False
    
    def _extract_css_selectors(self, source) -> Dict[str, List[str]]:
        """Extract dynamic CSS selectors from the actual webpage"""
        selectors = {
            'article_title': [],
            'article_content': [],
            'article_meta': [],
            'navigation': []
        }
        
        try:
            if hasattr(source, 'doc') and source.doc is not None:
                # Find title selectors
                title_candidates = ['h1', 'h2', '.title', '.article-title', '.entry-title', 
                                  '.headline', '.post-title', '.news-title']
                for selector in title_candidates:
                    if source.doc.cssselect(selector):
                        selectors['article_title'].append(selector)
                
                # Find content selectors
                content_candidates = ['.article-content', '.entry-content', '.content', 
                                    'article', '.post-content', '.news-content', '.article-body']
                for selector in content_candidates:
                    if source.doc.cssselect(selector):
                        selectors['article_content'].append(selector)
                
                # Find meta selectors
                meta_candidates = ['.article-meta', '.entry-meta', '.byline', '.date',
                                 '.author', '.publish-date', '.meta-info']
                for selector in meta_candidates:
                    if source.doc.cssselect(selector):
                        selectors['article_meta'].append(selector)
                
                # Find navigation selectors
                nav_candidates = ['nav', '.nav', '.navigation', '.menu', 'header nav',
                                '.main-menu', '.primary-menu']
                for selector in nav_candidates:
                    if source.doc.cssselect(selector):
                        selectors['navigation'].append(selector)
                        
        except Exception as e:
            logger.warning(f"Error extracting CSS selectors: {e}")
            # Fallback to hardcoded selectors
            selectors = {
                'article_title': ['h1', '.title', '.article-title', '.entry-title'],
                'article_content': ['.article-content', '.entry-content', '.content', 'article'],
                'article_meta': ['.article-meta', '.entry-meta', '.byline', '.date'],
                'navigation': ['nav', '.nav', '.navigation', '.menu']
            }
        
        return selectors
    
    def _extract_urls_from_rss_feeds(self, rss_feeds: List[str]) -> List[str]:
        """Extract article URLs from RSS feeds"""
        urls = set()
        
        for rss_url in rss_feeds:
            try:
                response = requests.get(rss_url, timeout=15, headers={'User-Agent': 'DomainAnalyzer/1.0'})
                if response.status_code == 200:
                    # Parse RSS/XML content for URLs
                    import re
                    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                    found_urls = re.findall(url_pattern, response.text)
                    urls.update(found_urls)
            except Exception as e:
                logger.warning(f"Error parsing RSS feed {rss_url}: {e}")
                continue
        
        return list(urls)
    
    def _extract_urls_from_categories(self, category_urls: List[str]) -> List[str]:
        """Extract article URLs from category pages with cycle-safe deep crawling"""
        all_urls = set()
        visited_urls = set()  # Track visited URLs to prevent infinite loops
        
        for category_url in category_urls[:10]:  # Limit to 10 categories to avoid timeout
            try:
                logger.info(f"Processing category: {category_url}")
                
                # Deep crawl with cycle detection and depth tracking
                deep_urls = self._deep_crawl_with_cycle_detection(
                    start_url=category_url,
                    max_depth=1,
                    visited_urls=visited_urls.copy(),  # Fresh visited set for each category
                    current_depth=0
                )
                
                all_urls.update(deep_urls)
                logger.info(f"Deep crawl completed for {category_url}: found {len(deep_urls)} URLs")
                
            except Exception as e:
                logger.warning(f"Error in deep crawling category {category_url}: {e}")
                continue
        
        # Remove duplicates and return
        final_urls = self._clean_and_deduplicate_urls(list(all_urls))
        logger.info(f"Deep crawling completed: {len(final_urls)} unique URLs after deduplication")
        return final_urls
    
    def _deep_crawl_with_cycle_detection(self, start_url: str, max_depth: int, 
                                       visited_urls: set, current_depth: int) -> set:
        """
        Recursive deep crawl with cycle detection and depth tracking
        
        Args:
            start_url: URL to start crawling from
            max_depth: Maximum crawl depth (0 = no limit)
            visited_urls: Set of already visited URLs to prevent cycles
            current_depth: Current crawl depth
            
        Returns:
            Set of discovered URLs
        """
        discovered_urls = set()
        
        # Check depth limit
        if max_depth > 0 and current_depth >= max_depth:
            logger.debug(f"Reached max depth {max_depth} for {start_url}")
            return discovered_urls
        
        # Normalize URL for cycle detection
        normalized_url = self._normalize_url_for_comparison(start_url)
        
        # Check if already visited (cycle detection)
        if normalized_url in visited_urls:
            logger.debug(f"Cycle detected: {start_url} already visited")
            return discovered_urls
        
        # Mark as visited
        visited_urls.add(normalized_url)
        
        logger.info(f"Level {current_depth + 1}: Crawling {start_url}")
        
        try:
            # Extract URLs from current page
            page_urls = self._extract_urls_from_single_page(start_url)
            discovered_urls.update(page_urls)
            
            logger.info(f"Level {current_depth + 1}: Found {len(page_urls)} URLs from {start_url}")
            
            # Apply limits based on depth to prevent exponential explosion
            if current_depth == 0:  # Level 1
                crawl_limit = 20
            elif current_depth == 1:  # Level 2  
                crawl_limit = 10
            else:  # Level 3+
                crawl_limit = 5
            
            # Recursively crawl deeper (only category/list pages)
            crawlable_urls = [url for url in list(page_urls)[:crawl_limit] 
                            if self._is_potential_category_or_list_page(url)]
            
            logger.debug(f"Level {current_depth + 1}: {len(crawlable_urls)} URLs eligible for deeper crawl")
            
            for url in crawlable_urls:
                try:
                    deeper_urls = self._deep_crawl_with_cycle_detection(
                        start_url=url,
                        max_depth=max_depth,
                        visited_urls=visited_urls,  # Share visited set
                        current_depth=current_depth + 1
                    )
                    discovered_urls.update(deeper_urls)
                    
                except Exception as e:
                    logger.warning(f"Error in recursive crawl for {url}: {e}")
                    continue
                
        except Exception as e:
            logger.warning(f"Error crawling {start_url}: {e}")
        
        return discovered_urls
    
    def _normalize_url_for_comparison(self, url: str) -> str:
        """Normalize URL for cycle detection comparison"""
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)
            
            # Normalize for comparison: remove query params, fragments, trailing slash
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc.lower(),
                parsed.path.rstrip('/'),
                '', '', ''  # Remove params, query, fragment
            ))
            
            return normalized
            
        except Exception:
            return url.lower().rstrip('/')
    
    def _extract_urls_from_single_page(self, page_url: str) -> set:
        """Extract all URLs from a single page"""
        urls = set()
        
        try:
            response = requests.get(page_url, timeout=15, headers={'User-Agent': 'DomainAnalyzer/1.0'})
            if response.status_code == 200:
                from lxml import html
                doc = html.fromstring(response.content)
                
                # Find all links in the page
                links = doc.cssselect('a[href]')
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(page_url, href)
                        # Clean URL artifacts
                        clean_url = self._clean_url_artifacts(full_url)
                        if self._is_valid_crawlable_url(clean_url, page_url):
                            urls.add(clean_url)
                            
        except Exception as e:
            logger.warning(f"Error extracting URLs from page {page_url}: {e}")
        
        return urls
    
    def _clean_url_artifacts(self, url: str) -> str:
        """Clean XML artifacts and other unwanted suffixes from URLs"""
        try:
            # Remove common XML artifacts from RSS/XML parsing
            artifacts = [']]></link>', ']]>', '</link>', '<![CDATA[', ']]']
            
            for artifact in artifacts:
                url = url.replace(artifact, '')
            
            # Remove CDATA prefix if exists
            if url.startswith('<![CDATA['):
                url = url[9:]  # Remove '<![CDATA['
                
            return url.strip()
            
        except Exception as e:
            logger.warning(f"Error cleaning URL artifacts from {url}: {e}")
            return url
    
    def _is_potential_category_or_list_page(self, url: str) -> bool:
        """Check if URL is likely a category/list page that should be crawled deeper"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Category/list page indicators
            category_indicators = [
                '/category/', '/section/', '/tag/', '/topic/',
                '/tin-tuc/', '/thoi-su/', '/the-gioi/', '/kinh-te/',
                '/giai-tri/', '/the-thao/', '/phap-luat/', '/giao-duc/',
                '/suc-khoe/', '/cong-nghe/', '/oto-xe-may/',
                '/page/', '/p/', '/trang-', '/danh-muc/'
            ]
            
            url_lower = url.lower()
            
            # Check for category indicators
            if any(indicator in url_lower for indicator in category_indicators):
                return True
            
            # Check if URL ends with common list page patterns
            if parsed.path.endswith(('/page', '/trang', '/p')) or '/page/' in url_lower:
                return True
            
            # Check path depth - category pages usually have moderate depth
            path_parts = [p for p in parsed.path.split('/') if p]
            if 1 <= len(path_parts) <= 3:
                return True
            
            return False
            
        except Exception:
            return False
    
    def _is_valid_crawlable_url(self, url: str, source_url: str) -> bool:
        """Check if URL is valid and worth crawling"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            source_parsed = urlparse(source_url)
            
            # Must be same domain
            if parsed.netloc != source_parsed.netloc:
                return False
            
            # Skip certain patterns
            skip_patterns = [
                'search', 'login', 'register', 'contact', 'about',
                'privacy', 'terms', 'sitemap.xml', 'robots.txt', 
                'javascript:', 'mailto:', '#', '?search', '?q=',
                '.jpg', '.png', '.gif', '.css', '.js', '.pdf',
                'facebook.com', 'twitter.com', 'youtube.com'
            ]
            
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in skip_patterns):
                return False
            
            # Must have reasonable length
            if len(url) > 300:
                return False
            
            # Check for valid URL structure
            if not (parsed.scheme in ['http', 'https'] and parsed.netloc):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _clean_and_deduplicate_urls(self, urls: List[str]) -> List[str]:
        """Clean and remove duplicate URLs"""
        seen_urls = set()
        clean_urls = []
        
        for url in urls:
            try:
                # Normalize URL for deduplication
                from urllib.parse import urlparse, urlunparse
                parsed = urlparse(url)
                
                # Create normalized version (remove fragments and query params for comparison)
                normalized = urlunparse((
                    parsed.scheme,
                    parsed.netloc.lower(),
                    parsed.path,
                    '', '', ''  # Remove params, query, fragment for dedup
                ))
                
                if normalized not in seen_urls:
                    seen_urls.add(normalized)
                    clean_urls.append(url)  # Keep original URL with query params if needed
                    
            except Exception:
                continue
        
        return clean_urls
    
    def _extract_urls_from_sitemaps(self, sitemaps: List[str]) -> List[str]:
        """Extract article URLs from sitemaps"""
        urls = set()
        
        for sitemap_url in sitemaps:
            try:
                response = requests.get(sitemap_url, timeout=15, headers={'User-Agent': 'DomainAnalyzer/1.0'})
                if response.status_code == 200:
                    from lxml import etree
                    try:
                        root = etree.fromstring(response.content)
                        # Handle different sitemap formats
                        for elem in root.iter():
                            if elem.tag.endswith('loc'):
                                url = elem.text
                                if url and self._is_article_url(url):
                                    urls.add(url)
                    except:
                        # If XML parsing fails, try regex
                        import re
                        url_pattern = r'<loc>(.*?)</loc>'
                        found_urls = re.findall(url_pattern, response.text)
                        for url in found_urls:
                            if self._is_article_url(url):
                                urls.add(url)
                                
            except Exception as e:
                logger.warning(f"Error parsing sitemap {sitemap_url}: {e}")
                continue
        
        return list(urls)
    
    def _extract_urls_from_homepage(self, homepage_url: str) -> List[str]:
        """Extract article URLs from homepage"""
        urls = set()
        
        try:
            response = requests.get(homepage_url, timeout=15, headers={'User-Agent': 'DomainAnalyzer/1.0'})
            if response.status_code == 200:
                from lxml import html
                doc = html.fromstring(response.content)
                
                # Find all links
                links = doc.cssselect('a[href]')
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(homepage_url, href)
                        if self._is_article_url(full_url):
                            urls.add(full_url)
                            
        except Exception as e:
            logger.warning(f"Error parsing homepage {homepage_url}: {e}")
        
        return list(urls)
    
    def _is_article_url(self, url: str) -> bool:
        """Check if URL looks like an article URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Skip certain patterns
            skip_patterns = [
                'search', 'login', 'register', 'contact', 'about',
                'privacy', 'terms', 'sitemap', 'rss', 'feed', 'category',
                'tag', 'author', 'page', 'javascript:', 'mailto:', '#'
            ]
            
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in skip_patterns):
                return False
            
            # Check for article indicators
            article_indicators = [
                '.html', '.htm', '/20', '/article', '/news', '/post'
            ]
            
            if any(indicator in url_lower for indicator in article_indicators):
                return True
            
            # Check path structure (articles usually have deeper paths)
            path_parts = [p for p in parsed.path.split('/') if p]
            return len(path_parts) >= 2 and len(path_parts) <= 6
            
        except Exception:
            return False
    
    def _deduplicate_and_filter_urls(self, urls: List[str], domain_url: str) -> List[str]:
        """Deduplicate and filter URLs"""
        from urllib.parse import urlparse
        domain_parsed = urlparse(domain_url)
        
        seen_urls = set()
        final_urls = []
        
        for url in urls:
            try:
                # Normalize URL
                parsed = urlparse(url)
                
                # Only keep URLs from same domain
                if parsed.netloc != domain_parsed.netloc:
                    continue
                
                # Create normalized version for deduplication
                normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                
                if normalized not in seen_urls:
                    seen_urls.add(normalized)
                    final_urls.append(url)
                    
            except Exception:
                continue
        
        return final_urls