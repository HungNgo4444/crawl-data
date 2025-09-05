"""
URL extractor for monitoring domains - adapted from domain-analyzer
"""
import logging
from typing import Dict, List, Any
from urllib.parse import urljoin, urlparse
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import newspaper4k
from newspaper import Source, Config
from ..config.worker_config import get_worker_config

logger = logging.getLogger(__name__)

class URLExtractor:
    """URL extractor using newspaper4k for monitoring"""
    
    def __init__(self):
        self.config = Config()
        self.config.language = 'vi'  # Vietnamese language
        self.config.memoize_articles = False
        self.config.fetch_images = False
        self.config.number_threads = 1
        self.config.disable_category_cache = True
        self.worker_config = get_worker_config()
        
        # ✅ Setup session with retry strategy
        self.session = self._create_session_with_retry()
    
    def _create_session_with_retry(self):
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        
        # Define retry strategy
        retry_strategy = Retry(
            total=3,  # Total number of retries
            status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # HTTP methods to retry (updated from method_whitelist)
            backoff_factor=1,  # Backoff factor (1, 2, 4 seconds)
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': 'URLTrackingWorker/2.0 (Newspaper URL Extractor)'
        })
        
        return session
        
    def extract_article_urls_from_domain_data(self, domain_url: str, domain_name: str, 
                                             domain_data: Dict[str, Any]) -> List[str]:
        """
        Extract article URLs from domain data for monitoring
        
        Args:
            domain_url: Base URL of the domain
            domain_name: Domain name
            domain_data: Domain data containing rss_feeds, sitemaps, etc.
            
        Returns:
            List of deduplicated article URLs
        """
        logger.info(f"🔍 Extracting article URLs for monitoring: {domain_name}")
        
        all_article_urls = set()
        
        # 🛡️ ENHANCED DEDUPLICATION: Pre-populate with source URLs to exclude them
        source_urls_to_exclude = set()
        
        # Add homepage URLs to exclusion set
        if domain_data.get('homepage_urls'):
            for url in domain_data['homepage_urls']:
                source_urls_to_exclude.add(self._normalize_url_for_comparison(url))
                
        # Add category URLs to exclusion set  
        if domain_data.get('category_urls'):
            for url in domain_data['category_urls']:
                source_urls_to_exclude.add(self._normalize_url_for_comparison(url))
                
        # Add sitemap URLs to exclusion set
        if domain_data.get('sitemaps'):
            for url in domain_data['sitemaps']:
                source_urls_to_exclude.add(self._normalize_url_for_comparison(url))
                
        # Add RSS feed URLs to exclusion set
        if domain_data.get('rss_feeds'):
            for url in domain_data['rss_feeds']:
                source_urls_to_exclude.add(self._normalize_url_for_comparison(url))
                
        # Add base domain URL to exclusion set
        source_urls_to_exclude.add(self._normalize_url_for_comparison(domain_url))
        
        logger.info(f"🛡️ Pre-loaded {len(source_urls_to_exclude)} source URLs to exclude from article extraction")
        
        try:
            # Extract from RSS feeds
            if domain_data.get('rss_feeds'):
                rss_articles = self._extract_urls_from_rss_feeds(domain_data['rss_feeds'])
                # Apply exclusion filter
                filtered_rss = self._apply_source_url_exclusion(rss_articles, source_urls_to_exclude)
                all_article_urls.update(filtered_rss)
                logger.info(f"📰 Extracted {len(filtered_rss)} URLs from RSS feeds (filtered from {len(rss_articles)})")
            
            # Extract from category pages
            if domain_data.get('category_urls'):
                category_articles = self._extract_urls_from_categories(domain_data['category_urls'])
                # Apply exclusion filter  
                filtered_categories = self._apply_source_url_exclusion(category_articles, source_urls_to_exclude)
                all_article_urls.update(filtered_categories)
                logger.info(f"📂 Extracted {len(filtered_categories)} URLs from categories (filtered from {len(category_articles)})")
            
            # Extract from sitemaps (if enabled)
            if domain_data.get('sitemaps') and self.worker_config.get('enable_sitemap_monitoring', False):
                sitemap_articles = self._extract_urls_from_sitemaps(domain_data['sitemaps'])
                # Apply exclusion filter
                filtered_sitemaps = self._apply_source_url_exclusion(sitemap_articles, source_urls_to_exclude)
                all_article_urls.update(filtered_sitemaps)
                logger.info(f"🗺️ Extracted {len(filtered_sitemaps)} URLs from sitemaps (filtered from {len(sitemap_articles)})")
            elif domain_data.get('sitemaps'):
                logger.info("Sitemap monitoring is disabled - skipping sitemap URL extraction")
            
            # Extract from homepage
            if domain_data.get('homepage_urls'):
                homepage_articles = self._extract_urls_from_homepage(domain_data['homepage_urls'][0])
                # Apply exclusion filter
                filtered_homepage = self._apply_source_url_exclusion(homepage_articles, source_urls_to_exclude)
                all_article_urls.update(filtered_homepage)
                logger.info(f"🏠 Extracted {len(filtered_homepage)} URLs from homepage (filtered from {len(homepage_articles)})")
            
            # Use newspaper4k built-in discovery for additional URLs
            try:
                source = Source(domain_url, config=self.config)
                source.build()
                builtin_articles = source.article_urls()
                # Apply exclusion filter
                filtered_builtin = self._apply_source_url_exclusion(builtin_articles, source_urls_to_exclude)
                all_article_urls.update(filtered_builtin)
                logger.info(f"📚 Extracted {len(filtered_builtin)} URLs from newspaper4k built-in (filtered from {len(builtin_articles)})")
            except Exception as e:
                logger.warning(f"Error with newspaper4k built-in extraction: {e}")
            
        except Exception as e:
            logger.error(f"Error extracting article URLs for {domain_name}: {e}")
        
        # Deduplicate and filter
        final_urls = self._deduplicate_and_filter_urls(list(all_article_urls), domain_url)
        logger.info(f"Final count after deduplication: {len(final_urls)} URLs for {domain_name}")
        
        return final_urls
    
    def _apply_source_url_exclusion(self, urls: List[str], source_urls_to_exclude: set) -> List[str]:
        """
        Filter out URLs that match homepage, category, sitemap, or RSS feed URLs
        
        Args:
            urls: List of URLs to filter
            source_urls_to_exclude: Set of normalized source URLs to exclude
            
        Returns:
            List of URLs that don't match any source URLs
        """
        filtered_urls = []
        excluded_count = 0
        
        for url in urls:
            normalized_url = self._normalize_url_for_comparison(url)
            
            if normalized_url not in source_urls_to_exclude:
                filtered_urls.append(url)
            else:
                excluded_count += 1
                logger.debug(f"🚫 Excluded source URL duplicate: {url}")
        
        if excluded_count > 0:
            logger.info(f"🛡️ Cross-reference exclusion: filtered out {excluded_count} source URL duplicates")
        
        return filtered_urls
    
    def _extract_urls_from_rss_feeds(self, rss_feeds: List[str]) -> List[str]:
        """Extract article URLs from RSS feeds using feedparser"""
        urls = set()
        
        for rss_url in rss_feeds:
            try:
                import feedparser
                feed = feedparser.parse(rss_url)
                
                # Extract URLs from RSS entries
                for entry in feed.entries:
                    if hasattr(entry, 'link') and entry.link:
                        # Clean XML artifacts from URL
                        clean_url = self._clean_url_artifacts(entry.link)
                        if self._is_article_url(clean_url):
                            urls.add(clean_url)
                            
                logger.debug(f"RSS {rss_url}: found {len(urls)} article URLs")
                            
            except Exception as e:
                logger.warning(f"Error parsing RSS feed {rss_url}: {e}")
                continue
        
        return list(urls)
    
    def _clean_url_artifacts(self, url: str) -> str:
        """Clean XML artifacts, decode URL encoding and fix Vietnamese characters"""
        try:
            # Remove common XML artifacts
            artifacts = [']]></link>', ']]>', '</link>', '<![CDATA[', ']]']
            
            for artifact in artifacts:
                url = url.replace(artifact, '')
            
            # Remove CDATA prefix if exists
            if url.startswith('<![CDATA['):
                url = url[9:]  # Remove '<![CDATA['
            
            # 🔧 FIX URL ENCODING: Decode Vietnamese characters from newspaper4k
            try:
                from urllib.parse import unquote
                # Decode URL encoding like %C3%A1 -> á, %E1%BA%A5 -> ấ
                decoded_url = unquote(url)
                
                # Replace + with spaces (common in URL encoding)
                decoded_url = decoded_url.replace('+', ' ')
                
                # Only use decoded version if it looks better (has Vietnamese chars)
                if any(ord(c) > 127 for c in decoded_url) or ' ' in decoded_url:
                    url = decoded_url
                    logger.debug(f"🔤 URL decoded: {url[:100]}...")
                    
            except Exception as e:
                logger.debug(f"URL decoding failed for {url[:100]}: {e}")
                
            return url.strip()
            
        except Exception as e:
            logger.warning(f"Error cleaning URL artifacts from {url}: {e}")
            return url
    
    def _extract_urls_from_categories(self, category_urls: List[str]) -> List[str]:
        """Extract article URLs from category pages with OPTIMIZED deep crawling + Early Deduplication"""
        all_urls = set()
        visited_pages = set()  # Track visited page URLs to prevent infinite loops
        global_seen_urls = set()  # EARLY DEDUPLICATION: Global set to prevent duplicate URL processing
        
        for category_url in category_urls:  # NO LIMIT - process all categories
            try:
                logger.info(f"🔍 Processing category: {category_url}")
                
                # Optimized deep crawl with immediate database save after each level
                deep_urls = self._optimized_deep_crawl_with_early_dedup(
                    start_url=category_url,
                    max_depth=1,
                    visited_pages=visited_pages,  # Share visited pages across categories
                    global_seen_urls=global_seen_urls,  # Share seen URLs for early dedup
                    current_depth=0,
                    domain_id=getattr(self, '_current_domain_id', None),  # Pass domain_id if available
                    db_manager=getattr(self, '_current_db_manager', None)  # Pass db_manager if available
                )
                
                all_urls.update(deep_urls)
                logger.info(f"✅ Deep crawl completed for {category_url}: {len(deep_urls)} new URLs, {len(global_seen_urls)} total seen")
                
            except Exception as e:
                logger.warning(f"❌ Error in deep crawling category {category_url}: {e}")
                continue
        
        # No final deduplication needed - already done during crawling!
        final_urls = list(all_urls)
        logger.info(f"🚀 OPTIMIZED deep crawling completed: {len(final_urls)} unique URLs (early dedup saved time!)")
        return final_urls
    
    def _deep_crawl_with_cycle_detection(self, start_url: str, max_depth: int, 
                                       visited_urls: set, current_depth: int) -> set:
        """
        Recursive deep crawl with cycle detection and depth tracking (NO URL LIMITS)
        
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
            
            # NO LIMITS - crawl ALL eligible URLs (only category/list pages to prevent article-to-article crawling)
            crawlable_urls = [url for url in page_urls if self._is_potential_category_or_list_page(url)]
            
            logger.debug(f"Level {current_depth + 1}: {len(crawlable_urls)} URLs eligible for deeper crawl")
            
            for url in crawlable_urls:  # NO LIMIT - process all crawlable URLs
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
    
    def _optimized_deep_crawl_with_early_dedup(self, start_url: str, max_depth: int, 
                                             visited_pages: set, global_seen_urls: set, 
                                             current_depth: int, domain_id: str = None, 
                                             db_manager=None) -> set:
        """
        OPTIMIZED recursive deep crawl with IMMEDIATE database save after each level
        
        Args:
            start_url: URL to start crawling from
            max_depth: Maximum crawl depth
            visited_pages: Set of visited page URLs (for cycle detection)
            global_seen_urls: Global set of all discovered URLs (for early dedup)
            current_depth: Current crawl depth
            domain_id: Domain ID for immediate database save
            db_manager: Database manager for immediate save
            
        Returns:
            Set of NEW discovered URLs (saved to database immediately)
        """
        new_urls_this_call = set()
        
        # Check depth limit
        if max_depth > 0 and current_depth >= max_depth:
            logger.debug(f"⏹️ Reached max depth {max_depth} for {start_url}")
            return new_urls_this_call
        
        # Normalize URL for cycle detection
        normalized_page_url = self._normalize_url_for_comparison(start_url)
        
        # Check if page already visited (cycle detection)
        if normalized_page_url in visited_pages:
            logger.debug(f"🔄 Cycle detected: page {start_url} already crawled")
            return new_urls_this_call
        
        # Mark page as visited
        visited_pages.add(normalized_page_url)
        
        logger.info(f"🔍 Level {current_depth + 1}: Crawling {start_url}")
        
        try:
            # Extract URLs from current page
            page_urls = self._extract_urls_from_single_page(start_url)
            
            # ⚡ EARLY DEDUPLICATION: Only keep URLs we haven't seen before
            truly_new_urls = set()
            skipped_duplicates = 0
            
            for url in page_urls:
                normalized_url = self._normalize_url_for_comparison(url)
                if normalized_url not in global_seen_urls:
                    global_seen_urls.add(normalized_url)  # Mark as seen globally
                    truly_new_urls.add(url)  # Keep original URL
                else:
                    skipped_duplicates += 1
            
            new_urls_this_call.update(truly_new_urls)
            
            # 💾 IMMEDIATE DATABASE SAVE: Save URLs từng level luôn
            if truly_new_urls and domain_id and db_manager:
                try:
                    new_urls_list = list(truly_new_urls)
                    # Filter out URLs already in database
                    filtered_new_urls = db_manager.filter_new_urls_only(new_urls_list, domain_id)
                    
                    if filtered_new_urls:
                        # Save immediately to database
                        urls_saved = db_manager.bulk_add_urls_to_tracking(
                            filtered_new_urls, domain_id, f'deep-crawl-level-{current_depth + 1}'
                        )
                        logger.info(f"💾 IMMEDIATE SAVE Level {current_depth + 1}: Saved {urls_saved} URLs to database from {start_url}")
                    else:
                        logger.debug(f"💾 Level {current_depth + 1}: All URLs already exist in database - no save needed")
                        
                except Exception as e:
                    logger.warning(f"❌ Error saving URLs to database at level {current_depth + 1}: {e}")
            
            logger.info(f"⚡ Level {current_depth + 1}: Found {len(page_urls)} total URLs, {len(truly_new_urls)} NEW URLs, skipped {skipped_duplicates} duplicates from {start_url}")
            
            # Only crawl deeper if we found new category/list pages
            crawlable_urls = [url for url in truly_new_urls if self._is_potential_category_or_list_page(url)]
            
            if crawlable_urls:
                logger.debug(f"🔗 Level {current_depth + 1}: {len(crawlable_urls)} NEW category URLs eligible for deeper crawl")
                
                # Recursive crawl of new category pages only
                for url in crawlable_urls:
                    try:
                        deeper_urls = self._optimized_deep_crawl_with_early_dedup(
                            start_url=url,
                            max_depth=max_depth,
                            visited_pages=visited_pages,  # Share visited pages
                            global_seen_urls=global_seen_urls,  # Share discovered URLs
                            current_depth=current_depth + 1,
                            domain_id=domain_id,  # Pass domain_id for database save
                            db_manager=db_manager  # Pass db_manager for immediate save
                        )
                        new_urls_this_call.update(deeper_urls)
                        
                    except Exception as e:
                        logger.warning(f"❌ Error in recursive crawl for {url}: {e}")
                        continue
            else:
                logger.debug(f"🚫 Level {current_depth + 1}: No new category URLs to crawl deeper")
                
        except Exception as e:
            logger.warning(f"❌ Error crawling page {start_url}: {e}")
        
        return new_urls_this_call
    
    def _extract_urls_from_single_page(self, page_url: str) -> set:
        """Extract all URLs from a single page"""
        urls = set()
        
        try:
            # ✅ Use session with retry strategy
            response = self.session.get(page_url, timeout=15)
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
    
    def _normalize_url_for_comparison(self, url: str) -> str:
        """Normalize URL for cycle detection comparison with URL decoding"""
        try:
            from urllib.parse import urlparse, urlunparse, unquote
            
            # First decode URL encoding to handle Vietnamese characters properly
            try:
                decoded_url = unquote(url).replace('+', ' ')
            except:
                decoded_url = url
            
            parsed = urlparse(decoded_url)
            
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
    
    def _extract_urls_from_sitemaps(self, sitemaps: List[str]) -> List[str]:
        """Extract article URLs from sitemaps"""
        urls = set()
        
        for sitemap_url in sitemaps:
            try:
                # ✅ Use session with retry strategy
                response = self.session.get(sitemap_url, timeout=15)
                if response.status_code == 200:
                    from lxml import etree
                    try:
                        root = etree.fromstring(response.content)
                        # Handle different sitemap formats
                        for elem in root.iter():
                            if elem.tag.endswith('loc'):
                                url = elem.text
                                if url:
                                    clean_url = self._clean_url_artifacts(url)
                                    if self._is_article_url(clean_url):
                                        urls.add(clean_url)
                    except:
                        # If XML parsing fails, try regex
                        import re
                        url_pattern = r'<loc>(.*?)</loc>'
                        found_urls = re.findall(url_pattern, response.text)
                        for url in found_urls:
                            clean_url = self._clean_url_artifacts(url)
                            if self._is_article_url(clean_url):
                                urls.add(clean_url)
                                
            except Exception as e:
                logger.warning(f"Error parsing sitemap {sitemap_url}: {e}")
                continue
        
        return list(urls)
    
    def _extract_urls_from_homepage(self, homepage_url: str) -> List[str]:
        """Extract article URLs from homepage"""
        urls = set()
        
        try:
            # ✅ Use session with retry strategy
            response = self.session.get(homepage_url, timeout=15)
            if response.status_code == 200:
                from lxml import html
                doc = html.fromstring(response.content)
                
                # Find all links
                links = doc.cssselect('a[href]')
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(homepage_url, href)
                        clean_url = self._clean_url_artifacts(full_url)
                        if self._is_article_url(clean_url):
                            urls.add(clean_url)
                            
        except Exception as e:
            logger.warning(f"Error parsing homepage {homepage_url}: {e}")
        
        return list(urls)
    
    def _is_article_url(self, url: str) -> bool:
        """Check if URL looks like an article URL"""
        try:
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
        """Deduplicate and filter URLs - no normalization, keep original URLs"""
        domain_parsed = urlparse(domain_url)
        
        seen_urls = set()
        final_urls = []
        
        for url in urls:
            try:
                # Parse URL for domain check
                parsed = urlparse(url)
                
                # Only keep URLs from same domain
                if parsed.netloc != domain_parsed.netloc:
                    continue
                
                # Deduplicate based on exact URL
                if url not in seen_urls:
                    seen_urls.add(url)
                    final_urls.append(url)
                    
            except Exception:
                continue
        
        return final_urls