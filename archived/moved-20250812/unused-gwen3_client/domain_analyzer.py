"""
GWEN-3 Domain Analyzer - Optimized for Database Storage
Tạo parsing templates nhất quán cho Vietnamese news domains
Author: Quinn (QA Agent)
Date: 2025-08-12
"""

import asyncio
import aiohttp
import json
import hashlib
import re
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DomainAnalysisResult:
    """Structured result for database storage"""
    
    # Domain information
    domain_name: str
    base_url: str
    
    # Analysis metadata
    analysis_id: str
    timestamp: datetime
    model_name: str
    
    # Template data (for JSONB storage)
    template_data: Dict[str, Any]
    confidence_score: float
    structure_hash: str
    
    # Performance metrics
    analysis_duration_seconds: float
    token_count: int
    
    # Validation status
    is_valid: bool
    validation_errors: List[str]

class OptimizedPromptTemplate:
    """Tối ưu prompt cho consistent output"""
    
    @staticmethod
    def create_analysis_prompt(html_content: str, domain_name: str) -> str:
        """
        Tạo prompt được tối ưu cho Vietnamese news domain analysis
        Đảm bảo output JSON structure nhất quán
        """
        
        prompt = f"""Bạn là chuyên gia phân tích cấu trúc website tin tức tiếng Việt. 
Phân tích HTML của domain "{domain_name}" và tạo CSS selectors chính xác.

HTML CONTENT:
{html_content}

YÊU CẦU OUTPUT JSON CHÍNH XÁC:
{{
    "domain_analysis": {{
        "domain_name": "{domain_name}",
        "page_type": "news_article|news_list|homepage",
        "language": "vi",
        "confidence_score": 0.95
    }},
    "selectors": {{
        "article_title": "CSS selector cho tiêu đề bài viết",
        "article_content": "CSS selector cho nội dung chính",
        "article_summary": "CSS selector cho tóm tắt (nếu có)",
        "publish_date": "CSS selector cho ngày đăng",
        "author": "CSS selector cho tác giả",
        "category": "CSS selector cho chuyên mục",
        "tags": "CSS selector cho tags (nếu có)",
        "image_main": "CSS selector cho ảnh chính"
    }},
    "content_patterns": {{
        "article_container": "CSS selector cho container chứa bài viết",
        "navigation": "CSS selector cho menu điều hướng",
        "sidebar": "CSS selector cho sidebar",
        "footer": "CSS selector cho footer",
        "advertisement": "CSS selector cho quảng cáo"
    }},
    "extraction_rules": {{
        "title_cleanup": ["remove_patterns", "trim_whitespace"],
        "content_cleanup": ["remove_ads", "remove_social_buttons", "preserve_paragraphs"],
        "date_format": "dd/mm/yyyy|yyyy-mm-dd|relative",
        "encoding": "utf-8"
    }},
    "validation": {{
        "required_selectors": ["article_title", "article_content", "publish_date"],
        "optional_selectors": ["article_summary", "author", "category"],
        "test_url_patterns": ["/tin-tuc/", "/bai-viet/", "/article/"]
    }},
    "performance_hints": {{
        "primary_selectors": ["article_title", "article_content"],
        "fallback_selectors": {{"article_title": ["h1", ".title", ".headline"]}},
        "xpath_alternatives": {{}},
        "estimated_success_rate": 0.95
    }}
}}

QUAN TRỌNG:
1. Chỉ trả về JSON format chính xác như trên
2. Tất cả CSS selectors phải specific và accurate
3. Confidence score từ 0.0 đến 1.0
4. Không thêm markdown, chỉ pure JSON
5. Đảm bảo syntax JSON hợp lệ

JSON Response:"""

        return prompt
    
    @staticmethod
    def create_validation_prompt(selectors: Dict[str, str], sample_html: str) -> str:
        """Prompt để validate selectors với sample HTML"""
        
        prompt = f"""Kiểm tra độ chính xác của CSS selectors này với HTML sample:

SELECTORS:
{json.dumps(selectors, indent=2, ensure_ascii=False)}

SAMPLE HTML:
{sample_html}

Trả về JSON validation result:
{{
    "validation_result": {{
        "overall_score": 0.95,
        "individual_scores": {{
            "article_title": 1.0,
            "article_content": 0.9,
            "publish_date": 0.8
        }},
        "failed_selectors": [],
        "recommendations": [
            "Selector cần cải thiện và đề xuất"
        ],
        "confidence_level": "high|medium|low"
    }}
}}

JSON Response:"""
        
        return prompt

class DomainAnalyzer:
    """Main analyzer class với optimized prompts"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model_name = "qwen2.5:3b"
        
    async def analyze_domain(self, 
                           domain_name: str, 
                           html_content: str,
                           base_url: str = None) -> DomainAnalysisResult:
        """
        Phân tích domain và trả về structured result cho database
        """
        
        analysis_start = datetime.now(timezone.utc)
        analysis_id = self._generate_analysis_id(domain_name, html_content)
        
        logger.info(f"Starting analysis for domain: {domain_name}")
        
        try:
            # Create optimized prompt
            prompt = OptimizedPromptTemplate.create_analysis_prompt(
                html_content, domain_name
            )
            
            # Call GWEN-3 model
            start_time = datetime.now()
            response_data = await self._call_ollama(prompt)
            duration = (datetime.now() - start_time).total_seconds()
            
            # Parse and validate response
            template_data, confidence_score = self._parse_response(response_data)
            
            # Calculate structure hash
            structure_hash = self._calculate_structure_hash(html_content)
            
            # Validate template data
            is_valid, validation_errors = self._validate_template_data(template_data)
            
            # Create result
            result = DomainAnalysisResult(
                domain_name=domain_name,
                base_url=base_url or f"https://{domain_name}",
                analysis_id=analysis_id,
                timestamp=analysis_start,
                model_name=self.model_name,
                template_data=template_data,
                confidence_score=confidence_score,
                structure_hash=structure_hash,
                analysis_duration_seconds=duration,
                token_count=len(prompt.split()),
                is_valid=is_valid,
                validation_errors=validation_errors
            )
            
            logger.info(f"Analysis completed for {domain_name}: {confidence_score:.2f} confidence")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed for {domain_name}: {str(e)}")
            # Return failed result
            return DomainAnalysisResult(
                domain_name=domain_name,
                base_url=base_url or f"https://{domain_name}",
                analysis_id=analysis_id,
                timestamp=analysis_start,
                model_name=self.model_name,
                template_data={},
                confidence_score=0.0,
                structure_hash="",
                analysis_duration_seconds=0.0,
                token_count=0,
                is_valid=False,
                validation_errors=[str(e)]
            )
    
    async def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API với optimized parameters"""
        
        request_data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent output
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 2048,  # Enough for detailed JSON
                "stop": ["Human:", "User:", "Assistant:"]
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.ollama_url}/api/generate",
                headers={"Content-Type": "application/json"},
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    raise Exception(f"Ollama API error: {response.status}")
    
    def _parse_response(self, response_data: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """Parse Ollama response và extract structured data"""
        
        response_text = response_data.get('response', '')
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                template_data = json.loads(json_str)
                
                # Extract confidence score
                confidence = template_data.get('domain_analysis', {}).get('confidence_score', 0.5)
                
                return template_data, float(confidence)
            else:
                raise ValueError("No valid JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            # Fallback: try to extract basic selectors
            return self._fallback_parsing(response_text), 0.3
    
    def _fallback_parsing(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing nếu JSON parsing fails"""
        
        # Basic fallback structure
        return {
            "domain_analysis": {
                "confidence_score": 0.3,
                "language": "vi",
                "page_type": "unknown"
            },
            "selectors": {
                "article_title": "h1",
                "article_content": ".content, article, .post-content",
                "publish_date": "time, .date, .publish-date"
            },
            "raw_response": response_text
        }
    
    def _validate_template_data(self, template_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate template data structure"""
        
        errors = []
        
        # Check required top-level keys
        required_keys = ['domain_analysis', 'selectors']
        for key in required_keys:
            if key not in template_data:
                errors.append(f"Missing required key: {key}")
        
        # Check selectors
        if 'selectors' in template_data:
            selectors = template_data['selectors']
            required_selectors = ['article_title', 'article_content']
            
            for selector in required_selectors:
                if selector not in selectors or not selectors[selector]:
                    errors.append(f"Missing required selector: {selector}")
        
        # Check confidence score
        if 'domain_analysis' in template_data:
            confidence = template_data['domain_analysis'].get('confidence_score', 0)
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                errors.append("Invalid confidence_score: must be 0.0-1.0")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _generate_analysis_id(self, domain_name: str, html_content: str) -> str:
        """Generate unique analysis ID"""
        
        content_hash = hashlib.md5(
            f"{domain_name}_{html_content[:1000]}_{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        return f"analysis_{content_hash[:12]}"
    
    def _calculate_structure_hash(self, html_content: str) -> str:
        """Calculate structure hash for HTML content"""
        
        # Extract structure (tags without content)
        structure = re.sub(r'>[^<]*<', '><', html_content)
        structure = re.sub(r'\s+', ' ', structure)
        
        return hashlib.sha256(structure.encode()).hexdigest()[:16]

# Test function
async def test_domain_analyzer():
    """Test function cho domain analyzer"""
    
    analyzer = DomainAnalyzer()
    
    # Sample Vietnamese news HTML
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head><title>VnExpress - Tin tức 24h</title></head>
    <body>
        <div class="container">
            <header class="header">
                <nav class="navigation">Menu</nav>
            </header>
            <main class="main-content">
                <article class="news-item">
                    <h1 class="title">Công nghệ AI phát triển mạnh tại Việt Nam</h1>
                    <div class="meta">
                        <span class="author">Nguyễn Văn A</span>
                        <time class="publish-date">12/08/2025</time>
                        <span class="category">Công nghệ</span>
                    </div>
                    <p class="summary">Tóm tắt bài viết về AI...</p>
                    <div class="content">
                        <p>Nội dung chi tiết về phát triển AI tại Việt Nam...</p>
                        <p>Các công ty đang đầu tư mạnh vào AI...</p>
                    </div>
                    <img src="ai-image.jpg" class="main-image" alt="AI Vietnam">
                </article>
            </main>
            <aside class="sidebar">Quảng cáo</aside>
            <footer class="footer">Footer</footer>
        </div>
    </body>
    </html>
    """
    
    try:
        result = await analyzer.analyze_domain(
            domain_name="vnexpress.net",
            html_content=sample_html,
            base_url="https://vnexpress.net"
        )
        
        print("=== DOMAIN ANALYSIS RESULT ===")
        print(f"Domain: {result.domain_name}")
        print(f"Analysis ID: {result.analysis_id}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Valid: {result.is_valid}")
        print(f"Duration: {result.analysis_duration_seconds:.2f}s")
        print(f"Structure Hash: {result.structure_hash}")
        
        if result.validation_errors:
            print(f"Errors: {result.validation_errors}")
        
        print("\nTemplate Data:")
        print(json.dumps(result.template_data, indent=2, ensure_ascii=False))
        
        return result
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return None

if __name__ == "__main__":
    # Run test
    asyncio.run(test_domain_analyzer())