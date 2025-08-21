# External API Integration

## **Ollama GWEN-3 API**
- **Purpose:** GWEN-3 8B model inference cho Vietnamese news content structure analysis
- **Documentation:** https://github.com/ollama/ollama/blob/main/docs/api.md
- **Base URL:** http://ollama:11434 (internal Docker network)
- **Authentication:** No authentication required (internal service)
- **Integration Method:** HTTP client integration trong GWEN3AnalysisWorker với connection pooling

**Key Endpoints Used:**
- `POST /api/generate` - Text completion với GWEN-3 model cho page structure analysis
- `POST /api/chat` - Conversational interface cho iterative content analysis
- `GET /api/tags` - Model availability checking và version verification
- `GET /api/show` - Model configuration và capability verification

**Error Handling:** Timeout handling (300s), retry logic với exponential backoff, model loading detection, memory management for 16GB constraint

## **Crawl4AI Engine API**
- **Purpose:** Enhanced content extraction engine với AI-powered parsing capabilities
- **Documentation:** https://crawl4ai.com/mkdocs/
- **Base URL:** Internal Python library integration (không external API calls)
- **Authentication:** N/A (library integration)
- **Integration Method:** Direct Python library usage với template-based configuration

**Key Endpoints Used:**
- `AsyncWebCrawler.arun()` - Main crawling method với GWEN-3 template integration
- `LLMExtractionStrategy` - AI-guided extraction với custom prompting
- `CosineStrategy` - Similarity-based content detection với template matching
- `JsonCssExtractionStrategy` - Structured extraction với GWEN-3 generated CSS selectors

**Error Handling:** Page load timeouts, JavaScript rendering failures, content extraction fallbacks, template parsing errors với graceful degradation

---
