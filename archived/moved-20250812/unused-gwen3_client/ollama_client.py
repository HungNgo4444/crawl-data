"""
Ollama GWEN-3 Client Implementation
Async HTTP client for Vietnamese content analysis via Ollama API
Author: James (Dev Agent)
Date: 2025-08-11
"""

import asyncio
import aiohttp
import json
import logging
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .config import config

@dataclass
class AnalysisResult:
    """Result of Vietnamese content analysis"""
    
    # Analysis metadata
    domain_name: str
    analysis_id: str
    timestamp: datetime
    analysis_duration_seconds: float
    
    # Model information
    model_name: str
    model_version: Optional[str]
    
    # Analysis results
    confidence_score: float
    language_detected: str
    parsing_template: Dict[str, Any]
    structure_hash: str
    
    # Vietnamese content specifics
    headline_selectors: List[str]
    content_selectors: List[str]
    metadata_selectors: Dict[str, str]
    navigation_patterns: List[str]
    
    # Quality metrics
    extraction_accuracy: float
    template_complexity: int
    
    # Error information
    errors: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

class OllamaGWEN3Client:
    """
    Async client for GWEN-3 model via Ollama API
    Optimized for Vietnamese news content analysis
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize Ollama client with configuration"""
        self.config = config
        self.base_url = base_url or self.config.ollama.base_url
        self.model_name = self.config.ollama.model_name
        
        # Connection management
        self.session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        
        # Logging setup
        self.logger = logging.getLogger(__name__)
        
        # Request tracking
        self._active_requests = 0
        self._request_lock = asyncio.Semaphore(self.config.ollama.max_concurrent_requests)
        
        self.logger.info(f"Initialized GWEN-3 client for {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Initialize HTTP session and connection pool"""
        if self.session and not self.session.closed:
            return
        
        # Create connector with connection pooling
        self._connector = aiohttp.TCPConnector(
            limit=self.config.ollama.connection_pool_size,
            limit_per_host=self.config.ollama.max_concurrent_requests,
            keepalive_timeout=self.config.ollama.keep_alive_timeout,
            enable_cleanup_closed=True
        )
        
        # Create client session
        timeout = aiohttp.ClientTimeout(total=self.config.ollama.timeout)
        self.session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        
        self.logger.info("HTTP session initialized with connection pooling")
    
    async def disconnect(self) -> None:
        """Close HTTP session and cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        
        if self._connector:
            await self._connector.close()
            self._connector = None
        
        self.logger.info("HTTP session closed and resources cleaned up")
    
    async def _make_request(self, endpoint: str, data: Dict[str, Any], retries: int = None) -> Dict[str, Any]:
        """Make HTTP request with retry logic and error handling"""
        if not self.session:
            await self.connect()
        
        retries = retries or self.config.ollama.max_retries
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retries + 1):
            try:
                async with self._request_lock:
                    self._active_requests += 1
                    
                    async with self.session.post(url, json=data) as response:
                        self._active_requests -= 1
                        
                        if response.status == 200:
                            result = await response.json()
                            return result
                        
                        elif response.status == 503:
                            # Service unavailable - likely model loading
                            if attempt < retries:
                                wait_time = self.config.ollama.retry_delay * (2 ** attempt)
                                self.logger.warning(f"Service unavailable, retrying in {wait_time}s (attempt {attempt + 1}/{retries + 1})")
                                await asyncio.sleep(wait_time)
                                continue
                        
                        else:
                            error_text = await response.text()
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=f"HTTP {response.status}: {error_text}"
                            )
            
            except aiohttp.ClientError as e:
                self._active_requests = max(0, self._active_requests - 1)
                
                if attempt < retries:
                    wait_time = self.config.ollama.retry_delay * (2 ** attempt)
                    self.logger.warning(f"Request failed: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{retries + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"Request failed after {retries + 1} attempts: {e}")
                    raise
            
            except Exception as e:
                self._active_requests = max(0, self._active_requests - 1)
                self.logger.error(f"Unexpected error during request: {e}")
                raise
        
        raise RuntimeError(f"Failed to complete request after {retries + 1} attempts")
    
    async def verify_model_availability(self) -> Tuple[bool, Optional[str]]:
        """Check if GWEN-3 model is loaded and available"""
        try:
            self.logger.info("Checking model availability...")
            
            # Get list of available models
            models_data = await self._make_request("/api/tags", {})
            
            if "models" not in models_data:
                return False, "No models list in response"
            
            # Check if GWEN-3 model is in the list
            available_models = [model.get("name", "") for model in models_data["models"]]
            
            if self.model_name not in available_models:
                return False, f"Model {self.model_name} not found. Available: {available_models}"
            
            # Test model inference capability
            test_result = await self._test_model_inference()
            if not test_result:
                return False, "Model loaded but inference test failed"
            
            self.logger.info(f"Model {self.model_name} is available and functional")
            return True, f"Model {self.model_name} ready"
        
        except Exception as e:
            error_msg = f"Model availability check failed: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    async def _test_model_inference(self) -> bool:
        """Test basic model inference capability"""
        try:
            test_request = {
                "model": self.model_name,
                "prompt": "Test prompt cho model GWEN-3",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 10
                }
            }
            
            response = await self._make_request("/api/generate", test_request)
            return "response" in response and len(response["response"]) > 0
        
        except Exception as e:
            self.logger.warning(f"Model inference test failed: {e}")
            return False
    
    async def analyze_domain_structure(self, domain_name: str, content: str, 
                                     sample_urls: Optional[List[str]] = None) -> AnalysisResult:
        """
        Analyze Vietnamese news domain structure and generate parsing template
        
        Args:
            domain_name: Domain to analyze (e.g., "vnexpress.net")
            content: HTML content sample for analysis
            sample_urls: Optional list of sample URLs for context
            
        Returns:
            AnalysisResult with parsing template and confidence metrics
        """
        start_time = time.time()
        analysis_id = self._generate_analysis_id(domain_name)
        
        try:
            self.logger.info(f"Starting analysis for domain: {domain_name}")
            
            # Prepare content for analysis
            processed_content = self._prepare_content_for_analysis(content)
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(domain_name, processed_content, sample_urls)
            
            # Prepare request
            request_data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.analysis.temperature,
                    "top_p": self.config.analysis.top_p,
                    "top_k": self.config.analysis.top_k,
                    "num_predict": self.config.analysis.num_predict,
                    "num_ctx": self.config.analysis.num_ctx,
                    "repeat_penalty": self.config.analysis.repeat_penalty,
                    "stop": ["Human:", "User:", "Assistant:"]
                }
            }
            
            # Make API request
            self.logger.info(f"Sending analysis request to model (ID: {analysis_id})")
            response = await self._make_request("/api/generate", request_data)
            
            # Parse response
            analysis_result = self._parse_analysis_response(
                response, domain_name, analysis_id, start_time, processed_content
            )
            
            duration = time.time() - start_time
            self.logger.info(f"Analysis completed for {domain_name} in {duration:.2f}s (confidence: {analysis_result.confidence_score:.2f})")
            
            return analysis_result
        
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Analysis failed for {domain_name}: {e}"
            self.logger.error(error_msg)
            
            # Return error result
            return AnalysisResult(
                domain_name=domain_name,
                analysis_id=analysis_id,
                timestamp=datetime.now(),
                analysis_duration_seconds=duration,
                model_name=self.model_name,
                model_version=None,
                confidence_score=0.0,
                language_detected="unknown",
                parsing_template={},
                structure_hash="",
                headline_selectors=[],
                content_selectors=[],
                metadata_selectors={},
                navigation_patterns=[],
                extraction_accuracy=0.0,
                template_complexity=0,
                errors=[error_msg],
                warnings=[]
            )
    
    def _generate_analysis_id(self, domain_name: str) -> str:
        """Generate unique analysis ID"""
        timestamp = datetime.now().isoformat()
        data = f"{domain_name}_{timestamp}_{self.model_name}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def _prepare_content_for_analysis(self, content: str) -> str:
        """Prepare HTML content for analysis (truncate, clean)"""
        # Truncate if too long
        if len(content) > self.config.analysis.max_content_length:
            content = content[:self.config.analysis.max_content_length]
        
        # Take sample for analysis if content is very long
        if len(content) > self.config.analysis.content_sample_size:
            # Take beginning and middle samples
            start_sample = content[:self.config.analysis.content_sample_size // 2]
            middle_start = len(content) // 2 - self.config.analysis.content_sample_size // 4
            middle_end = middle_start + self.config.analysis.content_sample_size // 2
            middle_sample = content[middle_start:middle_end]
            
            content = start_sample + "\n\n<!-- MIDDLE SAMPLE -->\n\n" + middle_sample
        
        return content
    
    def _create_analysis_prompt(self, domain_name: str, content: str, sample_urls: Optional[List[str]]) -> str:
        """Create analysis prompt for GWEN-3 model"""
        urls_context = ""
        if sample_urls:
            urls_context = f"\nSample URLs:\n" + "\n".join(f"- {url}" for url in sample_urls[:5])
        
        return f"""Bạn là chuyên gia phân tích cấu trúc trang web tin tức tiếng Việt. Hãy phân tích trang web sau và tạo template parsing JSON chi tiết.

Domain: {domain_name}
{urls_context}

HTML Content:
{content}

Yêu cầu phân tích:
1. Xác định các selector CSS cho tiêu đề bài viết
2. Tìm selector cho nội dung chính 
3. Xác định metadata (tác giả, ngày đăng, chuyên mục)
4. Phân tích cấu trúc navigation và menu
5. Đánh giá độ tin cậy của template

Trả về kết quả JSON theo format sau:
{{
  "confidence_score": 0.85,
  "language_detected": "vietnamese",
  "parsing_template": {{
    "headline": {{
      "selectors": ["h1.title", ".article-title"],
      "priority": 1,
      "confidence": 0.9
    }},
    "content": {{
      "selectors": [".article-content", ".content-body"],
      "priority": 1,
      "confidence": 0.8
    }},
    "metadata": {{
      "author": ".author-name, .byline",
      "publish_date": ".publish-date, time",
      "category": ".category, .section"
    }}
  }},
  "structure_analysis": {{
    "layout_type": "standard_news",
    "complexity_score": 3,
    "vietnamese_content_ratio": 0.95
  }},
  "recommendations": [
    "Selector .article-title có độ tin cậy cao cho tiêu đề",
    "Cần kiểm tra thêm selector backup cho nội dung"
  ]
}}

Chỉ trả về JSON, không giải thích thêm."""
    
    def _parse_analysis_response(self, response: Dict[str, Any], domain_name: str, 
                               analysis_id: str, start_time: float, content: str) -> AnalysisResult:
        """Parse GWEN-3 response into AnalysisResult"""
        duration = time.time() - start_time
        errors = []
        warnings = []
        
        try:
            # Extract response text
            response_text = response.get("response", "").strip()
            
            if not response_text:
                errors.append("Empty response from model")
                raise ValueError("Empty model response")
            
            # Try to parse JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                errors.append("No JSON found in model response")
                raise ValueError("Invalid JSON format in response")
            
            json_text = response_text[json_start:json_end]
            analysis_data = json.loads(json_text)
            
            # Extract analysis results
            confidence_score = analysis_data.get("confidence_score", 0.0)
            language_detected = analysis_data.get("language_detected", "unknown")
            parsing_template = analysis_data.get("parsing_template", {})
            structure_analysis = analysis_data.get("structure_analysis", {})
            recommendations = analysis_data.get("recommendations", [])
            
            # Extract selectors
            headline_selectors = self._extract_selectors(parsing_template.get("headline", {}))
            content_selectors = self._extract_selectors(parsing_template.get("content", {}))
            metadata_selectors = parsing_template.get("metadata", {})
            
            # Navigation patterns (simplified)
            navigation_patterns = []
            if "navigation" in parsing_template:
                navigation_patterns = self._extract_selectors(parsing_template["navigation"])
            
            # Quality metrics
            extraction_accuracy = confidence_score
            template_complexity = structure_analysis.get("complexity_score", 1)
            
            # Generate structure hash
            structure_hash = hashlib.sha256(
                json.dumps(parsing_template, sort_keys=True).encode()
            ).hexdigest()[:16]
            
            # Validation warnings
            if confidence_score < self.config.analysis.min_confidence_score:
                warnings.append(f"Low confidence score: {confidence_score}")
            
            if language_detected != "vietnamese":
                warnings.append(f"Language detected as {language_detected}, expected Vietnamese")
            
            if not headline_selectors:
                warnings.append("No headline selectors found")
            
            if not content_selectors:
                warnings.append("No content selectors found")
            
            return AnalysisResult(
                domain_name=domain_name,
                analysis_id=analysis_id,
                timestamp=datetime.now(),
                analysis_duration_seconds=duration,
                model_name=self.model_name,
                model_version=response.get("model", self.model_name),
                confidence_score=confidence_score,
                language_detected=language_detected,
                parsing_template=parsing_template,
                structure_hash=structure_hash,
                headline_selectors=headline_selectors,
                content_selectors=content_selectors,
                metadata_selectors=metadata_selectors,
                navigation_patterns=navigation_patterns,
                extraction_accuracy=extraction_accuracy,
                template_complexity=template_complexity,
                errors=errors,
                warnings=warnings
            )
        
        except Exception as e:
            errors.append(f"Failed to parse model response: {e}")
            
            return AnalysisResult(
                domain_name=domain_name,
                analysis_id=analysis_id,
                timestamp=datetime.now(),
                analysis_duration_seconds=duration,
                model_name=self.model_name,
                model_version=None,
                confidence_score=0.0,
                language_detected="unknown",
                parsing_template={},
                structure_hash="",
                headline_selectors=[],
                content_selectors=[],
                metadata_selectors={},
                navigation_patterns=[],
                extraction_accuracy=0.0,
                template_complexity=0,
                errors=errors,
                warnings=warnings
            )
    
    def _extract_selectors(self, selector_config: Dict[str, Any]) -> List[str]:
        """Extract CSS selectors from selector configuration"""
        if isinstance(selector_config, dict):
            selectors = selector_config.get("selectors", [])
            if isinstance(selectors, str):
                return [selectors]
            elif isinstance(selectors, list):
                return selectors
        elif isinstance(selector_config, str):
            return [selector_config]
        elif isinstance(selector_config, list):
            return selector_config
        
        return []
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the GWEN-3 model"""
        try:
            response = await self._make_request("/api/show", {"name": self.model_name})
            return response
        except Exception as e:
            self.logger.error(f"Failed to get model info: {e}")
            return {}
    
    def get_active_requests_count(self) -> int:
        """Get number of currently active requests"""
        return self._active_requests