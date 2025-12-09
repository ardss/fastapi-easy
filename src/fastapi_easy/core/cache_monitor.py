"""Cache monitoring and metrics collection.

This module provides comprehensive cache performance monitoring capabilities,
including hit/miss tracking, rate limiting, alerting, and detailed metrics
reporting. It helps identify cache performance issues and optimize caching
strategies.

The monitor tracks:
- Cache hit/miss rates
- Operation counts (sets, deletes)
- Request rates over time
- Performance alerts when thresholds are breached

Example:
    ```python
    monitor = CacheMonitor(hit_rate_threshold=75.0)

    # Record cache operations
    monitor.record_hit()
    monitor.record_miss()

    # Get performance report
    report = monitor.get_report()
    print(f"Hit rate: {report['hit_rate']}")
    ```
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class CacheMetrics:
    """Collects and tracks cache performance metrics.

    Tracks various cache operations and calculates performance indicators
    including hit rates, operation counts, and request throughput.
    """

    def __init__(self) -> None:
        """Initialize cache metrics collector."""
        self.hits: int = 0
        self.misses: int = 0
        self.sets: int = 0
        self.deletes: int = 0
        self.start_time: datetime = datetime.now()

    def record_hit(self) -> None:
        """Record a successful cache retrieval.

        Increments the hit counter and updates internal metrics.

        Example:
            ```python
            if value := await cache.get(key):
                metrics.record_hit()
            ```
        """
        self.hits += 1

    def record_miss(self) -> None:
        """Record a failed cache retrieval.

        Increments the miss counter and updates internal metrics.

        Example:
            ```python
            if not (value := await cache.get(key)):
                metrics.record_miss()
                value = await fetch_from_db(key)
            ```
        """
        self.misses += 1

    def record_set(self) -> None:
        """Record a cache set operation.

        Increments the set counter to track write operations.

        Example:
            ```python
            await cache.set(key, value)
            metrics.record_set()
            ```
        """
        self.sets += 1

    def record_delete(self) -> None:
        """Record a cache delete operation.

        Increments the delete counter to track removal operations.

        Example:
            ```python
            if await cache.delete(key):
                metrics.record_delete()
            ```
        """
        self.deletes += 1

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate percentage.

        Returns:
            Hit rate as a percentage between 0.0 and 100.0

        Example:
            ```python
            hit_rate = metrics.get_hit_rate()
            if hit_rate < 50.0:
                print("Cache performance needs improvement")
            ```
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100

    def get_report(self) -> dict[str, Any]:
        """Get comprehensive metrics report.

        Returns:
            Dictionary containing all metrics including:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - sets: Number of set operations
            - deletes: Number of delete operations
            - total_requests: Total cache requests
            - hit_rate: Hit rate as formatted percentage string
            - uptime_seconds: Time since metrics collection started
            - requests_per_second: Average requests per second

        Example:
            ```python
            report = metrics.get_report()
            print(f"Cache hit rate: {report['hit_rate']}")
            print(f"Requests/sec: {report['requests_per_second']:.2f}")
            ```
        """
        total_requests = self.hits + self.misses
        uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "total_requests": total_requests,
            "hit_rate": f"{self.get_hit_rate():.2f}%",
            "uptime_seconds": uptime,
            "requests_per_second": total_requests / uptime if uptime > 0 else 0,
        }

    def reset(self) -> None:
        """Reset all metrics to initial state.

        Useful for starting fresh measurements or periodic
        metric collection intervals.

        Example:
            ```python
            # Reset metrics daily
            if is_new_day():
                metrics.reset()
            ```
        """
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.start_time = datetime.now()


class CacheMonitor:
    """Monitors cache performance and provides intelligent alerts.

    Extends basic metrics collection with alerting capabilities and
    performance monitoring. Automatically triggers alerts when performance
    falls below configured thresholds.

    Attributes:
        metrics: The underlying metrics collector
        hit_rate_threshold: Minimum acceptable hit rate percentage
        alerts: List of generated alerts with timestamps

    Example:
        ```python
        # Create monitor with 75% hit rate threshold
        monitor = CacheMonitor(hit_rate_threshold=75.0)

        # Simulate cache operations
        for _ in range(100):
            if random.random() < 0.6:  # 60% hit rate
                monitor.record_hit()
            else:
                monitor.record_miss()

        # Check for alerts
        if monitor.get_alerts():
            print("Performance alerts triggered!")
        ```
    """

    def __init__(self, hit_rate_threshold: float = 50.0):
        """Initialize cache monitor with alerting.

        Args:
            hit_rate_threshold: Alert if hit rate falls below this percentage

        Raises:
            ValueError: If threshold is not between 0 and 100
        """
        if not 0 <= hit_rate_threshold <= 100:
            raise ValueError("Hit rate threshold must be between 0 and 100")

        self.metrics: CacheMetrics = CacheMetrics()
        self.hit_rate_threshold: float = hit_rate_threshold
        self.alerts: list[dict[str, Any]] = []

    def record_hit(self) -> None:
        """Record a cache hit and check for alerts.

        Updates metrics and triggers alert evaluation if performance
        has degraded below the threshold.

        Example:
            ```python
            if await cache.get(key):
                monitor.record_hit()
            ```
        """
        self.metrics.record_hit()
        self._check_alerts()

    def record_miss(self) -> None:
        """Record a cache miss and check for alerts.

        Updates metrics and triggers alert evaluation if performance
        has degraded below the threshold.

        Example:
            ```python
            if not await cache.get(key):
                monitor.record_miss()
            ```
        """
        self.metrics.record_miss()
        self._check_alerts()

    def record_set(self) -> None:
        """Record a cache set operation.

        Updates metrics without triggering alert evaluation as set operations
        don't directly affect hit rate performance.

        Example:
            ```python
            await cache.set(key, value, ttl=3600)
            monitor.record_set()
            ```
        """
        self.metrics.record_set()

    def record_delete(self) -> None:
        """Record a cache delete operation.

        Updates metrics without triggering alert evaluation as delete operations
        don't directly affect hit rate performance.

        Example:
            ```python
            if await cache.delete(key):
                monitor.record_delete()
            ```
        """
        self.metrics.record_delete()

    def _check_alerts(self) -> None:
        """Check if alerts should be triggered"""
        if self.metrics.get_hit_rate() < self.hit_rate_threshold:
            total = self.metrics.hits + self.metrics.misses
            if total >= 100:  # Only alert after sufficient requests
                self.alerts.append(
                    {
                        "timestamp": datetime.now(),
                        "type": "low_hit_rate",
                        "hit_rate": self.metrics.get_hit_rate(),
                        "threshold": self.hit_rate_threshold,
                    }
                )

    def get_report(self) -> Dict[str, Any]:
        """Get monitoring report

        Returns:
            Monitoring report with metrics and alerts
        """
        return {
            "metrics": self.metrics.get_report(),
            "alerts": self.alerts[-10:],  # Last 10 alerts
            "status": (
                "healthy" if self.metrics.get_hit_rate() >= self.hit_rate_threshold else "warning"
            ),
        }

    def clear_alerts(self) -> None:
        """Clear all alerts"""
        self.alerts.clear()


def create_cache_monitor(hit_rate_threshold: float = 50.0) -> CacheMonitor:
    """Create a cache monitor

    Args:
        hit_rate_threshold: Alert threshold for hit rate

    Returns:
        Cache monitor instance
    """
    return CacheMonitor(hit_rate_threshold)
