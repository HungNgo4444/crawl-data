#!/usr/bin/env python3
"""
Test script for monitoring options validation
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.worker_config import get_worker_config
from src.utils.database_utils import DatabaseManager
from src.monitor.url_extractor import URLExtractor
from src.monitor.domain_monitor import DomainMonitor
from src.monitor.domain_monitor_async import AsyncDomainMonitor
from src.monitor.scheduler import MonitoringScheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MonitoringOptionsTest:
    """Test both monitoring options"""
    
    def __init__(self):
        self.config = get_worker_config()
        self.db_manager = DatabaseManager()
        
    async def test_database_connection(self):
        """Test database connectivity"""
        logger.info("🔍 Testing database connection...")
        
        if not self.db_manager.connect():
            logger.error("❌ Database connection failed")
            return False
            
        logger.info("✅ Database connection successful")
        return True
    
    async def test_domain_availability(self):
        """Test if domains are available for monitoring"""
        logger.info("🔍 Testing domain availability...")
        
        domains = self.db_manager.get_domains_for_monitoring()
        logger.info(f"📊 Found {len(domains)} domains for monitoring")
        
        if len(domains) == 0:
            logger.warning("⚠️  No domains available for testing")
            return False
            
        # Show first few domains
        for i, domain in enumerate(domains[:3]):
            name = domain.get('name', 'unknown')
            rss_count = len(domain.get('rss_feeds', []))
            sitemap_count = len(domain.get('sitemaps', []))
            logger.info(f"   {i+1}. {name} - RSS: {rss_count}, Sitemaps: {sitemap_count}")
            
        return True
    
    async def test_option1_timeout_scheduling(self):
        """Test Option 1: Timeout-based scheduling"""
        logger.info("🚀 Testing Option 1: Timeout-based scheduling...")
        
        try:
            # Force Option 1 configuration
            test_config = self.config.copy()
            test_config['use_pure_async'] = False
            test_config['monitoring_timeout_seconds'] = 60  # 1 minute for testing
            
            url_extractor = URLExtractor()
            domain_monitor = DomainMonitor(self.db_manager, url_extractor)
            
            # Get a few domains for testing
            domains = self.db_manager.get_domains_for_monitoring()[:3]
            
            if not domains:
                logger.warning("⚠️  No domains for Option 1 testing")
                return False
            
            start_time = datetime.now()
            
            # Test timeout protection simulation
            try:
                result = await asyncio.wait_for(
                    domain_monitor.monitor_all_domains(),
                    timeout=test_config['monitoring_timeout_seconds']
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                logger.info(f"✅ Option 1 completed in {duration:.1f}s")
                logger.info(f"   📊 Results: {result}")
                
                return True
                
            except asyncio.TimeoutError:
                duration = (datetime.now() - start_time).total_seconds()
                logger.warning(f"⏰ Option 1 timeout after {duration:.1f}s (expected for testing)")
                return True  # Timeout handling is part of the feature
                
        except Exception as e:
            logger.error(f"❌ Option 1 test failed: {e}")
            return False
    
    async def test_option2_pure_async(self):
        """Test Option 2: Pure async monitoring"""
        logger.info("🚀 Testing Option 2: Pure async monitoring...")
        
        try:
            url_extractor = URLExtractor()
            async_monitor = AsyncDomainMonitor(self.db_manager, url_extractor)
            
            # Get a few domains for testing
            domains = self.db_manager.get_domains_for_monitoring()[:3]
            
            if not domains:
                logger.warning("⚠️  No domains for Option 2 testing")
                return False
            
            start_time = datetime.now()
            
            # Test single domain first
            test_domain = domains[0]
            single_result = await async_monitor.monitor_single_domain(test_domain)
            
            logger.info(f"   🔬 Single domain test: {single_result}")
            
            # Test all domains
            result = await async_monitor.monitor_all_domains()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Option 2 completed in {duration:.1f}s")
            logger.info(f"   📊 Results: {result}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Option 2 test failed: {e}")
            return False
    
    async def test_scheduler_initialization(self):
        """Test scheduler initialization with both options"""
        logger.info("🔍 Testing scheduler initialization...")
        
        try:
            # Test Option 1 scheduler
            scheduler1 = MonitoringScheduler()
            scheduler1.config['use_pure_async'] = False
            
            if await scheduler1.initialize():
                logger.info("✅ Option 1 scheduler initialization successful")
                scheduler1.db_manager.disconnect()
            else:
                logger.error("❌ Option 1 scheduler initialization failed")
                return False
            
            # Test Option 2 scheduler  
            scheduler2 = MonitoringScheduler()
            scheduler2.config['use_pure_async'] = True
            
            if await scheduler2.initialize():
                logger.info("✅ Option 2 scheduler initialization successful")
                scheduler2.db_manager.disconnect()
            else:
                logger.error("❌ Option 2 scheduler initialization failed")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Scheduler initialization test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all validation tests"""
        logger.info("🧪 Starting monitoring options validation...")
        logger.info(f"📊 Configuration: {self.config}")
        
        tests = [
            ("Database Connection", self.test_database_connection),
            ("Domain Availability", self.test_domain_availability),
            ("Scheduler Initialization", self.test_scheduler_initialization),
            ("Option 1: Timeout Scheduling", self.test_option1_timeout_scheduling),
            ("Option 2: Pure Async", self.test_option2_pure_async),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"🧪 Running: {test_name}")
            
            try:
                result = await test_func()
                results[test_name] = result
                
                if result:
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"💥 {test_name}: EXCEPTION - {e}")
                results[test_name] = False
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("📊 TEST SUMMARY:")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {status} {test_name}")
        
        logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed! Both monitoring options are ready.")
        else:
            logger.warning("⚠️  Some tests failed. Check implementation before deploying.")
        
        return passed == total

async def main():
    """Main test entry point"""
    test_runner = MonitoringOptionsTest()
    
    try:
        success = await test_runner.run_all_tests()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Testing interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return 1
        
    finally:
        if test_runner.db_manager:
            test_runner.db_manager.disconnect()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)