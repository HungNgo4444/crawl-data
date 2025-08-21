"""
Vietnamese Content Processing Utilities
Language-specific processing for Vietnamese news content analysis
Author: James (Dev Agent)
Date: 2025-08-12
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional, Set
from urllib.parse import urlparse
import unicodedata


class VietnameseContentProcessor:
    """Vietnamese content processing and analysis utilities"""
    
    def __init__(self):
        """Initialize Vietnamese content processor"""
        self.logger = logging.getLogger(__name__)
        
        # Vietnamese news keywords and phrases
        self.vietnamese_keywords = {
            "news_indicators": [
                "tin tức", "báo", "thời sự", "chính trị", "kinh tế", "xã hội",
                "thể thao", "giáo dục", "sức khỏe", "pháp luật", "quốc tế",
                "trong nước", "văn hóa", "giải trí", "công nghệ", "môi trường"
            ],
            "temporal_words": [
                "hôm nay", "ngày", "tháng", "năm", "tuần", "chiều", "sáng",
                "tối", "trưa", "mới nhất", "cập nhật", "vừa qua", "hiện tại"
            ],
            "location_words": [
                "việt nam", "hà nội", "hồ chí minh", "đà nẵng", "cần thơ",
                "hải phòng", "huế", "nha trang", "vũng tàu", "quy nhon",
                "thành phố", "tỉnh", "huyện", "xã", "phường", "quận"
            ],
            "structure_words": [
                "theo", "cho biết", "thông tin", "nguồn tin", "phóng viên",
                "tác giả", "bài viết", "tin bài", "chuyên mục", "chủ đề"
            ]
        }
        
        # Vietnamese URL patterns
        self.vietnamese_url_patterns = {
            "article_patterns": [
                r'/tin-tuc/',
                r'/bai-viet/',
                r'/bao-chi/',
                r'/tin/',
                r'/news/',
                r'/thoi-su/',
                r'/chinh-tri/',
                r'/kinh-te/',
                r'/xa-hoi/',
                r'/the-thao/',
                r'/giao-duc/',
                r'/suc-khoe/',
                r'/phap-luat/',
                r'/van-hoa/',
                r'/giai-tri/',
                r'/cong-nghe/',
                r'-\d{8,}-',  # Date patterns
                r'-\d{6,}\.html',
                r'-\d{6,}\.aspx'
            ],
            "category_patterns": [
                r'/thoi-su',
                r'/chinh-tri',
                r'/kinh-te',
                r'/kinh-doanh', 
                r'/xa-hoi',
                r'/the-thao',
                r'/giao-duc',
                r'/suc-khoe',
                r'/phap-luat',
                r'/van-hoa',
                r'/giai-tri',
                r'/cong-nghe',
                r'/moi-truong',
                r'/du-lich',
                r'/chuyên-mục',
                r'/the-loai',
                r'/chuyen-muc'
            ]
        }
        
        # Common Vietnamese news site selectors
        self.common_vietnamese_selectors = {
            "headlines": [
                "h1.title-news",
                "h1.news-title",
                "h1.article-title",
                ".title-detail h1",
                ".news-headline",
                ".bai-viet-title",
                ".tin-tuc-title",
                "[class*='tieu-de']",
                "[class*='title-main']"
            ],
            "content": [
                ".fck_detail",
                ".Normal", 
                ".article-content",
                ".news-content",
                ".bai-viet-content",
                ".tin-content",
                ".noidung",
                "[class*='noi-dung']",
                "[class*='content-detail']"
            ],
            "metadata": {
                "date": [
                    ".date",
                    ".time",
                    ".ngay-dang",
                    ".thoi-gian",
                    "[class*='date']",
                    "[class*='time']"
                ],
                "author": [
                    ".author",
                    ".tac-gia",
                    ".nguoi-viet",
                    ".byline",
                    "[class*='author']",
                    "[rel='author']"
                ],
                "category": [
                    ".category",
                    ".chuyen-muc",
                    ".the-loai",
                    ".section",
                    "[class*='category']",
                    "[class*='chuyen-muc']"
                ]
            }
        }
    
    def detect_vietnamese_content(self, text: str) -> Dict[str, Any]:
        """
        Detect and analyze Vietnamese content in text
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dict with detection results and metrics
        """
        try:
            if not text:
                return {"is_vietnamese": False, "confidence": 0.0, "indicators": []}
            
            text_lower = text.lower()
            text_length = len(text)
            
            # Count Vietnamese indicators
            indicator_scores = {}
            total_matches = 0
            
            for category, keywords in self.vietnamese_keywords.items():
                matches = sum(text_lower.count(keyword) for keyword in keywords)
                indicator_scores[category] = matches
                total_matches += matches
            
            # Vietnamese character detection
            vietnamese_chars = self._count_vietnamese_characters(text)
            vietnamese_char_ratio = vietnamese_chars / max(1, text_length)
            
            # Vietnamese tone marks
            tone_marks = self._count_tone_marks(text)
            tone_mark_ratio = tone_marks / max(1, text_length)
            
            # Calculate overall confidence
            keyword_density = total_matches / max(1, text_length / 100)  # per 100 chars
            
            confidence_factors = [
                min(1.0, keyword_density * 0.3),  # Keyword density
                min(1.0, vietnamese_char_ratio * 2.0),  # Vietnamese chars
                min(1.0, tone_mark_ratio * 10.0),  # Tone marks
            ]
            
            overall_confidence = sum(confidence_factors) / len(confidence_factors)
            
            # Determine if Vietnamese
            is_vietnamese = (
                overall_confidence > 0.3 or
                vietnamese_char_ratio > 0.1 or
                total_matches > 0
            )
            
            return {
                "is_vietnamese": is_vietnamese,
                "confidence": round(overall_confidence, 3),
                "indicators": {
                    "keyword_matches": indicator_scores,
                    "total_keyword_matches": total_matches,
                    "keyword_density": round(keyword_density, 3),
                    "vietnamese_char_ratio": round(vietnamese_char_ratio, 3),
                    "tone_mark_ratio": round(tone_mark_ratio, 3),
                    "vietnamese_char_count": vietnamese_chars,
                    "tone_mark_count": tone_marks
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to detect Vietnamese content: {e}")
            return {"is_vietnamese": False, "confidence": 0.0, "error": str(e)}
    
    def _count_vietnamese_characters(self, text: str) -> int:
        """Count Vietnamese-specific characters"""
        vietnamese_chars = set([
            'à', 'á', 'ạ', 'ả', 'ã', 'â', 'ầ', 'ấ', 'ậ', 'ẩ', 'ẫ', 'ă', 'ằ', 'ắ', 'ặ', 'ẳ', 'ẵ',
            'è', 'é', 'ẹ', 'ẻ', 'ẽ', 'ê', 'ề', 'ế', 'ệ', 'ể', 'ễ',
            'ì', 'í', 'ị', 'ỉ', 'ĩ',
            'ò', 'ó', 'ọ', 'ỏ', 'õ', 'ô', 'ồ', 'ố', 'ộ', 'ổ', 'ỗ', 'ơ', 'ờ', 'ớ', 'ợ', 'ở', 'ỡ',
            'ù', 'ú', 'ụ', 'ủ', 'ũ', 'ư', 'ừ', 'ứ', 'ự', 'ử', 'ữ',
            'ỳ', 'ý', 'ỵ', 'ỷ', 'ỹ',
            'đ'
        ])
        
        count = 0
        for char in text.lower():
            if char in vietnamese_chars:
                count += 1
        
        return count
    
    def _count_tone_marks(self, text: str) -> int:
        """Count Vietnamese tone marks"""
        tone_marks = [
            '\u0300',  # grave accent
            '\u0301',  # acute accent  
            '\u0303',  # tilde
            '\u0309',  # hook above
            '\u0323',  # dot below
        ]
        
        count = 0
        for char in text:
            normalized = unicodedata.normalize('NFD', char)
            for tone in tone_marks:
                if tone in normalized:
                    count += 1
        
        return count
    
    def analyze_vietnamese_news_structure(self, html_content: str) -> Dict[str, Any]:
        """
        Analyze Vietnamese news article structure
        
        Args:
            html_content: HTML content to analyze
            
        Returns:
            Analysis results with Vietnamese-specific insights
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            analysis = {
                "structure_detected": False,
                "vietnamese_selectors_found": [],
                "content_confidence": 0.0,
                "recommended_selectors": {},
                "vietnamese_content_areas": []
            }
            
            # Test common Vietnamese selectors
            for selector_type, selectors in self.common_vietnamese_selectors.items():
                if selector_type == "metadata":
                    continue
                    
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        # Check if element contains Vietnamese content
                        for element in elements[:3]:  # Check first 3 matches
                            text = element.get_text().strip()
                            if text:
                                vietnamese_check = self.detect_vietnamese_content(text)
                                if vietnamese_check["is_vietnamese"]:
                                    analysis["vietnamese_selectors_found"].append({
                                        "selector": selector,
                                        "type": selector_type,
                                        "confidence": vietnamese_check["confidence"],
                                        "sample_text": text[:100]
                                    })
            
            # Find content areas with Vietnamese text
            content_areas = soup.find_all(['div', 'article', 'section', 'main'])
            
            for area in content_areas:
                text = area.get_text().strip()
                if len(text) > 100:  # Only check substantial content
                    vietnamese_check = self.detect_vietnamese_content(text)
                    if vietnamese_check["is_vietnamese"] and vietnamese_check["confidence"] > 0.3:
                        # Try to generate a selector for this area
                        selector = self._generate_selector_for_element(area)
                        analysis["vietnamese_content_areas"].append({
                            "selector": selector,
                            "confidence": vietnamese_check["confidence"],
                            "content_length": len(text),
                            "sample_text": text[:200]
                        })
            
            # Generate recommendations
            if analysis["vietnamese_selectors_found"]:
                analysis["structure_detected"] = True
                analysis["recommended_selectors"] = self._generate_vietnamese_selector_recommendations(
                    analysis["vietnamese_selectors_found"]
                )
            
            # Calculate overall confidence
            if analysis["vietnamese_content_areas"]:
                avg_confidence = sum(
                    area["confidence"] for area in analysis["vietnamese_content_areas"]
                ) / len(analysis["vietnamese_content_areas"])
                analysis["content_confidence"] = round(avg_confidence, 3)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze Vietnamese news structure: {e}")
            return {"error": str(e)}
    
    def _generate_selector_for_element(self, element) -> str:
        """Generate CSS selector for element"""
        try:
            # Try ID first
            if element.get('id'):
                return f"#{element['id']}"
            
            # Try class
            if element.get('class'):
                classes = element['class']
                if classes:
                    return f".{classes[0]}"
            
            # Try tag with class of parent
            parent = element.parent
            if parent and parent.get('class'):
                parent_classes = parent['class']
                if parent_classes:
                    return f".{parent_classes[0]} {element.name}"
            
            # Fallback to tag name
            return element.name
            
        except Exception:
            return "div"  # Safe fallback
    
    def _generate_vietnamese_selector_recommendations(self, found_selectors: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate selector recommendations based on found Vietnamese selectors"""
        recommendations = {
            "headlines": [],
            "content": []
        }
        
        try:
            # Group selectors by type and confidence
            for selector_info in found_selectors:
                selector_type = selector_info["type"]
                selector = selector_info["selector"]
                confidence = selector_info["confidence"]
                
                if confidence > 0.5:  # Only recommend high-confidence selectors
                    if selector_type == "headlines":
                        recommendations["headlines"].append(selector)
                    elif selector_type == "content":
                        recommendations["content"].append(selector)
            
            # Add fallback selectors if none found
            if not recommendations["headlines"]:
                recommendations["headlines"] = self.common_vietnamese_selectors["headlines"][:3]
            
            if not recommendations["content"]:
                recommendations["content"] = self.common_vietnamese_selectors["content"][:3]
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            return recommendations
    
    def is_vietnamese_article_url(self, url: str) -> Tuple[bool, float]:
        """
        Check if URL is likely a Vietnamese article URL
        
        Args:
            url: URL to check
            
        Returns:
            Tuple of (is_vietnamese_article, confidence_score)
        """
        try:
            url_lower = url.lower()
            score = 0.0
            
            # Check article patterns
            article_matches = 0
            for pattern in self.vietnamese_url_patterns["article_patterns"]:
                if re.search(pattern, url_lower):
                    article_matches += 1
            
            if article_matches > 0:
                score += min(0.7, article_matches * 0.2)
            
            # Check for Vietnamese domain indicators
            vietnamese_domains = [
                'vnexpress', 'dantri', 'tuoitre', 'thanhnien', 'vietnamnet',
                'cafef', 'laodong', 'nld', 'baomoi', 'kienthuc'
            ]
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            for vn_domain in vietnamese_domains:
                if vn_domain in domain:
                    score += 0.3
                    break
            
            # Check path structure
            path = parsed.path.lower()
            vietnamese_path_indicators = [
                'tin-tuc', 'bai-viet', 'thoi-su', 'kinh-te', 'xa-hoi'
            ]
            
            for indicator in vietnamese_path_indicators:
                if indicator in path:
                    score += 0.1
            
            # File extensions common in Vietnamese news
            if any(ext in url_lower for ext in ['.html', '.aspx', '.php']):
                score += 0.1
            
            is_vietnamese = score > 0.3
            return is_vietnamese, min(1.0, score)
            
        except Exception as e:
            self.logger.error(f"Failed to check Vietnamese article URL: {e}")
            return False, 0.0
    
    def extract_vietnamese_metadata(self, html_content: str) -> Dict[str, Optional[str]]:
        """
        Extract Vietnamese-specific metadata from HTML content
        
        Args:
            html_content: HTML content to analyze
            
        Returns:
            Extracted metadata
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            metadata = {
                "title": None,
                "author": None,
                "publish_date": None,
                "category": None,
                "tags": [],
                "summary": None
            }
            
            # Extract title
            title_selectors = [
                "h1.title-news", "h1.article-title", ".title-detail h1",
                "h1", "title"
            ]
            
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title_text = element.get_text().strip()
                    vietnamese_check = self.detect_vietnamese_content(title_text)
                    if vietnamese_check["is_vietnamese"]:
                        metadata["title"] = title_text
                        break
            
            # Extract author
            author_selectors = self.common_vietnamese_selectors["metadata"]["author"]
            for selector in author_selectors:
                element = soup.select_one(selector)
                if element:
                    author_text = element.get_text().strip()
                    if author_text and len(author_text) < 100:  # Reasonable author length
                        metadata["author"] = author_text
                        break
            
            # Extract publish date
            date_selectors = self.common_vietnamese_selectors["metadata"]["date"]
            for selector in date_selectors:
                element = soup.select_one(selector)
                if element:
                    date_text = element.get_text().strip()
                    if date_text:
                        metadata["publish_date"] = date_text
                        break
            
            # Extract category
            category_selectors = self.common_vietnamese_selectors["metadata"]["category"]
            for selector in category_selectors:
                element = soup.select_one(selector)
                if element:
                    category_text = element.get_text().strip()
                    vietnamese_check = self.detect_vietnamese_content(category_text)
                    if vietnamese_check["is_vietnamese"]:
                        metadata["category"] = category_text
                        break
            
            # Extract tags (from meta keywords or tag elements)
            meta_keywords = soup.find("meta", {"name": "keywords"})
            if meta_keywords and meta_keywords.get("content"):
                keywords = meta_keywords["content"].split(",")
                for keyword in keywords[:10]:  # Limit to 10 tags
                    keyword = keyword.strip()
                    if keyword:
                        vietnamese_check = self.detect_vietnamese_content(keyword)
                        if vietnamese_check["is_vietnamese"]:
                            metadata["tags"].append(keyword)
            
            # Extract summary/description
            meta_description = soup.find("meta", {"name": "description"})
            if meta_description and meta_description.get("content"):
                desc_text = meta_description["content"].strip()
                vietnamese_check = self.detect_vietnamese_content(desc_text)
                if vietnamese_check["is_vietnamese"]:
                    metadata["summary"] = desc_text
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to extract Vietnamese metadata: {e}")
            return {}
    
    def normalize_vietnamese_text(self, text: str) -> str:
        """
        Normalize Vietnamese text for consistent processing
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        try:
            if not text:
                return ""
            
            # Unicode normalization
            text = unicodedata.normalize('NFC', text)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove special characters but keep Vietnamese diacritics
            text = re.sub(r'[^\w\sÀ-ỹ.,!?;:\-()]', '', text)
            
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to normalize Vietnamese text: {e}")
            return text
    
    def get_vietnamese_site_recommendations(self, domain_name: str) -> Dict[str, Any]:
        """
        Get site-specific recommendations for known Vietnamese news sites
        
        Args:
            domain_name: Domain name to check
            
        Returns:
            Site-specific recommendations
        """
        domain_lower = domain_name.lower()
        
        # Known Vietnamese news site configurations
        site_configs = {
            "vnexpress.net": {
                "selectors": {
                    "headline": ["h1.title-news", ".title-detail h1"],
                    "content": [".fck_detail", ".Normal"],
                    "author": [".author", ".right"],
                    "date": [".date"]
                },
                "confidence": 0.95
            },
            "dantri.com.vn": {
                "selectors": {
                    "headline": ["h1.title-page-detail", ".article-title h1"],
                    "content": [".detail-content", ".singular-content"],
                    "author": [".author"],
                    "date": [".time"]
                },
                "confidence": 0.95
            },
            "tuoitre.vn": {
                "selectors": {
                    "headline": ["h1.article-title", ".detail-title h1"],
                    "content": [".detail-content", ".article-content"],
                    "author": [".author"],
                    "date": [".date-time"]
                },
                "confidence": 0.95
            }
        }
        
        # Check for exact match
        if domain_lower in site_configs:
            return site_configs[domain_lower]
        
        # Check for partial matches
        for known_domain, config in site_configs.items():
            if known_domain.replace('.vn', '').replace('.com', '') in domain_lower:
                config_copy = config.copy()
                config_copy["confidence"] = 0.8  # Lower confidence for partial match
                return config_copy
        
        # Return generic Vietnamese news selectors
        return {
            "selectors": {
                "headline": self.common_vietnamese_selectors["headlines"][:3],
                "content": self.common_vietnamese_selectors["content"][:3],
                "author": self.common_vietnamese_selectors["metadata"]["author"][:2],
                "date": self.common_vietnamese_selectors["metadata"]["date"][:2]
            },
            "confidence": 0.6
        }