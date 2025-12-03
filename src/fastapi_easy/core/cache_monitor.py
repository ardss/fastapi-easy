"""Cache monitoring and metrics collection"""

from typing import Dict, Any, Optional
from datetime import datetime


class CacheMetrics:
    """Collects and tracks cache performance metrics"""

    def __init__(self):
        """Initialize cache metrics"""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.start_time = datetime.now()

    def record_hit(self) -> None:
        """Record a cache hit"""
        self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss"""
        self.misses += 1

    def record_set(self) -> None:
        """Record a cache set operation"""
        self.sets += 1

    def record_delete(self) -> None:
        """Record a cache delete operation"""
        self.deletes += 1

    def get_hit_rate(self) -> float:
        """Get cache hit rate percentage

        Returns:
            Hit rate as percentage (0-100)
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100

    def get_report(self) -> Dict[str, Any]:
        """Get comprehensive metrics report

        Returns:
            Metrics report dictionary
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
        """Reset all metrics"""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.start_time = datetime.now()


class CacheMonitor:
    """Monitors cache performance and provides alerts"""

    def __init__(self, hit_rate_threshold: float = 50.0):
        """Initialize cache monitor

        Args:
            hit_rate_threshold: Alert if hit rate falls below this percentage
        """
        self.metrics = CacheMetrics()
        self.hit_rate_threshold = hit_rate_threshold
        self.alerts: list = []

    def record_hit(self) -> None:
        """Record cache hit"""
        self.metrics.record_hit()
        self._check_alerts()

    def record_miss(self) -> None:
        """Record cache miss"""
        self.metrics.record_miss()
        self._check_alerts()

    def record_set(self) -> None:
        """Record cache set"""
        self.metrics.record_set()

    def record_delete(self) -> None:
        """Record cache delete"""
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
