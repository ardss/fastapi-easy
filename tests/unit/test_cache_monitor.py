"""Tests for cache monitor"""

from fastapi_easy.core.cache_monitor import CacheMetrics, CacheMonitor, create_cache_monitor


class TestCacheMetrics:
    """Test CacheMetrics class"""

    def test_record_operations(self):
        """Test recording cache operations"""
        metrics = CacheMetrics()

        metrics.record_hit()
        metrics.record_hit()
        metrics.record_miss()
        metrics.record_set()
        metrics.record_delete()

        assert metrics.hits == 2
        assert metrics.misses == 1
        assert metrics.sets == 1
        assert metrics.deletes == 1

    def test_hit_rate_calculation(self):
        """Test hit rate calculation"""
        metrics = CacheMetrics()

        # 80% hit rate
        for _ in range(8):
            metrics.record_hit()
        for _ in range(2):
            metrics.record_miss()

        assert abs(metrics.get_hit_rate() - 80.0) < 0.1

    def test_hit_rate_zero_requests(self):
        """Test hit rate with zero requests"""
        metrics = CacheMetrics()
        assert metrics.get_hit_rate() == 0.0

    def test_get_report(self):
        """Test metrics report"""
        metrics = CacheMetrics()

        metrics.record_hit()
        metrics.record_miss()
        metrics.record_set()

        report = metrics.get_report()

        assert report["hits"] == 1
        assert report["misses"] == 1
        assert report["sets"] == 1
        assert report["total_requests"] == 2
        assert "hit_rate" in report
        assert "uptime_seconds" in report

    def test_reset(self):
        """Test metrics reset"""
        metrics = CacheMetrics()

        metrics.record_hit()
        metrics.record_miss()

        metrics.reset()

        assert metrics.hits == 0
        assert metrics.misses == 0


class TestCacheMonitor:
    """Test CacheMonitor class"""

    def test_monitor_initialization(self):
        """Test monitor initialization"""
        monitor = CacheMonitor(hit_rate_threshold=60.0)

        assert monitor.hit_rate_threshold == 60.0
        assert len(monitor.alerts) == 0

    def test_record_operations(self):
        """Test recording operations"""
        monitor = CacheMonitor()

        monitor.record_hit()
        monitor.record_miss()
        monitor.record_set()
        monitor.record_delete()

        assert monitor.metrics.hits == 1
        assert monitor.metrics.misses == 1

    def test_alert_on_low_hit_rate(self):
        """Test alert generation on low hit rate"""
        monitor = CacheMonitor(hit_rate_threshold=80.0)

        # Create 100 requests with 50% hit rate (below threshold)
        for _ in range(50):
            monitor.record_hit()
        for _ in range(50):
            monitor.record_miss()

        assert len(monitor.alerts) > 0
        assert monitor.alerts[-1]["type"] == "low_hit_rate"

    def test_get_report(self):
        """Test monitor report"""
        monitor = CacheMonitor()

        monitor.record_hit()
        monitor.record_miss()

        report = monitor.get_report()

        assert "metrics" in report
        assert "alerts" in report
        assert "status" in report

    def test_clear_alerts(self):
        """Test clearing alerts"""
        monitor = CacheMonitor(hit_rate_threshold=80.0)

        # Generate alerts
        for _ in range(50):
            monitor.record_hit()
        for _ in range(50):
            monitor.record_miss()

        assert len(monitor.alerts) > 0

        monitor.clear_alerts()
        assert len(monitor.alerts) == 0


class TestFactoryFunction:
    """Test factory function"""

    def test_create_cache_monitor(self):
        """Test creating cache monitor"""
        monitor = create_cache_monitor(hit_rate_threshold=70.0)

        assert isinstance(monitor, CacheMonitor)
        assert monitor.hit_rate_threshold == 70.0
