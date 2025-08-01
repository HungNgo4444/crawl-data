import asyncio
from playwright.async_api import async_playwright, Browser
import logging

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Singleton async manager for Playwright browser instance.
    Đảm bảo chỉ có 1 browser được mở cho toàn bộ hệ thống.
    """
    _instance = None
    _browser: Browser = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_browser(cls, headless: bool = True) -> Browser:
        async with cls._lock:
            if cls._browser is None or not cls._browser.is_connected():
                logger.info("Launching Playwright browser (singleton)...")
                playwright = await async_playwright().start()
                cls._browser = await playwright.chromium.launch(headless=headless)
            return cls._browser

    @classmethod
    async def close_browser(cls):
        async with cls._lock:
            if cls._browser and cls._browser.is_connected():
                logger.info("Closing Playwright browser (singleton)...")
                await cls._browser.close()
                cls._browser = None 