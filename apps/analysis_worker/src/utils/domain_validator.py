"""
Domain Accessibility Validator
Comprehensive domain validation for Vietnamese news sites
Author: James (Dev Agent)
Date: 2025-08-12
"""

import asyncio
import aiohttp
import logging
import socket
import ssl
import time
from typing import Dict, Any, List, Tuple, Optional, Set
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta
import validators
import dns.resolver
import dns.exception

from .vietnamese_utils import VietnameseContentProcessor


class DomainValidationResult:
    """Domain validation result data structure"""
    
    def __init__(self):
        self.is_valid = False
        self.is_accessible = False
        self.is_vietnamese_content = False
        self.response_time_ms = 0
        self.status_code = 0
        self.content_type = ""
        self.content_size = 0
        self.ssl_valid = False
        self.redirects = []
        self.errors = []
        self.warnings = []
        self.vietnamese_analysis = {}
        self.technical_details = {}
        self.validation_timestamp = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "is_valid": self.is_valid,
            "is_accessible": self.is_accessible,
            "is_vietnamese_content": self.is_vietnamese_content,
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "content_size": self.content_size,
            "ssl_valid": self.ssl_valid,
            "redirects": self.redirects,
            "errors": self.errors,
            "warnings": self.warnings,
            "vietnamese_analysis": self.vietnamese_analysis,
            "technical_details": self.technical_details,
            "validation_timestamp": self.validation_timestamp.isoformat()
        }


class DomainValidator:
    """
    Comprehensive domain validator for Vietnamese news sites
    Validates accessibility, content, SSL, and Vietnamese content
    """
    
    def __init__(self):
        """Initialize domain validator"""
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self.vietnamese_processor = VietnameseContentProcessor()
        
        # Validation configuration
        self.timeout = 15  # seconds
        self.max_redirects = 5
        self.min_content_size = 500  # bytes
        self.max_content_size = 10 * 1024 * 1024  # 10MB
        self.user_agent = "Domain-Validator/1.0 (Vietnamese News Crawler)"
        
        # Cache for DNS lookups and validations
        self.dns_cache: Dict[str, Tuple[bool, datetime]] = {}
        self.validation_cache: Dict[str, Tuple[DomainValidationResult, datetime]] = {}
        self.cache_ttl = timedelta(minutes=30)
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self) -> None:
        """Initialize HTTP session and DNS resolver"""
        if self.session and not self.session.closed:
            return
        
        # Configure HTTP connector
        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=5,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
            verify_ssl=True
        )
        
        # Configure timeout
        timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=10,
            sock_read=10
        )
        
        # Create session
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'vi,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        self.logger.info("Domain validator initialized")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        
        self.logger.info("Domain validator cleaned up")
    
    async def validate_domain(self, url: str, use_cache: bool = True) -> DomainValidationResult:
        """
        Comprehensive domain validation
        
        Args:
            url: URL to validate
            use_cache: Whether to use cached results
            
        Returns:
            DomainValidationResult with complete validation info
        """
        if not self.session:
            await self.initialize()
        
        result = DomainValidationResult()
        
        try:
            # Check cache first
            if use_cache and url in self.validation_cache:
                cached_result, cached_time = self.validation_cache[url]
                if datetime.now() - cached_time < self.cache_ttl:
                    self.logger.debug(f"Using cached validation for {url}")
                    return cached_result
            
            self.logger.info(f"Validating domain: {url}")
            start_time = time.time()
            
            # Phase 1: Basic URL validation
            if not self._validate_url_format(url, result):
                return result
            
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Phase 2: DNS resolution
            if not await self._validate_dns_resolution(domain, result):
                return result
            
            # Phase 3: HTTP accessibility check
            if not await self._validate_http_accessibility(url, result):
                return result
            
            # Phase 4: Content analysis
            await self._analyze_content(url, result)
            
            # Phase 5: SSL validation (if HTTPS)
            if parsed.scheme == 'https':
                await self._validate_ssl(domain, result)
            
            # Phase 6: Vietnamese content detection
            await self._detect_vietnamese_content(result)
            
            # Phase 7: Technical checks
            await self._perform_technical_checks(url, result)
            
            # Calculate overall validation
            result.is_valid = self._calculate_overall_validity(result)
            
            # Record timing
            result.response_time_ms = int((time.time() - start_time) * 1000)
            
            # Cache result
            if use_cache:
                self.validation_cache[url] = (result, datetime.now())
            
            self.logger.info(f"Domain validation completed for {url}: valid={result.is_valid}")
            return result
            
        except Exception as e:
            error_msg = f"Domain validation failed: {e}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
            return result
    
    def _validate_url_format(self, url: str, result: DomainValidationResult) -> bool:
        """Validate URL format"""
        try:
            if not url or not isinstance(url, str):
                result.errors.append("Invalid URL: empty or not string")
                return False
            
            # Basic URL validation
            if not validators.url(url):
                result.errors.append("Invalid URL format")
                return False
            
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                result.errors.append(f"Unsupported scheme: {parsed.scheme}")
                return False
            
            # Check domain
            if not parsed.netloc:
                result.errors.append("Missing domain in URL")
                return False
            
            # Check for localhost/private IPs
            if any(term in parsed.netloc.lower() for term in ['localhost', '127.0.0.1', '0.0.0.0']):
                result.errors.append("Local/private domain not allowed")
                return False
            
            return True
            
        except Exception as e:
            result.errors.append(f"URL format validation error: {e}")
            return False
    
    async def _validate_dns_resolution(self, domain: str, result: DomainValidationResult) -> bool:
        """Validate DNS resolution"""
        try:
            # Check cache first
            if domain in self.dns_cache:
                is_resolved, cached_time = self.dns_cache[domain]
                if datetime.now() - cached_time < self.cache_ttl:
                    if not is_resolved:
                        result.errors.append("DNS resolution failed (cached)")
                    return is_resolved
            
            # Perform DNS lookup
            resolver = dns.resolver.Resolver()
            resolver.timeout = 5
            resolver.lifetime = 10
            
            try:
                # Try A record
                answers = await asyncio.get_event_loop().run_in_executor(
                    None, resolver.resolve, domain, 'A'
                )
                
                if answers:
                    ips = [str(answer) for answer in answers]
                    result.technical_details["dns_a_records"] = ips
                    
                    # Cache successful resolution
                    self.dns_cache[domain] = (True, datetime.now())
                    return True
                
            except dns.exception.DNSException as e:
                # Try AAAA record for IPv6
                try:
                    answers = await asyncio.get_event_loop().run_in_executor(
                        None, resolver.resolve, domain, 'AAAA'
                    )
                    
                    if answers:
                        ips = [str(answer) for answer in answers]
                        result.technical_details["dns_aaaa_records"] = ips
                        
                        # Cache successful resolution
                        self.dns_cache[domain] = (True, datetime.now())
                        return True
                        
                except dns.exception.DNSException:
                    pass
                
                error_msg = f"DNS resolution failed: {e}"
                result.errors.append(error_msg)
                
                # Cache failed resolution
                self.dns_cache[domain] = (False, datetime.now())
                return False
            
            return False
            
        except Exception as e:
            error_msg = f"DNS validation error: {e}"
            result.errors.append(error_msg)
            self.dns_cache[domain] = (False, datetime.now())
            return False
    
    async def _validate_http_accessibility(self, url: str, result: DomainValidationResult) -> bool:
        """Validate HTTP accessibility"""
        try:
            start_time = time.time()
            
            async with self.session.get(url, allow_redirects=True) as response:
                # Record response time
                response_time = int((time.time() - start_time) * 1000)
                result.response_time_ms = response_time
                
                # Record status
                result.status_code = response.status
                result.content_type = response.headers.get('content-type', '')
                
                # Check status code
                if response.status >= 400:
                    result.errors.append(f"HTTP {response.status}: {response.reason}")
                    return False
                
                if response.status >= 300:
                    result.warnings.append(f"HTTP {response.status}: Redirected")
                
                # Record redirects
                if hasattr(response, 'history') and response.history:
                    for redirect in response.history:
                        result.redirects.append({
                            "from": str(redirect.url),
                            "to": str(redirect.headers.get('location', '')),
                            "status": redirect.status
                        })
                
                # Check content type
                if 'text/html' not in result.content_type.lower():
                    result.warnings.append(f"Non-HTML content type: {result.content_type}")
                
                # Read content for analysis
                try:
                    content = await response.text()
                    result.content_size = len(content)
                    
                    # Store content for further analysis
                    result.technical_details["html_content"] = content
                    
                    # Check content size
                    if result.content_size < self.min_content_size:
                        result.warnings.append(f"Small content size: {result.content_size} bytes")
                    elif result.content_size > self.max_content_size:
                        result.warnings.append(f"Large content size: {result.content_size} bytes")
                    
                    result.is_accessible = True
                    return True
                    
                except Exception as e:
                    result.errors.append(f"Content reading error: {e}")
                    return False
                
        except asyncio.TimeoutError:
            result.errors.append("Connection timeout")
            return False
        except aiohttp.ClientError as e:
            result.errors.append(f"HTTP client error: {e}")
            return False
        except Exception as e:
            result.errors.append(f"HTTP accessibility error: {e}")
            return False
    
    async def _analyze_content(self, url: str, result: DomainValidationResult) -> None:
        """Analyze page content"""
        try:
            html_content = result.technical_details.get("html_content", "")
            if not html_content:
                return
            
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract basic metadata
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            description = soup.find('meta', {'name': 'description'})
            description_text = description.get('content', '').strip() if description else ""
            
            # Count elements
            link_count = len(soup.find_all('a', href=True))
            image_count = len(soup.find_all('img'))
            script_count = len(soup.find_all('script'))
            
            # Store analysis
            result.technical_details.update({
                "title": title_text,
                "description": description_text,
                "link_count": link_count,
                "image_count": image_count,
                "script_count": script_count,
                "has_navigation": bool(soup.find(['nav', '[class*="nav"]', '[class*="menu"]'])),
                "has_articles": bool(soup.find(['article', '[class*="article"]', '[class*="news"]']))
            })
            
            # Check for common news site indicators
            news_indicators = [
                'tin tức', 'báo', 'news', 'article', 'thời sự', 'chính trị',
                'kinh tế', 'thể thao', 'giáo dục', 'sức khỏe'
            ]
            
            content_text = soup.get_text().lower()
            news_score = sum(1 for indicator in news_indicators if indicator in content_text)
            
            result.technical_details["news_content_score"] = news_score
            result.technical_details["likely_news_site"] = news_score >= 2
            
        except Exception as e:
            result.warnings.append(f"Content analysis error: {e}")
    
    async def _validate_ssl(self, domain: str, result: DomainValidationResult) -> None:
        """Validate SSL certificate"""
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to domain
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, sock.connect, (domain, 443)
                )
                
                # Wrap with SSL
                ssl_sock = context.wrap_socket(sock, server_hostname=domain)
                
                # Get certificate info
                cert = ssl_sock.getpeercert()
                
                if cert:
                    result.ssl_valid = True
                    result.technical_details["ssl_certificate"] = {
                        "subject": dict(x[0] for x in cert.get('subject', [])),
                        "issuer": dict(x[0] for x in cert.get('issuer', [])),
                        "version": cert.get('version', 0),
                        "serialNumber": cert.get('serialNumber', ''),
                        "notBefore": cert.get('notBefore', ''),
                        "notAfter": cert.get('notAfter', '')
                    }
                else:
                    result.warnings.append("SSL certificate not found")
                
                ssl_sock.close()
                
            except Exception as e:
                result.warnings.append(f"SSL validation error: {e}")
            finally:
                sock.close()
                
        except Exception as e:
            result.warnings.append(f"SSL connection error: {e}")
    
    async def _detect_vietnamese_content(self, result: DomainValidationResult) -> None:
        """Detect Vietnamese content in the page"""
        try:
            html_content = result.technical_details.get("html_content", "")
            if not html_content:
                return
            
            # Analyze Vietnamese content
            title = result.technical_details.get("title", "")
            description = result.technical_details.get("description", "")
            
            # Check title for Vietnamese
            title_analysis = self.vietnamese_processor.detect_vietnamese_content(title)
            
            # Check description for Vietnamese  
            desc_analysis = self.vietnamese_processor.detect_vietnamese_content(description)
            
            # Check full content for Vietnamese
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()
            
            content_text = soup.get_text()
            content_analysis = self.vietnamese_processor.detect_vietnamese_content(content_text)
            
            # Store Vietnamese analysis
            result.vietnamese_analysis = {
                "title_analysis": title_analysis,
                "description_analysis": desc_analysis,
                "content_analysis": content_analysis,
                "overall_vietnamese": any([
                    title_analysis.get("is_vietnamese", False),
                    desc_analysis.get("is_vietnamese", False),
                    content_analysis.get("is_vietnamese", False)
                ]),
                "confidence_score": max([
                    title_analysis.get("confidence", 0),
                    desc_analysis.get("confidence", 0),
                    content_analysis.get("confidence", 0)
                ])
            }
            
            result.is_vietnamese_content = result.vietnamese_analysis["overall_vietnamese"]
            
        except Exception as e:
            result.warnings.append(f"Vietnamese content detection error: {e}")
    
    async def _perform_technical_checks(self, url: str, result: DomainValidationResult) -> None:
        """Perform additional technical checks"""
        try:
            # Check robots.txt
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            try:
                async with self.session.get(robots_url) as response:
                    if response.status == 200:
                        robots_content = await response.text()
                        result.technical_details["has_robots_txt"] = True
                        result.technical_details["robots_txt_size"] = len(robots_content)
                        
                        # Check for sitemap references
                        sitemaps = []
                        for line in robots_content.split('\n'):
                            if line.strip().lower().startswith('sitemap:'):
                                sitemap_url = line.split(':', 1)[1].strip()
                                sitemaps.append(sitemap_url)
                        
                        result.technical_details["sitemaps_in_robots"] = sitemaps
                    else:
                        result.technical_details["has_robots_txt"] = False
                        
            except Exception:
                result.technical_details["has_robots_txt"] = False
            
            # Check sitemap.xml
            sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
            
            try:
                async with self.session.get(sitemap_url) as response:
                    if response.status == 200:
                        result.technical_details["has_sitemap_xml"] = True
                    else:
                        result.technical_details["has_sitemap_xml"] = False
                        
            except Exception:
                result.technical_details["has_sitemap_xml"] = False
            
        except Exception as e:
            result.warnings.append(f"Technical checks error: {e}")
    
    def _calculate_overall_validity(self, result: DomainValidationResult) -> bool:
        """Calculate overall domain validity"""
        # Basic requirements
        if not result.is_accessible:
            return False
        
        if result.status_code >= 400:
            return False
        
        if len(result.errors) > 0:
            return False
        
        # Content requirements
        if result.content_size < self.min_content_size:
            return False
        
        # All checks passed
        return True
    
    async def validate_multiple_domains(self, urls: List[str]) -> Dict[str, DomainValidationResult]:
        """
        Validate multiple domains concurrently
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            Dictionary mapping URLs to validation results
        """
        if not self.session:
            await self.initialize()
        
        # Limit concurrent validations
        semaphore = asyncio.Semaphore(5)
        
        async def validate_with_semaphore(url: str) -> Tuple[str, DomainValidationResult]:
            async with semaphore:
                result = await self.validate_domain(url)
                return url, result
        
        # Run validations concurrently
        tasks = [validate_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        validation_results = {}
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Validation error: {result}")
                continue
            
            url, validation_result = result
            validation_results[url] = validation_result
        
        return validation_results
    
    def get_validation_summary(self, results: Dict[str, DomainValidationResult]) -> Dict[str, Any]:
        """Generate validation summary statistics"""
        total = len(results)
        valid = sum(1 for r in results.values() if r.is_valid)
        accessible = sum(1 for r in results.values() if r.is_accessible)
        vietnamese = sum(1 for r in results.values() if r.is_vietnamese_content)
        
        avg_response_time = sum(r.response_time_ms for r in results.values()) / max(1, total)
        
        return {
            "total_domains": total,
            "valid_domains": valid,
            "accessible_domains": accessible,
            "vietnamese_content_domains": vietnamese,
            "validity_rate": round(valid / max(1, total) * 100, 2),
            "accessibility_rate": round(accessible / max(1, total) * 100, 2),
            "vietnamese_content_rate": round(vietnamese / max(1, total) * 100, 2),
            "average_response_time_ms": round(avg_response_time, 2),
            "timestamp": datetime.now().isoformat()
        }