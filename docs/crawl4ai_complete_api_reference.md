# Tài liệu API Hoàn Chỉnh - Crawl4AI Framework

## Tổng quan hệ thống

Crawl4AI là một framework mạnh mẽ để crawl và trích xuất dữ liệu từ trang web. Hệ thống được tổ chức thành các module chính với các chức năng rõ ràng, bao gồm 73 file Python được tổ chức thành 8 module chính với kiến trúc modular, hỗ trợ async/await và nhiều chiến lược trích xuất dữ liệu.

---

## **1. CORE MODULE - AsyncWebCrawler và các Components chính**

### `async_webcrawler.py` - AsyncWebCrawler Class
**Chức năng**: Class chính để crawl web không đồng bộ

Đây là class chính của Crawl4AI, cung cấp khả năng crawl web không đồng bộ.

#### Các phương thức chính:
```python
class AsyncWebCrawler:
    def __init__(self, crawler_strategy=None, config=None, base_directory=str, thread_safe=False, logger=None, **kwargs)
    async def start(self) -> AsyncWebCrawler
    async def close(self) -> None
    async def arun(self, url: str, config: CrawlerRunConfig = None, **kwargs) -> CrawlResult
    async def arun_many(self, urls: List[str], config=None, dispatcher=None, **kwargs) -> List[CrawlResult]
    async def aprocess_html(self, url: str, html: str, extracted_content: str, config: CrawlerRunConfig, **kwargs) -> CrawlResult
    async def aseed_urls(self, domain_or_domains: Union[str, List[str]], config: SeedingConfig = None, **kwargs) -> Union[List[str], Dict]
```

##### `__init__(self, crawler_strategy, config, base_directory, thread_safe, logger, **kwargs)`
- **Chức năng**: Khởi tạo AsyncWebCrawler với các cấu hình cần thiết
- **Công dụng**: Thiết lập crawler với strategy, browser config, thư mục cache và logger
- **Tham số**:
  - `crawler_strategy`: Chiến lược crawler (mặc định: AsyncPlaywrightCrawlerStrategy)
  - `config`: Cấu hình browser (BrowserConfig) - proxy, headers, viewport
  - `base_directory`: Thư mục cơ sở để lưu cache và session data
  - `thread_safe`: Có sử dụng thread-safe không cho multi-threading
  - `logger`: Instance logger để tracking và debugging
- **Ví dụ sử dụng**: Khởi tạo crawler cho project với cache riêng và logging

##### `start(self)`
- **Chức năng**: Bắt đầu crawler và khởi tạo browser manager
- **Công dụng**: Khởi động browser instance, load plugins, setup context
- **Trả về**: AsyncWebCrawler instance đã sẵn sàng crawl
- **Lưu ý**: Phải gọi trước khi sử dụng arun() hoặc arun_many()

##### `close(self)`
- **Chức năng**: Đóng browser và dọn dẹp tài nguyên
- **Công dụng**: Giải phóng memory, đóng browser processes, cleanup sessions
- **Quan trọng**: Luôn gọi để tránh memory leaks và zombie processes

##### `arun(self, url, config, **kwargs)`
- **Chức năng**: Chạy crawler cho một URL đơn lẻ
- **Công dụng**: Crawl, extract content, apply filters, return structured data
- **Tham số**:
  - `url`: URL cần crawl (http/https/file)
  - `config`: Cấu hình crawler (CrawlerRunConfig) - selectors, filters, extraction
- **Trả về**: CrawlResult chứa HTML, markdown, media, links, metadata
- **Use cases**: Crawl single page, extract specific content, test configurations

##### `arun_many(self, urls, config, dispatcher, **kwargs)`
- **Chức năng**: Crawl nhiều URL đồng thời với parallel processing
- **Công dụng**: Batch crawling, rate limiting, memory management, concurrent extraction
- **Tham số**:
  - `urls`: Danh sách URLs để crawl song song
  - `config`: Cấu hình chung cho tất cả URLs
  - `dispatcher`: Chiến lược dispatch (MemoryAdaptive/FixedSemaphore)
- **Use cases**: Bulk crawling, sitemap processing, large-scale data collection

##### `aprocess_html(self, url, html, extracted_content, config, screenshot_data, pdf_data, verbose, **kwargs)`
- **Chức năng**: Xử lý nội dung HTML có sẵn mà không cần crawl
- **Công dụng**: Parse HTML, apply extraction strategies, generate markdown, extract media
- **Tham số**: HTML content, extraction config, optional screenshot/PDF data
- **Trả về**: CrawlResult với nội dung đã được xử lý và structured
- **Use cases**: Process saved HTML, test extraction strategies, offline processing

##### `aseed_urls(self, domain_or_domains, config, **kwargs)`
- **Chức năng**: Khám phá và lọc URLs cho domain(s) sử dụng sitemaps và Common Crawl
- **Công dụng**: Auto-discover URLs from sitemaps, robots.txt, Common Crawl data
- **Tham số**:
  - `domain_or_domains`: Domain hoặc danh sách domains để khám phá
  - `config`: Cấu hình seeding (SeedingConfig) - patterns, filters, sources
- **Trả về**: Danh sách URLs đã khám phá và lọc theo criteria
- **Use cases**: Site discovery, competitive analysis, comprehensive site crawling

---

## **2. EXTRACTION STRATEGIES - Chiến lược trích xuất dữ liệu**

### `extraction_strategy.py` - Chiến lược trích xuất dữ liệu
**Chức năng**: Các thuật toán trích xuất nội dung từ HTML

#### Class: ExtractionStrategy (Abstract)

#### Các implementation:

##### `NoExtractionStrategy`
- **Chức năng**: Không trích xuất nội dung có ý nghĩa, trả về toàn bộ HTML

##### `CosineStrategy`
- **Chức năng**: Trích xuất blocks/chunks sử dụng cosine similarity
- **Phương thức chính**:
  - `extract(url, html, **kwargs)`: Trích xuất clusters từ HTML
  - `hierarchical_clustering(sentences)`: Thực hiện clustering phân cấp
  - `filter_documents_embeddings(documents, semantic_filter)`: Lọc tài liệu dựa trên embeddings

##### `LLMExtractionStrategy`
- **Chức năng**: Sử dụng LLM để trích xuất nội dung có ý nghĩa
- **Phương thức chính**:
  - `extract(url, ix, html)`: Trích xuất blocks/chunks sử dụng LLM
  - `run(url, sections)`: Xử lý các sections tuần tự với rate limiting
  - `show_usage()`: Hiển thị báo cáo sử dụng token chi tiết

##### `JsonElementExtractionStrategy` (Abstract)
- **Chức năng**: Base class cho trích xuất JSON có cấu trúc từ HTML

##### `JsonCssExtractionStrategy`
- **Chức năng**: Implement JsonElementExtractionStrategy sử dụng CSS selectors
- **Phương thức chính**:
  - `_parse_html(html_content)`: Parse HTML với BeautifulSoup
  - `_get_elements(element, selector)`: Chọn elements với CSS selector

##### `JsonXPathExtractionStrategy`
- **Chức năng**: Implement JsonElementExtractionStrategy sử dụng XPath selectors

##### `RegexExtractionStrategy`
- **Chức năng**: Trích xuất entities thông dụng bằng regex
- **Phương thức chính**:
  - `extract(url, content, **kwargs)`: Tìm kiếm các pattern trong content
  - `generate_pattern(label, html, **kwargs)`: Tạo regex pattern từ HTML

#### Classes và methods chi tiết:
```python
class ExtractionStrategy(ABC):
    def __init__(self, input_format: str = "markdown", **kwargs)
    @abstractmethod
    def extract(self, url: str, html: str, *q, **kwargs) -> List[Dict[str, Any]]
    def run(self, url: str, sections: List[str], *q, **kwargs) -> List[Dict[str, Any]]

class NoExtractionStrategy(ExtractionStrategy):
    def extract(self, url: str, html: str, *q, **kwargs) -> List[Dict[str, Any]]
    def run(self, url: str, sections: List[str], *q, **kwargs) -> List[Dict[str, Any]]

class CosineStrategy(ExtractionStrategy):
    def __init__(self, semantic_filter=None, word_count_threshold=10, max_dist=0.2, linkage_method="ward", top_k=3, model_name="sentence-transformers/all-MiniLM-L6-v2", sim_threshold=0.3, **kwargs)
    def filter_documents_embeddings(self, documents: List[str], semantic_filter: str, at_least_k: int = 20) -> List[str]
    def get_embeddings(self, sentences: List[str], batch_size=None, bypass_buffer=False)
    def hierarchical_clustering(self, sentences: List[str], embeddings=None)
    def filter_clusters_by_word_count(self, clusters: Dict[int, List[str]]) -> Dict[int, List[str]]
    def extract(self, url: str, html: str, *q, **kwargs) -> List[Dict[str, Any]]
    def run(self, url: str, sections: List[str], *q, **kwargs) -> List[Dict[str, Any]]

class LLMExtractionStrategy(ExtractionStrategy):
    def __init__(self, llm_config=None, instruction=None, schema=None, extraction_type="block", chunk_token_threshold=CHUNK_TOKEN_THRESHOLD, overlap_rate=OVERLAP_RATE, word_token_rate=WORD_TOKEN_RATE, apply_chunking=True, input_format="markdown", force_json_response=False, verbose=False, **kwargs)
    def extract(self, url: str, ix: int, html: str) -> List[Dict[str, Any]]
    def _merge(self, documents, chunk_token_threshold, overlap) -> List[str]
    def run(self, url: str, sections: List[str]) -> List[Dict[str, Any]]
    def show_usage(self) -> None

class JsonElementExtractionStrategy(ExtractionStrategy):
    def __init__(self, schema: Dict[str, Any], **kwargs)
    def extract(self, url: str, html_content: str, *q, **kwargs) -> List[Dict[str, Any]]
    @abstractmethod
    def _parse_html(self, html_content: str)
    @abstractmethod
    def _get_base_elements(self, parsed_html, selector: str)
    @abstractmethod
    def _get_elements(self, element, selector: str)
    def _extract_field(self, element, field)
    def _extract_single_field(self, element, field)
    def _extract_list_item(self, element, fields)
    def _extract_item(self, element, fields)
    def _apply_transform(self, value, transform)
    def _compute_field(self, item, field)
    def run(self, url: str, sections: List[str], *q, **kwargs) -> List[Dict[str, Any]]
    @staticmethod
    def generate_schema(html: str, schema_type: str = "CSS", query: str = None, target_json_example: str = None, llm_config=None, **kwargs) -> dict

class JsonCssExtractionStrategy(JsonElementExtractionStrategy):
    def __init__(self, schema: Dict[str, Any], **kwargs)
    def _parse_html(self, html_content: str)
    def _get_base_elements(self, parsed_html, selector: str)
    def _get_elements(self, element, selector: str)
    def _get_element_text(self, element) -> str
    def _get_element_html(self, element) -> str
    def _get_element_attribute(self, element, attribute: str)

class JsonLxmlExtractionStrategy(JsonElementExtractionStrategy):
    def __init__(self, schema: Dict[str, Any], **kwargs)
    def _parse_html(self, html_content: str)
    def _optimize_selector(self, selector_str)
    def _create_selector_function(self, selector_str)
    def _get_base_elements(self, parsed_html, selector: str)
    def _get_elements(self, element, selector: str)
    def _get_element_text(self, element) -> str
    def _get_element_html(self, element) -> str
    def _get_element_attribute(self, element, attribute: str)

class JsonXPathExtractionStrategy(JsonElementExtractionStrategy):
    def __init__(self, schema: Dict[str, Any], **kwargs)
    def _parse_html(self, html_content: str)
    def _get_base_elements(self, parsed_html, selector: str)
    def _css_to_xpath(self, css_selector: str) -> str
    def _basic_css_to_xpath(self, css_selector: str) -> str
    def _get_elements(self, element, selector: str)
    def _get_element_text(self, element) -> str
    def _get_element_html(self, element) -> str
    def _get_element_attribute(self, element, attribute: str)

class RegexExtractionStrategy(ExtractionStrategy):
    def __init__(self, pattern=_B.NOTHING, *, custom=None, input_format="fit_html", **kwargs)
    def extract(self, url: str, content: str, *q, **kw) -> List[Dict[str, Any]]
    @staticmethod
    def generate_pattern(label: str, html: str, *, query=None, examples=None, llm_config=None, **kwargs) -> Dict[str, str]
```

---

## **3. CRAWLER STRATEGIES - Chiến lược Crawler**

### `async_crawler_strategy.py` - Chiến lược Crawler
**Chức năng**: Định nghĩa các chiến lược crawl khác nhau

#### Class: AsyncCrawlerStrategy (Abstract)

#### Implementations:

##### `AsyncPlaywrightCrawlerStrategy`
- **Chức năng**: Crawler strategy sử dụng Playwright
- **Phương thức chính**:
  - `crawl(url, config)`: Crawl URL với cấu hình đã cho
  - `_crawl_web(url, config)`: Phương thức nội bộ crawl web URLs
  - `smart_wait(page, wait_for, timeout)`: Chờ điều kiện một cách thông minh
  - `process_iframes(page)`: Xử lý iframes trên trang
  - `remove_overlay_elements(page)`: Loại bỏ overlay elements
  - `take_screenshot(page, **kwargs)`: Chụp screenshot trang
  - `export_pdf(page)`: Xuất trang thành PDF
  - `capture_mhtml(page)`: Capture trang thành MHTML

##### `AsyncHTTPCrawlerStrategy`
- **Chức năng**: Fast, lightweight HTTP-only crawler
- **Phương thức chính**:
  - `crawl(url, config, **kwargs)`: Crawl URL sử dụng HTTP requests
  - `_handle_http(url, config)`: Xử lý HTTP requests
  - `_handle_file(path)`: Xử lý file local
  - `_handle_raw(content)`: Xử lý raw HTML content

#### Classes chính:
```python
class AsyncCrawlerStrategy(ABC):
    @abstractmethod
    async def crawl(self, url: str, **kwargs) -> AsyncCrawlResponse

class AsyncPlaywrightCrawlerStrategy(AsyncCrawlerStrategy):
    def __init__(self, browser_config=None, logger=None, browser_adapter=None, **kwargs)
    async def start(self) -> None
    async def close(self) -> None
    async def crawl(self, url: str, config: CrawlerRunConfig, **kwargs) -> AsyncCrawlResponse
    async def _crawl_web(self, url: str, config: CrawlerRunConfig) -> AsyncCrawlResponse
    async def smart_wait(self, page: Page, wait_for: str, timeout: float = 30000)
    async def csp_compliant_wait(self, page: Page, user_wait_function: str, timeout: float = 30000)
    async def process_iframes(self, page) -> Page
    async def create_session(self, **kwargs) -> str
    async def kill_session(self, session_id: str) -> None
    async def remove_overlay_elements(self, page: Page) -> None
    async def export_pdf(self, page: Page) -> bytes
    async def capture_mhtml(self, page: Page) -> Optional[str]
    async def take_screenshot(self, page, **kwargs) -> str
    async def _handle_full_page_scan(self, page: Page, scroll_delay: float = 0.1, max_scroll_steps: Optional[int] = None)
    async def _handle_virtual_scroll(self, page: Page, config: VirtualScrollConfig)
    async def robust_execute_user_script(self, page: Page, js_code: Union[str, List[str]]) -> Dict[str, Any]
    def set_hook(self, hook_type: str, hook: Callable) -> None
    async def execute_hook(self, hook_type: str, *args, **kwargs)
    def update_user_agent(self, user_agent: str) -> None
    def set_custom_headers(self, headers: Dict[str, str]) -> None

class AsyncHTTPCrawlerStrategy(AsyncCrawlerStrategy):
    def __init__(self, browser_config=None, logger=None, max_connections=32, dns_cache_ttl=300, chunk_size=65536)
    async def start(self) -> None
    async def close(self) -> None
    async def crawl(self, url: str, config: CrawlerRunConfig = None, **kwargs) -> AsyncCrawlResponse
    async def _handle_http(self, url: str, config: CrawlerRunConfig) -> AsyncCrawlResponse
    async def _handle_file(self, path: str) -> AsyncCrawlResponse
    async def _handle_raw(self, content: str) -> AsyncCrawlResponse
```

---

## **4. CONTENT SCRAPING STRATEGY - Chiến lược Scraping Nội dung**

### `content_scraping_strategy.py` - Chiến lược Scraping Nội dung
**Chức năng**: Xử lý và làm sạch nội dung HTML

### Class: LXMLWebScrapingStrategy

- **Chức năng**: Implementation chính cho scraping nội dung web sử dụng lxml
- **Phương thức chính**:
  - `scrap(url, html, **kwargs)`: Entry point chính cho content scraping
  - `_process_element(url, element, media, internal_links_dict, external_links_dict, **kwargs)`: Xử lý HTML element
  - `process_image(img, url, index, total_images, **kwargs)`: Xử lý images
  - `remove_empty_elements_fast(root, word_count_threshold)`: Loại bỏ elements trống
  - `remove_unwanted_attributes_fast(root, important_attrs, keep_data_attributes)`: Loại bỏ attributes không cần thiết

#### Classes và methods:
```python
class ContentScrapingStrategy(ABC):
    @abstractmethod
    def scrap(self, url: str, html: str, **kwargs) -> ScrapingResult
    @abstractmethod
    async def ascrap(self, url: str, html: str, **kwargs) -> ScrapingResult

class LXMLWebScrapingStrategy(ContentScrapingStrategy):
    def __init__(self, logger=None)
    def scrap(self, url: str, html: str, **kwargs) -> ScrapingResult
    async def ascrap(self, url: str, html: str, **kwargs) -> ScrapingResult
    def process_element(self, url, element: lhtml.HtmlElement, **kwargs) -> Dict[str, Any]
    def _process_element(self, url: str, element: lhtml.HtmlElement, media: Dict[str, List], internal_links_dict: Dict[str, Any], external_links_dict: Dict[str, Any], **kwargs) -> bool
    def find_closest_parent_with_useful_text(self, element: lhtml.HtmlElement, **kwargs) -> Optional[str]
    def flatten_nested_elements(self, element: lhtml.HtmlElement) -> lhtml.HtmlElement
    def process_image(self, img: lhtml.HtmlElement, url: str, index: int, total_images: int, **kwargs) -> Optional[List[Dict]]
    def remove_empty_elements_fast(self, root, word_count_threshold=5)
    def remove_unwanted_attributes_fast(self, root: lhtml.HtmlElement, important_attrs=None, keep_data_attributes=False) -> lhtml.HtmlElement
    def _scrap(self, url: str, html: str, word_count_threshold: int = MIN_WORD_THRESHOLD, css_selector: str = None, target_elements: List[str] = None, **kwargs) -> Dict[str, Any]
```

---

## **5. CHUNKING STRATEGY - Chiến lược phân đoạn văn bản**

### `chunking_strategy.py` - Chiến lược phân đoạn văn bản
**Chức năng**: Chia nhỏ văn bản thành các chunks để xử lý

### Classes trong `chunking_strategy.py`:

##### `ChunkingStrategy` (Abstract)
- **Chức năng**: Base class cho các chiến lược chunking

##### `IdentityChunking`
- **Chức năng**: Trả về input text như một chunk duy nhất

##### `RegexChunking`
- **Chức năng**: Chia text dựa trên regex patterns

##### `NlpSentenceChunking`
- **Chức năng**: Chia text thành câu sử dụng NLTK sentence tokenizer

##### `TopicSegmentationChunking`
- **Chức năng**: Phân đoạn text thành topics sử dụng TextTilingTokenizer

##### `FixedLengthWordChunking`
- **Chức năng**: Chia text thành chunks có độ dài cố định (theo từ)

##### `SlidingWindowChunking`
- **Chức năng**: Chia text thành chunks trùng lặp với sliding window

##### `OverlappingWindowChunking`
- **Chức năng**: Chia text thành chunks với overlap giữa các chunks liên tiếp

#### Classes và methods:
```python
class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, text: str) -> list

class IdentityChunking(ChunkingStrategy):
    def chunk(self, text: str) -> list

class RegexChunking(ChunkingStrategy):
    def __init__(self, patterns=None, **kwargs)
    def chunk(self, text: str) -> list

class NlpSentenceChunking(ChunkingStrategy):
    def __init__(self, **kwargs)
    def chunk(self, text: str) -> list

class TopicSegmentationChunking(ChunkingStrategy):
    def __init__(self, num_keywords=3, **kwargs)
    def chunk(self, text: str) -> list
    def extract_keywords(self, text: str) -> list
    def chunk_with_topics(self, text: str) -> list

class FixedLengthWordChunking(ChunkingStrategy):
    def __init__(self, chunk_size=100, **kwargs)
    def chunk(self, text: str) -> list

class SlidingWindowChunking(ChunkingStrategy):
    def __init__(self, window_size=100, step=50, **kwargs)
    def chunk(self, text: str) -> list

class OverlappingWindowChunking(ChunkingStrategy):
    def __init__(self, window_size=1000, overlap=100, **kwargs)
    def chunk(self, text: str) -> list
```

---

## **6. CONFIGURATION CLASSES - Classes Cấu hình**

### `async_configs.py` - Configuration Classes
**Chức năng**: Các class cấu hình cho crawler

### BrowserConfig
- **Chức năng**: Cấu hình browser settings

### CrawlerRunConfig
- **Chức năng**: Cấu hình cho một lần chạy crawler

### ProxyConfig
- **Chức năng**: Cấu hình proxy

### SeedingConfig
- **Chức năng**: Cấu hình cho URL seeding

#### Classes và methods:
```python
class BrowserConfig:
    def __init__(self, browser_type="chromium", headless=True, viewport_width=1280, viewport_height=720, user_agent=None, **kwargs)
    @classmethod
    def from_kwargs(cls, kwargs: dict) -> 'BrowserConfig'
    def clone(self, **changes) -> 'BrowserConfig'

class CrawlerRunConfig:
    def __init__(self, cache_mode=None, css_selector=None, word_count_threshold=MIN_WORD_THRESHOLD, **kwargs)
    @classmethod
    def from_kwargs(cls, kwargs: dict) -> 'CrawlerRunConfig'
    def clone(self, **changes) -> 'CrawlerRunConfig'

class ProxyConfig:
    def __init__(self, server: str, username: str = None, password: str = None)
    def to_playwright_proxy(self) -> dict

class SeedingConfig:
    def __init__(self, source="sitemap", live_check=False, extract_head=False, pattern=None, **kwargs)
    @classmethod
    def from_kwargs(cls, kwargs: dict) -> 'SeedingConfig'
    def clone(self, **changes) -> 'SeedingConfig'

class HTTPCrawlerConfig:
    def __init__(self, method="GET", headers=None, follow_redirects=True, verify_ssl=True, **kwargs)

class VirtualScrollConfig:
    def __init__(self, container_selector: str, scroll_count: int = 10, scroll_by="container_height", wait_after_scroll: float = 2.0)
    @classmethod
    def from_dict(cls, data: dict) -> 'VirtualScrollConfig'
    def to_dict(self) -> dict
```

---

## **7. DATA MODELS - Models**

### `models.py` - Data Models
**Chức năng**: Định nghĩa các data model và structure

### File: `models.py`
- `CrawlResult`: Kết quả của quá trình crawl
- `AsyncCrawlResponse`: Response từ async crawler
- `ScrapingResult`: Kết quả scraping
- `MediaItem`: Item media (image, video, audio)
- `Link`: Link object
- `Media`, `Links`: Collections của media items và links

#### Classes chính:
```python
class CrawlResult:
    def __init__(self, url="", html="", cleaned_html="", markdown="", fit_html="", media=None, links=None, metadata=None, **kwargs)
    def to_dict(self) -> dict
    @classmethod
    def from_dict(cls, data: dict) -> 'CrawlResult'

class AsyncCrawlResponse:
    def __init__(self, html="", response_headers=None, status_code=200, screenshot=None, **kwargs)

class ScrapingResult:
    def __init__(self, cleaned_html="", success=True, media=None, links=None, metadata=None)

class MediaItem:
    def __init__(self, src="", alt="", type="", description="", **kwargs)

class Link:
    def __init__(self, href="", text="", title="", **kwargs)

class Media:
    def __init__(self, images=None, videos=None, audios=None, tables=None)

class Links:
    def __init__(self, internal=None, external=None)

class TokenUsage:
    def __init__(self, completion_tokens=0, prompt_tokens=0, total_tokens=0, **kwargs)

class MarkdownGenerationResult:
    def __init__(self, raw_markdown="", fit_markdown="", **kwargs)

class DispatchResult:
    def __init__(self, task_id="", memory_usage=0, peak_memory=0, **kwargs)

class CrawlResultContainer:
    def __init__(self, result: CrawlResult)
    def __getattr__(self, name)
    def dict(self) -> dict
    def model_dump(self) -> dict
```

---

## **8. BROWSER MANAGEMENT - Quản lý Browser**

### `browser_manager.py` - Quản lý Browser
**Chức năng**: Quản lý instances browser và context

### BrowserManager
- **Chức năng**: Quản lý browser instances
- `start()`: Khởi động browser
- `get_page()`: Lấy page instance
- `close()`: Đóng browser

### BrowserAdapter
- **Chức năng**: Adapter cho các loại browser khác nhau
- `PlaywrightAdapter`: Adapter cho Playwright
- `UndetectedAdapter`: Adapter cho undetected browser

#### Methods chính:
```python
class BrowserManager:
    def __init__(self, browser_config: BrowserConfig, logger=None, use_undetected=False)
    async def start(self) -> None
    async def close(self) -> None
    async def get_page(self, crawlerRunConfig: CrawlerRunConfig = None) -> Tuple[Page, BrowserContext]
    async def create_context(self, crawlerRunConfig: CrawlerRunConfig = None) -> BrowserContext
    async def kill_session(self, session_id: str) -> None
    async def _cleanup_expired_sessions(self) -> None
    async def _get_playwright_instance(self) -> Playwright
    async def _get_browser_instance(self) -> Browser
    def _prepare_browser_args(self) -> List[str]
    def _prepare_context_options(self, crawlerRunConfig: CrawlerRunConfig = None) -> dict
```

### `browser_adapter.py` - Browser Adapters
**Chức năng**: Adapter pattern cho các loại browser

#### Classes:
```python
class BrowserAdapter(ABC):
    @abstractmethod
    async def evaluate(self, page: Page, script: str, *args)
    @abstractmethod
    async def setup_console_capture(self, page: Page, captured_console: list)
    @abstractmethod
    async def setup_error_capture(self, page: Page, captured_console: list)
    @abstractmethod
    async def cleanup_console_capture(self, page: Page, handle_console, handle_error)

class PlaywrightAdapter(BrowserAdapter):
    async def evaluate(self, page: Page, script: str, *args)
    async def setup_console_capture(self, page: Page, captured_console: list)
    async def setup_error_capture(self, page: Page, captured_console: list)
    async def cleanup_console_capture(self, page: Page, handle_console, handle_error)

class UndetectedAdapter(BrowserAdapter):
    def __init__(self, **kwargs)
    async def evaluate(self, page: Page, script: str, *args)
    async def setup_console_capture(self, page: Page, captured_console: list)
    async def setup_error_capture(self, page: Page, captured_console: list)
    async def cleanup_console_capture(self, page: Page, handle_console, handle_error)
    async def retrieve_console_messages(self, page: Page) -> List[Dict]
```

---

## **9. DATABASE VÀ CACHE - Database và Cache**

### `async_database.py` - Database Management
**Chức năng**: Quản lý database và caching

### AsyncDatabaseManager
- **Chức năng**: Quản lý database không đồng bộ cho cache
- `acache_url()`: Cache URL results
- `aget_cached_url()`: Lấy cached URL results

### CacheContext
- **Chức năng**: Quản lý context cho caching

#### Methods chính:
```python
class AsyncDatabaseManager:
    def __init__(self, db_path: str = None)
    async def ainit_db(self) -> None
    async def acache_url(self, result: CrawlResult) -> bool
    async def aget_cached_url(self, url: str) -> Optional[CrawlResult]
    async def adelete_cached_url(self, url: str) -> bool
    async def aclear_cache(self) -> bool
    async def aget_cache_size(self) -> int
    async def aexecute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]
    async def aclose(self) -> None
```

### `cache_context.py` - Cache Management
**Chức năng**: Quản lý context cho caching

#### Classes:
```python
class CacheMode(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled" 
    BYPASS = "bypass"
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"

class CacheContext:
    def __init__(self, url: str, mode: CacheMode, always_bypass: bool = False)
    def should_read(self) -> bool
    def should_write(self) -> bool
    @property
    def display_url(self) -> str
```

---

## **10. TASK DISPATCHING VÀ LOGGING**

### `async_dispatcher.py` - Task Dispatching
**Chức năng**: Quản lý và dispatch các tasks crawling

#### Classes:
```python
class BaseDispatcher(ABC):
    @abstractmethod
    async def run_urls(self, crawler, urls: List[str], config) -> List
    @abstractmethod
    async def run_urls_stream(self, crawler, urls: List[str], config) -> AsyncGenerator

class RateLimiter:
    def __init__(self, base_delay=(1.0, 3.0), max_delay=60.0, max_retries=3)
    async def limit_rate(self, func, *args, **kwargs)
    def _calculate_delay(self, attempt: int) -> float

class MemoryAdaptiveDispatcher(BaseDispatcher):
    def __init__(self, rate_limiter=None, memory_threshold_percent=80.0, cpu_threshold_percent=85.0, **kwargs)
    async def run_urls(self, crawler, urls: List[str], config) -> List
    async def run_urls_stream(self, crawler, urls: List[str], config) -> AsyncGenerator
    def _get_memory_usage(self) -> float
    def _get_cpu_usage(self) -> float
    def _calculate_optimal_semaphore(self) -> int
    async def _process_url_with_monitoring(self, semaphore, crawler, url, config, session, index, total_urls)

class FixedSemaphoreDispatcher(BaseDispatcher):
    def __init__(self, max_workers=10, rate_limiter=None, **kwargs)
    async def run_urls(self, crawler, urls: List[str], config) -> List
    async def run_urls_stream(self, crawler, urls: List[str], config) -> AsyncGenerator
```

### `async_logger.py` - Logging System
**Chức năng**: Hệ thống logging với formatting đẹp

### AsyncLogger
- **Chức năng**: Logger không đồng bộ với formatting đẹp

#### Methods chính:
```python
class AsyncLogger:
    def __init__(self, log_file=None, verbose=True, tag_width=10, **kwargs)
    def info(self, message="", tag="INFO", params=None)
    def error(self, message="", tag="ERROR", params=None)
    def warning(self, message="", tag="WARN", params=None)
    def success(self, message="", tag="SUCCESS", params=None)
    def debug(self, message="", tag="DEBUG", params=None)
    def url_status(self, url="", success=True, timing=0, tag="CRAWL", params=None)
    def error_status(self, url="", error="", tag="ERROR", params=None)
    def _format_log_message(self, level, message, tag, params)
    def _format_duration(self, seconds: float) -> str
    def _format_url(self, url: str, max_length=50) -> str
```

---

## **11. URL DISCOVERY VÀ CONTENT FILTERING**

### `async_url_seeder.py` - URL Discovery
**Chức năng**: Khám phá và seed URLs từ sitemaps, Common Crawl

#### Methods chính:
```python
class AsyncUrlSeeder:
    def __init__(self, base_directory=None, logger=None)
    async def urls(self, domain: str, config: SeedingConfig) -> Union[List[str], List[Dict]]
    async def many_urls(self, domains: List[str], config: SeedingConfig) -> Dict[str, Union[List[str], List[Dict]]]
    async def _discover_urls_from_sitemap(self, domain: str, config: SeedingConfig) -> List[str]
    async def _discover_urls_from_common_crawl(self, domain: str, config: SeedingConfig) -> List[str]
    async def _perform_live_check(self, urls: List[str], config: SeedingConfig) -> List[str]
    async def _extract_head_data(self, urls: List[str], config: SeedingConfig) -> List[Dict]
    def _apply_pattern_filter(self, urls: List[str], pattern: str) -> List[str]
    def _load_cache(self, cache_file: str) -> Optional[Dict]
    def _save_cache(self, cache_file: str, data: Dict) -> None
```

### `content_filter_strategy.py` - Content Filtering
**Chức năng**: Lọc và xử lý nội dung

#### Classes:
```python
class ContentFilter(ABC):
    @abstractmethod
    def filter_content(self, content: str, **kwargs) -> str

class PruningContentFilter(ContentFilter):
    def __init__(self, min_word_count=50, min_avg_word_length=3, **kwargs)
    def filter_content(self, content: str, **kwargs) -> str
    def _calculate_text_metrics(self, text: str) -> Dict

class BM25ContentFilter(ContentFilter):
    def __init__(self, top_k=10, bm25_threshold=1.0, **kwargs)
    def filter_content(self, content: str, **kwargs) -> str
    def _calculate_bm25_scores(self, query_terms: List[str], documents: List[str]) -> List[float]
```

---

## **12. MARKDOWN GENERATION VÀ LINK PREVIEW**

### `markdown_generation_strategy.py` - Markdown Generation
**Chức năng**: Tạo markdown từ HTML

#### Classes:
```python
class MarkdownGenerationStrategy(ABC):
    @abstractmethod
    def generate_markdown(self, input_html: str, base_url: str = "", **kwargs) -> MarkdownGenerationResult

class DefaultMarkdownGenerator(MarkdownGenerationStrategy):
    def __init__(self, content_filter=None, content_source="cleaned_html", **kwargs)
    def generate_markdown(self, input_html: str, base_url: str = "", **kwargs) -> MarkdownGenerationResult
    def _generate_fit_markdown(self, markdown: str, base_url: str) -> str
    def _clean_markdown(self, markdown: str) -> str
```

### `link_preview.py` - Link Preview
**Chức năng**: Trích xuất metadata từ links

#### Methods chính:
```python
class LinkPreview:
    def __init__(self, logger=None)
    async def __aenter__(self)
    async def __aexit__(self, exc_type, exc_val, exc_tb)
    async def extract_link_heads(self, links: Links, config) -> Links
    async def _extract_head_for_link(self, link: Link, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, config) -> Link
    def _parse_head_content(self, html_content: str, link_url: str) -> Dict[str, Any]
    def _extract_meta_tags(self, soup) -> Dict[str, str]
    def _extract_structured_data(self, soup) -> List[Dict]
    def _score_link_relevance(self, link: Link, head_data: Dict, page_context: Dict) -> float
```

---

## **13. TABLE EXTRACTION VÀ UTILITY FUNCTIONS**

### `table_extraction.py` - Table Extraction
**Chức năng**: Trích xuất và xử lý bảng

#### Classes:
```python
class BaseTableExtractionStrategy(ABC):
    @abstractmethod
    def extract_tables(self, html_element, **kwargs) -> List[Dict]

class DefaultTableExtractionStrategy(BaseTableExtractionStrategy):
    def __init__(self, min_rows=2, min_cols=2, **kwargs)
    def extract_tables(self, html_element, **kwargs) -> List[Dict]
    def _extract_table_data(self, table_element) -> Dict
    def _extract_headers(self, table_element) -> List[str]
    def _extract_rows(self, table_element) -> List[List[str]]
    def _clean_cell_text(self, cell_text: str) -> str
```

### `utils.py` - Utility Functions
**Chức năng**: Các hàm tiện ích chung

### File: `utils.py`
- `sanitize_input_encode()`: Làm sạch và encode input
- `normalize_url()`: Normalize URL
- `is_external_url()`: Kiểm tra URL external
- `get_base_domain()`: Lấy base domain từ URL
- `extract_metadata()`: Trích xuất metadata
- `calculate_link_intrinsic_score()`: Tính điểm intrinsic của link

#### Functions chính:
```python
def sanitize_input_encode(text: str) -> str
def normalize_url(url: str, base_url: str = "") -> str
def is_external_url(url: str, base_domain: str) -> bool
def get_base_domain(url: str) -> str
def extract_metadata(soup, url: str = "") -> Dict
def extract_metadata_using_lxml(html: str, doc) -> Dict
def extract_page_context(title: str, headlines: str, meta_description: str, url: str) -> Dict
def calculate_link_intrinsic_score(link_text: str, url: str, title_attr: str, class_attr: str, rel_attr: str, page_context: Dict) -> float
def fast_format_html(html: str) -> str
def get_error_context(exc_info) -> Dict
def RobotsParser() -> object
def preprocess_html_for_schema(html_content: str, text_threshold: int = 500, max_size: int = 300000) -> str
def perform_completion_with_backoff(provider: str, prompt: str, api_token: str, **kwargs)
def extract_xml_data(tags: List[str], text: str) -> Dict
def split_and_parse_json_objects(text: str) -> Tuple[List, str]
def merge_chunks(docs: List[str], target_size: int, overlap: int, word_token_ratio: float = 4.0) -> List[str]
```

---

## **14. COMPONENTS DIRECTORY**

### `components/crawler_monitor.py` - Monitoring UI
**Chức năng**: Terminal UI để monitor crawling process

#### Classes:
```python
class CrawlerMonitor:
    def __init__(self, max_visible_urls=10)
    def start_monitoring(self, total_urls: int)
    def stop_monitoring(self)
    def update_url_status(self, url: str, status: str, timing: float = 0, error: str = "")
    def update_statistics(self, **stats)
    def _create_main_table(self) -> Table
    def _create_status_panels(self) -> Dict[str, Panel]
    def _create_url_table(self) -> Table
    def _update_display(self)
    def _format_duration(self, seconds: float) -> str
    def _format_memory(self, bytes_val: int) -> str
```

---

## **15. CRAWLERS DIRECTORY**

### `crawlers/amazon_product/crawler.py` - Amazon Product Crawler
**Chức năng**: Crawler chuyên biệt cho Amazon products

#### Classes:
```python
class AmazonProductCrawler:
    def __init__(self, **kwargs)
    async def crawl_product(self, product_url: str, **kwargs) -> Dict
    async def crawl_search_results(self, search_query: str, **kwargs) -> List[Dict]
    def _extract_product_data(self, html: str) -> Dict
    def _extract_search_results(self, html: str) -> List[Dict]
```

### `crawlers/google_search/crawler.py` - Google Search Crawler
**Chức năng**: Crawler cho Google search results

#### Classes:
```python
class GoogleSearchCrawler:
    def __init__(self, **kwargs)
    async def search(self, query: str, num_results: int = 10, **kwargs) -> List[Dict]
    def _extract_search_results(self, html: str) -> List[Dict]
    def _clean_result_data(self, result: Dict) -> Dict
```

---

## **16. DEEP_CRAWLING DIRECTORY**

### `deep_crawling/base_strategy.py` - Base Deep Crawl Strategy
**Chức năng**: Base class cho deep crawling strategies

#### Classes:
```python
class DeepCrawlStrategy(ABC):
    @abstractmethod
    async def crawl(self, url: str, depth: int, **kwargs) -> List[CrawlResult]
    @abstractmethod
    def should_crawl_url(self, url: str, current_depth: int, **kwargs) -> bool

class DeepCrawlDecorator:
    def __init__(self, crawler)
    def __call__(self, func)
    async def _deep_crawl_wrapper(self, url: str, config: CrawlerRunConfig, **kwargs)
```

### `deep_crawling/filters.py` - URL Filtering
**Chức năng**: Lọc URLs trong deep crawling

#### Classes và functions:
```python
class URLFilter(ABC):
    @abstractmethod
    def should_crawl(self, url: str, context: Dict) -> bool

class DomainFilter(URLFilter):
    def __init__(self, allowed_domains: List[str])
    def should_crawl(self, url: str, context: Dict) -> bool

class PatternFilter(URLFilter):
    def __init__(self, include_patterns: List[str] = None, exclude_patterns: List[str] = None)
    def should_crawl(self, url: str, context: Dict) -> bool

class DepthFilter(URLFilter):
    def __init__(self, max_depth: int)
    def should_crawl(self, url: str, context: Dict) -> bool

class SimilarityFilter(URLFilter):
    def __init__(self, similarity_threshold: float = 0.8)
    def should_crawl(self, url: str, context: Dict) -> bool
    def _calculate_similarity(self, url1: str, url2: str) -> float

class MediaTypeFilter(URLFilter):
    def __init__(self, allowed_types: List[str] = None, blocked_types: List[str] = None)
    def should_crawl(self, url: str, context: Dict) -> bool

def create_combined_filter(filters: List[URLFilter]) -> URLFilter
```

### `deep_crawling/scorers.py` - URL Scoring
**Chức năng**: Tính điểm ưu tiên cho URLs

#### Classes:
```python
class URLScorer(ABC):
    @abstractmethod
    def score_url(self, url: str, context: Dict) -> float

class DepthScorer(URLScorer):
    def __init__(self, depth_penalty: float = 0.1)
    def score_url(self, url: str, context: Dict) -> float

class KeywordScorer(URLScorer):
    def __init__(self, keywords: List[str], boost_factor: float = 2.0)
    def score_url(self, url: str, context: Dict) -> float

class BacklinkScorer(URLScorer):
    def __init__(self, boost_per_backlink: float = 0.1)
    def score_url(self, url: str, context: Dict) -> float

class FreshnessScorer(URLScorer):
    def __init__(self, decay_rate: float = 0.01)
    def score_url(self, url: str, context: Dict) -> float

class CombinedScorer(URLScorer):
    def __init__(self, scorers: List[URLScorer], weights: List[float] = None)
    def score_url(self, url: str, context: Dict) -> float
```

### `deep_crawling/bfs_strategy.py` - Breadth-First Strategy
**Chức năng**: Chiến lược crawl theo chiều rộng

#### Classes:
```python
class BreadthFirstDeepCrawlStrategy(DeepCrawlStrategy):
    def __init__(self, max_depth: int = 3, max_urls: int = 100, **kwargs)
    async def crawl(self, url: str, depth: int, **kwargs) -> List[CrawlResult]
    def should_crawl_url(self, url: str, current_depth: int, **kwargs) -> bool
    def _extract_links(self, html: str, base_url: str) -> List[str]
    def _filter_urls(self, urls: List[str], **kwargs) -> List[str]
```

### `deep_crawling/dfs_strategy.py` - Depth-First Strategy
**Chức năng**: Chiến lược crawl theo chiều sâu

#### Classes:
```python
class DepthFirstDeepCrawlStrategy(DeepCrawlStrategy):
    def __init__(self, max_depth: int = 3, max_urls: int = 100, **kwargs)
    async def crawl(self, url: str, depth: int, **kwargs) -> List[CrawlResult]
    def should_crawl_url(self, url: str, current_depth: int, **kwargs) -> bool
    async def _crawl_recursive(self, url: str, current_depth: int, visited: set, **kwargs) -> List[CrawlResult]
```

---

## **17. HTML2TEXT DIRECTORY**

### `html2text/config.py` - HTML2Text Configuration
**Chức năng**: Cấu hình cho html2text converter

#### Classes:
```python
class Html2TextConfig:
    def __init__(self, **kwargs)
    body_width: int = 0
    unicode_snob: bool = True
    escape_all: bool = False
    reference_links: bool = False
    mark_code: bool = False
```

### `html2text/elements.py` - HTML Elements Processing
**Chức năng**: Xử lý các HTML elements

#### Functions:
```python
def handle_tag(tag_name: str, attrs: Dict, config: Html2TextConfig) -> str
def handle_text(text: str, config: Html2TextConfig) -> str
def handle_link(href: str, text: str, config: Html2TextConfig) -> str
def handle_image(src: str, alt: str, config: Html2TextConfig) -> str
def handle_table(table_html: str, config: Html2TextConfig) -> str
def handle_list(list_html: str, config: Html2TextConfig) -> str
```

---

## **18. JS_SNIPPET DIRECTORY**

### JavaScript Files và Functions:
- `navigator_overrider.js`: Override navigator properties to avoid detection
- `remove_overlay_elements.js`: Remove popup overlays and modals
- `update_image_dimensions.js`: Update image dimensions for better processing

---

## **19. LEGACY DIRECTORY**

### `legacy/web_crawler.py` - Legacy Web Crawler
**Chức năng**: Crawler cũ để tương thích ngược

#### Classes:
```python
class WebCrawler:
    def __init__(self, **kwargs)
    def crawl(self, url: str, **kwargs) -> Dict
    def crawl_many(self, urls: List[str], **kwargs) -> List[Dict]
```

### `legacy/database.py` - Legacy Database
**Chức năng**: Database cũ để tương thích ngược

#### Classes:
```python
class DatabaseManager:
    def __init__(self, db_path: str)
    def cache_url(self, result: Dict) -> bool
    def get_cached_url(self, url: str) -> Optional[Dict]
    def clear_cache(self) -> bool
```

---

## **20. PROCESSORS DIRECTORY**

### `processors/pdf/processor.py` - PDF Processing
**Chức năng**: Xử lý PDF files

#### Classes:
```python
class PDFProcessor:
    def __init__(self, **kwargs)
    def extract_text(self, pdf_path: str) -> str
    def extract_metadata(self, pdf_path: str) -> Dict
    def convert_to_images(self, pdf_path: str) -> List[str]
    def merge_pdfs(self, pdf_paths: List[str], output_path: str) -> bool
```

---

## **21. SCRIPT DIRECTORY**

### `script/c4a_compile.py` - C4A Script Compiler
**Chức năng**: Compiler cho C4A scripting language

#### Functions:
```python
def compile_script(script_content: str) -> Dict
def parse_script(script_content: str) -> List[Dict]
def validate_script(parsed_script: List[Dict]) -> bool
def execute_script_step(step: Dict, context: Dict) -> Dict
```

### `script/c4a_result.py` - C4A Result Processing
**Chức năng**: Xử lý kết quả từ C4A scripts

#### Functions:
```python
def process_script_result(result: Dict) -> Dict
def extract_data_from_result(result: Dict, extractors: List[Dict]) -> Dict
def format_result_output(result: Dict, format_type: str) -> str
def validate_result_schema(result: Dict, schema: Dict) -> bool
```

---

## **22. ADDITIONAL CORE FILES**

### `types.py` - Type Definitions
**Chức năng**: Định nghĩa types và interfaces

#### Classes và Types:
```python
class LLMConfig:
    def __init__(self, provider: str, api_token: str = None, base_url: str = None, **kwargs)
    
def create_llm_config(provider: str = "ollama/llama3.2", api_token: str = None, **kwargs) -> LLMConfig
```

### `user_agent_generator.py` - User Agent Generation
**Chức năng**: Tạo user agents ngẫu nhiên

#### Classes:
```python
class ValidUAGenerator:
    def __init__(self)
    def generate(self, browser_type: str = "chrome", platform: str = "random", **kwargs) -> str
    def get_random_chrome_ua(self) -> str
    def get_random_firefox_ua(self) -> str
    def get_random_safari_ua(self) -> str
```

### `ssl_certificate.py` - SSL Certificate Handling
**Chức năng**: Xử lý SSL certificates

#### Classes:
```python
class SSLCertificate:
    def __init__(self, **kwargs)
    @classmethod
    def from_url(cls, url: str) -> 'SSLCertificate'
    def to_dict(self) -> Dict
    def is_valid(self) -> bool
    def get_expiry_date(self) -> datetime
    def get_issuer(self) -> str
    def get_subject(self) -> str
```

### `proxy_strategy.py` - Proxy Management
**Chức năng**: Quản lý proxy strategies

#### Classes:
```python
class ProxyStrategy(ABC):
    @abstractmethod
    async def get_next_proxy(self) -> Optional[ProxyConfig]
    @abstractmethod
    def mark_proxy_failed(self, proxy: ProxyConfig) -> None

class RotatingProxyStrategy(ProxyStrategy):
    def __init__(self, proxies: List[ProxyConfig])
    async def get_next_proxy(self) -> Optional[ProxyConfig]
    def mark_proxy_failed(self, proxy: ProxyConfig) -> None
    def _test_proxy_health(self, proxy: ProxyConfig) -> bool

class StaticProxyStrategy(ProxyStrategy):
    def __init__(self, proxy: ProxyConfig)
    async def get_next_proxy(self) -> Optional[ProxyConfig]
    def mark_proxy_failed(self, proxy: ProxyConfig) -> None
```

### `docker_client.py` - Docker Integration
**Chức năng**: Tích hợp với Docker

#### Classes:
```python
class DockerCrawler:
    def __init__(self, image_name: str = "crawl4ai", **kwargs)
    async def crawl(self, url: str, **kwargs) -> Dict
    async def crawl_many(self, urls: List[str], **kwargs) -> List[Dict]
    def _prepare_docker_command(self, **kwargs) -> List[str]
    def _parse_docker_output(self, output: str) -> Dict
```

### `migrations.py` - Database Migrations
**Chức năng**: Quản lý database migrations

#### Functions:
```python
def run_migrations(db_path: str) -> bool
def create_migration(name: str, sql: str) -> str
def get_migration_status(db_path: str) -> Dict
def rollback_migration(db_path: str, migration_id: str) -> bool
```

### `model_loader.py` - Model Loading
**Chức năng**: Load các ML models

#### Functions:
```python
def load_HF_embedding_model(model_name: str) -> Tuple
def load_text_multilabel_classifier() -> Tuple
def calculate_batch_size(device) -> int
def get_device() -> str
def load_nltk_punkt() -> None
```

### `prompts.py` - LLM Prompts
**Chức năng**: Các prompt templates cho LLM

#### Constants:
```python
PROMPT_EXTRACT_BLOCKS: str
PROMPT_EXTRACT_BLOCKS_WITH_INSTRUCTION: str
PROMPT_EXTRACT_SCHEMA_WITH_INSTRUCTION: str
PROMPT_EXTRACT_INFERRED_SCHEMA: str
JSON_SCHEMA_BUILDER: str
JSON_SCHEMA_BUILDER_XPATH: str
```

### `config.py` - Configuration Constants
**Chức năng**: Các constants và config values

#### Constants:
```python
MIN_WORD_THRESHOLD: int = 50
IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD: int = 5
IMAGE_SCORE_THRESHOLD: int = 2
SCREENSHOT_HEIGHT_TRESHOLD: int = 20000
CHUNK_TOKEN_THRESHOLD: int = 8192
OVERLAP_RATE: float = 0.1
WORD_TOKEN_RATE: float = 4.0
DEFAULT_PROVIDER: str = "ollama/llama3.2"
DEFAULT_PROVIDER_API_KEY: str = "OLLAMA_API_KEY"
IMPORTANT_ATTRS: List[str] = ["href", "src", "alt", "title", "id", "class"]
SOCIAL_MEDIA_DOMAINS: List[str] = ["facebook.com", "twitter.com", "instagram.com", ...]
ONLY_TEXT_ELIGIBLE_TAGS: List[str] = ["span", "a", "p", "div", "h1", "h2", "h3", "h4", "h5", "h6"]
```

### `cli.py` - Command Line Interface
**Chức năng**: CLI cho Crawl4AI

### File: `cli.py`
- **Chức năng**: Command line interface cho Crawl4AI
- Cung cấp các lệnh để crawl từ command line

#### Functions:
```python
def main():
def crawl_command(url: str, **kwargs):
def extract_command(html_file: str, **kwargs):
def serve_command(host: str = "localhost", port: int = 8000, **kwargs):
```

---

## **Kết luận và Tính năng nổi bật**

Crawl4AI cung cấp một kiến trúc modular và linh hoạt để crawl web với các tính năng:

- **Async crawling**: Crawl không đồng bộ hiệu suất cao
- **Multiple extraction strategies**: Nhiều chiến lược trích xuất khác nhau
- **Flexible chunking**: Các phương pháp phân đoạn văn bản linh hoạt
- **Rich media support**: Hỗ trợ đầy đủ cho images, videos, audio
- **Smart caching**: Hệ thống cache thông minh
- **Browser management**: Quản lý browser mạnh mẽ
- **Configuration flexibility**: Cấu hình linh hoạt cho mọi use case

## **Thống kê tổng quan:**

- **73 file Python** tổ chức trong kiến trúc modular
- **75+ classes** với strategy patterns rõ ràng
- **500+ methods/functions** cho mọi khía cạnh của web crawling
- **Async/await** performance cao
- **Multiple extraction strategies**: LLM, Cosine similarity, CSS/XPath selectors, Regex
- **Advanced browser management**: Playwright, Undetected browsers
- **Rich monitoring**: Terminal UI, logging, statistics
- **Docker integration** và cloud deployment
- **Custom scripting language** (C4A Script)
- **Comprehensive configuration** system

Framework này phù hợp cho việc crawl dữ liệu quy mô lớn, trích xuất nội dung phức tạp, và xây dựng các ứng dụng data intelligence. Framework này phù hợp cho các dự án từ đơn giản đến phức tạp, từ crawl cơ bản đến AI-powered content extraction và large-scale data collection.