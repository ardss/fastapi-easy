"""
Comprehensive performance monitoring utilities for FastAPI-Easy tests.
Provides detailed metrics, benchmarking, and regression detection.
"""

import time
import json
import asyncio
import threading
import psutil
from pathlib import Path
from contextlib import asynccontextmanager, contextmanager
from typing import Dict, Any, Optional, List, Callable, AsyncGenerator
from dataclasses import dataclass, asdict
from functools import wraps
import warnings

try:
    import memory_profiler
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    duration: float
    memory_delta: float  # in MB
    memory_peak: float  # in MB
    cpu_percent: float
    operations_per_second: Optional[float] = None
    throughput_mb_per_sec: Optional[float] = None


@dataclass
class BenchmarkResult:
    """Benchmark result data structure"""
    test_name: str
    metrics: PerformanceMetrics
    iterations: int
    min_duration: float
    max_duration: float
    avg_duration: float
    std_deviation: float
    percentile_95: float
    percentile_99: float


class PerformanceMonitor:
    """Main performance monitoring class"""

    def __init__(self, baseline_file: Optional[Path] = None):
        self.baseline_file = baseline_file or Path(".performance_baseline.json")
        self.current_session: Dict[str, List[PerformanceMetrics]] = {}
        self.baseline_metrics = self._load_baseline()
        self.process = psutil.Process()
        self._lock = threading.Lock()

    def _load_baseline(self) -> Dict[str, Dict[str, float]]:
        """Load performance baseline from file"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_baseline(self):
        """Save current metrics as baseline"""
        if not self.current_session:
            return

        baseline = {}
        for test_name, metrics_list in self.current_session.items():
            if metrics_list:
                baseline[test_name] = {
                    "avg_duration": sum(m.duration for m in metrics_list) / len(metrics_list),
                    "max_duration": max(m.duration for m in metrics_list),
                    "max_memory_delta": max(m.memory_delta for m in metrics_list),
                    "avg_memory_delta": sum(m.memory_delta for m in metrics_list) / len(metrics_list),
                }

        try:
            with open(self.baseline_file, "w") as f:
                json.dump(baseline, f, indent=2)
        except IOError as e:
            warnings.warn(f"Could not save performance baseline: {e}")

    @contextmanager
    def monitor(self, test_name: str) -> Any:
        """Context manager for monitoring performance"""
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = self.process.cpu_percent()

        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = self.process.cpu_percent()

            metrics = PerformanceMetrics(
                duration=end_time - start_time,
                memory_delta=end_memory - start_memory,
                memory_peak=end_memory,
                cpu_percent=end_cpu - start_cpu if end_cpu > start_cpu else 0
            )

            with self._lock:
                if test_name not in self.current_session:
                    self.current_session[test_name] = []
                self.current_session[test_name].append(metrics)

    @asynccontextmanager
    async def async_monitor(self, test_name: str) -> AsyncGenerator[None, None]:
        """Async context manager for monitoring performance"""
        with self.monitor(test_name):
            yield

    def check_regression(self, test_name: str, metrics: PerformanceMetrics,
                        threshold: float = 0.2) -> Optional[Dict[str, Any]]:
        """Check if metrics indicate performance regression"""
        if test_name not in self.baseline_metrics:
            return None

        baseline = self.baseline_metrics[test_name]
        regressions = {}

        # Check duration regression
        if metrics.duration > baseline["avg_duration"] * (1 + threshold):
            regressions["duration"] = {
                "current": metrics.duration,
                "baseline": baseline["avg_duration"],
                "increase_percent": ((metrics.duration - baseline["avg_duration"]) /
                                   baseline["avg_duration"]) * 100
            }

        # Check memory regression
        if metrics.memory_delta > baseline["max_memory_delta"] * (1 + threshold):
            regressions["memory"] = {
                "current": metrics.memory_delta,
                "baseline": baseline["max_memory_delta"],
                "increase_percent": ((metrics.memory_delta - baseline["max_memory_delta"]) /
                                   baseline["max_memory_delta"]) * 100
            }

        return regressions if regressions else None

    def benchmark(self, test_func: Callable, iterations: int = 10,
                  warmup_iterations: int = 3) -> BenchmarkResult:
        """Benchmark a function with multiple iterations"""

        # Warmup
        for _ in range(warmup_iterations):
            if asyncio.iscoroutinefunction(test_func):
                asyncio.run(test_func())
            else:
                test_func()

        # Benchmark iterations
        durations = []
        memory_deltas = []
        test_name = test_func.__name__

        for _ in range(iterations):
            with self.monitor(test_name):
                start_time = time.perf_counter()

                if asyncio.iscoroutinefunction(test_func):
                    asyncio.run(test_func())
                else:
                    test_func()

                end_time = time.perf_counter()
                durations.append(end_time - start_time)

                # Get latest metrics
                if test_name in self.current_session:
                    latest_metrics = self.current_session[test_name][-1]
                    memory_deltas.append(latest_metrics.memory_delta)

        # Calculate statistics
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
        std_deviation = variance ** 0.5

        # Calculate percentiles
        sorted_durations = sorted(durations)
        p95_index = int(0.95 * len(sorted_durations))
        p99_index = int(0.99 * len(sorted_durations))
        percentile_95 = sorted_durations[p95_index]
        percentile_99 = sorted_durations[p99_index]

        # Create benchmark result
        avg_metrics = PerformanceMetrics(
            duration=avg_duration,
            memory_delta=sum(memory_deltas) / len(memory_deltas) if memory_deltas else 0,
            memory_peak=max(memory_deltas) if memory_deltas else 0,
            cpu_percent=0  # Not calculated for benchmarks
        )

        return BenchmarkResult(
            test_name=test_func.__name__,
            metrics=avg_metrics,
            metrics=avg_metrics,
            iterations=iterations,
            min_duration=min_duration,
            max_duration=max_duration,
            avg_duration=avg_duration,
            std_deviation=std_deviation,
            percentile_95=percentile_95,
            percentile_99=percentile_99
        )

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current test session"""
        if not self.current_session:
            return {}

        all_durations = []
        all_memory_deltas = []
        slow_tests = []

        for test_name, metrics_list in self.current_session.items():
            for metrics in metrics_list:
                all_durations.append(metrics.duration)
                all_memory_deltas.append(metrics.memory_delta)

                if metrics.duration > 1.0:  # Slow test threshold
                    slow_tests.append({
                        "test": test_name,
                        "duration": metrics.duration
                    })

        return {
            "total_tests": len(all_durations),
            "avg_duration": sum(all_durations) / len(all_durations),
            "max_duration": max(all_durations),
            "min_duration": min(all_durations),
            "avg_memory_delta": sum(all_memory_deltas) / len(all_memory_deltas),
            "max_memory_delta": max(all_memory_deltas),
            "slow_tests_count": len(slow_tests),
            "slow_tests": sorted(slow_tests, key=lambda x: x["duration"], reverse=True)[:10],
        }

    def save_report(self, output_file: Optional[Path] = None) -> Path:
        """Save detailed performance report"""
        output_file = output_file or Path("performance_report.json")

        report = {
            "session_summary": self.get_session_summary(),
            "baseline_comparison": self._compare_with_baseline(),
            "detailed_metrics": {
                test_name: [asdict(m) for m in metrics_list]
                for test_name, metrics_list in self.current_session.items()
            }
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        return output_file

    def _compare_with_baseline(self) -> Dict[str, Any]:
        """Compare current session with baseline"""
        comparison = {}

        for test_name, metrics_list in self.current_session.items():
            if not metrics_list or test_name not in self.baseline_metrics:
                continue

            current_avg = sum(m.duration for m in metrics_list) / len(metrics_list)
            baseline_avg = self.baseline_metrics[test_name]["avg_duration"]

            if current_avg > baseline_avg * 1.1:  # 10% regression threshold
                comparison[test_name] = {
                    "current_avg": current_avg,
                    "baseline_avg": baseline_avg,
                    "regression_percent": ((current_avg - baseline_avg) / baseline_avg) * 100
                }

        return comparison


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def performance_test(benchmark: bool = False, iterations: int = 10,
                    regression_threshold: float = 0.2):
    """Decorator for performance testing"""
    def decorator(func: Callable):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            test_name = f"{func.__module__}.{func.__name__}"

            if benchmark:
                result = performance_monitor.benchmark(func, iterations=iterations)
                print(f"\n[BENCHMARK] {test_name}:")
                print(f"  Duration: {result.avg_duration:.4f}s ± {result.std_deviation:.4f}s")
                print(f"  Range: {result.min_duration:.4f}s - {result.max_duration:.4f}s")
                print(f"  Memory: {result.metrics.memory_delta:.2f}MB")
                return result
            else:
                with performance_monitor.monitor(test_name):
                    result = func(*args, **kwargs)

                    # Check for regression
                    if test_name in performance_monitor.current_session:
                        latest_metrics = performance_monitor.current_session[test_name][-1]
                        regression = performance_monitor.check_regression(
                            test_name, latest_metrics, regression_threshold
                        )

                        if regression:
                            warnings.warn(
                                f"Performance regression detected in {test_name}: {regression}",
                                UserWarning
                            )

                    return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            test_name = f"{func.__module__}.{func.__name__}"

            async with performance_monitor.async_monitor(test_name):
                if benchmark:
                    # For async functions, run benchmark in event loop
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, performance_monitor.benchmark, func, iterations
                    )
                    return result
                else:
                    result = await func(*args, **kwargs)

                    # Check for regression
                    if test_name in performance_monitor.current_session:
                        latest_metrics = performance_monitor.current_session[test_name][-1]
                        regression = performance_monitor.check_regression(
                            test_name, latest_metrics, regression_threshold
                        )

                        if regression:
                            warnings.warn(
                                f"Performance regression detected in {test_name}: {regression}",
                                UserWarning
                            )

                    return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class LoadTester:
    """Load testing utility for performance validation"""

    def __init__(self, target_func: Callable, max_concurrent: int = 100):
        self.target_func = target_func
        self.max_concurrent = max_concurrent
        self.results = []

    async def run_concurrent_test(self, num_requests: int = 1000,
                                ramp_up_time: float = 1.0) -> Dict[str, Any]:
        """Run concurrent load test"""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def single_request(request_id: int):
            async with semaphore:
                start_time = time.perf_counter()
                try:
                    if asyncio.iscoroutinefunction(self.target_func):
                        await self.target_func()
                    else:
                        await asyncio.to_thread(self.target_func)

                    duration = time.perf_counter() - start_time
                    self.results.append({"request_id": request_id, "duration": duration, "success": True})

                except Exception as e:
                    duration = time.perf_counter() - start_time
                    self.results.append({"request_id": request_id, "duration": duration, "success": False, "error": str(e)})

        # Create tasks with ramp-up
        tasks = []
        delay_between_requests = ramp_up_time / num_requests

        for i in range(num_requests):
            task = asyncio.create_task(single_request(i))
            tasks.append(task)
            if i < num_requests - 1:  # Don't delay after last request
                await asyncio.sleep(delay_between_requests)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Calculate statistics
        successful_results = [r for r in self.results if r["success"]]
        durations = [r["duration"] for r in successful_results]

        if not durations:
            return {"error": "All requests failed"}

        return {
            "total_requests": num_requests,
            "successful_requests": len(successful_results),
            "failed_requests": len(self.results) - len(successful_results),
            "avg_response_time": sum(durations) / len(durations),
            "min_response_time": min(durations),
            "max_response_time": max(durations),
            "requests_per_second": len(successful_results) / (time.perf_counter() - tasks[0].get_coro().__name__) if tasks else 0,
            "error_rate": (len(self.results) - len(successful_results)) / len(self.results) * 100,
        }


# Convenience exports
__all__ = [
    "PerformanceMonitor",
    "PerformanceMetrics",
    "BenchmarkResult",
    "LoadTester",
    "performance_monitor",
    "performance_test",
]