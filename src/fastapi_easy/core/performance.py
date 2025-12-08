"""Performance monitoring and metrics for FastAPI-Easy"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricData:
    """Metric data point"""

    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceStats:
    """Performance statistics"""

    total_requests: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    min_duration: float = float("inf")
    max_duration: float = 0.0
    error_count: int = 0
    last_requests: deque = field(default_factory=lambda: deque(maxlen=100))


class PerformanceMonitor:
    """Performance monitoring for FastAPI-Easy"""

    def __init__(self, max_history: int = 1000):
        """Initialize performance monitor

        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.max_history = max_history
        self.metrics: List[MetricData] = []
        self.stats: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def measure_request(self, path: str, method: str):
        """Measure request performance

        Args:
            path: Request path
            method: HTTP method
        """
        start_time = time.time()
        request_key = f"{method} {path}"

        try:
            yield
        except Exception:
            # Record error
            async with self._lock:
                self.stats[request_key].error_count += 1
            raise
        finally:
            duration = time.time() - start_time

            # Record metric
            await self.record_metric(
                name="request_duration", value=duration, tags={"path": path, "method": method}
            )

            # Update statistics
            async with self._lock:
                stats = self.stats[request_key]
                stats.total_requests += 1
                stats.total_duration += duration
                stats.avg_duration = stats.total_duration / stats.total_requests
                stats.min_duration = min(stats.min_duration, duration)
                stats.max_duration = max(stats.max_duration, duration)
                stats.last_requests.append(
                    {"timestamp": start_time, "duration": duration, "status": "success"}
                )

    async def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a metric

        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for categorization
        """
        metric = MetricData(name=name, value=value, timestamp=time.time(), tags=tags or {})

        async with self._lock:
            self.metrics.append(metric)

            # Maintain max history
            if len(self.metrics) > self.max_history:
                self.metrics = self.metrics[-self.max_history :]

        logger.debug(f"Recorded metric: {name}={value}")

    async def get_metrics(
        self,
        name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        since: Optional[float] = None,
    ) -> List[MetricData]:
        """Get metrics with optional filtering

        Args:
            name: Filter by metric name
            tags: Filter by tags (all must match)
            since: Only return metrics after this timestamp

        Returns:
            List of matching metrics
        """
        async with self._lock:
            filtered = self.metrics

        # Apply filters
        if name:
            filtered = [m for m in filtered if m.name == name]

        if tags:
            filtered = [m for m in filtered if all(m.tags.get(k) == v for k, v in tags.items())]

        if since:
            filtered = [m for m in filtered if m.timestamp >= since]

        return filtered

    async def get_stats(self, request_key: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics

        Args:
            request_key: Specific request to get stats for (format: "METHOD /path")

        Returns:
            Statistics dictionary
        """
        async with self._lock:
            if request_key:
                stats = self.stats.get(request_key)
                if not stats:
                    return {}

                return {
                    "total_requests": stats.total_requests,
                    "avg_duration": stats.avg_duration,
                    "min_duration": stats.min_duration,
                    "max_duration": stats.max_duration,
                    "error_count": stats.error_count,
                    "error_rate": stats.error_count / max(stats.total_requests, 1),
                    "recent_requests": list(stats.last_requests),
                }

            # Return all stats
            return {
                key: {
                    "total_requests": stats.total_requests,
                    "avg_duration": stats.avg_duration,
                    "min_duration": stats.min_duration,
                    "max_duration": stats.max_duration,
                    "error_count": stats.error_count,
                    "error_rate": stats.error_count / max(stats.total_requests, 1),
                }
                for key, stats in self.stats.items()
            }

    async def reset_stats(self):
        """Reset all statistics"""
        async with self._lock:
            self.metrics.clear()
            self.stats.clear()
            logger.info("Performance statistics reset")

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health check metrics

        Returns:
            Health metrics dictionary
        """
        return {
            "total_metrics": len(self.metrics),
            "total_request_types": len(self.stats),
            "memory_usage": {
                "metrics_size": len(self.metrics),
                "stats_size": len(self.stats),
                "max_history": self.max_history,
            },
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
