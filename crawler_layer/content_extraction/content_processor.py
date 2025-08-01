"""
Content cleaning and normalization
"""

import re
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ContentProcessor:
    """Advanced content processing and cleaning"""
    
    def __init__(self):
        # Vietnamese stop words for content analysis
        self.vietnamese_stop_words = {
            'là', 'của', 'và', 'có', 'được', 'một', 'cho', 'với', 'không', 'này',
            'để', 'trong', 'từ', 'những', 'khi', 'đã', 'sẽ', 'về', 'các', 'người'
        }
        
        # Patterns for content cleaning
        self.noise_patterns = [
            r'Theo .+?\|',
            r'Đăng ký nhận tin.+',
            r'Bình luận.+',
            r'Chia sẻ.+',
            r'Tags?\s*:.+',
            r'Từ khóa\s*:.+',
            r'Xem thêm.+',
            r'Liên quan.+',
            r'Tin liên quan.+',
            r'Bài viết liên quan.+',
            r'>>> .+',
            r'>> .+',
            r'\.{3,}',
            r'_{3,}',
            r'-{3,}',
            r'={3,}',
            r'\*{3,}',
            r'#hashtag',
            r'@\w+',
            r'https?://\S+',
            r'www\.\S+',
        ]
        
        # Ad-related patterns
        self.ad_patterns = [
            r'quảng cáo',
            r'advertisement',
            r'sponsored',
            r'khuyến mãi',
            r'ưu đãi',
            r'giảm giá',
            r'mua ngay',
            r'đặt hàng',
            r'hotline',
            r'liên hệ.+\d{10,}',
        ]
    
    def process_content(self, raw_content: str, content_type: str = 'article') -> Dict[str, Any]:
        """
        Process and clean content
        Returns processed content with metadata
        """
        if not raw_content:
            return {
                'cleaned_content': '',
                'word_count': 0,
                'reading_time': 0,
                'quality_score': 0.0,
                'language': 'vi',
                'has_ads': False,
                'processing_notes': ['Empty content']
            }
        
        processing_notes = []
        
        # Step 1: Basic cleaning
        cleaned_content = self._basic_clean(raw_content)
        processing_notes.append('Basic cleaning applied')
        
        # Step 2: Remove noise patterns
        cleaned_content, noise_removed = self._remove_noise_patterns(cleaned_content)
        if noise_removed:
            processing_notes.append(f'Removed {noise_removed} noise patterns')
        
        # Step 3: Detect and remove ads
        cleaned_content, has_ads = self._detect_and_remove_ads(cleaned_content)
        if has_ads:
            processing_notes.append('Ad content detected and removed')
        
        # Step 4: Normalize whitespace and structure
        cleaned_content = self._normalize_structure(cleaned_content)
        processing_notes.append('Structure normalized')
        
        # Step 5: Calculate metrics
        word_count = self._count_words(cleaned_content)
        reading_time = max(1, word_count // 200)  # ~200 words per minute
        quality_score = self._calculate_content_quality(cleaned_content)
        language = self._detect_language(cleaned_content)
        
        return {
            'cleaned_content': cleaned_content,
            'word_count': word_count,
            'reading_time': reading_time,
            'quality_score': quality_score,
            'language': language,
            'has_ads': has_ads,
            'processing_notes': processing_notes
        }
    
    def _basic_clean(self, content: str) -> str:
        """Basic content cleaning"""
        if not content:
            return content
        
        # Remove HTML tags if any remain
        content = re.sub(r'<[^>]+>', '', content)
        
        # Fix common encoding issues
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&quot;', '"')
        content = content.replace('&#39;', "'")
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        return content.strip()
    
    def _remove_noise_patterns(self, content: str) -> tuple[str, int]:
        """Remove noise patterns from content"""
        original_length = len(content)
        removed_count = 0
        
        for pattern in self.noise_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
                removed_count += len(matches)
        
        # Remove empty lines created by pattern removal
        content = re.sub(r'\n\s*\n+', '\n\n', content)
        
        return content.strip(), removed_count
    
    def _detect_and_remove_ads(self, content: str) -> tuple[str, bool]:
        """Detect and remove advertising content"""
        has_ads = False
        
        # Check for ad patterns
        for pattern in self.ad_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_ads = True
                content = re.sub(pattern + r'[^\n]*', '', content, flags=re.IGNORECASE)
        
        # Remove suspicious promotional sentences
        sentences = content.split('.')
        clean_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Too short
                continue
            
            # Check for promotional keywords
            promotional_score = 0
            promo_keywords = ['mua', 'bán', 'giá', 'liên hệ', 'hotline', 'website', 'click']
            
            for keyword in promo_keywords:
                if keyword in sentence.lower():
                    promotional_score += 1
            
            # If sentence has too many promotional keywords, likely an ad
            if promotional_score >= 2:
                has_ads = True
                continue
            
            clean_sentences.append(sentence)
        
        cleaned_content = '. '.join(clean_sentences)
        return cleaned_content, has_ads
    
    def _normalize_structure(self, content: str) -> str:
        """Normalize content structure"""
        if not content:
            return content
        
        # Fix paragraph breaks
        content = re.sub(r'\.(\s*)([A-ZĂÂÊÔƠƯĐ])', r'.\n\n\2', content)
        
        # Ensure proper sentence spacing
        content = re.sub(r'\.(\s+)([a-z])', r'. \2', content)
        
        # Clean up multiple spaces
        content = re.sub(r' {2,}', ' ', content)
        
        # Clean up multiple newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    def _count_words(self, content: str) -> int:
        """Count words in Vietnamese text"""
        if not content:
            return 0
        
        # Remove punctuation and split by whitespace
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Filter out very short words and stop words
        meaningful_words = [
            word for word in words 
            if len(word) > 1 and word not in self.vietnamese_stop_words
        ]
        
        return len(meaningful_words)
    
    def _detect_language(self, content: str) -> str:
        """Detect content language (simple heuristic)"""
        if not content:
            return 'unknown'
        
        # Vietnamese-specific characters
        vietnamese_chars = 'áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ'
        
        # Count Vietnamese characters
        vietnamese_count = sum(1 for char in content.lower() if char in vietnamese_chars)
        total_chars = len(re.sub(r'\s', '', content))
        
        if total_chars == 0:
            return 'unknown'
        
        vietnamese_ratio = vietnamese_count / total_chars
        
        if vietnamese_ratio > 0.05:  # 5% threshold
            return 'vi'
        elif re.search(r'[a-zA-Z]', content):
            return 'en'
        else:
            return 'unknown'
    
    def _calculate_content_quality(self, content: str) -> float:
        """Calculate content quality score (0-10)"""
        if not content:
            return 0.0
        
        score = 0.0
        
        # Length score (0-3 points)
        word_count = len(content.split())
        if word_count > 1000:
            score += 3.0
        elif word_count > 500:
            score += 2.5
        elif word_count > 200:
            score += 2.0
        elif word_count > 100:
            score += 1.0
        
        # Sentence structure score (0-2 points)
        sentences = content.count('.')
        if sentences > 10:
            score += 2.0
        elif sentences > 5:
            score += 1.0
        
        # Paragraph structure score (0-2 points)
        paragraphs = content.count('\n\n')
        if paragraphs > 3:
            score += 2.0
        elif paragraphs > 1:
            score += 1.0
        
        # Information density score (0-2 points)
        # Check for presence of specific information indicators
        info_indicators = ['theo', 'cho biết', 'thông tin', 'dữ liệu', 'số liệu', 'báo cáo']
        indicator_count = sum(1 for indicator in info_indicators if indicator in content.lower())
        if indicator_count >= 3:
            score += 2.0
        elif indicator_count >= 1:
            score += 1.0
        
        # Language quality score (0-1 points)
        if self._detect_language(content) == 'vi':
            score += 1.0
        
        return min(score, 10.0)  # Cap at 10.0
    
    def extract_summary(self, content: str, max_length: int = 300) -> str:
        """Extract summary from content"""
        if not content or len(content) <= max_length:
            return content
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        
        # Select first few sentences that fit in max_length
        summary_parts = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_length + len(sentence) + 1 <= max_length:
                summary_parts.append(sentence)
                current_length += len(sentence) + 1
            else:
                break
        
        summary = '. '.join(summary_parts)
        if summary and not summary.endswith('.'):
            summary += '.'
        
        return summary or content[:max_length] + '...'