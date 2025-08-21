#!/usr/bin/env python3
"""
Analysis Worker Test Script
Test Vietnamese domain analysis with real database
Author: Quinn (QA Architect)
Date: 2025-08-12
"""

import asyncio
import aiohttp
import json
import time
import sys
from typing import Dict, List, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AnalysisWorkerTester:
    """Test Analysis Worker with Vietnamese domains"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> Dict[str, Any]:
        """Check worker health status"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
    
    async def trigger_analysis(self, domain_name: str, base_url: str, trigger_source: str = "test") -> Dict[str, Any]:
        """Trigger domain analysis"""
        payload = {
            "domain_name": domain_name,
            "base_url": base_url,
            "trigger_source": trigger_source
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/analysis/trigger",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                result["http_status"] = response.status
                return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/queue/stats") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/worker/stats") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_analysis_result(self, job_id: str) -> Dict[str, Any]:
        """Get analysis result by job ID"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/analysis/result/{job_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_recent_analyses(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent analysis results"""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/analysis/recent?limit={limit}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def wait_for_analysis_completion(self, job_id: str, timeout: int = 60) -> Dict[str, Any]:
        """Wait for analysis to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = await self.get_analysis_result(job_id)
            
            if "error" not in result:
                if result.get("status") in ["COMPLETED", "FAILED"]:
                    return result
            
            await asyncio.sleep(2)  # Wait 2 seconds before checking again
        
        return {"error": "Timeout waiting for analysis completion"}


async def test_vietnamese_domains():
    """Test Analysis Worker with Vietnamese news domains"""
    
    # Vietnamese news domains to test
    test_domains = [
        {"name": "vnexpress.net", "url": "https://vnexpress.net", "priority": "high"},
        {"name": "dantri.com.vn", "url": "https://dantri.com.vn", "priority": "high"},
        {"name": "tuoitre.vn", "url": "https://tuoitre.vn", "priority": "high"},
        {"name": "thanhnien.vn", "url": "https://thanhnien.vn", "priority": "medium"},
        {"name": "cafef.vn", "url": "https://cafef.vn", "priority": "medium"},
        {"name": "vtv.vn", "url": "https://vtv.vn", "priority": "medium"},
        {"name": "vietnamnet.vn", "url": "https://vietnamnet.vn", "priority": "low"},
        {"name": "24h.com.vn", "url": "https://24h.com.vn", "priority": "low"}
    ]
    
    print("🚀 Testing Analysis Worker with Vietnamese News Domains")
    print("=" * 60)
    
    async with AnalysisWorkerTester() as tester:
        
        # 1. Check health status
        print("\n🏥 Checking worker health...")
        health = await tester.check_health()
        print(f"Health Status: {health.get('status', 'unknown')}")
        
        if health.get('status') != 'healthy':
            print("❌ Worker is not healthy. Please check the service.")
            if 'error' in health:
                print(f"Error: {health['error']}")
            return
        
        # 2. Get initial stats
        print("\n📊 Initial worker statistics...")
        worker_stats = await tester.get_worker_stats()
        queue_stats = await tester.get_queue_stats()
        
        print(f"Worker Status: {worker_stats.get('status', 'unknown')}")
        print(f"Processed Jobs: {worker_stats.get('processed_jobs', 0)}")
        print(f"Failed Jobs: {worker_stats.get('failed_jobs', 0)}")
        print(f"Queue Depth: {queue_stats.get('total_depth', 0)}")
        
        # 3. Test domain analysis
        print("\n🔍 Testing domain analysis...")
        analysis_jobs = []
        
        for domain in test_domains[:5]:  # Test first 5 domains
            print(f"\n📰 Analyzing {domain['name']} ({domain['priority']} priority)...")
            
            result = await tester.trigger_analysis(
                domain_name=domain['name'],
                base_url=domain['url'],
                trigger_source="automated_test"
            )
            
            if result.get('success'):
                job_id = result.get('job_id')
                print(f"✅ Analysis triggered. Job ID: {job_id}")
                analysis_jobs.append({
                    'job_id': job_id,
                    'domain': domain['name'],
                    'started_at': time.time()
                })
            else:
                print(f"❌ Failed to trigger analysis: {result.get('error', 'Unknown error')}")
        
        # 4. Wait for analyses to complete
        if analysis_jobs:
            print(f"\n⏳ Waiting for {len(analysis_jobs)} analyses to complete...")
            
            completed_jobs = []
            for job in analysis_jobs:
                print(f"\nWaiting for {job['domain']} analysis...")
                
                result = await tester.wait_for_analysis_completion(job['job_id'], timeout=120)
                
                if "error" not in result:
                    duration = time.time() - job['started_at']
                    print(f"✅ {job['domain']} completed in {duration:.1f}s")
                    print(f"   Status: {result.get('status')}")
                    print(f"   Confidence: {result.get('overall_confidence_score', 0):.2f}")
                    print(f"   Language: {result.get('language_detected', 'unknown')}")
                    print(f"   Vietnamese Ratio: {result.get('vietnamese_content_ratio', 0):.2f}")
                    
                    completed_jobs.append({**job, 'result': result, 'duration': duration})
                else:
                    print(f"❌ {job['domain']} failed or timed out: {result.get('error')}")
        
        # 5. Get final stats
        print("\n📊 Final statistics...")
        final_worker_stats = await tester.get_worker_stats()
        final_queue_stats = await tester.get_queue_stats()
        
        print(f"Total Processed: {final_worker_stats.get('processed_jobs', 0)}")
        print(f"Total Failed: {final_worker_stats.get('failed_jobs', 0)}")
        print(f"Success Rate: {final_worker_stats.get('success_rate', 0):.1f}%")
        print(f"Final Queue Depth: {final_queue_stats.get('total_depth', 0)}")
        
        # 6. Get recent analyses
        print("\n🕒 Recent analysis results...")
        recent = await tester.get_recent_analyses(limit=10)
        
        if "error" not in recent and recent.get('analyses'):
            for analysis in recent['analyses'][:5]:  # Show top 5
                print(f"  • {analysis.get('domain_name')}: {analysis.get('status')} "
                      f"(confidence: {analysis.get('overall_confidence_score', 0):.2f})")
        
        # 7. Performance summary
        if analysis_jobs:
            print("\n🎯 Performance Summary:")
            print("-" * 30)
            
            successful_analyses = [job for job in completed_jobs if job.get('result', {}).get('status') == 'COMPLETED']
            
            if successful_analyses:
                avg_duration = sum(job['duration'] for job in successful_analyses) / len(successful_analyses)
                avg_confidence = sum(job['result']['overall_confidence_score'] for job in successful_analyses) / len(successful_analyses)
                avg_vietnamese_ratio = sum(job['result']['vietnamese_content_ratio'] for job in successful_analyses) / len(successful_analyses)
                
                print(f"Successful Analyses: {len(successful_analyses)}/{len(analysis_jobs)}")
                print(f"Average Duration: {avg_duration:.1f} seconds")
                print(f"Average Confidence: {avg_confidence:.2f}")
                print(f"Average Vietnamese Ratio: {avg_vietnamese_ratio:.2f}")
                
                # Performance benchmarks
                print("\n📏 Benchmark Results:")
                fast_analyses = sum(1 for job in successful_analyses if job['duration'] < 10)
                high_confidence = sum(1 for job in successful_analyses if job['result']['overall_confidence_score'] > 0.8)
                high_vietnamese = sum(1 for job in successful_analyses if job['result']['vietnamese_content_ratio'] > 0.8)
                
                print(f"Fast Analyses (< 10s): {fast_analyses}/{len(successful_analyses)} ({fast_analyses/len(successful_analyses)*100:.1f}%)")
                print(f"High Confidence (> 0.8): {high_confidence}/{len(successful_analyses)} ({high_confidence/len(successful_analyses)*100:.1f}%)")
                print(f"High Vietnamese Content (> 0.8): {high_vietnamese}/{len(successful_analyses)} ({high_vietnamese/len(successful_analyses)*100:.1f}%)")
            
        print("\n✅ Analysis Worker testing completed!")


async def test_specific_domain(domain_name: str, base_url: str):
    """Test analysis of a specific domain"""
    print(f"🔍 Testing specific domain: {domain_name}")
    print("=" * 50)
    
    async with AnalysisWorkerTester() as tester:
        # Check health
        health = await tester.check_health()
        if health.get('status') != 'healthy':
            print("❌ Worker is not healthy")
            return
        
        # Trigger analysis
        print(f"📰 Analyzing {domain_name}...")
        result = await tester.trigger_analysis(domain_name, base_url, "manual_test")
        
        if not result.get('success'):
            print(f"❌ Failed to trigger analysis: {result.get('error')}")
            return
        
        job_id = result.get('job_id')
        print(f"✅ Analysis triggered. Job ID: {job_id}")
        
        # Wait for completion
        print("⏳ Waiting for analysis to complete...")
        analysis_result = await tester.wait_for_analysis_completion(job_id, timeout=120)
        
        if "error" in analysis_result:
            print(f"❌ Analysis failed: {analysis_result['error']}")
            return
        
        # Display detailed results
        print(f"\n📊 Analysis Results for {domain_name}:")
        print("-" * 40)
        print(f"Status: {analysis_result.get('status')}")
        print(f"Confidence Score: {analysis_result.get('overall_confidence_score', 0):.3f}")
        print(f"Language Detected: {analysis_result.get('language_detected')}")
        print(f"Vietnamese Content Ratio: {analysis_result.get('vietnamese_content_ratio', 0):.3f}")
        print(f"Layout Type: {analysis_result.get('layout_type')}")
        print(f"Analysis Duration: {analysis_result.get('analysis_duration_seconds', 0):.2f}s")
        
        # Show parsing template
        if analysis_result.get('parsing_template'):
            template = analysis_result['parsing_template']
            print(f"\n🏗️ Parsing Template:")
            print(f"  Headline Selectors: {template.get('headline_selectors', [])}")
            print(f"  Content Selectors: {template.get('content_selectors', [])}")
            if template.get('metadata_selectors'):
                print(f"  Metadata Selectors: {template.get('metadata_selectors')}")
        
        # Show discovery methods
        if analysis_result.get('discovery_methods'):
            print(f"\n🔍 URL Discovery Methods:")
            for method in analysis_result['discovery_methods']:
                print(f"  • {method.get('method_type')}: {len(method.get('urls', []))} URLs (confidence: {method.get('confidence_score', 0):.2f})")
        
        # Show errors/warnings
        if analysis_result.get('errors'):
            print(f"\n❌ Errors: {analysis_result['errors']}")
        if analysis_result.get('warnings'):
            print(f"\n⚠️ Warnings: {analysis_result['warnings']}")


async def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "domain" and len(sys.argv) >= 4:
            # Test specific domain
            domain_name = sys.argv[2]
            base_url = sys.argv[3]
            await test_specific_domain(domain_name, base_url)
        else:
            print("Usage:")
            print("  python test_analysis_worker.py                    # Test multiple Vietnamese domains")
            print("  python test_analysis_worker.py domain <name> <url>  # Test specific domain")
            print("\nExamples:")
            print("  python test_analysis_worker.py")
            print("  python test_analysis_worker.py domain vnexpress.net https://vnexpress.net")
    else:
        # Test multiple Vietnamese domains
        await test_vietnamese_domains()


if __name__ == "__main__":
    asyncio.run(main())