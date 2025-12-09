"""
Performance Monitoring Dashboard

This module provides a comprehensive real-time performance monitoring dashboard with:
- Real-time metrics visualization
- Performance trend analysis
- Alert system for performance issues
- Performance optimization recommendations
- Resource usage monitoring
- Customizable dashboards and widgets
"""

from __future__ import annotations

import asyncio
import logging
import statistics
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Awaitable

from .advanced_cache import AdvancedCacheManager
from .memory_profiler import MemoryProfiler
from .performance_benchmarker import PerformanceBenchmarker, PerformanceMetric

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Performance alert"""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    metric_name: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""

    id: str
    title: str
    type: str  # chart, gauge, table, text
    metrics: List[str]
    refresh_interval: int = 30  # seconds
    position: Dict[str, int] = field(default_factory=dict)
    size: Dict[str, int] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """Comprehensive performance report"""

    timestamp: datetime
    duration: timedelta
    total_requests: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float
    throughput: float
    memory_usage_mb: float
    cpu_usage_percent: float
    cache_hit_rate: float
    database_queries: int
    alerts: List[Alert]
    recommendations: List[str]


class AlertManager:
    """Manages performance alerts"""

    def __init__(self) -> None:
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self._alert_id_counter = 0

    def add_alert_rule(
        self,
        metric_name: str,
        threshold: float,
        operator: str = "gt",
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        title: Optional[str] = None,
        description: Optional[str] = None,
        consecutive_violations: int = 1,
    ) -> None:
        """Add alert rule"""
        self.alert_rules[metric_name] = {
            "threshold": threshold,
            "operator": operator,
            "severity": severity,
            "title": title or f"{metric_name} Alert",
            "description": description or f"{metric_name} exceeded threshold",
            "consecutive_violations": consecutive_violations,
            "violation_count": 0,
        }

    def check_metric(self, metric: PerformanceMetric) -> None:
        """Check if metric triggers an alert"""
        if metric.name not in self.alert_rules:
            return

        rule = self.alert_rules[metric.name]
        threshold = rule["threshold"]
        operator = rule["operator"]

        # Check if threshold is violated
        violation = False
        if (
            (operator == "gt" and metric.value > threshold)
            or (operator == "lt" and metric.value < threshold)
            or (operator == "eq" and metric.value == threshold)
            or (operator == "ne" and metric.value != threshold)
        ):
            violation = True

        if violation:
            rule["violation_count"] += 1
            if rule["violation_count"] >= rule["consecutive_violations"]:
                self._trigger_alert(metric, rule)
        else:
            rule["violation_count"] = 0
            self._resolve_alerts(metric.name)

    def _trigger_alert(self, metric: PerformanceMetric, rule: Dict[str, Any]) -> None:
        """Trigger a new alert"""
        alert_id = f"alert_{self._alert_id_counter}"
        self._alert_id_counter += 1

        alert = Alert(
            id=alert_id,
            title=rule["title"],
            description=rule["description"],
            severity=rule["severity"],
            metric_name=metric.name,
            threshold=rule["threshold"],
            current_value=metric.value,
            timestamp=datetime.now(),
            metadata=rule,
        )

        self.alerts[alert_id] = alert

        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.warning(f"Alert triggered: {alert.title} - {alert.description}")

    def _resolve_alerts(self, metric_name: str) -> None:
        """Resolve alerts for a metric"""
        for alert in self.alerts.values():
            if alert.metric_name == metric_name and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()

    def get_active_alerts(self) -> List[Alert]:
        """Get active (unresolved) alerts"""
        return [alert for alert in self.alerts.values() if not alert.resolved]

    def get_all_alerts(self, limit: int = 100) -> List[Alert]:
        """Get all alerts (limited)"""
        all_alerts = sorted(self.alerts.values(), key=lambda a: a.timestamp, reverse=True)
        return all_alerts[:limit]

    def register_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register alert callback"""
        self.alert_callbacks.append(callback)


class MetricsCollector:
    """Collects and aggregates performance metrics"""

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.metrics_history: Dict[str, Deque[PerformanceMetric]] = defaultdict(lambda: deque(maxlen=max_history))
        self.real_time_metrics: Dict[str, float] = {}
        self.metric_callbacks: List[Callable[[PerformanceMetric], None]] = []

    def add_metric(self, metric: PerformanceMetric) -> None:
        """Add a metric to history"""
        self.metrics_history[metric.name].append(metric)
        self.real_time_metrics[metric.name] = metric.value

        # Notify callbacks
        for callback in self.metric_callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"Metric callback error: {e}")

    def get_metric_history(
        self, metric_name: str, since: Optional[datetime] = None, limit: Optional[int] = None
    ) -> List[PerformanceMetric]:
        """Get metric history"""
        history = list(self.metrics_history[metric_name])

        if since:
            history = [m for m in history if m.timestamp >= since]

        if limit:
            history = history[-limit:]

        return history

    def get_metric_stats(self, metric_name: str, window_minutes: int = 5) -> Dict[str, float]:
        """Get metric statistics for a time window"""
        since = datetime.now() - timedelta(minutes=window_minutes)
        metrics = self.get_metric_history(metric_name, since)

        if not metrics:
            return {}

        values = [m.value for m in metrics]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "median": statistics.median(values),
            "p50": statistics.median(values),
            "p90": values[int(len(values) * 0.9)],
            "p95": values[int(len(values) * 0.95)],
            "p99": values[int(len(values) * 0.99)] if len(values) > 100 else max(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0,
            "trend": self._calculate_trend(values),
        }

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (linear regression slope)"""
        if len(values) < 2:
            return 0

        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
        return slope

    def register_callback(self, callback: Callable[[PerformanceMetric], None]):
        """Register metric callback"""
        self.metric_callbacks.append(callback)


class PerformanceDashboard:
    """Main performance monitoring dashboard"""

    def __init__(
        self,
        benchmarker: Optional[PerformanceBenchmarker] = None,
        memory_profiler: Optional[MemoryProfiler] = None,
        cache_manager: Optional[AdvancedCacheManager] = None,
        update_interval: int = 30,
    ):
        """
        Initialize performance dashboard

        Args:
            benchmarker: Performance benchmarker instance
            memory_profiler: Memory profiler instance
            cache_manager: Cache manager instance
            update_interval: Dashboard update interval in seconds
        """
        self.benchmarker = benchmarker
        self.memory_profiler = memory_profiler
        self.cache_manager = cache_manager
        self.update_interval = update_interval

        # Components
        self.alert_manager = AlertManager()
        self.metrics_collector = MetricsCollector()

        # Dashboard configuration
        self.widgets: Dict[str, DashboardWidget] = {}
        self.dashboards: Dict[str, List[str]] = {}  # dashboard_name -> widget_ids

        # State
        self._running = False
        self._update_task: Optional[asyncio.Task[None]] = None
        self._last_update = datetime.now()

        # Setup default widgets and alerts
        self._setup_default_widgets()
        self._setup_default_alerts()

        # Register callbacks
        self.metrics_collector.register_callback(self.alert_manager.check_metric)

    def _setup_default_widgets(self) -> None:
        """Setup default dashboard widgets"""
        default_widgets = [
            DashboardWidget(
                id="request_rate",
                title="Request Rate",
                type="gauge",
                metrics=["request_rate"],
                config={"unit": "req/s", "max": 1000},
            ),
            DashboardWidget(
                id="response_time",
                title="Response Time",
                type="chart",
                metrics=["avg_response_time", "p95_response_time", "p99_response_time"],
                config={"unit": "ms", "chart_type": "line"},
            ),
            DashboardWidget(
                id="memory_usage",
                title="Memory Usage",
                type="chart",
                metrics=["memory_usage_mb"],
                config={"unit": "MB", "chart_type": "area"},
            ),
            DashboardWidget(
                id="cache_performance",
                title="Cache Performance",
                type="table",
                metrics=["cache_hit_rate", "cache_size"],
                config={"columns": ["metric", "value", "unit"]},
            ),
            DashboardWidget(
                id="error_rate",
                title="Error Rate",
                type="gauge",
                metrics=["error_rate"],
                config={"unit": "%", "max": 100},
            ),
            DashboardWidget(
                id="throughput",
                title="Throughput",
                type="chart",
                metrics=["throughput"],
                config={"unit": "ops/sec", "chart_type": "line"},
            ),
        ]

        for widget in default_widgets:
            self.widgets[widget.id] = widget

        # Setup default dashboard
        self.dashboards["main"] = list(self.widgets.keys())

    def _setup_default_alerts(self) -> None:
        """Setup default alert rules"""
        default_alerts = [
            ("response_time", 1000, "gt", AlertSeverity.HIGH),
            ("error_rate", 5.0, "gt", AlertSeverity.HIGH),
            ("memory_usage_mb", 1000, "gt", AlertSeverity.MEDIUM),
            ("cache_hit_rate", 70.0, "lt", AlertSeverity.MEDIUM),
            ("request_rate", 500, "lt", AlertSeverity.LOW),
        ]

        for metric_name, threshold, operator, severity in default_alerts:
            self.alert_manager.add_alert_rule(
                metric_name=metric_name, threshold=threshold, operator=operator, severity=severity
            )

    async def start(self) -> None:
        """Start dashboard monitoring"""
        if self._running:
            return

        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())

        # Start memory profiling if available
        if self.memory_profiler:
            self.memory_profiler.start_monitoring()

        logger.info("Performance dashboard started")

    async def stop(self):
        """Stop dashboard monitoring"""
        if not self._running:
            return

        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        # Stop memory profiling if available
        if self.memory_profiler:
            self.memory_profiler.stop_monitoring()

        logger.info("Performance dashboard stopped")

    async def _update_loop(self):
        """Main update loop"""
        while self._running:
            try:
                await self._collect_metrics()
                self._last_update = datetime.now()
                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dashboard update error: {e}")
                await asyncio.sleep(self.update_interval)

    async def _collect_metrics(self):
        """Collect metrics from all sources"""
        current_time = datetime.now()

        # Collect from benchmarker
        if self.benchmarker:
            summary = self.benchmarker.get_performance_summary()
            await self._add_metric("request_rate", summary.get("request_rate", 0), "req/s")
            await self._add_metric("total_requests", summary.get("total_requests", 0), "count")
            await self._add_metric("avg_response_time", summary.get("avg_response_time", 0), "ms")
            await self._add_metric("p95_response_time", summary.get("p95_response_time", 0), "ms")
            await self._add_metric("p99_response_time", summary.get("p99_response_time", 0), "ms")
            await self._add_metric("error_rate", summary.get("error_rate", 0), "%")
            await self._add_metric("throughput", summary.get("throughput", 0), "ops/sec")

        # Collect from memory profiler
        if self.memory_profiler:
            stats = self.memory_profiler.get_memory_statistics()
            await self._add_metric("memory_usage_mb", stats.get("current_memory_mb", 0), "MB")
            await self._add_metric(
                "memory_trend_mb_per_hour", stats.get("memory_trend_mb_per_hour", 0), "MB/hr"
            )
            await self._add_metric("gc_objects", stats.get("gc_objects", 0), "count")

        # Collect from cache manager
        if self.cache_manager:
            cache_stats = self.cache_manager.get_comprehensive_stats()
            l1_stats = cache_stats.get("l1", {})
            await self._add_metric("cache_hit_rate", l1_stats.get("hit_rate", 0), "%")
            await self._add_metric("cache_size", l1_stats.get("total_entries", 0), "count")
            await self._add_metric(
                "cache_memory_usage_mb", l1_stats.get("memory_usage_mb", 0), "MB"
            )

        # System metrics
        try:
            import psutil

            process = psutil.Process()
            await self._add_metric("cpu_percent", process.cpu_percent(), "%")
            await self._add_metric("open_files", len(process.open_files()), "count")
            await self._add_metric("threads", process.num_threads(), "count")
        except ImportError:
            pass

    async def _add_metric(self, name: str, value: float, unit: str):
        """Add metric to collector"""
        metric = PerformanceMetric(name=name, value=value, unit=unit, timestamp=datetime.now())
        self.metrics_collector.add_metric(metric)

    def get_dashboard_data(self, dashboard_name: str = "main") -> Dict[str, Any]:
        """Get dashboard data for frontend"""
        if dashboard_name not in self.dashboards:
            return {"error": f"Dashboard '{dashboard_name}' not found"}

        widget_ids = self.dashboards[dashboard_name]
        widget_data = {}

        for widget_id in widget_ids:
            if widget_id not in self.widgets:
                continue

            widget = self.widgets[widget_id]
            widget_data[widget_id] = {
                "id": widget.id,
                "title": widget.title,
                "type": widget.type,
                "config": widget.config,
                "data": self._get_widget_data(widget),
            }

        return {
            "dashboard": dashboard_name,
            "widgets": widget_data,
            "last_update": self._last_update.isoformat(),
            "alerts": self._get_active_alerts_summary(),
        }

    def _get_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for a specific widget"""
        data = {}

        for metric_name in widget.metrics:
            stats = self.metrics_collector.get_metric_stats(metric_name, window_minutes=30)
            history = self.metrics_collector.get_metric_history(metric_name, limit=100)

            data[metric_name] = {
                "current": self.metrics_collector.real_time_metrics.get(metric_name, 0),
                "stats": stats,
                "history": [
                    {"timestamp": m.timestamp.isoformat(), "value": m.value} for m in history
                ],
            }

        return data

    def _get_active_alerts_summary(self) -> Dict[str, Any]:
        """Get summary of active alerts"""
        active_alerts = self.alert_manager.get_active_alerts()

        return {
            "count": len(active_alerts),
            "severity_counts": {
                severity.value: len([a for a in active_alerts if a.severity == severity])
                for severity in AlertSeverity
            },
            "recent": [
                {
                    "id": alert.id,
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "timestamp": alert.timestamp.isoformat(),
                }
                for alert in sorted(active_alerts, key=lambda a: a.timestamp, reverse=True)[:10]
            ],
        }

    async def generate_performance_report(self, duration_minutes: int = 60) -> PerformanceReport:
        """Generate comprehensive performance report"""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=duration_minutes)

        # Collect metrics for the period
        request_metrics = self.metrics_collector.get_metric_history(
            "avg_response_time", since=start_time
        )
        memory_metrics = self.metrics_collector.get_metric_history(
            "memory_usage_mb", since=start_time
        )
        error_metrics = self.metrics_collector.get_metric_history("error_rate", since=start_time)
        throughput_metrics = self.metrics_collector.get_metric_history(
            "throughput", since=start_time
        )
        cache_metrics = self.metrics_collector.get_metric_history(
            "cache_hit_rate", since=start_time
        )

        # Calculate aggregates
        total_requests = len(request_metrics)
        avg_response_time = (
            statistics.mean([m.value for m in request_metrics]) if request_metrics else 0
        )
        p95_response_time = (
            statistics.quantiles([m.value for m in request_metrics], n=20)[18]
            if len(request_metrics) > 20
            else 0
        )
        p99_response_time = (
            statistics.quantiles([m.value for m in request_metrics], n=100)[98]
            if len(request_metrics) > 100
            else 0
        )
        error_rate = statistics.mean([m.value for m in error_metrics]) if error_metrics else 0
        throughput = (
            statistics.mean([m.value for m in throughput_metrics]) if throughput_metrics else 0
        )
        memory_usage = statistics.mean([m.value for m in memory_metrics]) if memory_metrics else 0
        cache_hit_rate = statistics.mean([m.value for m in cache_metrics]) if cache_metrics else 0

        # Get alerts for the period
        period_alerts = [
            alert for alert in self.alert_manager.get_all_alerts() if alert.timestamp >= start_time
        ]

        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_response_time, error_rate, memory_usage, cache_hit_rate
        )

        return PerformanceReport(
            timestamp=end_time,
            duration=end_time - start_time,
            total_requests=int(total_requests),
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            error_rate=error_rate,
            throughput=throughput,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=0,  # Would need to collect this metric
            cache_hit_rate=cache_hit_rate,
            database_queries=0,  # Would need to collect this metric
            alerts=period_alerts,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        avg_response_time: float,
        error_rate: float,
        memory_usage: float,
        cache_hit_rate: float,
    ) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        if avg_response_time > 500:
            recommendations.append(
                "High response times detected. Consider optimizing database queries or adding caching."
            )

        if error_rate > 1.0:
            recommendations.append(
                f"Elevated error rate ({error_rate:.1f}%). Review application logs for errors."
            )

        if memory_usage > 1000:
            recommendations.append(
                "High memory usage detected. Check for memory leaks or optimize data structures."
            )

        if cache_hit_rate < 70:
            recommendations.append(
                f"Low cache hit rate ({cache_hit_rate:.1f}%). Consider adjusting cache TTL or size."
            )

        # Additional recommendations based on alerts
        active_alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        high_alerts = [a for a in active_alerts if a.severity == AlertSeverity.HIGH]

        if critical_alerts:
            recommendations.append(
                f"Critical alerts require immediate attention: {len(critical_alerts)} active."
            )

        if high_alerts:
            recommendations.append(
                f"High severity alerts need investigation: {len(high_alerts)} active."
            )

        if not recommendations:
            recommendations.append(
                "Performance looks good! All metrics are within acceptable ranges."
            )

        return recommendations

    def add_widget(self, widget: DashboardWidget, dashboard_name: str = "main"):
        """Add widget to dashboard"""
        self.widgets[widget.id] = widget
        if dashboard_name not in self.dashboards:
            self.dashboards[dashboard_name] = []
        self.dashboards[dashboard_name].append(widget.id)

    def remove_widget(self, widget_id: str, dashboard_name: str = "main"):
        """Remove widget from dashboard"""
        if widget_id in self.widgets:
            del self.widgets[widget_id]
        if dashboard_name in self.dashboards and widget_id in self.dashboards[dashboard_name]:
            self.dashboards[dashboard_name].remove(widget_id)

    def get_alerts(self, active_only: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alerts"""
        if active_only:
            alerts = self.alert_manager.get_active_alerts()
        else:
            alerts = self.alert_manager.get_all_alerts(limit)

        return [
            {
                **asdict(alert),
                "timestamp": alert.timestamp.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "severity": alert.severity.value,
            }
            for alert in alerts
        ]


# Global dashboard instance
_global_dashboard: Optional[PerformanceDashboard] = None


def get_performance_dashboard() -> PerformanceDashboard:
    """Get or create global performance dashboard"""
    global _global_dashboard
    if _global_dashboard is None:
        _global_dashboard = PerformanceDashboard()
    return _global_dashboard


def create_performance_dashboard(**kwargs) -> PerformanceDashboard:
    """Create new performance dashboard instance"""
    return PerformanceDashboard(**kwargs)
