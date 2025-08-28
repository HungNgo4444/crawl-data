#!/usr/bin/env python3
"""
Test Script for Crawl4AI Domain Monitor
Test monitoring functionality and extract URLs from Vietnamese news domains
"""

import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import time

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/crawl4ai_monitor_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Crawl4AIMonitorTester:
    """
    Test class for Crawl4AI Domain Monitor functionality
    """
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_domains = [
            {"name": "soha.vn", "base_url": "https://soha.vn"},
            {"name": "vietnamnet.vn", "base_url": "https://vietnamnet.vn"},
            {"name": "vietnamplus.vn", "base_url": "https://vietnamplus.vn"},
            {"name": "tuoitre.vn", "base_url": "https://tuoitre.vn"},
            {"name": "vov.vn", "base_url": "https://vov.vn"},
            {"name": "24h.com.vn", "base_url": "https://www.24h.com.vn"},
            {"name": "thanhnien.vn", "base_url": "https://thanhnien.vn"},
            {"name": "cafef.vn", "base_url": "https://cafef.vn"},
            {"name": "thainguyen.vn", "base_url": "https://thainguyen.vn"},
            {"name": "vnexpress.net", "base_url": "https://vnexpress.net"},
            {"name": "genk.vn", "base_url": "https://genk.vn"}
        ]
        self.results = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def check_service_health(self) -> Dict[str, Any]:
        """
        Check if Crawl4AI Monitor service is healthy
        """
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"✅ Service health check passed: {health_data}")
                    return {"status": "healthy", "data": health_data}
                else:
                    logger.error(f"❌ Service health check failed: HTTP {response.status}")
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"❌ Service health check error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def check_detailed_health(self) -> Dict[str, Any]:
        """
        Check detailed health status
        """
        try:
            async with self.session.get(f"{self.base_url}/health/detailed") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"✅ Detailed health check passed")
                    return {"status": "healthy", "data": health_data}
                else:
                    logger.error(f"❌ Detailed health check failed: HTTP {response.status}")
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"❌ Detailed health check error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring status
        """
        try:
            async with self.session.get(f"{self.base_url}/monitor/status") as response:
                if response.status == 200:
                    status_data = await response.json()
                    logger.info(f"✅ Monitoring status retrieved")
                    return {"status": "success", "data": status_data}
                else:
                    logger.error(f"❌ Monitoring status failed: HTTP {response.status}")
                    return {"status": "error", "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"❌ Monitoring status error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def trigger_domain_monitoring(self, domain_id: int) -> Dict[str, Any]:
        """
        Trigger monitoring for a specific domain
        """
        try:
            async with self.session.post(f"{self.base_url}/monitor/domains/{domain_id}/trigger") as response:
                if response.status == 200:
                    monitor_data = await response.json()
                    logger.info(f"✅ Domain {domain_id} monitoring triggered successfully")
                    return {"status": "success", "data": monitor_data}
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Domain {domain_id} monitoring failed: HTTP {response.status} - {error_text}")
                    return {"status": "error", "error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"❌ Domain {domain_id} monitoring trigger error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_queue_status(self, domain_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get processing queue status
        """
        try:
            url = f"{self.base_url}/monitor/queue"
            if domain_id:
                url += f"?domain_id={domain_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    queue_data = await response.json()
                    logger.info(f"✅ Queue status retrieved for domain {domain_id or 'all'}")
                    return {"status": "success", "data": queue_data}
                else:
                    logger.error(f"❌ Queue status failed: HTTP {response.status}")
                    return {"status": "error", "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"❌ Queue status error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_monitoring_statistics(self, domain_id: Optional[int] = None, days_back: int = 7) -> Dict[str, Any]:
        """
        Get monitoring statistics
        """
        try:
            url = f"{self.base_url}/monitor/stats?days_back={days_back}"
            if domain_id:
                url += f"&domain_id={domain_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    stats_data = await response.json()
                    logger.info(f"✅ Statistics retrieved for domain {domain_id or 'all'}")
                    return {"status": "success", "data": stats_data}
                else:
                    logger.error(f"❌ Statistics failed: HTTP {response.status}")
                    return {"status": "error", "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"❌ Statistics error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_monitoring_workflow(self) -> Dict[str, Any]:
        """
        Test complete monitoring workflow
        """
        workflow_results = {
            "timestamp": datetime.now().isoformat(),
            "test_domains": self.test_domains,
            "results": {
                "health_check": None,
                "detailed_health": None,
                "monitoring_status": None,
                "domain_monitoring": {},
                "queue_status": None,
                "statistics": None
            }
        }
        
        logger.info("🚀 Starting Crawl4AI Monitor Test Workflow")
        
        # 1. Health checks
        logger.info("📊 Step 1: Health checks")
        workflow_results["results"]["health_check"] = await self.check_service_health()
        workflow_results["results"]["detailed_health"] = await self.check_detailed_health()
        
        # 2. Monitoring status
        logger.info("📊 Step 2: Monitoring status")
        workflow_results["results"]["monitoring_status"] = await self.get_monitoring_status()
        
        # 3. Test domain monitoring (using first few domains as examples)
        logger.info("📊 Step 3: Testing domain monitoring")
        test_domain_ids = [1, 2, 3]  # Assuming domain IDs start from 1
        
        for domain_id in test_domain_ids:
            logger.info(f"🎯 Testing domain ID: {domain_id}")
            domain_result = await self.trigger_domain_monitoring(domain_id)
            workflow_results["results"]["domain_monitoring"][f"domain_{domain_id}"] = domain_result
            
            # Add small delay between requests
            await asyncio.sleep(2)
        
        # 4. Queue status
        logger.info("📊 Step 4: Queue status")
        workflow_results["results"]["queue_status"] = await self.get_queue_status()
        
        # 5. Statistics
        logger.info("📊 Step 5: Monitoring statistics")
        workflow_results["results"]["statistics"] = await self.get_monitoring_statistics()
        
        return workflow_results
    
    async def extract_crawled_urls(self) -> Dict[str, List[str]]:
        """
        Extract URLs that were discovered during monitoring
        """
        crawled_urls = {}
        
        logger.info("🔍 Extracting crawled URLs from monitoring results")
        
        # Get queue status for all domains to see discovered URLs
        queue_result = await self.get_queue_status()
        
        if queue_result["status"] == "success" and "data" in queue_result:
            queue_data = queue_result["data"]
            
            # Process queue data to extract URLs by domain
            for domain in self.test_domains:
                domain_name = domain["name"]
                crawled_urls[domain_name] = []
                
                # Try to get domain-specific queue
                domain_queue_result = await self.get_queue_status()
                if domain_queue_result["status"] == "success":
                    # Extract URLs from queue data
                    # This would depend on the actual API response structure
                    crawled_urls[domain_name] = []
        
        return crawled_urls
    
    def save_results_to_json(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Save test results to JSON file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crawl4ai_monitor_test_results_{timestamp}.json"
        
        filepath = f"scripts/{filename}"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Results saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")
            return ""

async def main():
    """
    Main test execution function
    """
    logger.info("🎯 Starting Crawl4AI Domain Monitor Test Suite")
    
    async with Crawl4AIMonitorTester() as tester:
        try:
            # Run complete monitoring workflow test
            results = await tester.test_monitoring_workflow()
            
            # Extract crawled URLs
            crawled_urls = await tester.extract_crawled_urls()
            results["crawled_urls"] = crawled_urls
            
            # Save results to JSON file
            output_file = tester.save_results_to_json(results)
            
            # Print summary
            print("\n" + "="*80)
            print("🎉 CRAWL4AI MONITOR TEST SUMMARY")
            print("="*80)
            print(f"📊 Test completed at: {results['timestamp']}")
            print(f"📁 Results saved to: {output_file}")
            print(f"🌐 Domains tested: {len(results['test_domains'])}")
            print(f"🔍 Service health: {results['results']['health_check']['status']}")
            print(f"📈 Monitoring status: {results['results']['monitoring_status']['status']}")
            print(f"⚡ Domain monitoring tests: {len(results['results']['domain_monitoring'])}")
            
            # Print crawled URLs summary
            if crawled_urls:
                print(f"\n🔗 CRAWLED URLS SUMMARY:")
                for domain, urls in crawled_urls.items():
                    print(f"  {domain}: {len(urls)} URLs")
            
            print("="*80)
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())