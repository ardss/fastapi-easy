"""
Comprehensive Performance Benchmarker for FastAPI-Easy

This module provides advanced performance benchmarking capabilities including:
- Database query analysis and optimization
- Memory usage profiling and leak detection
- API endpoint performance measurement
- Concurrent load testing
- Caching efficiency analysis
- Scalability benchmarking
"""

from __future__ import annotations

import asyncio
import gc
import json
import logging
import statistics
import threading
import time
import tracemalloc
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance metric measurement"""

    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Complete benchmark results"""

    test_name: str
    duration: float
    start_time: datetime
    end_time: datetime
    metrics: List[PerformanceMetric] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    sample_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryAnalysisResult:
    """Database query analysis result"""

    query_hash: str
    query_template: str
    execution_count: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    min_duration: float = float("inf")
    max_duration: float = 0.0
    p50_duration: float = 0.0
    p95_duration: float = 0.0
    p99_duration: float = 0.0
    rows_affected: int = 0
    memory_usage: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""

    timestamp: datetime
    rss_mb: float
    vms_mb: float
    percent: float
    gc_objects: int
    tracemalloc_current: int
    tracemalloc_peak: int


class PerformanceBenchmarker:
    """
    Advanced performance benchmarker for comprehensive analysis
    """

    def __init__(
        self,
        output_dir: str = "benchmarks",
        enable_tracemalloc: bool = True,
        enable_gc_monitoring: bool = True,
        max_history: int = 10000,
    ):
        """
        Initialize performance benchmarker

        Args:
            output_dir: Directory to store benchmark results
            enable_tracemalloc: Enable memory tracing
            enable_gc_monitoring: Enable garbage collection monitoring
            max_history: Maximum number of metrics to keep in memory
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.enable_tracemalloc = enable_tracemalloc
        self.enable_gc_monitoring = enable_gc_monitoring
        self.max_history = max_history

        # Performance metrics storage
        self.metrics_history: List[PerformanceMetric] = []
        self.benchmark_results: List[BenchmarkResult] = []
        self.query_analysis: Dict[str, QueryAnalysisResult] = {}
        self.memory_snapshots: List[MemorySnapshot] = []

        # Real-time monitoring
        self.active_benchmarks: Dict[str, BenchmarkResult] = {}
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None

        # Statistics tracking
        self._operation_stats: Dict[str, List[float]] = defaultdict(list)
        self._query_durations: List[float] = []

        # Setup
        if enable_tracemalloc:
            tracemalloc.start()

        # Locks for thread safety
        self._metrics_lock = threading.Lock()
        self._analysis_lock = threading.Lock()

    @asynccontextmanager
    async def benchmark(self, test_name: str, **tags):
        """
        Context manager for benchmarking operations

        Args:
            test_name: Name of the benchmark test
            **tags: Additional tags for categorization
        """
        start_time = datetime.now()
        result = BenchmarkResult(
            test_name=test_name,
            start_time=start_time,
            end_time=start_time,
            duration=0.0,
            metadata={"tags": tags},
        )

        # Memory snapshot before
        if self.enable_tracemalloc:
            tracemalloc.start()
        initial_memory = self._take_memory_snapshot()

        try:
            self.active_benchmarks[test_name] = result
            yield result

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            raise

        finally:
            # Final measurements
            end_time = datetime.now()
            final_memory = self._take_memory_snapshot()

            result.end_time = end_time
            result.duration = (end_time - start_time).total_seconds()

            # Memory analysis
            memory_delta = {
                "rss_mb": final_memory.rss_mb - initial_memory.rss_mb,
                "vms_mb": final_memory.vms_mb - initial_memory.vms_mb,
                "percent": final_memory.percent - initial_memory.percent,
            }
            result.metadata["memory_delta"] = memory_delta

            if self.enable_tracemalloc:
                current, peak = tracemalloc.get_traced_memory()
                result.metadata["tracemalloc"] = {
                    "current_mb": current / 1024 / 1024,
                    "peak_mb": peak / 1024 / 1024,
                }
                tracemalloc.stop()

            # Store results
            with self._metrics_lock:
                self.benchmark_results.append(result)

                # Maintain history limit
                if len(self.benchmark_results) > self.max_history:
                    self.benchmark_results = self.benchmark_results[-self.max_history :]

            if test_name in self.active_benchmarks:
                del self.active_benchmarks[test_name]

            # Save to file
            await self._save_benchmark_result(result)

            logger.info(f"Benchmark '{test_name}' completed in {result.duration:.3f}s")

    async def measure_query_performance(
        self,
        session: AsyncSession,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        iterations: int = 10,
        warmup_iterations: int = 3,
    ) -> QueryAnalysisResult:
        """
        Measure database query performance with statistical analysis

        Args:
            session: Database session
            query: SQL query to benchmark
            params: Query parameters
            iterations: Number of benchmark iterations
            warmup_iterations: Number of warmup iterations

        Returns:
            QueryAnalysisResult with performance metrics
        """
        query_hash = hash(query)
        durations = []
        rows_affected = 0

        # Warmup iterations
        for _ in range(warmup_iterations):
            try:
                await session.execute(text(query), params or {})
            except Exception:
                pass  # Ignore warmup errors

        # Benchmark iterations
        for i in range(iterations):
            start_time = time.perf_counter()

            try:
                result = await session.execute(text(query), params or {})
                if result.returns_rows:
                    rows = result.fetchall()
                    rows_affected = max(rows_affected, len(rows))
                else:
                    rows_affected = result.rowcount

                duration = time.perf_counter() - start_time
                durations.append(duration)

            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                durations.append(float("inf"))

        # Filter out failed attempts
        valid_durations = [d for d in durations if d != float("inf")]

        if not valid_durations:
            raise ValueError("All query executions failed")

        # Calculate statistics
        result = QueryAnalysisResult(
            query_hash=str(query_hash),
            query_template=query[:100] + "..." if len(query) > 100 else query,
            execution_count=len(valid_durations),
            total_duration=sum(valid_durations),
            avg_duration=statistics.mean(valid_durations),
            min_duration=min(valid_durations),
            max_duration=max(valid_durations),
            p50_duration=statistics.median(valid_durations),
            p95_duration=valid_durations[int(len(valid_durations) * 0.95)],
            p99_duration=(
                valid_durations[int(len(valid_durations) * 0.99)]
                if len(valid_durations) > 100
                else max(valid_durations)
            ),
            rows_affected=rows_affected,
        )

        # Store analysis
        with self._analysis_lock:
            self.query_analysis[result.query_hash] = result

        # Record metrics
        await self.record_metric(
            "query_duration",
            result.avg_duration,
            "seconds",
            query_hash=result.query_hash,
            query_template=result.query_template,
        )

        return result

    async def benchmark_concurrent_operations(
        self,
        operation: Callable,
        concurrent_tasks: int = 10,
        total_operations: int = 100,
        operation_args: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkResult:
        """
        Benchmark concurrent operations with varying load levels

        Args:
            operation: Async function to benchmark
            concurrent_tasks: Number of concurrent tasks
            total_operations: Total number of operations to execute
            operation_args: Arguments to pass to operation

        Returns:
            BenchmarkResult with concurrent performance metrics
        """
        operation_args = operation_args or {}

        async with self.benchmark(
            f"concurrent_{operation.__name__}",
            concurrent_tasks=concurrent_tasks,
            total_operations=total_operations,
        ) as result:

            # Create batches of operations
            operations_per_task = total_operations // concurrent_tasks
            remaining_operations = total_operations % concurrent_tasks

            tasks = []
            for i in range(concurrent_tasks):
                ops_count = operations_per_task + (1 if i < remaining_operations else 0)

                async def task_runner(ops_count: int, task_id: int):
                    task_results = []
                    for j in range(ops_count):
                        start_time = time.perf_counter()
                        try:
                            op_result = await operation(**operation_args)
                            duration = time.perf_counter() - start_time
                            task_results.append(
                                {"duration": duration, "success": True, "result": op_result}
                            )
                        except Exception as e:
                            duration = time.perf_counter() - start_time
                            task_results.append(
                                {"duration": duration, "success": False, "error": str(e)}
                            )
                    return task_results

                tasks.append(task_runner(ops_count, i))

            # Execute all tasks concurrently
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Analyze results
            all_results = []
            for task_result in task_results:
                if isinstance(task_result, Exception):
                    logger.error(f"Task failed: {task_result}")
                else:
                    all_results.extend(task_result)

            successful_ops = [r for r in all_results if r["success"]]
            failed_ops = [r for r in all_results if not r["success"]]

            durations = [r["duration"] for r in successful_ops]

            result.metadata.update(
                {
                    "total_operations": total_operations,
                    "successful_operations": len(successful_ops),
                    "failed_operations": len(failed_ops),
                    "success_rate": len(successful_ops) / total_operations,
                    "avg_duration": statistics.mean(durations) if durations else 0,
                    "min_duration": min(durations) if durations else 0,
                    "max_duration": max(durations) if durations else 0,
                    "p95_duration": (
                        statistics.quantiles(durations, n=20)[18]
                        if len(durations) > 20
                        else (max(durations) if durations else 0)
                    ),
                    "operations_per_second": (
                        len(successful_ops) / result.duration if result.duration > 0 else 0
                    ),
                    "concurrency_level": concurrent_tasks,
                }
            )

            # Record metrics
            await self.record_metric(
                "concurrent_throughput",
                result.metadata["operations_per_second"],
                "ops/sec",
                operation_name=operation.__name__,
                concurrency=concurrent_tasks,
            )

        return result

    async def benchmark_memory_usage(
        self,
        operation: Callable,
        iterations: int = 100,
        operation_args: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkResult:
        """
        Benchmark memory usage of an operation

        Args:
            operation: Function to benchmark
            iterations: Number of iterations
            operation_args: Arguments to pass to operation

        Returns:
            BenchmarkResult with memory usage metrics
        """
        operation_args = operation_args or {}
        memory_snapshots = []

        async with self.benchmark(f"memory_{operation.__name__}", iterations=iterations) as result:

            # Force garbage collection before starting
            gc.collect()
            initial_snapshot = self._take_memory_snapshot()

            for i in range(iterations):
                # Memory before operation
                before_snapshot = self._take_memory_snapshot()

                # Execute operation
                try:
                    op_result = await operation(**operation_args)
                    success = True
                except Exception as e:
                    op_result = None
                    success = False
                    result.error_message = str(e)

                # Memory after operation
                after_snapshot = self._take_memory_snapshot()

                memory_snapshots.append(
                    {
                        "iteration": i,
                        "success": success,
                        "before": before_snapshot,
                        "after": after_snapshot,
                        "delta": {
                            "rss_mb": after_snapshot.rss_mb - before_snapshot.rss_mb,
                            "vms_mb": after_snapshot.vms_mb - before_snapshot.vms_mb,
                            "percent": after_snapshot.percent - before_snapshot.percent,
                        },
                    }
                )

                # Periodic garbage collection
                if i % 10 == 0:
                    gc.collect()

            # Final garbage collection
            gc.collect()
            final_snapshot = self._take_memory_snapshot()

            # Analyze memory usage
            successful_deltas = [s["delta"] for s in memory_snapshots if s["success"]]

            if successful_deltas:
                avg_rss_delta = statistics.mean([d["rss_mb"] for d in successful_deltas])
                avg_vms_delta = statistics.mean([d["vms_mb"] for d in successful_deltas])
                max_rss_delta = max([d["rss_mb"] for d in successful_deltas])
                max_vms_delta = max([d["vms_mb"] for d in successful_deltas])
            else:
                avg_rss_delta = avg_vms_delta = max_rss_delta = max_vms_delta = 0

            total_memory_growth = final_snapshot.rss_mb - initial_snapshot.rss_mb

            result.metadata.update(
                {
                    "initial_memory_mb": initial_snapshot.rss_mb,
                    "final_memory_mb": final_snapshot.rss_mb,
                    "total_memory_growth_mb": total_memory_growth,
                    "avg_rss_delta_per_op_mb": avg_rss_delta,
                    "avg_vms_delta_per_op_mb": avg_vms_delta,
                    "max_rss_delta_per_op_mb": max_rss_delta,
                    "max_vms_delta_per_op_mb": max_vms_delta,
                    "memory_leak_suspected": total_memory_growth > 50,  # 50MB threshold
                    "iterations": iterations,
                    "successful_iterations": len(successful_deltas),
                }
            )

            # Record metrics
            await self.record_metric(
                "memory_usage_per_op", avg_rss_delta, "MB", operation_name=operation.__name__
            )

        return result

    async def record_metric(self, name: str, value: float, unit: str = "count", **tags):
        """
        Record a performance metric

        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
            **tags: Additional tags for categorization
        """
        metric = PerformanceMetric(
            name=name, value=value, unit=unit, timestamp=datetime.now(), tags=tags
        )

        with self._metrics_lock:
            self.metrics_history.append(metric)

            # Maintain history limit
            if len(self.metrics_history) > self.max_history:
                self.metrics_history = self.metrics_history[-self.max_history :]

            # Update operation stats
            self._operation_stats[name].append(value)
            if len(self._operation_stats[name]) > 1000:
                self._operation_stats[name] = self._operation_stats[name][-1000:]

    def _take_memory_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot"""
        process = psutil.Process()
        memory_info = process.memory_info()

        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=process.memory_percent(),
            gc_objects=len(gc.get_objects()),
            tracemalloc_current=0,
            tracemalloc_peak=0,
        )

        if self.enable_tracemalloc and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            snapshot.tracemalloc_current = current / 1024 / 1024
            snapshot.tracemalloc_peak = peak / 1024 / 1024

        self.memory_snapshots.append(snapshot)

        # Maintain memory snapshot history
        if len(self.memory_snapshots) > 1000:
            self.memory_snapshots = self.memory_snapshots[-1000:]

        return snapshot

    async def _save_benchmark_result(self, result: BenchmarkResult):
        """Save benchmark result to file"""
        timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_{result.test_name}_{timestamp}.json"
        filepath = self.output_dir / filename

        # Convert datetime objects to ISO strings
        data = asdict(result)
        data["start_time"] = result.start_time.isoformat()
        data["end_time"] = result.end_time.isoformat()

        # Convert metrics
        if result.metrics:
            data["metrics"] = [
                {**asdict(metric), "timestamp": metric.timestamp.isoformat()}
                for metric in result.metrics
            ]

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        with self._metrics_lock:
            # Recent benchmarks
            recent_benchmarks = sorted(
                self.benchmark_results, key=lambda x: x.start_time, reverse=True
            )[:10]

            # Operation statistics
            operation_stats = {}
            for name, values in self._operation_stats.items():
                if values:
                    operation_stats[name] = {
                        "count": len(values),
                        "avg": statistics.mean(values),
                        "min": min(values),
                        "max": max(values),
                        "recent": values[-10:] if len(values) >= 10 else values,
                    }

            # Memory analysis
            if len(self.memory_snapshots) > 1:
                memory_trend = (
                    self.memory_snapshots[-1].rss_mb - self.memory_snapshots[0].rss_mb
                ) / (
                    self.memory_snapshots[-1].timestamp - self.memory_snapshots[0].timestamp
                ).total_seconds()
            else:
                memory_trend = 0

            return {
                "total_benchmarks": len(self.benchmark_results),
                "successful_benchmarks": len([b for b in self.benchmark_results if b.success]),
                "failed_benchmarks": len([b for b in self.benchmark_results if not b.success]),
                "recent_benchmarks": [
                    {
                        "name": b.test_name,
                        "duration": b.duration,
                        "success": b.success,
                        "timestamp": b.start_time.isoformat(),
                    }
                    for b in recent_benchmarks
                ],
                "operation_stats": operation_stats,
                "query_analysis_count": len(self.query_analysis),
                "memory_snapshots_count": len(self.memory_snapshots),
                "current_memory_mb": (
                    self.memory_snapshots[-1].rss_mb if self.memory_snapshots else 0
                ),
                "memory_trend_mb_per_sec": memory_trend,
                "metrics_count": len(self.metrics_history),
            }

    def generate_performance_report(self) -> str:
        """Generate a detailed performance report"""
        summary = self.get_performance_summary()

        report = []
        report.append("# FastAPI-Easy Performance Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        # Summary statistics
        report.append("## Summary Statistics")
        report.append(f"- Total Benchmarks: {summary['total_benchmarks']}")
        report.append(f"- Successful: {summary['successful_benchmarks']}")
        report.append(f"- Failed: {summary['failed_benchmarks']}")
        report.append(f"- Current Memory Usage: {summary['current_memory_mb']:.2f} MB")
        report.append(f"- Memory Trend: {summary['memory_trend_mb_per_sec']:.4f} MB/sec")
        report.append("")

        # Recent benchmarks
        report.append("## Recent Benchmarks")
        for benchmark in summary["recent_benchmarks"][:5]:
            status = "✅" if benchmark["success"] else "❌"
            report.append(
                f"- {status} {benchmark['name']}: {benchmark['duration']:.3f}s "
                f"({benchmark['timestamp'][:19]})"
            )
        report.append("")

        # Operation statistics
        report.append("## Operation Performance")
        for op_name, stats in summary["operation_stats"].items():
            report.append(
                f"- {op_name}: avg={stats['avg']:.4f}, "
                f"min={stats['min']:.4f}, max={stats['max']:.4f} "
                f"({stats['count']} samples)"
            )
        report.append("")

        # Query analysis
        if self.query_analysis:
            report.append("## Query Performance")
            for query_hash, analysis in list(self.query_analysis.items())[:5]:
                report.append(
                    f"- Query {query_hash[:8]}: "
                    f"avg={analysis.avg_duration:.4f}s, "
                    f"executions={analysis.execution_count}"
                )
            report.append("")

        # Recommendations
        report.append("## Performance Recommendations")

        # Memory leak detection
        if summary["memory_trend_mb_per_sec"] > 0.1:
            report.append("⚠️ **Potential Memory Leak**: Memory usage is increasing")

        # Slow benchmarks
        slow_benchmarks = [b for b in self.benchmark_results if b.success and b.duration > 1.0]
        if slow_benchmarks:
            report.append("⚠️ **Slow Operations Detected**: Consider optimization")
            for b in slow_benchmarks[:3]:
                report.append(f"  - {b.test_name}: {b.duration:.3f}s")

        # High variance operations
        high_variance_ops = []
        for op_name, stats in summary["operation_stats"].items():
            if len(stats["recent"]) > 5:
                variance = statistics.variance(stats["recent"])
                if variance > stats["avg"] ** 2:
                    high_variance_ops.append(op_name)

        if high_variance_ops:
            report.append("⚠️ **High Variance Operations**: Performance is inconsistent")
            for op in high_variance_ops[:3]:
                report.append(f"  - {op}")

        return "\n".join(report)

    async def cleanup(self):
        """Cleanup resources"""
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            tracemalloc.stop()

        # Save final report
        report = self.generate_performance_report()
        report_path = (
            self.output_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with open(report_path, "w") as f:
            f.write(report)

        logger.info(f"Performance report saved to {report_path}")


# Global benchmarker instance
_global_benchmarker: Optional[PerformanceBenchmarker] = None


def get_benchmarker() -> PerformanceBenchmarker:
    """Get or create global benchmarker instance"""
    global _global_benchmarker
    if _global_benchmarker is None:
        _global_benchmarker = PerformanceBenchmarker()
    return _global_benchmarker


def create_benchmarker(**kwargs) -> PerformanceBenchmarker:
    """Create new benchmarker instance"""
    return PerformanceBenchmarker(**kwargs)
