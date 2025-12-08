"""
Comprehensive Performance Monitoring and Metrics Collection

This module provides:
- Real-time performance metrics collection
- Resource usage monitoring
- Custom metrics tracking
- Performance alerts and notifications
- Historical data analysis
- Export capabilities for metrics
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

import psutil

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class MetricValue:
    """Single metric value with timestamp"""

    value: Union[int, float, str]
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceMetric:
    """Performance metric definition"""

    name: str
    description: str
    unit: str
    metric_type: str  # counter, gauge, histogram, timer
    values: Deque[MetricValue] = field(default_factory=lambda: deque(maxlen=1000))
    aggregation: str = "avg"  # avg, sum, min, max
    alert_threshold: Optional[float] = None
    alert_operator: str = ">"  # >, <, >=, <=, ==, !=

    def add_value(self, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
        """Add metric value"""
        metric_value = MetricValue(value=value, tags=tags or {})
        self.values.append(metric_value)

        # Check alert threshold
        if self.alert_threshold is not None:
            self._check_alert(metric_value)

    def _check_alert(self, metric_value: MetricValue):
        """Check if metric triggers alert"""
        if not isinstance(metric_value.value, (int, float)):
            return

        trigger = False
        if self.alert_operator == ">":
            trigger = metric_value.value > self.alert_threshold
        elif self.alert_operator == "<":
            trigger = metric_value.value < self.alert_threshold
        elif self.alert_operator == ">=":
            trigger = metric_value.value >= self.alert_threshold
        elif self.alert_operator == "<=":
            trigger = metric_value.value <= self.alert_threshold
        elif self.alert_operator == "==":
            trigger = metric_value.value == self.alert_threshold
        elif self.alert_operator == "!=":
            trigger = metric_value.value != self.alert_threshold

        if trigger:
            alert_msg = (
                f"Performance alert: {self.name} = {metric_value.value} "
                f"{self.unit} {self.alert_operator} {self.alert_threshold} {self.unit}"
            )
            logger.warning(alert_msg)

    def get_stats(self) -> Dict[str, Any]:
        """Get metric statistics"""
        if not self.values:
            return {}

        numeric_values = [v.value for v in self.values if isinstance(v.value, (int, float))]

        if not numeric_values:
            return {"count": len(self.values)}

        return {
            "count": len(numeric_values),
            "min": min(numeric_values),
            "max": max(numeric_values),
            "avg": sum(numeric_values) / len(numeric_values),
            "latest": numeric_values[-1] if numeric_values else None,
            "sum": sum(numeric_values),
        }


class MetricsCollector:
    """Central metrics collection system"""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._metrics: Dict[str, PerformanceMetric] = {}
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()

        # Built-in metrics
        self._register_builtin_metrics()

    def _register_builtin_metrics(self):
        """Register built-in performance metrics"""
        self.register_metric(
            "cpu_usage_percent",
            "CPU usage percentage",
            "percent",
            "gauge",
            alert_threshold=90.0,
            alert_operator=">",
        )

        self.register_metric(
            "memory_usage_mb",
            "Memory usage in MB",
            "MB",
            "gauge",
            alert_threshold=1000.0,
            alert_operator=">",
        )

        self.register_metric("response_time", "Operation response time", "ms", "timer")

        self.register_metric(
            "error_rate",
            "Error rate percentage",
            "percent",
            "gauge",
            alert_threshold=5.0,
            alert_operator=">",
        )

        self.register_metric("request_rate", "Requests per second", "rps", "gauge")

    def register_metric(
        self,
        name: str,
        description: str,
        unit: str,
        metric_type: str,
        aggregation: str = "avg",
        alert_threshold: Optional[float] = None,
        alert_operator: str = ">",
    ) -> PerformanceMetric:
        """Register a new metric"""
        with self._lock:
            if name in self._metrics:
                logger.warning(f"Metric {name} already registered, updating...")
                metric = self._metrics[name]
                metric.description = description
                metric.unit = unit
                metric.metric_type = metric_type
                metric.aggregation = aggregation
                metric.alert_threshold = alert_threshold
                metric.alert_operator = alert_operator
            else:
                metric = PerformanceMetric(
                    name=name,
                    description=description,
                    unit=unit,
                    metric_type=metric_type,
                    aggregation=aggregation,
                    alert_threshold=alert_threshold,
                    alert_operator=alert_operator,
                )
                self._metrics[name] = metric

            return metric

    def increment_counter(
        self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None
    ):
        """Increment a counter metric"""
        with self._lock:
            self._counters[name] += value

        if name in self._metrics:
            self._metrics[name].add_value(self._counters[name], tags)

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric value"""
        with self._lock:
            self._gauges[name] = value

        if name in self._metrics:
            self._metrics[name].add_value(value, tags)

    def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timer metric value"""
        with self._lock:
            self._timers[name].append(duration)
            # Keep only recent values
            if len(self._timers[name]) > self.max_history:
                self._timers[name] = self._timers[name][-self.max_history :]

        if name in self._metrics:
            self._metrics[name].add_value(duration * 1000, tags)  # Convert to ms

    def get_metric(self, name: str) -> Optional[PerformanceMetric]:
        """Get metric by name"""
        return self._metrics.get(name)

    def get_all_metrics(self) -> Dict[str, PerformanceMetric]:
        """Get all registered metrics"""
        return dict(self._metrics)

    def get_metric_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics for specific metric"""
        metric = self._metrics.get(name)
        if metric:
            return metric.get_stats()
        return {}

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {
            "total_metrics": len(self._metrics),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "metric_stats": {},
        }

        for name, metric in self._metrics.items():
            stats = metric.get_stats()
            if stats:
                summary["metric_stats"][name] = {
                    "type": metric.metric_type,
                    "unit": metric.unit,
                    "latest_value": stats.get("latest"),
                    "count": stats.get("count"),
                    "avg": stats.get("avg"),
                    "min": stats.get("min"),
                    "max": stats.get("max"),
                }

        return summary

    def reset_metrics(self, pattern: Optional[str] = None):
        """Reset metrics (all or matching pattern)"""
        with self._lock:
            if pattern:
                # Reset matching metrics
                for name in list(self._metrics.keys()):
                    if pattern in name:
                        if name in self._counters:
                            self._counters[name] = 0.0
                        if name in self._gauges:
                            del self._gauges[name]
                        if name in self._timers:
                            self._timers[name].clear()
                        self._metrics[name].values.clear()
            else:
                # Reset all metrics
                self._counters.clear()
                self._gauges.clear()
                self._timers.clear()
                for metric in self._metrics.values():
                    metric.values.clear()


class ResourceMonitor:
    """System resource monitoring"""

    def __init__(self, metrics_collector: MetricsCollector, interval: float = 5.0):
        self.metrics_collector = metrics_collector
        self.interval = interval
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._process = psutil.Process()

    def start(self):
        """Start resource monitoring"""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="ResourceMonitor"
        )
        self._monitor_thread.start()
        logger.info(f"Resource monitoring started (interval: {self.interval}s)")

    def stop(self):
        """Stop resource monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Resource monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self._collect_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                time.sleep(self.interval)

    def _collect_metrics(self):
        """Collect system resource metrics"""
        try:
            # CPU usage
            cpu_percent = self._process.cpu_percent()
            self.metrics_collector.set_gauge("cpu_usage_percent", cpu_percent)

            # Memory usage
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            self.metrics_collector.set_gauge("memory_usage_mb", memory_mb)

            # Memory percent
            memory_percent = self._process.memory_percent()
            self.metrics_collector.set_gauge("memory_usage_percent", memory_percent)

            # System memory
            system_memory = psutil.virtual_memory()
            self.metrics_collector.set_gauge(
                "system_memory_available_mb", system_memory.available / 1024 / 1024
            )
            self.metrics_collector.set_gauge("system_memory_usage_percent", system_memory.percent)

            # File descriptors
            if hasattr(self._process, "num_fds"):
                self.metrics_collector.set_gauge("open_file_descriptors", self._process.num_fds())

            # Threads
            if hasattr(self._process, "num_threads"):
                self.metrics_collector.set_gauge("thread_count", self._process.num_threads())

            # Disk I/O
            if hasattr(self._process, "io_counters"):
                io_counters = self._process.io_counters()
                self.metrics_collector.set_gauge("disk_read_bytes", io_counters.read_bytes)
                self.metrics_collector.set_gauge("disk_write_bytes", io_counters.write_bytes)

            # Network I/O (system-wide)
            net_io = psutil.net_io_counters()
            self.metrics_collector.set_gauge("network_bytes_sent", net_io.bytes_sent)
            self.metrics_collector.set_gauge("network_bytes_recv", net_io.bytes_recv)

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Cannot collect resource metrics: {e}")
        except Exception as e:
            logger.error(f"Resource collection error: {e}")

    def get_current_stats(self) -> Dict[str, Any]:
        """Get current resource statistics"""
        try:
            memory_info = self._process.memory_info()
            return {
                "cpu_percent": self._process.cpu_percent(),
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_vms_mb": memory_info.vms / 1024 / 1024,
                "memory_percent": self._process.memory_percent(),
                "threads": (
                    self._process.num_threads() if hasattr(self._process, "num_threads") else 0
                ),
                "fds": self._process.num_fds() if hasattr(self._process, "num_fds") else 0,
            }
        except Exception as e:
            logger.error(f"Error getting resource stats: {e}")
            return {}


class PerformanceProfiler:
    """Performance profiler for operations"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._active_profiles: Dict[str, float] = {}

    @asynccontextmanager
    async def profile(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for profiling operations"""
        start_time = time.time()
        operation_id = f"{operation_name}_{start_time}"

        try:
            self._active_profiles[operation_id] = start_time
            yield
        except Exception:
            # Record error
            self.metrics_collector.increment_counter(f"{operation_name}_errors", tags=tags)
            raise
        finally:
            duration = time.time() - start_time
            if operation_id in self._active_profiles:
                del self._active_profiles[operation_id]

            # Record timing
            self.metrics_collector.record_timer(operation_name, duration, tags)

            # Record successful operation
            self.metrics_collector.increment_counter(f"{operation_name}_success", tags=tags)

    def get_active_operations(self) -> List[str]:
        """Get list of currently profiled operations"""
        return list(self._active_profiles.keys())

    def get_long_running_operations(
        self, threshold_seconds: float = 10.0
    ) -> List[Tuple[str, float]]:
        """Get operations running longer than threshold"""
        current_time = time.time()
        long_running = []

        for operation_id, start_time in self._active_profiles.items():
            duration = current_time - start_time
            if duration > threshold_seconds:
                long_running.append((operation_id, duration))

        return sorted(long_running, key=lambda x: x[1], reverse=True)


class PerformanceMonitor:
    """Main performance monitoring system"""

    def __init__(
        self,
        metrics_history: int = 1000,
        resource_interval: float = 5.0,
        export_interval: float = 60.0,
    ):
        self.metrics_collector = MetricsCollector(metrics_history)
        self.resource_monitor = ResourceMonitor(self.metrics_collector, resource_interval)
        self.profiler = PerformanceProfiler(self.metrics_collector)

        self.export_interval = export_interval
        self._export_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._export_task: Optional[asyncio.Task] = None
        self._running = False

    def start(self):
        """Start performance monitoring"""
        self.resource_monitor.start()
        self._running = True

        # Start export task if callbacks are registered
        if self._export_callbacks:
            self._start_export_task()

        logger.info("Performance monitoring started")

    def stop(self):
        """Stop performance monitoring"""
        self._running = False
        self.resource_monitor.stop()

        if self._export_task:
            self._export_task.cancel()
            try:
                # Try to wait for task to finish
                if hasattr(self._export_task, "result"):
                    self._export_task.result(timeout=5.0)
            except:
                pass

        logger.info("Performance monitoring stopped")

    async def _start_export_task(self):
        """Start periodic export task"""
        self._export_task = asyncio.create_task(self._export_loop())

    async def _export_loop(self):
        """Periodic metrics export loop"""
        while self._running:
            try:
                await asyncio.sleep(self.export_interval)
                await self._export_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics export error: {e}")

    async def _export_metrics(self):
        """Export metrics to registered callbacks"""
        if not self._export_callbacks:
            return

        summary = self.metrics_collector.get_summary()
        resource_stats = self.resource_monitor.get_current_stats()

        export_data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": summary,
            "resources": resource_stats,
        }

        for callback in self._export_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(export_data)
                else:
                    callback(export_data)
            except Exception as e:
                logger.error(f"Export callback error: {e}")

    def add_export_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add metrics export callback"""
        self._export_callbacks.append(callback)

        # Start export task if not running
        if self._running and not self._export_task:
            asyncio.create_task(self._start_export_task())

    @asynccontextmanager
    async def monitor(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """Monitor operation performance"""
        async with self.profiler.profile(operation_name, tags):
            yield

    def track_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration: float,
        response_size: Optional[int] = None,
    ):
        """Track HTTP request metrics"""
        tags = {"endpoint": endpoint, "method": method, "status": str(status_code)}

        # Request count
        self.metrics_collector.increment_counter("http_requests_total", tags=tags)

        # Request duration
        self.metrics_collector.record_timer("http_request_duration", duration, tags=tags)

        # Response size
        if response_size:
            self.metrics_collector.set_gauge("http_response_size", response_size, tags=tags)

        # Error tracking
        if status_code >= 400:
            self.metrics_collector.increment_counter("http_errors_total", tags=tags)

    def track_database_operation(
        self, operation: str, table: str, duration: float, rows_affected: Optional[int] = None
    ):
        """Track database operation metrics"""
        tags = {"operation": operation, "table": table}

        # Operation count
        self.metrics_collector.increment_counter("db_operations_total", tags=tags)

        # Operation duration
        self.metrics_collector.record_timer("db_operation_duration", duration, tags=tags)

        # Rows affected
        if rows_affected is not None:
            self.metrics_collector.set_gauge("db_rows_affected", rows_affected, tags=tags)

    def track_cache_operation(
        self,
        cache_name: str,
        operation: str,  # hit, miss, set, delete
        duration: Optional[float] = None,
    ):
        """Track cache operation metrics"""
        tags = {"cache": cache_name, "operation": operation}

        self.metrics_collector.increment_counter("cache_operations_total", tags=tags)

        if duration is not None:
            self.metrics_collector.record_timer("cache_operation_duration", duration, tags=tags)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics_collector.get_summary(),
            "resources": self.resource_monitor.get_current_stats(),
            "active_operations": self.profiler.get_active_operations(),
            "long_running": self.profiler.get_long_running_operations(),
        }

    def export_to_file(self, filename: str):
        """Export current metrics to file"""
        data = {
            "export_time": datetime.now().isoformat(),
            "metrics": self.metrics_collector.get_summary(),
            "resources": self.resource_monitor.get_current_stats(),
        }

        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Metrics exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def monitor_performance(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for monitoring function performance"""
    monitor = get_performance_monitor()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                async with monitor.monitor(operation_name, tags):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    monitor.metrics_collector.record_timer(operation_name, duration, tags)
                    monitor.metrics_collector.increment_counter(f"{operation_name}_success", tags)
                    return result
                except Exception:
                    duration = time.time() - start_time
                    monitor.metrics_collector.record_timer(operation_name, duration, tags)
                    monitor.metrics_collector.increment_counter(f"{operation_name}_errors", tags)
                    raise

            return sync_wrapper

    return decorator


# Utility functions for common monitoring tasks
async def monitor_function_performance(
    func: Callable,
    *args,
    operation_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Any:
    """Monitor function performance"""
    if operation_name is None:
        operation_name = f"{func.__module__}.{func.__qualname__}"

    monitor = get_performance_monitor()
    async with monitor.monitor(operation_name, tags):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)


class MetricsExporter:
    """Base class for metrics exporters"""

    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor

    async def export(self, data: Dict[str, Any]):
        """Export metrics data"""
        raise NotImplementedError


class JSONFileExporter(MetricsExporter):
    """Export metrics to JSON file"""

    def __init__(self, monitor: PerformanceMonitor, filename: str):
        super().__init__(monitor)
        self.filename = filename

    async def export(self, data: Dict[str, Any]):
        """Export to JSON file"""
        try:
            with open(self.filename, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to export metrics to {self.filename}: {e}")


def setup_monitoring(
    enable_resource_monitoring: bool = True,
    resource_interval: float = 5.0,
    export_file: Optional[str] = None,
) -> PerformanceMonitor:
    """Setup performance monitoring with optional exporters"""
    monitor = get_performance_monitor()

    if enable_resource_monitoring:
        monitor.resource_monitor.interval = resource_interval

    if export_file:
        exporter = JSONFileExporter(monitor, export_file)
        monitor.add_export_callback(exporter.export)

    monitor.start()
    return monitor
