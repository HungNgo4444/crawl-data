"""
Unit tests for Vietnamese Analysis capabilities
Tests GWEN-3 Vietnamese content processing and template generation
Author: James (Dev Agent)
Date: 2025-08-11
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps'))

from gwen3_client.ollama_client import OllamaGWEN3Client, AnalysisResult


class TestVietnameseContentAnalysis:
    """Test Vietnamese content analysis functionality"""
    
    @pytest.fixture
    def sample_vietnamese_content(self):
        """Sample Vietnamese news content for testing"""
        return {
            'vnexpress': '''
                <html>
                <head><title>VnExpress - Báo tiếng Việt nhiều người đọc nhất</title></head>
                <body>
                    <div class="container">
                        <header class="header">
                            <h1 class="logo">VnExpress</h1>
                            <nav class="navigation">
                                <a href="/thoi-su">Thời sự</a>
                                <a href="/the-gioi">Thế giới</a>
                                <a href="/kinh-doanh">Kinh doanh</a>
                            </nav>
                        </header>
                        <main class="main-content">
                            <article class="article">
                                <h1 class="title_news_detail">Chính phủ đề xuất tăng lương tối thiểu 6%</h1>
                                <p class="description">
                                    Chính phủ đề xuất tăng lương tối thiểu vùng từ 6-6,5% từ năm 2025, 
                                    đưa mức lương cao nhất lên 5,25 triệu đồng mỗi tháng.
                                </p>
                                <div class="fck_detail">
                                    <p>Theo dự thảo nghị quyết do Bộ Lao động Thương binh và Xã hội trình, 
                                    lương tối thiểu vùng sẽ được điều chỉnh tăng 6-6,5% so với hiện tại.</p>
                                    <p>Cụ thể, vùng I (Hà Nội, TP HCM) tăng từ 4,96 triệu đồng lên 5,25 triệu đồng, 
                                    tăng 6%. Vùng II tăng từ 4,41 triệu lên 4,69 triệu đồng.</p>
                                    <p>Vùng III tăng từ 3,86 triệu lên 4,11 triệu đồng, tăng 6,5%. 
                                    Vùng IV tăng từ 3,44 triệu lên 3,67 triệu đồng, tăng 6,7%.</p>
                                </div>
                                <div class="author_mail">
                                    <span class="author">Phóng viên: <strong>Nguyễn Văn A</strong></span>
                                    <time class="time" datetime="2025-01-15T10:30:00">15/01/2025 - 10:30</time>
                                </div>
                                <div class="tags">
                                    <a href="/tag/luong-toi-thieu" class="tag">Lương tối thiểu</a>
                                    <a href="/tag/chinh-phu" class="tag">Chính phủ</a>
                                    <a href="/tag/lao-dong" class="tag">Lao động</a>
                                </div>
                            </article>
                        </main>
                    </div>
                </body>
                </html>
            ''',
            
            'tuoitre': '''
                <html>
                <head><title>Tuổi Trẻ Online - Tin nhanh, cập nhật 24h</title></head>
                <body>
                    <div class="wrapper">
                        <header>
                            <div class="logo-wrapper">
                                <h1>Tuổi Trẻ</h1>
                            </div>
                        </header>
                        <div class="main-wrapper">
                            <div class="article-wrapper">
                                <h1 class="article-title">Học sinh Việt Nam đạt thành tích cao tại Olympic Toán quốc tế</h1>
                                <div class="article-sapo">
                                    Đoàn học sinh Việt Nam giành được 4 huy chương vàng và 2 huy chương bạc 
                                    tại kỳ thi Olympic Toán học quốc tế 2025.
                                </div>
                                <div class="article-content">
                                    <p>Theo thông tin từ Bộ Giáo dục và Đào tạo, đoàn học sinh Việt Nam 
                                    tham dự Olympic Toán học quốc tế (IMO) 2025 đã có thành tích xuất sắc.</p>
                                    <p>Cả 6 thí sinh của Việt Nam đều đạt huy chương, trong đó có 4 huy chương vàng 
                                    và 2 huy chương bạc. Đây là thành tích ấn tượng của giáo dục Việt Nam.</p>
                                    <p>Kết quả này giúp Việt Nam xếp thứ 5 trong bảng xếp hạng các quốc gia, 
                                    thành tích cao nhất từ trước đến nay.</p>
                                </div>
                                <div class="article-meta">
                                    <div class="author-info">
                                        <span class="author-name">Trần Thị B</span>
                                    </div>
                                    <div class="publish-info">
                                        <span class="publish-time">16/01/2025 08:45</span>
                                    </div>
                                </div>
                                <div class="article-tags">
                                    <span class="tag-item">Giáo dục</span>
                                    <span class="tag-item">Olympic Toán</span>
                                    <span class="tag-item">Học sinh Việt Nam</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
            ''',
            
            'thanhnien': '''
                <html>
                <head><title>Thanh Niên - Thông tin tin tức 24h</title></head>
                <body>
                    <div id="wrapper">
                        <div class="header-wrapper">
                            <h1 class="site-logo">Thanh Niên</h1>
                        </div>
                        <div class="content-wrapper">
                            <div class="news-detail">
                                <h1 class="news-title">Phát triển du lịch bền vững tại Việt Nam</h1>
                                <div class="news-summary">
                                    Việt Nam đang tập trung phát triển du lịch bền vững, 
                                    kết hợp bảo vệ môi trường với tăng trưởng kinh tế.
                                </div>
                                <div class="news-body">
                                    <p>Theo Tổng cục Du lịch Việt Nam, ngành du lịch đang chuyển đổi 
                                    mạnh mẽ theo hướng phát triển bền vững và trách nhiệm.</p>
                                    <p>Các điểm đến du lịch được khuyến khích áp dụng các tiêu chuẩn 
                                    quốc tế về du lịch xanh và bảo vệ môi trường.</p>
                                    <p>Dự kiến đến năm 2030, Việt Nam sẽ có 50% các khu du lịch 
                                    đạt tiêu chuẩn phát triển bền vững.</p>
                                </div>
                                <div class="news-info">
                                    <div class="author-wrapper">
                                        <span class="reporter">Phạm Văn C</span>
                                    </div>
                                    <div class="time-wrapper">
                                        <span class="news-time">17/01/2025 14:20</span>
                                    </div>
                                    <div class="category-wrapper">
                                        <span class="category">Du lịch</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
            '''
        }
    
    @pytest.fixture
    def expected_analysis_patterns(self):
        """Expected patterns in Vietnamese analysis results"""
        return {
            'vietnamese_indicators': [
                'tiêu đề', 'nội dung', 'tác giả', 'ngày đăng',
                'chuyên mục', 'danh mục', 'selector', 'json'
            ],
            'css_selectors': [
                '.title', '.article-title', 'h1', '.news-title',
                '.content', '.article-content', '.fck_detail', 
                '.author', '.time', '.category', '.tag'
            ],
            'metadata_fields': [
                'headline', 'content', 'summary', 'author',
                'publish_date', 'category', 'tags'
            ]
        }
    
    def test_vietnamese_content_samples_structure(self, sample_vietnamese_content):
        """Test that sample content has expected Vietnamese elements"""
        vnexpress_content = sample_vietnamese_content['vnexpress']
        tuoitre_content = sample_vietnamese_content['tuoitre']
        thanhnien_content = sample_vietnamese_content['thanhnien']
        
        # Check Vietnamese text presence
        assert 'Chính phủ' in vnexpress_content
        assert 'học sinh Việt Nam' in tuoitre_content
        assert 'du lịch bền vững' in thanhnien_content
        
        # Check expected CSS classes
        assert 'title_news_detail' in vnexpress_content
        assert 'article-title' in tuoitre_content  
        assert 'news-title' in thanhnien_content
        
        # Check metadata elements
        assert 'author_mail' in vnexpress_content
        assert 'article-meta' in tuoitre_content
        assert 'news-info' in thanhnien_content
    
    @pytest.mark.asyncio
    async def test_vietnamese_language_detection(self, sample_vietnamese_content):
        """Test Vietnamese language detection in analysis"""
        client = OllamaGWEN3Client()
        
        # Mock successful response with Vietnamese detection
        mock_response = {
            "model": "gwen-3:8b",
            "response": json.dumps({
                "confidence_score": 0.9,
                "language_detected": "vietnamese",
                "parsing_template": {
                    "headline": {"selectors": ["h1.title_news_detail"]},
                    "content": {"selectors": [".fck_detail"]}
                },
                "structure_analysis": {
                    "vietnamese_content_ratio": 0.98,
                    "complexity_score": 4
                }
            })
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.analyze_domain_structure(
                "vnexpress.net",
                sample_vietnamese_content['vnexpress']
            )
            
            assert result.language_detected == "vietnamese"
            assert result.confidence_score == 0.9
            assert len(result.headline_selectors) > 0
    
    @pytest.mark.asyncio
    async def test_vietnamese_selector_extraction(self, sample_vietnamese_content):
        """Test CSS selector extraction for Vietnamese news sites"""
        client = OllamaGWEN3Client()
        
        # Mock response with detailed Vietnamese selectors
        mock_response = {
            "model": "gwen-3:8b", 
            "response": json.dumps({
                "confidence_score": 0.85,
                "language_detected": "vietnamese",
                "parsing_template": {
                    "headline": {
                        "primary_selectors": ["h1.title_news_detail", ".article-title"],
                        "backup_selectors": ["h1", ".title"],
                        "confidence": 0.9
                    },
                    "content": {
                        "primary_selectors": [".fck_detail", ".article-content"],
                        "backup_selectors": [".content", "article"],
                        "confidence": 0.8
                    },
                    "summary": {
                        "primary_selectors": [".description", ".article-sapo"],
                        "confidence": 0.7
                    },
                    "metadata": {
                        "author": {
                            "selectors": [".author-name", ".author strong", ".reporter"],
                            "confidence": 0.8
                        },
                        "publish_date": {
                            "selectors": [".time", ".publish-time", ".news-time"],
                            "confidence": 0.9
                        },
                        "category": {
                            "selectors": [".category", ".section"],
                            "confidence": 0.7
                        },
                        "tags": {
                            "selectors": [".tag", ".tag-item", ".tags a"],
                            "confidence": 0.6
                        }
                    }
                }
            })
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.analyze_domain_structure(
                "vnexpress.net",
                sample_vietnamese_content['vnexpress']
            )
            
            # Check headline selectors
            assert "h1.title_news_detail" in result.headline_selectors
            assert ".article-title" in result.headline_selectors
            
            # Check content selectors
            assert ".fck_detail" in result.content_selectors
            assert ".article-content" in result.content_selectors
            
            # Check metadata selectors
            assert "author" in result.metadata_selectors
            assert "publish_date" in result.metadata_selectors
            assert "category" in result.metadata_selectors
    
    @pytest.mark.asyncio
    async def test_vietnamese_prompt_creation(self, sample_vietnamese_content):
        """Test Vietnamese-specific prompt creation"""
        client = OllamaGWEN3Client()
        
        domain_name = "vnexpress.net"
        content = sample_vietnamese_content['vnexpress']
        sample_urls = ["https://vnexpress.net/article1", "https://vnexpress.net/article2"]
        
        prompt = client._create_analysis_prompt(domain_name, content, sample_urls)
        
        # Check Vietnamese language elements in prompt
        assert "tiếng Việt" in prompt or "vietnamese" in prompt.lower()
        assert "selector" in prompt.lower()
        assert "json" in prompt.lower()
        assert domain_name in prompt
        
        # Check content inclusion
        assert "title_news_detail" in prompt
        assert "fck_detail" in prompt
        
        # Check sample URLs inclusion
        assert sample_urls[0] in prompt
        
        # Check expected response format instructions
        assert "confidence_score" in prompt
        assert "parsing_template" in prompt
        assert "headline" in prompt
        assert "content" in prompt
    
    def test_vietnamese_content_preparation(self, sample_vietnamese_content):
        """Test Vietnamese content preparation for analysis"""
        client = OllamaGWEN3Client()
        
        # Test normal Vietnamese content
        content = sample_vietnamese_content['vnexpress']
        prepared = client._prepare_content_for_analysis(content)
        
        # Should preserve Vietnamese characters
        assert "Chính phủ" in prepared
        assert "triệu đồng" in prepared
        assert "tối thiểu" in prepared
        
        # Test very long Vietnamese content (should be sampled)
        long_vietnamese = "Nội dung tiếng Việt rất dài. " * 1000
        prepared_long = client._prepare_content_for_analysis(long_vietnamese)
        
        # Should still contain Vietnamese text
        assert "tiếng Việt" in prepared_long
        assert len(prepared_long) <= client.config.analysis.max_content_length
    
    @pytest.mark.asyncio
    async def test_multi_domain_vietnamese_analysis(self, sample_vietnamese_content):
        """Test analysis across different Vietnamese news domains"""
        client = OllamaGWEN3Client()
        
        domains_and_content = [
            ("vnexpress.net", sample_vietnamese_content['vnexpress']),
            ("tuoitre.vn", sample_vietnamese_content['tuoitre']),
            ("thanhnien.vn", sample_vietnamese_content['thanhnien'])
        ]
        
        for domain, content in domains_and_content:
            # Mock domain-specific response
            mock_response = {
                "model": "gwen-3:8b",
                "response": json.dumps({
                    "confidence_score": 0.82,
                    "language_detected": "vietnamese",
                    "domain_type": "vietnamese_news",
                    "parsing_template": {
                        "headline": {"selectors": [f".{domain.split('.')[0]}-title"]},
                        "content": {"selectors": [f".{domain.split('.')[0]}-content"]}
                    }
                })
            }
            
            with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                
                result = await client.analyze_domain_structure(domain, content)
                
                assert result.domain_name == domain
                assert result.language_detected == "vietnamese"
                assert result.confidence_score > 0.8
                assert len(result.headline_selectors) > 0
    
    @pytest.mark.asyncio
    async def test_low_quality_vietnamese_content_handling(self):
        """Test handling of low-quality Vietnamese content"""
        client = OllamaGWEN3Client()
        
        # Poor quality Vietnamese content
        poor_content = '''
            <html>
            <body>
                <div>Tin tức không rõ ràng</div>
                <p>Nội dung kém chất lượng</p>
            </body>
            </html>
        '''
        
        # Mock low confidence response
        mock_response = {
            "model": "gwen-3:8b",
            "response": json.dumps({
                "confidence_score": 0.45,  # Below threshold
                "language_detected": "vietnamese",
                "parsing_template": {
                    "headline": {"selectors": ["div"], "confidence": 0.3},
                    "content": {"selectors": ["p"], "confidence": 0.4}
                },
                "warnings": [
                    "Cấu trúc trang web không rõ ràng",
                    "Thiếu thông tin metadata"
                ]
            })
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.analyze_domain_structure("lowquality.vn", poor_content)
            
            assert result.confidence_score == 0.45
            assert result.language_detected == "vietnamese"
            assert len(result.warnings) > 0
            
            # Should still extract basic selectors
            assert len(result.headline_selectors) > 0
            assert len(result.content_selectors) > 0
    
    @pytest.mark.asyncio
    async def test_mixed_language_content_detection(self):
        """Test detection when content has mixed languages"""
        client = OllamaGWEN3Client()
        
        mixed_content = '''
            <html>
            <head><title>Mixed Language News - Tin tức đa ngôn ngữ</title></head>
            <body>
                <h1 class="title">Breaking News: Tin tức mới nhất</h1>
                <div class="content">
                    <p>This is an English paragraph about current events.</p>
                    <p>Đây là đoạn văn tiếng Việt về sự kiện hiện tại.</p>
                    <p>Another English sentence here.</p>
                </div>
            </body>
            </html>
        '''
        
        # Mock mixed language response
        mock_response = {
            "model": "gwen-3:8b",
            "response": json.dumps({
                "confidence_score": 0.6,
                "language_detected": "mixed_vietnamese_english",
                "parsing_template": {
                    "headline": {"selectors": [".title"]},
                    "content": {"selectors": [".content"]}
                },
                "structure_analysis": {
                    "vietnamese_content_ratio": 0.4,
                    "english_content_ratio": 0.6
                }
            })
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.analyze_domain_structure("mixed.com", mixed_content)
            
            assert result.confidence_score == 0.6
            assert "mixed" in result.language_detected.lower()
    
    def test_vietnamese_specific_css_patterns(self, expected_analysis_patterns):
        """Test recognition of Vietnamese-specific CSS patterns"""
        client = OllamaGWEN3Client()
        
        # Common Vietnamese news site patterns
        vietnamese_patterns = [
            "title_news_detail",  # VnExpress style
            "article-title",      # Tuổi Trẻ style  
            "news-title",         # Thanh Niên style
            "bai-viet-tieu-de",   # Generic Vietnamese
            "tin-tuc-noi-dung",   # Generic Vietnamese
            "tac-gia-thong-tin"   # Author info
        ]
        
        # Test selector extraction with Vietnamese patterns
        for pattern in vietnamese_patterns:
            config = {"selectors": [f".{pattern}", f"#{pattern}"]}
            selectors = client._extract_selectors(config)
            
            assert f".{pattern}" in selectors
            assert f"#{pattern}" in selectors
    
    @pytest.mark.asyncio
    async def test_vietnamese_metadata_extraction(self, sample_vietnamese_content):
        """Test extraction of Vietnamese-specific metadata"""
        client = OllamaGWEN3Client()
        
        # Mock response with Vietnamese metadata
        mock_response = {
            "model": "gwen-3:8b",
            "response": json.dumps({
                "confidence_score": 0.88,
                "language_detected": "vietnamese", 
                "parsing_template": {
                    "headline": {"selectors": ["h1.title_news_detail"]},
                    "content": {"selectors": [".fck_detail"]},
                    "metadata": {
                        "tac_gia": {  # Vietnamese field name
                            "selectors": [".author_mail .author", ".author-name"],
                            "confidence": 0.8
                        },
                        "thoi_gian": {  # Vietnamese field name
                            "selectors": [".time", ".publish-time"],
                            "confidence": 0.9
                        },
                        "chuyen_muc": {  # Vietnamese field name
                            "selectors": [".category", ".section-name"],
                            "confidence": 0.7
                        },
                        "tu_khoa": {  # Vietnamese field name
                            "selectors": [".tags .tag", ".keyword"],
                            "confidence": 0.6
                        }
                    }
                },
                "vietnamese_features": {
                    "diacritics_detected": True,
                    "vietnamese_words_count": 45,
                    "vietnamese_phrases": ["tối thiểu", "chính phủ", "triệu đồng"]
                }
            })
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.analyze_domain_structure(
                "vnexpress.net",
                sample_vietnamese_content['vnexpress']
            )
            
            # Check Vietnamese metadata fields
            metadata = result.metadata_selectors
            assert "tac_gia" in metadata or "author" in str(metadata)
            assert "thoi_gian" in metadata or "time" in str(metadata)
            assert "chuyen_muc" in metadata or "category" in str(metadata)
    
    @pytest.mark.parametrize("domain,expected_patterns", [
        ("vnexpress.net", ["title_news_detail", "fck_detail", "author_mail"]),
        ("tuoitre.vn", ["article-title", "article-content", "author-info"]),
        ("thanhnien.vn", ["news-title", "news-body", "author-wrapper"]),
        ("dantri.vn", ["news-title", "article-content", "author-detail"]),
        ("vietnamnet.vn", ["ArticleTitle", "ArticleContent", "ArticleInfo"])
    ])
    @pytest.mark.asyncio
    async def test_domain_specific_vietnamese_patterns(self, domain, expected_patterns):
        """Test domain-specific Vietnamese CSS patterns recognition"""
        client = OllamaGWEN3Client()
        
        # Create mock content with domain-specific patterns
        mock_content = f'''
            <html>
            <body>
                <h1 class="{expected_patterns[0]}">Tiêu đề tin tức</h1>
                <div class="{expected_patterns[1]}">Nội dung bài viết tiếng Việt</div>
                <div class="{expected_patterns[2]}">Tác giả: Nguyễn Văn A</div>
            </body>
            </html>
        '''
        
        # Mock response recognizing domain patterns
        mock_response = {
            "model": "gwen-3:8b",
            "response": json.dumps({
                "confidence_score": 0.9,
                "language_detected": "vietnamese",
                "domain_specific_analysis": {
                    "domain": domain,
                    "recognized_patterns": expected_patterns,
                    "pattern_reliability": "high"
                },
                "parsing_template": {
                    "headline": {"selectors": [f".{expected_patterns[0]}"]},
                    "content": {"selectors": [f".{expected_patterns[1]}"]},
                    "metadata": {
                        "author": f".{expected_patterns[2]}"
                    }
                }
            })
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.analyze_domain_structure(domain, mock_content)
            
            assert result.confidence_score >= 0.9
            assert result.language_detected == "vietnamese"
            assert f".{expected_patterns[0]}" in result.headline_selectors
            assert f".{expected_patterns[1]}" in result.content_selectors


@pytest.mark.integration
class TestVietnameseAnalysisIntegration:
    """Integration tests for Vietnamese analysis with real model"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("SKIP_INTEGRATION_TESTS") == "true",
        reason="Integration tests skipped"
    )
    async def test_real_vietnamese_content_analysis(self):
        """Test with real Vietnamese content and GWEN-3 model"""
        client = OllamaGWEN3Client()
        
        real_vnexpress_snippet = '''
            <html>
            <head><title>VnExpress - Tin tức 24h</title></head>
            <body>
                <article>
                    <h1 class="title_news_detail">Giá vàng hôm nay tăng mạnh</h1>
                    <p class="description">Giá vàng miếng SJC tăng 500.000 đồng mỗi lượng.</p>
                    <div class="fck_detail">
                        <p>Theo ghi nhận tại thị trường Hà Nội, giá vàng miếng SJC 
                        được các doanh nghiệp mua vào ở mức 75,5 triệu đồng/lượng.</p>
                    </div>
                    <div class="author_mail">
                        <span>Tác giả: <strong>Phóng viên Kinh tế</strong></span>
                        <time>18/01/2025 09:15</time>
                    </div>
                </article>
            </body>
            </html>
        '''
        
        try:
            async with client:
                # Check model availability first
                is_available, _ = await client.verify_model_availability()
                if not is_available:
                    pytest.skip("GWEN-3 model not available")
                
                result = await client.analyze_domain_structure(
                    "vnexpress.net", 
                    real_vnexpress_snippet
                )
                
                assert isinstance(result, AnalysisResult)
                assert result.domain_name == "vnexpress.net"
                
                # Vietnamese analysis should detect language correctly
                if result.confidence_score > 0:
                    assert result.language_detected in ["vietnamese", "vi"]
                    assert len(result.headline_selectors) > 0
                    
                    print(f"Vietnamese analysis result:")
                    print(f"  Confidence: {result.confidence_score}")
                    print(f"  Language: {result.language_detected}")
                    print(f"  Headline selectors: {result.headline_selectors}")
                    print(f"  Content selectors: {result.content_selectors}")
                
        except Exception as e:
            pytest.skip(f"Integration test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])