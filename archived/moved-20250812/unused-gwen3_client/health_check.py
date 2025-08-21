"""
GWEN-3 Health Check Implementation
Comprehensive health monitoring for Ollama GWEN-3 service
Author: James (Dev Agent)
Date: 2025-08-11
"""

import asyncio
import aiohttp
import logging
import time
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from .config import config

class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a health check operation"""
    
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    duration_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class SystemHealth:
    """Overall system health status"""
    
    status: HealthStatus
    message: str
    timestamp: datetime
    checks: List[HealthCheckResult]
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'checks': [check.to_dict() for check in self.checks],
            'summary': self.summary
        }

class GWEN3HealthChecker:
    """
    Comprehensive health checker for GWEN-3 Ollama service
    Monitors model availability, performance, and resource usage
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize health checker"""
        self.config = config
        self.base_url = base_url or self.config.ollama.base_url
        self.model_name = self.config.ollama.model_name
        
        # HTTP session for health checks
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Health check history
        self._health_history: List[SystemHealth] = []
        self._max_history_size = 100
        
        # Performance metrics
        self._performance_metrics = {
            "response_times": [],
            "error_count": 0,
            "last_successful_check": None,
            "consecutive_failures": 0
        }
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Health checker initialized for {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._init_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup_session()
    
    async def _init_session(self) -> None:
        """Initialize HTTP session for health checks"""
        if self.session and not self.session.closed:
            return
        
        timeout = aiohttp.ClientTimeout(total=30)  # Shorter timeout for health checks
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
    
    async def _cleanup_session(self) -> None:
        """Cleanup HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def perform_comprehensive_health_check(self) -> SystemHealth:
        """
        Perform comprehensive health check of GWEN-3 system
        
        Returns:
            SystemHealth object with overall status and detailed results
        """
        start_time = time.time()
        checks = []
        
        self.logger.info("Starting comprehensive health check")
        
        try:
            # Ensure session is initialized
            await self._init_session()
            
            # 1. Service Connectivity Check
            service_check = await self._check_service_connectivity()
            checks.append(service_check)
            
            # 2. Model Availability Check
            model_check = await self._check_model_availability()
            checks.append(model_check)
            
            # 3. Model Performance Check (if model is available)
            if model_check.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]:
                performance_check = await self._check_model_performance()
                checks.append(performance_check)
            
            # 4. Resource Usage Check
            resource_check = await self._check_resource_usage()
            checks.append(resource_check)
            
            # 5. API Endpoints Check
            api_check = await self._check_api_endpoints()
            checks.append(api_check)
            
            # 6. Vietnamese Analysis Capability Check
            if model_check.status == HealthStatus.HEALTHY:
                vietnamese_check = await self._check_vietnamese_analysis()
                checks.append(vietnamese_check)
            
            # Determine overall health status
            overall_status, overall_message = self._determine_overall_status(checks)
            
            # Create summary
            summary = self._create_health_summary(checks, time.time() - start_time)
            
            # Create system health result
            system_health = SystemHealth(
                status=overall_status,
                message=overall_message,
                timestamp=datetime.now(),
                checks=checks,
                summary=summary
            )
            
            # Update performance metrics
            self._update_performance_metrics(system_health)
            
            # Store in history
            self._add_to_history(system_health)
            
            self.logger.info(f"Health check completed: {overall_status.value} - {overall_message}")
            
            return system_health
            
        except Exception as e:
            error_msg = f"Health check failed with exception: {e}"
            self.logger.error(error_msg)
            
            # Create error result
            error_check = HealthCheckResult(
                component="health_checker",
                status=HealthStatus.CRITICAL,
                message=error_msg,
                details={"exception": str(e)},
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
            return SystemHealth(
                status=HealthStatus.CRITICAL,
                message="Health check system failure",
                timestamp=datetime.now(),
                checks=[error_check],
                summary={"error": str(e)}
            )
    
    async def _check_service_connectivity(self) -> HealthCheckResult:
        """Check if Ollama service is reachable"""
        start_time = time.time()
        
        try:
            async with self.session.get(f"{self.base_url}/api/version", timeout=aiohttp.ClientTimeout(total=10)) as response:
                duration_ms = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    version_data = await response.json()
                    
                    return HealthCheckResult(
                        component="service_connectivity",
                        status=HealthStatus.HEALTHY,
                        message="Ollama service is reachable and responding",
                        details={
                            "response_status": response.status,
                            "version": version_data.get("version", "unknown"),
                            "response_time_ms": duration_ms
                        },
                        timestamp=datetime.now(),
                        duration_ms=duration_ms
                    )
                else:
                    return HealthCheckResult(
                        component="service_connectivity",
                        status=HealthStatus.WARNING,
                        message=f"Service responding but with status {response.status}",
                        details={"response_status": response.status},
                        timestamp=datetime.now(),
                        duration_ms=duration_ms
                    )
        
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="service_connectivity",
                status=HealthStatus.CRITICAL,
                message="Service connectivity timeout",
                details={"timeout_seconds": 10},
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="service_connectivity",
                status=HealthStatus.CRITICAL,
                message=f"Service connectivity failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
    
    async def _check_model_availability(self) -> HealthCheckResult:
        """Check if GWEN-3 model is loaded and available"""
        start_time = time.time()
        
        try:
            # Get list of loaded models
            async with self.session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=15)) as response:
                duration_ms = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    models_data = await response.json()
                    models = models_data.get("models", [])
                    model_names = [model.get("name", "") for model in models]
                    
                    if self.model_name in model_names:
                        # Get specific model information
                        model_info = next((m for m in models if m.get("name") == self.model_name), {})
                        
                        return HealthCheckResult(
                            component="model_availability",
                            status=HealthStatus.HEALTHY,
                            message=f"Model {self.model_name} is loaded and available",
                            details={
                                "model_name": self.model_name,
                                "model_info": model_info,
                                "total_models": len(models),
                                "all_models": model_names
                            },
                            timestamp=datetime.now(),
                            duration_ms=duration_ms
                        )
                    else:
                        return HealthCheckResult(
                            component="model_availability",
                            status=HealthStatus.CRITICAL,
                            message=f"Model {self.model_name} not found in loaded models",
                            details={
                                "expected_model": self.model_name,
                                "available_models": model_names
                            },
                            timestamp=datetime.now(),
                            duration_ms=duration_ms
                        )
                else:
                    return HealthCheckResult(
                        component="model_availability",
                        status=HealthStatus.WARNING,
                        message=f"Failed to retrieve model list (status {response.status})",
                        details={"response_status": response.status},
                        timestamp=datetime.now(),
                        duration_ms=duration_ms
                    )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="model_availability",
                status=HealthStatus.CRITICAL,
                message=f"Model availability check failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
    
    async def _check_model_performance(self) -> HealthCheckResult:
        """Check model inference performance with simple test"""
        start_time = time.time()
        
        try:
            test_request = {
                "model": self.model_name,
                "prompt": "Test inference: Xin chào",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 20
                }
            }
            
            async with self.session.post(f"{self.base_url}/api/generate", 
                                       json=test_request, 
                                       timeout=aiohttp.ClientTimeout(total=60)) as response:
                
                duration_ms = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Check response structure
                    if "response" in result and len(result["response"]) > 0:
                        status = HealthStatus.HEALTHY
                        if duration_ms > 30000:  # 30 seconds
                            status = HealthStatus.WARNING
                        elif duration_ms > 60000:  # 60 seconds
                            status = HealthStatus.CRITICAL
                        
                        return HealthCheckResult(
                            component="model_performance",
                            status=status,
                            message=f"Model inference working (response time: {duration_ms:.0f}ms)",
                            details={
                                "response_time_ms": duration_ms,
                                "response_length": len(result["response"]),
                                "total_duration": result.get("total_duration", 0),
                                "load_duration": result.get("load_duration", 0),
                                "prompt_eval_count": result.get("prompt_eval_count", 0),
                                "eval_count": result.get("eval_count", 0)
                            },
                            timestamp=datetime.now(),
                            duration_ms=duration_ms
                        )
                    else:
                        return HealthCheckResult(
                            component="model_performance",
                            status=HealthStatus.WARNING,
                            message="Model responded but with empty/invalid response",
                            details={"response_structure": result},
                            timestamp=datetime.now(),
                            duration_ms=duration_ms
                        )
                else:
                    return HealthCheckResult(
                        component="model_performance",
                        status=HealthStatus.CRITICAL,
                        message=f"Model inference failed (status {response.status})",
                        details={"response_status": response.status},
                        timestamp=datetime.now(),
                        duration_ms=duration_ms
                    )
        
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="model_performance",
                status=HealthStatus.CRITICAL,
                message="Model inference timeout (>60s)",
                details={"timeout_seconds": 60},
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="model_performance",
                status=HealthStatus.CRITICAL,
                message=f"Model performance check failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
    
    async def _check_resource_usage(self) -> HealthCheckResult:
        """Check resource usage (basic implementation)"""
        start_time = time.time()
        
        try:
            # This is a placeholder - in a real container environment,
            # you would check actual memory usage, CPU usage, etc.
            # For now, we'll just return a healthy status
            
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="resource_usage",
                status=HealthStatus.HEALTHY,
                message="Resource usage monitoring not implemented",
                details={
                    "note": "Container resource monitoring would be implemented here",
                    "memory_limit": "8GB",
                    "cpu_limit": "4 cores"
                },
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="resource_usage",
                status=HealthStatus.WARNING,
                message=f"Resource usage check failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
    
    async def _check_api_endpoints(self) -> HealthCheckResult:
        """Check availability of key API endpoints"""
        start_time = time.time()
        
        endpoints = [
            ("/api/version", "GET"),
            ("/api/tags", "GET"),
        ]
        
        endpoint_results = []
        
        try:
            for endpoint, method in endpoints:
                endpoint_start = time.time()
                
                try:
                    if method == "GET":
                        async with self.session.get(f"{self.base_url}{endpoint}", 
                                                  timeout=aiohttp.ClientTimeout(total=10)) as response:
                            endpoint_duration = (time.time() - endpoint_start) * 1000
                            endpoint_results.append({
                                "endpoint": endpoint,
                                "method": method,
                                "status": response.status,
                                "duration_ms": endpoint_duration,
                                "success": response.status == 200
                            })
                
                except Exception as e:
                    endpoint_duration = (time.time() - endpoint_start) * 1000
                    endpoint_results.append({
                        "endpoint": endpoint,
                        "method": method,
                        "error": str(e),
                        "duration_ms": endpoint_duration,
                        "success": False
                    })
            
            duration_ms = (time.time() - start_time) * 1000
            successful_endpoints = sum(1 for r in endpoint_results if r.get("success", False))
            total_endpoints = len(endpoints)
            
            if successful_endpoints == total_endpoints:
                status = HealthStatus.HEALTHY
                message = f"All {total_endpoints} API endpoints are accessible"
            elif successful_endpoints > total_endpoints // 2:
                status = HealthStatus.WARNING
                message = f"Some API endpoints accessible ({successful_endpoints}/{total_endpoints})"
            else:
                status = HealthStatus.CRITICAL
                message = f"Most API endpoints failed ({successful_endpoints}/{total_endpoints})"
            
            return HealthCheckResult(
                component="api_endpoints",
                status=status,
                message=message,
                details={
                    "endpoints_tested": total_endpoints,
                    "endpoints_successful": successful_endpoints,
                    "results": endpoint_results
                },
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="api_endpoints",
                status=HealthStatus.CRITICAL,
                message=f"API endpoint check failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
    
    async def _check_vietnamese_analysis(self) -> HealthCheckResult:
        """Check Vietnamese content analysis capability"""
        start_time = time.time()
        
        vietnamese_test_prompt = """Phân tích cấu trúc trang web tin tức sau:
<html>
<head><title>Báo VN Test</title></head>
<body>
<h1 class="title">Tin tức mới nhất</h1>
<div class="content">Đây là nội dung bài viết test.</div>
</body>
</html>

Trả về JSON với selector cho tiêu đề và nội dung."""
        
        try:
            test_request = {
                "model": self.model_name,
                "prompt": vietnamese_test_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 200
                }
            }
            
            async with self.session.post(f"{self.base_url}/api/generate", 
                                       json=test_request,
                                       timeout=aiohttp.ClientTimeout(total=120)) as response:
                
                duration_ms = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    response_text = result.get("response", "").strip()
                    
                    # Basic checks for Vietnamese analysis capability
                    vietnamese_indicators = ["tiêu đề", "nội dung", "selector", "class"]
                    found_indicators = sum(1 for indicator in vietnamese_indicators 
                                         if indicator in response_text.lower())
                    
                    if found_indicators >= 2:
                        status = HealthStatus.HEALTHY
                        message = "Vietnamese analysis capability confirmed"
                    elif found_indicators >= 1:
                        status = HealthStatus.WARNING
                        message = "Limited Vietnamese analysis capability"
                    else:
                        status = HealthStatus.CRITICAL
                        message = "Vietnamese analysis capability not detected"
                    
                    return HealthCheckResult(
                        component="vietnamese_analysis",
                        status=status,
                        message=message,
                        details={
                            "response_length": len(response_text),
                            "vietnamese_indicators_found": found_indicators,
                            "response_time_ms": duration_ms,
                            "sample_response": response_text[:200] + "..." if len(response_text) > 200 else response_text
                        },
                        timestamp=datetime.now(),
                        duration_ms=duration_ms
                    )
                else:
                    return HealthCheckResult(
                        component="vietnamese_analysis",
                        status=HealthStatus.CRITICAL,
                        message=f"Vietnamese analysis test failed (status {response.status})",
                        details={"response_status": response.status},
                        timestamp=datetime.now(),
                        duration_ms=duration_ms
                    )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="vietnamese_analysis",
                status=HealthStatus.CRITICAL,
                message=f"Vietnamese analysis check failed: {e}",
                details={"error": str(e)},
                timestamp=datetime.now(),
                duration_ms=duration_ms
            )
    
    def _determine_overall_status(self, checks: List[HealthCheckResult]) -> Tuple[HealthStatus, str]:
        """Determine overall health status from individual checks"""
        if not checks:
            return HealthStatus.UNKNOWN, "No health checks performed"
        
        critical_count = sum(1 for check in checks if check.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for check in checks if check.status == HealthStatus.WARNING)
        healthy_count = sum(1 for check in checks if check.status == HealthStatus.HEALTHY)
        
        if critical_count > 0:
            return HealthStatus.CRITICAL, f"{critical_count} critical issues detected"
        elif warning_count > 0:
            return HealthStatus.WARNING, f"{warning_count} warnings, {healthy_count} healthy"
        else:
            return HealthStatus.HEALTHY, f"All {healthy_count} checks passed"
    
    def _create_health_summary(self, checks: List[HealthCheckResult], total_duration: float) -> Dict[str, Any]:
        """Create health check summary"""
        status_counts = {}
        for status in HealthStatus:
            status_counts[status.value] = sum(1 for check in checks if check.status == status)
        
        avg_duration = sum(check.duration_ms for check in checks) / len(checks) if checks else 0
        
        return {
            "total_checks": len(checks),
            "total_duration_seconds": total_duration,
            "average_check_duration_ms": avg_duration,
            "status_breakdown": status_counts,
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_performance_metrics(self, health: SystemHealth) -> None:
        """Update internal performance metrics"""
        # Record response time
        if health.summary.get("average_check_duration_ms"):
            self._performance_metrics["response_times"].append(health.summary["average_check_duration_ms"])
            
            # Keep only last 100 measurements
            if len(self._performance_metrics["response_times"]) > 100:
                self._performance_metrics["response_times"] = self._performance_metrics["response_times"][-100:]
        
        # Update success/failure tracking
        if health.status == HealthStatus.HEALTHY:
            self._performance_metrics["last_successful_check"] = datetime.now()
            self._performance_metrics["consecutive_failures"] = 0
        else:
            self._performance_metrics["error_count"] += 1
            self._performance_metrics["consecutive_failures"] += 1
    
    def _add_to_history(self, health: SystemHealth) -> None:
        """Add health check result to history"""
        self._health_history.append(health)
        
        # Trim history if it gets too large
        if len(self._health_history) > self._max_history_size:
            self._health_history = self._health_history[-self._max_history_size:]
    
    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check history"""
        recent_history = self._health_history[-limit:] if limit > 0 else self._health_history
        return [health.to_dict() for health in recent_history]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        response_times = self._performance_metrics["response_times"]
        
        metrics = {
            "total_checks": len(self._health_history),
            "error_count": self._performance_metrics["error_count"],
            "consecutive_failures": self._performance_metrics["consecutive_failures"],
            "last_successful_check": self._performance_metrics["last_successful_check"].isoformat() if self._performance_metrics["last_successful_check"] else None
        }
        
        if response_times:
            metrics.update({
                "average_response_time_ms": sum(response_times) / len(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "recent_response_times": response_times[-10:]  # Last 10 measurements
            })
        
        return metrics