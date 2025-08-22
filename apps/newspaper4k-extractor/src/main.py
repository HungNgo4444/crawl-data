"""FastAPI main application for Newspaper4k Content Extractor"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .extractor.article_processor import ArticleProcessor
from .models.request_models import DomainRequest, ExtractionResponse, HealthResponse
from .config.settings import get_settings

# Initialize settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Standalone Newspaper4k Content Extractor for Vietnamese news sites"
)

# Dependency injection for processor
def get_processor() -> ArticleProcessor:
    """Get ArticleProcessor instance - dependency injection pattern"""
    return ArticleProcessor()


@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "message": "Newspaper4k Content Extractor API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    processor = get_processor()
    db_connected = processor.db.test_connection()
    
    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        version=settings.app_version,
        timestamp=datetime.utcnow().isoformat(),
        database_connected=db_connected
    )


@app.get("/domains", response_class=JSONResponse)
async def get_domains():
    """Get all active domains"""
    try:
        domains = processor.get_all_domains()
        return {
            "domains": domains,
            "count": len(domains)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract/{domain_name}", response_model=ExtractionResponse)
async def extract_domain(
    domain_name: str,
    max_articles: int = Query(default=10, ge=1, le=100, description="Maximum articles to extract")
):
    """Extract articles from a specific domain"""
    try:
        result = processor.process_domain(domain_name, max_articles)
        
        if result.get('success'):
            return ExtractionResponse(
                success=True,
                message=f"Successfully extracted {result['success_count']} articles",
                data=result,
                processing_time=result['processing_time']
            )
        else:
            return ExtractionResponse(
                success=False,
                message=result.get('error', 'Unknown error'),
                data=None,
                processing_time=0
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/extract/{domain_name}", response_model=ExtractionResponse)
async def extract_domain_get(
    domain_name: str,
    max_articles: int = Query(default=10, ge=1, le=100, description="Maximum articles to extract")
):
    """Extract articles from a specific domain (GET method)"""
    return await extract_domain(domain_name, max_articles)


@app.get("/test/{domain_name}", response_class=JSONResponse)
async def test_domain(domain_name: str):
    """Test extraction for a domain with minimal articles"""
    try:
        processor = get_processor()
        result = processor.process_domain(domain_name, max_articles=2)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-url", response_class=JSONResponse)
async def extract_single_url(url: str):
    """Extract article from single URL"""
    try:
        processor = get_processor()
        result = processor.extract_single_url(url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, debug=settings.debug)
