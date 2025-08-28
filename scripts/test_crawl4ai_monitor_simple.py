#!/usr/bin/env python3
"""
Simple Test Script for Crawl4AI Domain Monitor
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

# Configure logging without emoji
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
    Simple test class for Crawl4AI Domain Monitor functionality
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
        """Check if Crawl4AI Monitor service is healthy"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"Service health check passed: {health_data}")
                    return {"status": "healthy", "data": health_data}
                else:
                    logger.error(f"Service health check failed: HTTP {response.status}")
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Service health check error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        try:
            async with self.session.get(f"{self.base_url}/monitor/status") as response:
                if response.status == 200:
                    status_data = await response.json()
                    logger.info(f"Monitoring status retrieved successfully")
                    return {"status": "success", "data": status_data}
                else:
                    logger.error(f"Monitoring status failed: HTTP {response.status}")
                    return {"status": "error", "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Monitoring status error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def trigger_domain_monitoring(self, domain_id: int) -> Dict[str, Any]:
        """Trigger monitoring for a specific domain"""
        try:
            async with self.session.post(f"{self.base_url}/monitor/domains/{domain_id}/trigger") as response:
                if response.status == 200:
                    monitor_data = await response.json()
                    logger.info(f"Domain {domain_id} monitoring triggered successfully")
                    return {"status": "success", "data": monitor_data}
                else:
                    error_text = await response.text()
                    logger.error(f"Domain {domain_id} monitoring failed: HTTP {response.status} - {error_text}")
                    return {"status": "error", "error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"Domain {domain_id} monitoring trigger error: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_monitoring_workflow(self) -> Dict[str, Any]:
        """Test complete monitoring workflow"""
        workflow_results = {
            "timestamp": datetime.now().isoformat(),
            "test_domains": self.test_domains,
            "service_url": self.base_url,
            "results": {
                "health_check": None,
                "monitoring_status": None,
                "domain_monitoring": {},
            }
        }
        
        logger.info("Starting Crawl4AI Monitor Test Workflow")
        
        # 1. Health check
        logger.info("Step 1: Health check")
        workflow_results["results"]["health_check"] = await self.check_service_health()
        
        # 2. Monitoring status
        logger.info("Step 2: Monitoring status")
        workflow_results["results"]["monitoring_status"] = await self.get_monitoring_status()
        
        # 3. Test domain monitoring (using first few domains as examples)
        logger.info("Step 3: Testing domain monitoring")
        
        # Get domain IDs from database first
        try:
            # Check what domains are available
            async with self.session.get(f"{self.base_url}/config") as response:
                if response.status == 200:
                    config_data = await response.json()
                    logger.info(f"Config retrieved: {config_data.get('app_name', 'Unknown')}")
                    workflow_results["results"]["config"] = {"status": "success", "data": config_data}
        except Exception as e:
            workflow_results["results"]["config"] = {"status": "error", "error": str(e)}
        
        # Try to trigger monitoring for domain IDs 1, 2, 3
        test_domain_ids = [1, 2, 3]
        
        for domain_id in test_domain_ids:
            logger.info(f"Testing domain ID: {domain_id}")
            domain_result = await self.trigger_domain_monitoring(domain_id)
            workflow_results["results"]["domain_monitoring"][f"domain_{domain_id}"] = domain_result
            
            # Add small delay between requests
            await asyncio.sleep(1)
        
        return workflow_results
    
    def save_results_to_json(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Save test results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crawl4ai_monitor_test_results_{timestamp}.json"
        
        filepath = f"scripts/{filename}"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return ""

async def main():
    """Main test execution function"""
    logger.info("Starting Crawl4AI Domain Monitor Test Suite")
    
    async with Crawl4AIMonitorTester() as tester:
        try:
            # Run complete monitoring workflow test
            results = await tester.test_monitoring_workflow()
            
            # Save results to JSON file
            output_file = tester.save_results_to_json(results)
            
            # Print summary without emoji
            print("\n" + "="*80)
            print("CRAWL4AI MONITOR TEST SUMMARY")
            print("="*80)
            print(f"Test completed at: {results['timestamp']}")
            print(f"Results saved to: {output_file}")
            print(f"Service URL: {results['service_url']}")
            print(f"Domains configured: {len(results['test_domains'])}")
            print(f"Service health: {results['results']['health_check']['status']}")
            print(f"Monitoring status: {results['results']['monitoring_status']['status']}")
            print(f"Domain monitoring tests: {len(results['results']['domain_monitoring'])}")
            print("="*80)
            
            # Check if any domain monitoring worked
            successful_domains = [
                domain_key for domain_key, result in results['results']['domain_monitoring'].items()
                if result.get('status') == 'success'
            ]
            
            if successful_domains:
                print(f"Successfully triggered monitoring for: {successful_domains}")
            else:
                print("No domain monitoring was successful - check service availability")
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())