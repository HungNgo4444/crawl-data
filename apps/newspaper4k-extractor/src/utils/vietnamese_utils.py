"""Vietnamese text processing utilities"""

import re
import unicodedata
from typing import List, Set
from datetime import datetime
from langdetect import detect, DetectorFactory

# Set seed for consistent language detection
DetectorFactory.seed = 0


class VietnameseTextProcessor:
    """Vietnamese text processing utilities"""
    
    # Vietnamese stopwords
    VIETNAMESE_STOPWORDS = {
        "và", "của", "cho", "với", "từ", "trong", "trên", "dưới", "về", "sau", "trước",
        "này", "đó", "những", "các", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười",
        "là", "có", "được", "sẽ", "đã", "đang", "bị", "không", "chưa", "rất", "khá", "hơn", "nhất",
        "theo", "như", "vì", "do", "bởi", "nên", "mà", "để", "khi", "nếu", "thì", "hay", "hoặc",
        "người", "việc", "công", "tại", "lại", "cũng", "thể", "thật", "nhiều", "ít", "lớn", "nhỏ",
        "ông", "bà", "anh", "chị", "em", "cô", "chú", "thầy", "cô", "giáo", "viên", "sư"
    }
    
    # Vietnamese date patterns
    VIETNAMESE_DATE_PATTERNS = [
        r'(\d{1,2})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{4})',  # dd/mm/yyyy or dd-mm-yyyy
        r'(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})',  # dd tháng mm năm yyyy
        r'ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})',  # ngày dd tháng mm năm yyyy
        r'(\d{4})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{1,2})',  # yyyy/mm/dd or yyyy-mm-dd
    ]
    
    # Vietnamese category mappings
    CATEGORY_MAPPINGS = {
        "thoi-su": "thời sự",
        "the-gioi": "thế giới", 
        "kinh-te": "kinh tế",
        "giai-tri": "giải trí",
        "the-thao": "thể thao",
        "phap-luat": "pháp luật",
        "giao-duc": "giáo dục",
        "suc-khoe": "sức khỏe",
        "doi-song": "đời sống",
        "khoa-hoc": "khoa học",
        "cong-nghe": "công nghệ",
        "oto-xe-may": "ô tô xe máy",
        "nha-dat": "nhà đất",
        "du-lich": "du lịch"
    }
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize Vietnamese text"""
        if not text:
            return ""
        
        # Normalize unicode
        text = unicodedata.normalize('NFC', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        return text.strip()
    
    @staticmethod
    def clean_content(content: str) -> str:
        """Clean Vietnamese article content"""
        if not content:
            return ""
        
        # Normalize text first
        content = VietnameseTextProcessor.normalize_text(content)
        
        # Remove common unwanted patterns
        unwanted_patterns = [
            r'(Theo|Nguồn):\s*\S+',  # Source attribution
            r'\(Ảnh:\s*[^)]+\)',     # Image attribution
            r'\(Video:\s*[^)]+\)',   # Video attribution
            r'Bài viết cùng chuyên mục:.*$',  # Related articles
            r'Xem thêm:.*$',          # See more
            r'Tags?:\s*.*$',          # Tags
            r'Từ khóa:.*$',           # Keywords
        ]
        
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE | re.IGNORECASE)
        
        # Remove excessive line breaks
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        return content.strip()
    
    @staticmethod
    def extract_vietnamese_date(text: str) -> datetime:
        """Extract Vietnamese date from text"""
        if not text:
            return None
        
        for pattern in VietnameseTextProcessor.VIETNAMESE_DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if 'tháng' in pattern:
                        # Vietnamese format: day, month, year
                        day, month, year = match.groups()
                        return datetime(int(year), int(month), int(day))
                    elif pattern.startswith(r'(\d{4})'):
                        # ISO format: year, month, day
                        year, month, day = match.groups()
                        return datetime(int(year), int(month), int(day))
                    else:
                        # dd/mm/yyyy format
                        day, month, year = match.groups()
                        return datetime(int(year), int(month), int(day))
                except (ValueError, TypeError):
                    continue
        
        return None
    
    @staticmethod
    def is_vietnamese_content(text: str, threshold: float = 0.8) -> bool:
        """Check if content is in Vietnamese"""
        if not text or len(text.strip()) < 10:
            return False
        
        try:
            detected_lang = detect(text)
            return detected_lang == 'vi'
        except:
            # Fallback: check for Vietnamese characters
            vietnamese_chars = 'àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ'
            vietnamese_count = sum(1 for char in text.lower() if char in vietnamese_chars)
            return (vietnamese_count / len(text)) >= (threshold * 0.1)  # Adjust threshold
    
    @staticmethod
    def normalize_category(category: str) -> str:
        """Normalize Vietnamese category name"""
        if not category:
            return ""
        
        # Convert to lowercase and remove special chars
        normalized = category.lower().strip()
        normalized = re.sub(r'[^a-z0-9\s-]', '', normalized)
        normalized = re.sub(r'\s+', '-', normalized)
        
        # Map to Vietnamese if available
        return VietnameseTextProcessor.CATEGORY_MAPPINGS.get(normalized, category)
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from Vietnamese text"""
        if not text:
            return []
        
        # Simple keyword extraction - remove stopwords and get frequent words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out stopwords and short words
        keywords = [
            word for word in words 
            if len(word) > 2 and word not in VietnameseTextProcessor.VIETNAMESE_STOPWORDS
        ]
        
        # Count frequency and return top keywords
        from collections import Counter
        word_counts = Counter(keywords)
        
        return [word for word, count in word_counts.most_common(max_keywords)]
    
    @staticmethod
    def calculate_reading_time(content: str) -> int:
        """Calculate estimated reading time in minutes (Vietnamese)"""
        if not content:
            return 0
        
        # Average Vietnamese reading speed: ~200-250 words per minute
        words = len(content.split())
        reading_speed = 225  # words per minute
        
        return max(1, round(words / reading_speed))
    
    @staticmethod
    def get_content_quality_score(article_data: dict) -> float:
        """Calculate content quality score for Vietnamese articles"""
        score = 0.0
        
        # Title quality (20%)
        title = article_data.get('title', '')
        if title and len(title.strip()) > 10:
            score += 0.2
            if VietnameseTextProcessor.is_vietnamese_content(title):
                score += 0.05
        
        # Content quality (40%)
        content = article_data.get('content', '')
        if content:
            content_length = len(content.strip())
            if content_length > 100:
                score += 0.2
            if content_length > 500:
                score += 0.1
            if content_length > 1000:
                score += 0.1
            if VietnameseTextProcessor.is_vietnamese_content(content):
                score += 0.1
        
        # Author quality (10%)
        authors = article_data.get('author', [])
        if authors and any(author.strip() for author in authors):
            score += 0.1
        
        # Date quality (10%)
        publish_date = article_data.get('publish_date')
        if publish_date:
            score += 0.1
        
        # Image quality (10%)
        image_url = article_data.get('url_image')
        if image_url:
            score += 0.1
        
        # Category quality (10%)
        category = article_data.get('category')
        if category and category.strip():
            score += 0.1
        
        return round(min(1.0, score), 2)
