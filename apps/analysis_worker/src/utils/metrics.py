"""
Prometheus Metrics Integration
Performance tracking and monitoring for analysis worker
Author: James (Dev Agent)
Date: 2025-08-12
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Counter as TypingCounter
from collections import defaultdict, Counter, deque
from dataclasses import dataclass, field
import psutil
import asyncio

# Prometheus metrics (will be mocked if not available)
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes for development
    class Counter:
        def __init__(self, *args, **kwargs):
            self._value = 0
        def inc(self, amount=1):
            self._value += amount
        def labels(self, **kwargs):
            return self
    
    class Histogram:
        def __init__(self, *args, **kwargs):
            self._observations = []
        def observe(self, value):
            self._observations.append(value)
        def time(self):
            return HistogramTimer(self)
        def labels(self, **kwargs):
            return self
    
    class Gauge:
        def __init__(self, *args, **kwargs):
            self._value = 0
        def set(self, value):
            self._value = value
        def inc(self, amount=1):
            self._value += amount
        def dec(self, amount=1):
            self._value -= amount
        def labels(self, **kwargs):
            return self
    
    class Summary:
        def __init__(self, *args, **kwargs):
            self._observations = []
        def observe(self, value):
            self._observations.append(value)
        def time(self):
            return SummaryTimer(self)
        def labels(self, **kwargs):
            return self
    
    class Info:
        def __init__(self, *args, **kwargs):
            self._info = {}
        def info(self, data):
            self._info = data
        def labels(self, **kwargs):
            return self
    
    class CollectorRegistry:
        pass
    
    def generate_latest(registry=None):
        return "# Prometheus metrics not available\n"
    
    CONTENT_TYPE_LATEST = "text/plain"


class HistogramTimer:
    """Timer context for histogram"""
    def __init__(self, histogram):
        self.histogram = histogram
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.histogram.observe(duration)


class SummaryTimer:
    """Timer context for summary"""
    def __init__(self, summary):
        self.summary = summary
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.summary.observe(duration)


@dataclass
class PerformanceStats:
    """Performance statistics data structure"""
    operation_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    error_types: TypingCounter = field(default_factory=Counter)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100
    
    @property
    def average_duration(self) -> float:
        """Calculate average duration"""
        if self.total_calls == 0:
            return 0.0
        return self.total_duration / self.total_calls
    
    @property
    def recent_average_duration(self) -> float:
        """Calculate average of recent durations"""
        if not self.recent_durations:
            return 0.0
        return sum(self.recent_durations) / len(self.recent_durations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "operation_name": self.operation_name,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": round(self.success_rate, 2),
            "average_duration": round(self.average_duration, 4),
            "recent_average_duration": round(self.recent_average_duration, 4),
            "min_duration": self.min_duration if self.min_duration != float('inf') else 0.0,
            "max_duration": self.max_duration,
            "error_types": dict(self.error_types)
        }


class AnalysisWorkerMetrics:
    """
    Comprehensive metrics collection for analysis worker
    Includes Prometheus metrics and custom performance tracking
    """
    
    def __init__(self, worker_id: str = "default"):
        """Initialize metrics collector"""
        self.worker_id = worker_id
        self.logger = logging.getLogger(__name__)
        
        # Metrics registry
        self.registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None
        
        # Performance tracking
        self.performance_stats: Dict[str, PerformanceStats] = defaultdict(
            lambda: PerformanceStats("")
        )
        self.stats_lock = threading.Lock()
        
        # System metrics tracking
        self.system_stats = {
            "start_time": datetime.now(),
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_usage_mb": 0.0,
            "disk_usage_percent": 0.0
        }
        
        # Initialize Prometheus metrics
        self._init_prometheus_metrics()
        
        # Start background monitoring
        self._monitoring_active = True
        self._monitoring_task = None
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        labels = ['worker_id', 'operation', 'status']
        
        # Domain analysis metrics
        self.analysis_requests_total = Counter(
            'analysis_requests_total',
            'Total number of analysis requests',
            ['worker_id', 'domain', 'trigger_type'],
            registry=self.registry
        )
        
        self.analysis_duration_seconds = Histogram(
            'analysis_duration_seconds',
            'Duration of domain analysis operations',
            ['worker_id', 'domain', 'status'],
            buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
            registry=self.registry
        )
        
        self.gwen3_requests_total = Counter(
            'gwen3_requests_total',
            'Total GWEN-3 model requests',
            ['worker_id', 'model', 'status'],
            registry=self.registry
        )
        
        self.gwen3_duration_seconds = Histogram(
            'gwen3_duration_seconds',
            'Duration of GWEN-3 model calls',
            ['worker_id', 'model'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
            registry=self.registry
        )
        
        # Queue metrics
        self.queue_depth_gauge = Gauge(
            'queue_depth',
            'Current queue depth',
            ['worker_id', 'queue_type'],
            registry=self.registry
        )
        
        self.queue_processing_rate = Gauge(
            'queue_processing_rate',
            'Queue processing rate (jobs per minute)',
            ['worker_id'],
            registry=self.registry
        )
        
        # Database metrics
        self.database_operations_total = Counter(
            'database_operations_total',
            'Total database operations',
            ['worker_id', 'operation', 'status'],
            registry=self.registry
        )
        
        self.database_duration_seconds = Histogram(
            'database_duration_seconds',
            'Duration of database operations',
            ['worker_id', 'operation'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
            registry=self.registry
        )
        
        # System metrics
        self.worker_cpu_percent = Gauge(
            'worker_cpu_percent',
            'Worker CPU usage percentage',
            ['worker_id'],
            registry=self.registry
        )
        
        self.worker_memory_percent = Gauge(
            'worker_memory_percent',
            'Worker memory usage percentage',
            ['worker_id'],
            registry=self.registry
        )
        
        self.worker_memory_mb = Gauge(
            'worker_memory_mb',
            'Worker memory usage in MB',
            ['worker_id'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors by type',
            ['worker_id', 'error_type', 'operation'],
            registry=self.registry
        )
        
        # Template metrics
        self.template_confidence_score = Histogram(
            'template_confidence_score',
            'Template confidence scores',
            ['worker_id', 'domain'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # Vietnamese content metrics
        self.vietnamese_content_ratio = Histogram(
            'vietnamese_content_ratio',
            'Vietnamese content ratio detected',
            ['worker_id', 'domain'],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # Worker info
        self.worker_info = Info(
            'worker_info',
            'Information about analysis worker',
            registry=self.registry
        )
        
        # Set worker info
        self.worker_info.info({
            'worker_id': self.worker_id,
            'start_time': self.system_stats['start_time'].isoformat(),
            'prometheus_available': str(PROMETHEUS_AVAILABLE)
        })
    
    def record_analysis_request(self, domain: str, trigger_type: str = "web_interface"):
        """Record domain analysis request"""
        self.analysis_requests_total.labels(
            worker_id=self.worker_id,
            domain=domain,
            trigger_type=trigger_type
        ).inc()
    
    def record_analysis_duration(self, domain: str, duration: float, status: str = "success"):
        """Record analysis duration"""
        self.analysis_duration_seconds.labels(
            worker_id=self.worker_id,
            domain=domain,
            status=status
        ).observe(duration)
        
        # Update performance stats
        operation_name = f"domain_analysis_{domain}"
        self._update_performance_stats(operation_name, duration, status == "success")
    
    def record_gwen3_request(self, model: str, duration: float, status: str = "success"):
        """Record GWEN-3 model request"""
        self.gwen3_requests_total.labels(
            worker_id=self.worker_id,
            model=model,
            status=status
        ).inc()
        
        self.gwen3_duration_seconds.labels(
            worker_id=self.worker_id,
            model=model
        ).observe(duration)
        
        # Update performance stats
        self._update_performance_stats("gwen3_request", duration, status == "success")
    
    def record_queue_depth(self, queue_type: str, depth: int):
        """Record queue depth"""
        self.queue_depth_gauge.labels(
            worker_id=self.worker_id,
            queue_type=queue_type
        ).set(depth)
    
    def record_database_operation(self, operation: str, duration: float, status: str = "success"):
        """Record database operation"""
        self.database_operations_total.labels(
            worker_id=self.worker_id,
            operation=operation,
            status=status
        ).inc()
        
        self.database_duration_seconds.labels(
            worker_id=self.worker_id,
            operation=operation
        ).observe(duration)
        
        # Update performance stats
        operation_name = f"database_{operation}"
        self._update_performance_stats(operation_name, duration, status == "success")
    
    def record_error(self, error_type: str, operation: str):
        """Record error occurrence"""
        self.errors_total.labels(
            worker_id=self.worker_id,
            error_type=error_type,
            operation=operation
        ).inc()
    
    def record_template_confidence(self, domain: str, confidence: float):
        """Record template confidence score"""
        self.template_confidence_score.labels(
            worker_id=self.worker_id,
            domain=domain
        ).observe(confidence)
    
    def record_vietnamese_content_ratio(self, domain: str, ratio: float):
        """Record Vietnamese content ratio"""
        self.vietnamese_content_ratio.labels(
            worker_id=self.worker_id,
            domain=domain
        ).observe(ratio)
    
    def _update_performance_stats(self, operation: str, duration: float, success: bool, error_type: Optional[str] = None):
        """Update internal performance statistics"""
        with self.stats_lock:
            stats = self.performance_stats[operation]
            stats.operation_name = operation
            stats.total_calls += 1
            stats.total_duration += duration
            stats.recent_durations.append(duration)
            
            if success:
                stats.successful_calls += 1
            else:
                stats.failed_calls += 1
                if error_type:
                    stats.error_types[error_type] += 1
            
            # Update min/max duration
            stats.min_duration = min(stats.min_duration, duration)
            stats.max_duration = max(stats.max_duration, duration)
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            # CPU percentage
            cpu_percent = psutil.cpu_percent()
            self.system_stats["cpu_percent"] = cpu_percent
            self.worker_cpu_percent.labels(worker_id=self.worker_id).set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_mb = memory.used / (1024 * 1024)
            
            self.system_stats["memory_percent"] = memory_percent
            self.system_stats["memory_usage_mb"] = memory_mb
            
            self.worker_memory_percent.labels(worker_id=self.worker_id).set(memory_percent)
            self.worker_memory_mb.labels(worker_id=self.worker_id).set(memory_mb)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.system_stats["disk_usage_percent"] = disk_percent
            
        except Exception as e:
            self.logger.error(f"Failed to update system metrics: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        with self.stats_lock:
            summary = {}
            for operation, stats in self.performance_stats.items():
                summary[operation] = stats.to_dict()
        
        # Add system stats
        uptime = datetime.now() - self.system_stats["start_time"]
        summary["system"] = {
            **self.system_stats,
            "uptime_seconds": uptime.total_seconds(),
            "start_time": self.system_stats["start_time"].isoformat()
        }
        
        return summary
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        if PROMETHEUS_AVAILABLE and self.registry:
            return generate_latest(self.registry)
        else:
            return "# Prometheus metrics not available\n"
    
    def reset_metrics(self):
        """Reset all metrics (for testing)"""
        with self.stats_lock:
            self.performance_stats.clear()
        
        self.system_stats = {
            "start_time": datetime.now(),
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_usage_mb": 0.0,
            "disk_usage_percent": 0.0
        }
    
    async def start_monitoring(self, interval: float = 30.0):
        """Start background system monitoring"""
        self._monitoring_active = True
        
        async def monitor_loop():
            while self._monitoring_active:
                try:
                    self.update_system_metrics()
                    await asyncio.sleep(interval)
                except Exception as e:
                    self.logger.error(f"Monitoring loop error: {e}")
                    await asyncio.sleep(interval)
        
        self._monitoring_task = asyncio.create_task(monitor_loop())
        self.logger.info(f"Started system monitoring with {interval}s interval")
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped system monitoring")
    
    def create_operation_timer(self, operation: str):
        """Create timer context for operation timing"""
        return OperationTimer(self, operation)


class OperationTimer:
    """Context manager for timing operations"""
    
    def __init__(self, metrics: AnalysisWorkerMetrics, operation: str):
        self.metrics = metrics
        self.operation = operation
        self.start_time = None
        self.success = True
        self.error_type = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            
            if exc_type:
                self.success = False
                self.error_type = exc_type.__name__
            
            self.metrics._update_performance_stats(
                self.operation, duration, self.success, self.error_type
            )
    
    def mark_error(self, error_type: str):
        """Mark operation as failed with specific error type"""
        self.success = False
        self.error_type = error_type


# Global metrics instance
_metrics_instance: Optional[AnalysisWorkerMetrics] = None


def get_metrics(worker_id: str = "default") -> AnalysisWorkerMetrics:
    """Get or create global metrics instance"""
    global _metrics_instance
    
    if _metrics_instance is None:
        _metrics_instance = AnalysisWorkerMetrics(worker_id)
    
    return _metrics_instance


def reset_metrics():
    """Reset global metrics instance"""
    global _metrics_instance
    _metrics_instance = None