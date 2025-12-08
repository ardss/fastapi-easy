"""
Advanced Memory Profiler and Resource Analyzer

This module provides comprehensive memory profiling capabilities including:
- Memory leak detection
- Object allocation tracking
- Garbage collection analysis
- Memory usage patterns
- Resource cleanup verification
"""

from __future__ import annotations

import gc
import json
import logging
import sys
import threading
import time
import tracemalloc
import weakref
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Detailed memory snapshot"""

    timestamp: datetime
    rss_mb: float
    vms_mb: float
    shared_mb: float
    text_mb: float
    lib_mb: float
    data_mb: float
    dirty_mb: float
    percent: float
    gc_objects: int
    gc_collections: Dict[int, int]
    tracemalloc_current: int
    tracemalloc_peak: int
    file_descriptors: int
    threads: int


@dataclass
class ObjectAllocation:
    """Object allocation tracking"""

    object_type: str
    count: int
    total_size_bytes: int
    avg_size_bytes: float
    file_location: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class MemoryLeakReport:
    """Memory leak analysis report"""

    suspected_leaks: List[Dict[str, Any]]
    growing_objects: List[ObjectAllocation]
    uncollectable_objects: int
    reference_cycles: int
    recommendations: List[str]
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class ResourceUsage:
    """Resource usage tracking"""

    cpu_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_recv_mb: float
    network_io_sent_mb: float
    open_files: int
    threads: int
    timestamp: datetime


class MemoryProfiler:
    """
    Advanced memory profiler with leak detection and resource analysis
    """

    def __init__(
        self,
        snapshot_interval: float = 1.0,
        max_snapshots: int = 1000,
        enable_tracemalloc: bool = True,
        enable_object_tracking: bool = True,
        output_dir: str = "memory_profiles",
    ):
        """
        Initialize memory profiler

        Args:
            snapshot_interval: Interval between memory snapshots (seconds)
            max_snapshots: Maximum number of snapshots to keep
            enable_tracemalloc: Enable detailed memory tracing
            enable_object_tracking: Enable object allocation tracking
            output_dir: Directory to save profiling results
        """
        self.snapshot_interval = snapshot_interval
        self.max_snapshots = max_snapshots
        self.enable_tracemalloc = enable_tracemalloc
        self.enable_object_tracking = enable_object_tracking
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Data storage
        self.snapshots: List[MemorySnapshot] = []
        self.object_allocations: Dict[str, ObjectAllocation] = {}
        self.resource_usage: List[ResourceUsage] = []
        self.allocation_sites: Dict[str, int] = defaultdict(int)
        self.weak_refs: List[weakref.ref] = []

        # Monitoring state
        self._monitoring = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._snapshot_count = 0
        self._start_time = datetime.now()

        # Analysis state
        self._baseline_snapshot: Optional[MemorySnapshot] = None
        self._peak_memory = 0
        self._gc_stats_baseline: Optional[Dict[int, int]] = None

        # Locks for thread safety
        self._snapshots_lock = threading.Lock()
        self._allocations_lock = threading.Lock()

        # Setup
        if enable_tracemalloc:
            if not tracemalloc.is_tracing():
                tracemalloc.start(25)  # Track 25 frames

        # Get initial GC stats
        self._gc_stats_baseline = {i: gc.get_count()[i] for i in range(3)}

    @asynccontextmanager
    async def profile_memory(self, operation_name: str = "unknown"):
        """
        Context manager for memory profiling operations

        Args:
            operation_name: Name of the operation being profiled
        """
        # Start profiling
        start_time = datetime.now()
        initial_snapshot = self._take_snapshot()

        # Enable object tracking if requested
        if self.enable_object_tracking:
            initial_objects = self._get_object_counts()
        else:
            initial_objects = {}

        try:
            logger.info(f"Starting memory profiling for '{operation_name}'")
            yield self

        finally:
            # End profiling
            end_time = datetime.now()
            final_snapshot = self._take_snapshot()

            if self.enable_object_tracking:
                final_objects = self._get_object_counts()
                object_changes = self._analyze_object_changes(initial_objects, final_objects)
            else:
                object_changes = {}

            # Calculate memory changes
            duration = (end_time - start_time).total_seconds()
            memory_delta = final_snapshot.rss_mb - initial_snapshot.rss_mb
            memory_growth_rate = memory_delta / duration if duration > 0 else 0

            # Analysis
            analysis = {
                "operation_name": operation_name,
                "duration": duration,
                "initial_memory_mb": initial_snapshot.rss_mb,
                "final_memory_mb": final_snapshot.rss_mb,
                "memory_delta_mb": memory_delta,
                "memory_growth_rate_mb_per_sec": memory_growth_rate,
                "peak_memory_mb": max(initial_snapshot.rss_mb, final_snapshot.rss_mb),
                "object_changes": object_changes,
                "gc_collections": {
                    i: final_snapshot.gc_collections[i] - initial_snapshot.gc_collections[i]
                    for i in range(3)
                },
            }

            # Save profile
            await self._save_profile(analysis)

            logger.info(
                f"Memory profiling for '{operation_name}' completed. "
                f"Memory delta: {memory_delta:.2f}MB, "
                f"Duration: {duration:.2f}s"
            )

    def start_monitoring(self):
        """Start continuous memory monitoring"""
        if self._monitoring:
            logger.warning("Memory monitoring is already active")
            return

        self._monitoring = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()

        logger.info(f"Started memory monitoring with {self.snapshot_interval}s interval")

    def stop_monitoring(self):
        """Stop continuous memory monitoring"""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)

        logger.info("Stopped memory monitoring")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                # Take memory snapshot
                snapshot = self._take_snapshot()

                with self._snapshots_lock:
                    self.snapshots.append(snapshot)

                    # Maintain max snapshots
                    if len(self.snapshots) > self.max_snapshots:
                        self.snapshots = self.snapshots[-self.max_snapshots :]

                # Track peak memory
                if snapshot.rss_mb > self._peak_memory:
                    self._peak_memory = snapshot.rss_mb

                # Track resource usage
                resource_usage = self._get_resource_usage()
                self.resource_usage.append(resource_usage)

                # Object allocation tracking
                if self.enable_object_tracking and self._snapshot_count % 10 == 0:
                    self._track_object_allocations()

                self._snapshot_count += 1

                # Check for memory leaks periodically
                if self._snapshot_count % 60 == 0:  # Every minute
                    leaks = self.detect_memory_leaks()
                    if leaks["suspected_leaks"]:
                        logger.warning(
                            f"Potential memory leaks detected: {len(leaks['suspected_leaks'])}"
                        )

                time.sleep(self.snapshot_interval)

            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                time.sleep(self.snapshot_interval)

    def _take_snapshot(self) -> MemorySnapshot:
        """Take a comprehensive memory snapshot"""
        process = psutil.Process()

        # Memory info
        memory_info = process.memory_info()
        memory_full_info = process.memory_full_info()

        # GC stats
        gc_counts = gc.get_count()

        # Tracemalloc stats
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
        else:
            current = peak = 0

        # System stats
        try:
            num_threads = process.num_threads()
        except (psutil.NoSuchProcess, AttributeError):
            num_threads = 0

        try:
            num_fds = process.num_fds() if hasattr(process, "num_fds") else 0
        except (psutil.NoSuchProcess, AttributeError):
            num_fds = 0

        return MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            shared_mb=memory_full_info.shared / 1024 / 1024,
            text_mb=memory_full_info.text / 1024 / 1024,
            lib_mb=memory_full_info.lib / 1024 / 1024,
            data_mb=memory_full_info.data / 1024 / 1024,
            dirty_mb=memory_full_info.dirty / 1024 / 1024,
            percent=process.memory_percent(),
            gc_objects=len(gc.get_objects()),
            gc_collections={i: gc_counts[i] for i in range(3)},
            tracemalloc_current=current / 1024 / 1024,
            tracemalloc_peak=peak / 1024 / 1024,
            file_descriptors=num_fds,
            threads=num_threads,
        )

    def _get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage"""
        process = psutil.Process()

        # CPU usage
        cpu_percent = process.cpu_percent()

        # Memory
        memory_mb = process.memory_info().rss / 1024 / 1024

        # Disk I/O
        io_counters = process.io_counters()
        disk_read_mb = io_counters.read_bytes / 1024 / 1024
        disk_write_mb = io_counters.write_bytes / 1024 / 1024

        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            net_recv_mb = net_io.bytes_recv / 1024 / 1024
            net_sent_mb = net_io.bytes_sent / 1024 / 1024
        except (psutil.AccessDenied, AttributeError):
            net_recv_mb = net_sent_mb = 0

        # Files and threads
        try:
            open_files = len(process.open_files())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            open_files = 0

        try:
            threads = process.num_threads()
        except (psutil.NoSuchProcess, AttributeError):
            threads = 0

        return ResourceUsage(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_io_recv_mb=net_recv_mb,
            network_io_sent_mb=net_sent_mb,
            open_files=open_files,
            threads=threads,
            timestamp=datetime.now(),
        )

    def _get_object_counts(self) -> Dict[str, int]:
        """Get counts of objects by type"""
        objects = gc.get_objects()
        type_counts = defaultdict(int)

        for obj in objects:
            type_name = type(obj).__name__
            type_counts[type_name] += 1

        return dict(type_counts)

    def _track_object_allocations(self):
        """Track object allocations and sizes"""
        objects = gc.get_objects()
        type_counts = defaultdict(int)
        type_sizes = defaultdict(int)

        for obj in objects:
            obj_type = type(obj)
            type_name = obj_type.__name__

            type_counts[type_name] += 1

            # Estimate object size
            try:
                size = sys.getsizeof(obj)
                type_sizes[type_name] += size
            except (ValueError, TypeError):
                # Some objects can't be sized
                pass

        # Update allocations
        with self._allocations_lock:
            for type_name, count in type_counts.items():
                total_size = type_sizes.get(type_name, 0)
                avg_size = total_size / count if count > 0 else 0

                self.object_allocations[type_name] = ObjectAllocation(
                    object_type=type_name,
                    count=count,
                    total_size_bytes=total_size,
                    avg_size_bytes=avg_size,
                )

    def _analyze_object_changes(
        self, initial_objects: Dict[str, int], final_objects: Dict[str, int]
    ) -> Dict[str, Any]:
        """Analyze changes in object counts"""
        changes = {}
        all_types = set(initial_objects.keys()) | set(final_objects.keys())

        for obj_type in all_types:
            initial_count = initial_objects.get(obj_type, 0)
            final_count = final_objects.get(obj_type, 0)
            delta = final_count - initial_count

            if delta != 0:
                changes[obj_type] = {
                    "initial": initial_count,
                    "final": final_count,
                    "delta": delta,
                    "percent_change": (
                        (delta / initial_count * 100) if initial_count > 0 else float("inf")
                    ),
                }

        return changes

    def detect_memory_leaks(self, window_minutes: int = 5) -> MemoryLeakReport:
        """
        Detect potential memory leaks based on recent memory trends

        Args:
            window_minutes: Time window to analyze for leaks

        Returns:
            MemoryLeakReport with analysis results
        """
        with self._snapshots_lock:
            if len(self.snapshots) < 10:
                return MemoryLeakReport(
                    suspected_leaks=[],
                    growing_objects=[],
                    uncollectable_objects=0,
                    reference_cycles=0,
                    recommendations=["Insufficient data for leak detection"],
                    severity="LOW",
                )

            # Get recent snapshots
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            recent_snapshots = [s for s in self.snapshots if s.timestamp >= cutoff_time]

            if len(recent_snapshots) < 2:
                return MemoryLeakReport(
                    suspected_leaks=[],
                    growing_objects=[],
                    uncollectable_objects=0,
                    reference_cycles=0,
                    recommendations=["Insufficient recent data"],
                    severity="LOW",
                )

        # Analyze memory trend
        memory_values = [s.rss_mb for s in recent_snapshots]
        initial_memory = memory_values[0]
        final_memory = memory_values[-1]
        memory_growth = final_memory - initial_memory

        # Calculate growth rate
        time_span = (recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp).total_seconds()
        growth_rate = memory_growth / time_span if time_span > 0 else 0

        # Detect growing object types
        growing_objects = []
        with self._allocations_lock:
            for obj_type, allocation in self.object_allocations.items():
                if allocation.count > 1000:  # Threshold for large allocations
                    growing_objects.append(allocation)

        # Check for uncollectable objects
        try:
            uncollectable = len(gc.garbage)
        except AttributeError:
            uncollectable = 0

        # Detect reference cycles (simplified)
        reference_cycles = len([obj for obj in gc.garbage if obj is not None])

        # Generate recommendations
        recommendations = []
        suspected_leaks = []

        if growth_rate > 1.0:  # More than 1MB/sec growth
            suspected_leaks.append(
                {
                    "type": "memory_growth",
                    "severity": "HIGH",
                    "growth_rate_mb_per_sec": growth_rate,
                    "total_growth_mb": memory_growth,
                }
            )
            recommendations.append("High memory growth rate detected - investigate for leaks")

        if uncollectable_objects > 0:
            suspected_leaks.append(
                {
                    "type": "uncollectable_objects",
                    "severity": "MEDIUM",
                    "count": uncollectable_objects,
                }
            )
            recommendations.append("Uncollectable objects detected - check for reference cycles")

        if len(growing_objects) > 5:
            suspected_leaks.append(
                {
                    "type": "object_growth",
                    "severity": "MEDIUM",
                    "growing_types": len(growing_objects),
                }
            )
            recommendations.append(
                "Multiple object types growing rapidly - analyze allocation patterns"
            )

        # Determine overall severity
        if growth_rate > 5.0 or uncollectable_objects > 100:
            severity = "CRITICAL"
        elif growth_rate > 1.0 or uncollectable_objects > 10:
            severity = "HIGH"
        elif len(suspected_leaks) > 0:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        if not recommendations:
            recommendations.append("No obvious memory leaks detected")

        return MemoryLeakReport(
            suspected_leaks=suspected_leaks,
            growing_objects=growing_objects[:10],  # Top 10
            uncollectable_objects=uncollectable,
            reference_cycles=reference_cycles,
            recommendations=recommendations,
            severity=severity,
        )

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        with self._snapshots_lock:
            if not self.snapshots:
                return {"error": "No memory snapshots available"}

            latest_snapshot = self.snapshots[-1]
            memory_values = [s.rss_mb for s in self.snapshots]

        # Basic statistics
        stats = {
            "current_memory_mb": latest_snapshot.rss_mb,
            "peak_memory_mb": max(memory_values),
            "min_memory_mb": min(memory_values),
            "avg_memory_mb": sum(memory_values) / len(memory_values),
            "total_snapshots": len(self.snapshots),
            "monitoring_duration_hours": (datetime.now() - self._start_time).total_seconds() / 3600,
            "gc_objects": latest_snapshot.gc_objects,
            "file_descriptors": latest_snapshot.file_descriptors,
            "threads": latest_snapshot.threads,
        }

        # Memory trend analysis
        if len(memory_values) > 10:
            # Simple linear regression for trend
            n = len(memory_values)
            x = list(range(n))
            sum_x = sum(x)
            sum_y = sum(memory_values)
            sum_xy = sum(x[i] * memory_values[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
            stats["memory_trend_mb_per_snapshot"] = slope
            stats["memory_trend_mb_per_hour"] = slope * (3600 / self.snapshot_interval)

        # Top object allocations
        with self._allocations_lock:
            if self.object_allocations:
                sorted_allocations = sorted(
                    self.object_allocations.values(), key=lambda x: x.total_size_bytes, reverse=True
                )
                stats["top_object_allocations"] = [
                    {
                        "type": obj.object_type,
                        "count": obj.count,
                        "total_size_mb": obj.total_size_bytes / 1024 / 1024,
                        "avg_size_bytes": obj.avg_size_bytes,
                    }
                    for obj in sorted_allocations[:10]
                ]

        # Resource usage summary
        if self.resource_usage:
            recent_usage = (
                self.resource_usage[-100:]
                if len(self.resource_usage) > 100
                else self.resource_usage
            )
            stats.update(
                {
                    "avg_cpu_percent": sum(u.cpu_percent for u in recent_usage) / len(recent_usage),
                    "max_cpu_percent": max(u.cpu_percent for u in recent_usage),
                    "avg_open_files": sum(u.open_files for u in recent_usage) / len(recent_usage),
                    "max_open_files": max(u.open_files for u in recent_usage),
                }
            )

        return stats

    async def generate_memory_report(self) -> str:
        """Generate comprehensive memory analysis report"""
        stats = self.get_memory_statistics()
        leak_report = self.detect_memory_leaks()

        report = []
        report.append("# Memory Profiling Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        # Summary
        report.append("## Memory Summary")
        report.append(f"- Current Memory: {stats['current_memory_mb']:.2f} MB")
        report.append(f"- Peak Memory: {stats['peak_memory_mb']:.2f} MB")
        report.append(f"- Average Memory: {stats['avg_memory_mb']:.2f} MB")
        report.append(f"- GC Objects: {stats['gc_objects']:,}")
        report.append(f"- File Descriptors: {stats['file_descriptors']}")
        report.append(f"- Threads: {stats['threads']}")
        report.append(f"- Monitoring Duration: {stats['monitoring_duration_hours']:.2f} hours")
        report.append("")

        # Memory trend
        if "memory_trend_mb_per_hour" in stats:
            trend = stats["memory_trend_mb_per_hour"]
            if trend > 0:
                report.append(f"⚠️ **Memory Growing**: +{trend:.2f} MB/hour")
            else:
                report.append(f"✅ **Memory Stable**: {trend:.2f} MB/hour")
            report.append("")

        # Leak detection
        report.append("## Memory Leak Analysis")
        report.append(f"Severity: {leak_report.severity}")
        report.append("")

        if leak_report.suspected_leaks:
            report.append("### Suspected Leaks:")
            for leak in leak_report.suspected_leaks:
                report.append(
                    f"- **{leak['type'].title()}** (Severity: {leak.get('severity', 'UNKNOWN')})"
                )
                for key, value in leak.items():
                    if key not in ["type", "severity"]:
                        report.append(f"  - {key}: {value}")
            report.append("")

        if leak_report.recommendations:
            report.append("### Recommendations:")
            for rec in leak_report.recommendations:
                report.append(f"- {rec}")
            report.append("")

        # Top object allocations
        if "top_object_allocations" in stats:
            report.append("## Top Object Allocations")
            for obj in stats["top_object_allocations"][:5]:
                report.append(
                    f"- **{obj['type']}**: {obj['count']:,} objects, "
                    f"{obj['total_size_mb']:.2f} MB total"
                )
            report.append("")

        # Resource usage
        if "avg_cpu_percent" in stats:
            report.append("## Resource Usage")
            report.append(f"- Average CPU: {stats['avg_cpu_percent']:.1f}%")
            report.append(f"- Peak CPU: {stats['max_cpu_percent']:.1f}%")
            report.append(f"- Average Open Files: {stats['avg_open_files']:.1f}")
            report.append(f"- Peak Open Files: {stats['max_open_files']}")
            report.append("")

        return "\n".join(report)

    async def _save_profile(self, analysis: Dict[str, Any]):
        """Save memory profile to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"memory_profile_{analysis['operation_name']}_{timestamp}.json"
        filepath = self.output_dir / filename

        # Convert datetime objects to strings
        analysis["timestamp"] = datetime.now().isoformat()

        with open(filepath, "w") as f:
            json.dump(analysis, f, indent=2, default=str)

    async def save_full_report(self):
        """Save complete memory analysis report"""
        report = await self.generate_memory_report()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"memory_report_{timestamp}.md"
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            f.write(report)

        logger.info(f"Memory report saved to {filepath}")

    async def cleanup(self):
        """Cleanup profiler resources"""
        self.stop_monitoring()

        # Save final report
        await self.save_full_report()

        # Stop tracemalloc
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            tracemalloc.stop()

        logger.info("Memory profiler cleanup completed")


# Global profiler instance
_global_profiler: Optional[MemoryProfiler] = None


def get_memory_profiler() -> MemoryProfiler:
    """Get or create global memory profiler instance"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = MemoryProfiler()
    return _global_profiler


def create_memory_profiler(**kwargs) -> MemoryProfiler:
    """Create new memory profiler instance"""
    return MemoryProfiler(**kwargs)
