# GWEN-3 Model Configuration Guide

Comprehensive configuration guide for GWEN-3 8B model optimization for Vietnamese content analysis.

## Overview

This guide covers the configuration and optimization of the GWEN-3 8B model for Vietnamese news content analysis, including model parameters, performance tuning, memory management, and Vietnamese-specific optimizations.

## Model Specifications

### GWEN-3 8B Architecture
- **Model Type**: Transformer-based language model
- **Parameters**: 8 billion parameters
- **Specialization**: Vietnamese language processing
- **Context Window**: 8,192 tokens
- **Maximum Output**: 4,096 tokens
- **Memory Requirement**: 6-8GB RAM

### Vietnamese Language Capabilities
- **Language Understanding**: Native Vietnamese comprehension
- **Content Analysis**: News article structure recognition
- **CSS Selector Generation**: Automated parsing rule creation
- **Confidence Scoring**: Reliability assessment for generated templates
- **Multi-domain Support**: Adaptable to different Vietnamese news sites

## Configuration Files

### 1. Model Configuration (`config/gwen3/model-config.yml`)

#### Core Model Settings
```yaml
# Model identification
model:
  name: "gwen-3:8b"
  version: "8b"
  language: "vietnamese"
  specialized_for: "vietnamese_news_analysis"

# Performance parameters
performance:
  inference:
    temperature: 0.1          # Low for consistent output
    top_p: 0.9               # Nucleus sampling
    top_k: 40                # Top-k filtering
    num_predict: 4096        # Max output tokens
    num_ctx: 8192            # Context window size
    repeat_penalty: 1.1      # Prevent repetition
```

#### Vietnamese Analysis Settings
```yaml
vietnamese_analysis:
  language_detection:
    threshold: 0.8           # Minimum confidence for Vietnamese
    keywords:                # Vietnamese indicator words
      - "tin tức"
      - "báo chí"
      - "bài viết"
      - "tiêu đề"
      - "nội dung"
      
  content:
    max_length_chars: 50000  # Maximum content length
    sample_size_chars: 5000  # Sample size for analysis
    min_confidence_score: 0.7 # Minimum template confidence
    
  template:
    min_selectors_per_element: 2    # Minimum selectors
    max_selectors_per_element: 5    # Maximum selectors  
    confidence_threshold: 0.8       # Selector confidence
    complexity_max_score: 10        # Template complexity limit
```

### 2. Analysis Prompts (`config/gwen3/analysis-prompts.yml`)

#### System Prompt Configuration
```yaml
system_prompts:
  vietnamese_analyzer: |
    Bạn là GWEN-3, chuyên gia phân tích cấu trúc trang web tin tức tiếng Việt. 
    Nhiệm vụ của bạn là phân tích HTML và tạo các CSS selector chính xác.
    
    Nguyên tắc:
    - Luôn trả về JSON hợp lệ
    - Đánh giá độ tin cậy selector (0.0-1.0)
    - Ưu tiên selector ổn định và semantic
    - Cung cấp backup selectors
```

#### Domain Analysis Prompt
```yaml
analysis_prompts:
  domain_structure_analysis: |
    Phân tích cấu trúc trang web tin tức tiếng Việt:
    
    Domain: {domain_name}
    HTML Content: {html_content}
    
    Yêu cầu:
    1. Xác định CSS selectors cho:
       - Tiêu đề bài viết
       - Nội dung chính
       - Metadata (tác giả, ngày, chuyên mục)
    2. Đánh giá độ tin cậy selectors
    3. Tạo JSON response format
```

### 3. Performance Thresholds (`config/gwen3/performance-thresholds.yml`)

#### Memory Management
```yaml
system_resources:
  memory:
    total_limit_gb: 8
    thresholds:
      normal: 
        percent: 70
        action: "continue_normal_operation"
      warning:
        percent: 85  
        action: "log_warning_reduce_cache"
      critical:
        percent: 95
        action: "emergency_cleanup_pause_requests"
```

#### Performance Metrics
```yaml
performance_metrics:
  response_time:
    single_analysis:
      excellent_ms: 10000    # 10 seconds
      good_ms: 30000        # 30 seconds
      acceptable_ms: 60000   # 1 minute
      critical_ms: 300000   # 5 minutes
      
  quality_metrics:
    confidence_score:
      excellent: 0.9
      good: 0.8
      acceptable: 0.7
      critical: 0.5
```

## Model Parameter Tuning

### Temperature Settings
Controls randomness in model output:

```yaml
temperature_profiles:
  deterministic:    # For production parsing
    value: 0.1
    use_case: "Consistent CSS selector generation"
    
  balanced:         # For general analysis  
    value: 0.3
    use_case: "Balanced creativity and consistency"
    
  creative:         # For content understanding
    value: 0.7
    use_case: "Creative content interpretation"
```

### Top-P and Top-K Configuration
```yaml
sampling_parameters:
  top_p: 0.9              # Nucleus sampling threshold
  top_k: 40               # Top-k token filtering
  
  # Rationale:
  # - top_p=0.9: Keeps most probable tokens (90% mass)
  # - top_k=40: Limits to 40 most likely tokens
  # - Balance between quality and diversity
```

### Context Window Optimization
```yaml
context_settings:
  num_ctx: 8192           # Context window size
  
  # Vietnamese content optimization:
  # - 8192 tokens ≈ 6000-8000 Vietnamese words
  # - Sufficient for full news article analysis
  # - Includes HTML structure context
```

## Vietnamese Language Optimization

### Language Detection Configuration
```yaml
vietnamese_detection:
  primary_indicators:
    - "á, à, ả, ã, ạ"      # Vietnamese diacritics
    - "đ, Đ"               # Specific Vietnamese letters
    - Common words:
      - "và", "của", "có"
      - "được", "những", "này"
      - "tin tức", "báo chí"
      
  detection_threshold: 0.8  # 80% confidence required
  
  mixed_content_handling:
    min_vietnamese_ratio: 0.4  # 40% Vietnamese content minimum
    fallback_language: "mixed_vietnamese_english"
```

### Vietnamese News Site Patterns
```yaml
site_patterns:
  vnexpress:
    selectors:
      headline: ["h1.title_news_detail", ".article-title"]
      content: [".fck_detail", ".article-body"]
      author: [".author_mail", ".byline"]
      
  tuoitre:
    selectors:
      headline: [".article-title", "h1.title"]
      content: [".article-content", ".content-body"]
      author: [".author-info", ".author-name"]
      
  thanhnien:
    selectors:
      headline: [".news-title", "h1.article-title"]
      content: [".news-body", ".article-detail"]
      author: [".author-wrapper", ".reporter"]
```

### Content Processing Rules
```yaml
vietnamese_processing:
  text_normalization:
    unicode_form: "NFC"      # Canonical form
    preserve_diacritics: true
    remove_extra_spaces: true
    
  content_filtering:
    min_content_length: 100   # Characters
    max_content_length: 50000
    remove_html_tags: false   # Keep for structure analysis
    
  metadata_extraction:
    date_formats:             # Vietnamese date patterns
      - "dd/MM/yyyy"
      - "dd/MM/yyyy - HH:mm"
      - "dd-MM-yyyy"
    
    author_patterns:          # Author detection
      - "Tác giả:"
      - "Phóng viên:"
      - "Người viết:"
      - "By:"
```

## Memory Management

### Model Loading Strategy
```yaml
memory_management:
  model_loading:
    preload_model: true       # Load model at startup
    keep_alive_duration: "300s"  # 5 minutes
    max_concurrent_sessions: 1   # Limit for 8GB
    
  cache_strategy:
    enable_analysis_cache: true
    cache_ttl_hours: 24
    max_cache_entries: 1000
    cleanup_threshold: 0.8    # 80% memory usage
```

### Garbage Collection
```yaml
gc_settings:
  automatic_cleanup: true
  cleanup_interval_minutes: 30
  memory_threshold_percent: 85
  
  cleanup_priorities:
    1: "expired_cache_entries"
    2: "unused_model_weights"
    3: "old_analysis_results"
    4: "temporary_files"
```

## Performance Optimization

### Inference Optimization
```yaml
inference_tuning:
  batch_processing:
    enabled: false          # Single request processing
    max_batch_size: 1       # Memory constraint
    
  streaming:
    enabled: false          # Full response needed
    chunk_size: 512
    
  quantization:
    enabled: true           # Reduce memory usage
    precision: "int8"       # 8-bit quantization
    
  attention_optimization:
    flash_attention: true   # Memory efficient attention
    attention_dropout: 0.0  # Disable during inference
```

### Request Processing
```yaml
request_optimization:
  timeout_settings:
    connection_timeout: 30s
    inference_timeout: 300s  # 5 minutes max
    total_timeout: 330s
    
  retry_logic:
    max_retries: 3
    backoff_multiplier: 2.0
    initial_delay: 10s
    max_delay: 300s
    
  rate_limiting:
    max_concurrent_requests: 2
    queue_size: 10
    request_interval: 1s
```

## Monitoring Configuration

### Performance Metrics Collection
```yaml
monitoring:
  metrics_collection:
    enabled: true
    interval_seconds: 30
    retention_hours: 24
    
  collected_metrics:
    - "inference_duration_ms"
    - "memory_usage_bytes"
    - "cpu_usage_percent"
    - "request_count"
    - "error_count"
    - "confidence_scores"
    
  alerting:
    high_memory_usage:
      threshold: 85
      duration: 5min
      action: "restart_service"
      
    slow_inference:
      threshold: 60000      # 60 seconds
      duration: 3min
      action: "log_warning"
```

### Health Check Configuration
```yaml
health_checks:
  model_health:
    interval: 30s
    timeout: 30s
    retries: 3
    
  api_health:
    endpoints:
      - "/api/version"
      - "/api/tags"
    expected_status: 200
    timeout: 10s
    
  inference_health:
    test_prompt: "Test Vietnamese: Xin chào"
    max_response_time: 30s
    min_response_length: 5
```

## Environment Variables

### Docker Environment
```bash
# Model configuration
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_MODELS=/root/.ollama/models
OLLAMA_KEEP_ALIVE=300s
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1

# Memory settings  
OLLAMA_MAX_VRAM=8388608     # 8GB in KB
OLLAMA_FLASH_ATTENTION=1

# Vietnamese analysis settings
GWEN3_TEMPERATURE=0.1
GWEN3_TOP_P=0.9
GWEN3_TOP_K=40
GWEN3_NUM_PREDICT=4096
GWEN3_NUM_CTX=8192
GWEN3_MIN_CONFIDENCE=0.7

# Logging
GWEN3_LOG_LEVEL=INFO
GWEN3_LOG_FORMAT=json
```

### Application Environment
```bash
# Client configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL_NAME=gwen-3:8b
OLLAMA_TIMEOUT=300
OLLAMA_MAX_RETRIES=3

# Caching
ANALYSIS_CACHE_TTL=24
MAX_CACHE_SIZE=1000

# Vietnamese specific
VIETNAMESE_DETECTION_THRESHOLD=0.8
MIN_CONFIDENCE_SCORE=0.7
MAX_CONTENT_LENGTH=50000
```

## Troubleshooting Configuration Issues

### Common Configuration Problems

#### 1. Memory Allocation Issues
```yaml
# Problem: Model doesn't load due to insufficient memory
# Solution: Adjust memory limits
deploy:
  resources:
    limits:
      memory: 8G          # Increase if needed
    reservations:
      memory: 6G          # Minimum required
```

#### 2. Performance Issues
```yaml
# Problem: Slow inference times
# Solutions:
temperature: 0.1          # Lower temperature
num_predict: 2048         # Reduce max tokens
flash_attention: true     # Enable optimization
quantization: "int8"      # Use quantization
```

#### 3. Vietnamese Detection Issues
```yaml
# Problem: Language not detected correctly
# Solution: Adjust thresholds
vietnamese_detection:
  threshold: 0.7          # Lower threshold
  mixed_content_handling:
    min_vietnamese_ratio: 0.3  # Accept less Vietnamese content
```

### Configuration Validation

#### Syntax Validation
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/gwen3/model-config.yml'))"

# Check for required fields
grep -q "temperature:" config/gwen3/model-config.yml
grep -q "vietnamese_analysis:" config/gwen3/model-config.yml
```

#### Performance Testing
```bash
# Test model response time
time curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"gwen-3:8b","prompt":"Test","options":{"temperature":0.1}}'

# Should complete within 30 seconds
```

## Best Practices

### Configuration Management
1. **Version Control**: Track all configuration changes
2. **Environment Separation**: Different configs for dev/prod
3. **Validation**: Test configurations before deployment
4. **Backup**: Keep backup copies of working configurations
5. **Documentation**: Document all custom settings

### Performance Optimization
1. **Memory Monitoring**: Regular memory usage checks
2. **Temperature Tuning**: Start with 0.1 for consistency
3. **Context Length**: Balance between accuracy and speed
4. **Caching**: Enable for repeated analyses
5. **Batch Size**: Keep at 1 for memory constraints

### Vietnamese Analysis
1. **Language Detection**: Use multiple indicators
2. **Site Patterns**: Maintain domain-specific patterns
3. **Selector Quality**: Prefer semantic selectors
4. **Confidence Thresholds**: Balance accuracy vs coverage
5. **Error Handling**: Graceful degradation for edge cases

---

**Configuration Version**: 1.0.0  
**Last Updated**: 2025-08-11  
**Author**: James (Dev Agent)  
**Review Date**: Monthly configuration review recommended