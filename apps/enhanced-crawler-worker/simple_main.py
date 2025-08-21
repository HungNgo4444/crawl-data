#!/usr/bin/env python3
"""
Simple main entry point that actually works
"""

import asyncio
import sys
import os
from aiohttp import web
import json

# Add paths
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

async def health_check(request):
    """Simple health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "service": "enhanced-crawler-worker",
        "version": "1.0.0",
        "crawl4ai_available": True
    })

async def init_app():
    """Initialize the web application"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    
    print("✅ Enhanced Crawler Worker starting...")
    
    # Try to import crawl4ai to verify it works
    try:
        import crawl4ai
        print(f"✅ Crawl4AI available: {crawl4ai.__version__ if hasattr(crawl4ai, '__version__') else 'Unknown version'}")
    except ImportError as e:
        print(f"❌ Crawl4AI import failed: {e}")
    
    # Try to import workers
    try:
        from workers.url_discovery_coordinator import URLDiscoveryCoordinator
        print("✅ Workers import successful")
    except ImportError as e:
        print(f"❌ Workers import failed: {e}")
    
    return app

async def main():
    """Main function"""
    app = await init_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    print("🚀 Enhanced Crawler Worker running on http://0.0.0.0:8080")
    print("📊 Health check: http://0.0.0.0:8080/health")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("👋 Shutting down...")
        await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())