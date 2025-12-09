"""
Advanced Memory Management and Optimization

This module provides comprehensive memory optimization features:
- Fixed memory leak detection with automatic cleanup
- Periodic cleanup of stale data
- Memory usage monitoring with alerts
- Optimized data structures for space efficiency
- Weak reference management
- Memory pool allocation for small objects
"""

from __future__ import annotations

import asyncio
import gc
import logging
import threading
import time
import tracemalloc
import weakref
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
)

try:
    from typing import WeakSet
except ImportError:
    # Python 3.13+ compatibility
    from weakref import WeakSet

import psutil

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class MemoryStats:
    """Memory usage statistics"""

    rss_mb: float = 0.0  # Resident Set Size in MB
    vms_mb: float = 0.0  # Virtual Memory Size in MB
    percent: float = 0.0  # Memory percentage
    available_mb: float = 0.0
    gc_objects: int = 0
    gc_collections: Dict[int, int] = field(default_factory=dict)
    tracemalloc_current: int = 0
    tracemalloc_peak: int = 0
    file_descriptors: int = 0
    threads: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MemoryLeakInfo:
    """Information about a potential memory leak"""

    object_type: str
    count: int
    size_bytes: int
    growth_rate: float  # objects per minute
    first_seen: datetime
    last_seen: datetime
    sample_refs: List[weakref.ref] = field(default_factory=list)


@dataclass
class MemoryAlert:
    """Memory usage alert"""

    level: str  # INFO, WARNING, ERROR, CRITICAL
    message: str
    current_usage_mb: float
    threshold_mb: float
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


class WeakReferenceManager:
    """Manager for weak references with automatic cleanup"""

    def __init__(self, cleanup_interval: float = 60.0):
        self.cleanup_interval = cleanup_interval
        self._refs: Dict[str, WeakSet] = defaultdict(WeakSet)
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

        # Metrics
        self._stats = {"refs_registered": 0, "refs_cleaned": 0, "callbacks_executed": 0}

    def start(self):
        """Start automatic cleanup"""
        if self._running:
            return

        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True, name="WeakRefCleanup"
        )
        self._cleanup_thread.start()
        logger.info("Weak reference manager started")

    def stop(self):
        """Stop cleanup thread"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
        logger.info("Weak reference manager stopped")

    def register(self, obj: Any, category: str = "default", callback: Optional[Callable] = None):
        """Register object for weak reference tracking"""

        def cleanup_callback(ref):
            with self._lock:
                self._stats["refs_cleaned"] += 1
                if category in self._callbacks:
                    for cb in self._callbacks[category]:
                        try:
                            cb(ref)
                        except Exception as e:
                            logger.warning(f"Cleanup callback error: {e}")
                    self._stats["callbacks_executed"] += len(self._callbacks[category])

        ref = weakref.ref(obj, cleanup_callback)
        with self._lock:
            self._refs[category].add(ref)
            if callback:
                self._callbacks[category].append(callback)
            self._stats["refs_registered"] += 1

        return ref

    def get_live_objects(self, category: str = "default") -> List[Any]:
        """Get live objects in category"""
        live_objects = []
        with self._lock:
            if category in self._refs:
                for ref in self._refs[category]:
                    obj = ref()
                    if obj is not None:
                        live_objects.append(obj)
        return live_objects

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        with self._lock:
            category_stats = {}
            for cat, refs in self._refs.items():
                live_count = sum(1 for ref in refs if ref() is not None)
                category_stats[cat] = {"total_refs": len(refs), "live_objects": live_count}

            return {**self._stats, "categories": category_stats}

    def _cleanup_loop(self):
        """Periodic cleanup loop"""
        while self._running:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_dead_references()
            except Exception as e:
                logger.error(f"Weak reference cleanup error: {e}")

    def _cleanup_dead_references(self):
        """Remove dead references"""
        with self._lock:
            for category in list(self._refs.keys()):
                live_refs = WeakSet(ref for ref in self._refs[category] if ref() is not None)
                dead_count = len(self._refs[category]) - len(live_refs)
                if dead_count > 0:
                    self._stats["refs_cleaned"] += dead_count
                self._refs[category] = live_refs


class MemoryPool:
    """Memory pool for efficient allocation of small objects"""

    def __init__(self, pool_size: int = 1000, object_size: int = 1024):
        self.pool_size = pool_size
        self.object_size = object_size
        self._pool = bytearray()
        self._free_blocks: List[Tuple[int, int]] = []
        self._allocated_blocks: Dict[int, int] = {}
        self._lock = threading.Lock()
        self._next_offset = 0

        # Pre-allocate pool
        self._pool.extend(b"\x00" * (pool_size * object_size))

        # Initialize free blocks
        for i in range(pool_size):
            self._free_blocks.append((i * object_size, object_size))

    def allocate(self, size: int) -> Optional[memoryview]:
        """Allocate memory block from pool"""
        if size > self.object_size:
            return None  # Too large for pool

        with self._lock:
            # Find suitable free block
            for i, (offset, block_size) in enumerate(self._free_blocks):
                if block_size >= size:
                    # Mark as allocated
                    self._allocated_blocks[offset] = size
                    del self._free_blocks[i]

                    # Return memory view
                    return memoryview(self._pool)[offset : offset + size]

        return None  # No suitable block found

    def deallocate(self, block: memoryview):
        """Deallocate memory block back to pool"""
        if not block:
            return

        with self._lock:
            offset = block.obj_start if hasattr(block, "obj_start") else 0
            size = len(block)

            if offset in self._allocated_blocks:
                del self._allocated_blocks[offset]
                self._free_blocks.append((offset, size))

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            total_allocated = sum(self._allocated_blocks.values())
            free_blocks = sum(size for _, size in self._free_blocks)

            return {
                "pool_size": self.pool_size,
                "object_size": self.object_size,
                "total_allocated_bytes": total_allocated,
                "free_bytes": free_blocks,
                "utilization_percent": (
                    total_allocated / (self.pool_size * self.object_size) * 100
                ),
                "allocated_blocks": len(self._allocated_blocks),
                "free_blocks_count": len(self._free_blocks),
            }


class OptimizedResourceTracker:
    """Optimized resource tracker with automatic cleanup and monitoring"""

    def __init__(
        self,
        cleanup_interval: float = 60.0,
        max_resource_age: float = 300.0,
        enable_leak_detection: bool = True,
    ):
        self.cleanup_interval = cleanup_interval
        self.max_resource_age = max_resource_age
        self.enable_leak_detection = enable_leak_detection

        # Resource tracking
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._resource_types: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

        # Leak detection
        self._object_counts: Dict[str, int] = defaultdict(int)
        self._growth_rates: Dict[str, float] = defaultdict(float)
        self._last_cleanup = time.time()

        # Metrics
        self._metrics = {
            "resources_registered": 0,
            "resources_unregistered": 0,
            "auto_cleaned": 0,
            "leaks_detected": 0,
            "memory_freed_mb": 0.0,
        }

        # Monitoring
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Memory tracking
        self._memory_history: deque = deque(maxlen=1000)
        self._alerts: List[MemoryAlert] = []

    async def start_monitoring(self):
        """Start resource monitoring"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Resource tracker monitoring started")

    async def stop_monitoring(self):
        """Stop resource monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource tracker monitoring stopped")

    async def register_resource(
        self,
        resource_id: str,
        resource_type: str,
        resource_obj: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cleanup_callback: Optional[Callable] = None,
    ):
        """Register resource for tracking"""
        async with self._lock:
            self._resources[resource_id] = {
                "type": resource_type,
                "object": resource_obj,
                "created_at": time.time(),
                "last_accessed": time.time(),
                "size_bytes": self._estimate_size(resource_obj) if resource_obj else 0,
                "metadata": metadata or {},
                "cleanup_callback": cleanup_callback,
            }
            self._resource_types[resource_type].add(resource_id)
            self._metrics["resources_registered"] += 1

            # Track object counts for leak detection
            if resource_obj:
                obj_type = type(resource_obj).__name__
                self._object_counts[obj_type] += 1

        logger.debug(f"Resource registered: {resource_id} ({resource_type})")

    async def unregister_resource(self, resource_id: str):
        """Unregister resource"""
        async with self._lock:
            if resource_id in self._resources:
                resource_info = self._resources[resource_id]
                resource_type = resource_info["type"]

                # Execute cleanup callback
                if resource_info.get("cleanup_callback"):
                    try:
                        await resource_info["cleanup_callback"](resource_info.get("object"))
                    except Exception as e:
                        logger.warning(f"Cleanup callback error for {resource_id}: {e}")

                # Remove from tracking
                del self._resources[resource_id]
                self._resource_types[resource_type].discard(resource_id)
                self._metrics["resources_unregistered"] += 1

                logger.debug(f"Resource unregistered: {resource_id}")

    async def access_resource(self, resource_id: str) -> Optional[Any]:
        """Access resource and update last accessed time"""
        async with self._lock:
            if resource_id in self._resources:
                self._resources[resource_id]["last_accessed"] = time.time()
                return self._resources[resource_id].get("object")
        return None

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_resources()
                await self._update_memory_stats()
                await self._detect_memory_leaks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")

    async def _cleanup_expired_resources(self):
        """Clean up expired resources"""
        current_time = time.time()
        expired_resources = []

        async with self._lock:
            for resource_id, info in self._resources.items():
                age = current_time - info["created_at"]
                if age > self.max_resource_age:
                    expired_resources.append(resource_id)

            for resource_id in expired_resources:
                await self.unregister_resource(resource_id)
                self._metrics["auto_cleaned"] += 1

        if expired_resources:
            logger.info(f"Auto-cleaned {len(expired_resources)} expired resources")

    async def _update_memory_stats(self):
        """Update memory usage statistics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            stats = MemoryStats(
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=process.memory_percent(),
                available_mb=psutil.virtual_memory().available / 1024 / 1024,
                gc_objects=len(gc.get_objects()),
                gc_collections={i: gc.get_count()[i] for i in range(3)},
                file_descriptors=process.num_fds() if hasattr(process, "num_fds") else 0,
                threads=process.num_threads() if hasattr(process, "num_threads") else 0,
            )

            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                stats.tracemalloc_current = current
                stats.tracemalloc_peak = peak

            self._memory_history.append(stats)

            # Check for memory alerts
            await self._check_memory_alerts(stats)

        except Exception as e:
            logger.error(f"Memory stats update error: {e}")

    async def _check_memory_alerts(self, stats: MemoryStats):
        """Check for memory usage alerts"""
        alerts = []

        # High memory usage alert
        if stats.rss_mb > 1000:  # > 1GB
            alerts.append(
                MemoryAlert(
                    level="WARNING" if stats.rss_mb < 2000 else "ERROR",
                    message=f"High memory usage: {stats.rss_mb:.1f} MB",
                    current_usage_mb=stats.rss_mb,
                    threshold_mb=1000,
                    details={"percent": stats.percent},
                )
            )

        # High object count alert
        if stats.gc_objects > 100000:
            alerts.append(
                MemoryAlert(
                    level="WARNING",
                    message=f"High object count: {stats.gc_objects:,}",
                    current_usage_mb=stats.rss_mb,
                    threshold_mb=0,
                    details={"gc_objects": stats.gc_objects},
                )
            )

        # Many file descriptors
        if stats.file_descriptors > 1000:
            alerts.append(
                MemoryAlert(
                    level="WARNING",
                    message=f"Many file descriptors: {stats.file_descriptors}",
                    current_usage_mb=stats.rss_mb,
                    threshold_mb=0,
                    details={"file_descriptors": stats.file_descriptors},
                )
            )

        self._alerts.extend(alerts)

        # Keep only recent alerts (last 100)
        self._alerts = self._alerts[-100:]

        for alert in alerts:
            logger.warning(f"Memory alert [{alert.level}]: {alert.message}")

    async def _detect_memory_leaks(self):
        """Detect potential memory leaks"""
        if not self.enable_leak_detection:
            return

        current_time = time.time()
        time_since_last = current_time - self._last_cleanup

        if time_since_last < 60:  # Check every minute
            return

        self._last_cleanup = current_time

        try:
            # Get current object counts
            current_counts = defaultdict(int)
            for obj in gc.get_objects():
                obj_type = type(obj).__name__
                current_counts[obj_type] += 1

            # Calculate growth rates
            for obj_type, count in current_counts.items():
                prev_count = self._object_counts.get(obj_type, 0)
                growth_rate = (count - prev_count) / (time_since_last / 60)  # per minute
                self._growth_rates[obj_type] = growth_rate

            # Update object counts
            self._object_counts = current_counts

            # Detect suspicious growth
            suspicious_types = []
            for obj_type, growth_rate in self._growth_rates.items():
                if growth_rate > 100 and current_counts[obj_type] > 1000:  # > 100 objects/minute
                    suspicious_types.append((obj_type, growth_rate, current_counts[obj_type]))

            if suspicious_types:
                self._metrics["leaks_detected"] += len(suspicious_types)
                logger.warning(f"Potential memory leaks detected: {suspicious_types}")

        except Exception as e:
            logger.error(f"Memory leak detection error: {e}")

    def _estimate_size(self, obj: Any) -> int:
        """Estimate object size in bytes"""
        try:
            import sys

            return sys.getsizeof(obj)
        except Exception:
            return 0

    async def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return stats"""
        before_counts = [gc.get_count()[i] for i in range(3)]

        # Run garbage collection
        collected = gc.collect()

        after_counts = [gc.get_count()[i] for i in range(3)]

        return {
            "collected_objects": collected,
            "before_collections": dict(enumerate(before_counts)),
            "after_collections": dict(enumerate(after_counts)),
        }

    def get_memory_trend(self, minutes: int = 60) -> Dict[str, Any]:
        """Get memory usage trend"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_stats = [stat for stat in self._memory_history if stat.timestamp >= cutoff_time]

        if not recent_stats:
            return {"error": "No recent memory data available"}

        rss_values = [stat.rss_mb for stat in recent_stats]

        return {
            "duration_minutes": minutes,
            "samples": len(recent_stats),
            "current_mb": rss_values[-1],
            "min_mb": min(rss_values),
            "max_mb": max(rss_values),
            "avg_mb": sum(rss_values) / len(rss_values),
            "trend_mb_per_minute": (rss_values[-1] - rss_values[0])
            / len(rss_values)
            * (len(recent_stats) / minutes),
        }

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive resource tracking report"""
        return {
            "metrics": self._metrics,
            "resource_counts": {
                resource_type: len(resources)
                for resource_type, resources in self._resource_types.items()
            },
            "total_resources": len(self._resources),
            "memory_trend_60min": self.get_memory_trend(60),
            "recent_alerts": [
                {
                    "level": alert.level,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "details": alert.details,
                }
                for alert in self._alerts[-10:]  # Last 10 alerts
            ],
            "object_growth_rates": dict(
                sorted(self._growth_rates.items(), key=lambda x: x[1], reverse=True)[:10]
            ),  # Top 10 growing types
        }

    @contextmanager
    def track_resource(
        self, resource_id: str, resource_type: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Context manager for automatic resource tracking"""

        async def register():
            await self.register_resource(resource_id, resource_type, metadata=metadata)

        async def unregister():
            await self.unregister_resource(resource_id)

        # This is a sync context manager, but we need async operations
        # In practice, you'd use asynccontextmanager instead
        loop = asyncio.get_event_loop()
        loop.run_until_complete(register())

        try:
            yield
        finally:
            loop.run_until_complete(unregister())


# Global resource tracker instance
_global_tracker: Optional[OptimizedResourceTracker] = None
_global_weak_ref_manager: Optional[WeakReferenceManager] = None


def get_resource_tracker() -> OptimizedResourceTracker:
    """Get or create global resource tracker"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = OptimizedResourceTracker()
    return _global_tracker


def get_weak_ref_manager() -> WeakReferenceManager:
    """Get or create global weak reference manager"""
    global _global_weak_ref_manager
    if _global_weak_ref_manager is None:
        _global_weak_ref_manager = WeakReferenceManager()
        _global_weak_ref_manager.start()
    return _global_weak_ref_manager


@asynccontextmanager
async def tracked_resource(
    resource_id: str,
    resource_type: str,
    resource_obj: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
    cleanup_callback: Optional[Callable] = None,
):
    """Async context manager for tracked resources"""
    tracker = get_resource_tracker()
    await tracker.register_resource(
        resource_id, resource_type, resource_obj, metadata, cleanup_callback
    )
    try:
        yield resource_obj
    finally:
        await tracker.unregister_resource(resource_id)


def optimize_memory_usage():
    """Apply memory optimizations to the current process"""
    # Enable aggressive garbage collection
    gc.set_threshold(700, 10, 10)

    # Start tracking
    tracker = get_resource_tracker()
    weak_manager = get_weak_ref_manager()

    # Enable tracemalloc if not already enabled
    if not tracemalloc.is_tracing():
        tracemalloc.start(25)  # Track 25 frames

    logger.info("Memory optimizations applied")


def get_memory_optimization_report() -> str:
    """Generate memory optimization report"""
    tracker = get_resource_tracker()
    weak_manager = get_weak_ref_manager()

    report = []
    report.append("# Memory Optimization Report")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("")

    # Resource tracking report
    tracker_report = tracker.get_comprehensive_report()
    report.append("## Resource Tracking")
    report.append(f"- Total Resources: {tracker_report['total_resources']}")
    report.append(f"- Resources Registered: {tracker_report['metrics']['resources_registered']}")
    report.append(
        f"- Resources Unregistered: {tracker_report['metrics']['resources_unregistered']}"
    )
    report.append(f"- Auto-cleaned: {tracker_report['metrics']['auto_cleaned']}")
    report.append(f"- Leaks Detected: {tracker_report['metrics']['leaks_detected']}")
    report.append("")

    # Memory trend
    if "memory_trend_60min" in tracker_report and "samples" in tracker_report["memory_trend_60min"]:
        trend = tracker_report["memory_trend_60min"]
        report.append("## Memory Trend (60 minutes)")
        report.append(f"- Current: {trend['current_mb']:.1f} MB")
        report.append(f"- Average: {trend['avg_mb']:.1f} MB")
        report.append(f"- Peak: {trend['max_mb']:.1f} MB")
        report.append(f"- Trend: {trend['trend_mb_per_minute']:.2f} MB/min")
        report.append("")

    # Recent alerts
    if tracker_report["recent_alerts"]:
        report.append("## Recent Alerts")
        for alert in tracker_report["recent_alerts"]:
            report.append(f"- **{alert['level']}**: {alert['message']}")
        report.append("")

    # Weak reference stats
    weak_stats = weak_manager.get_stats()
    report.append("## Weak Reference Management")
    report.append(f"- References Registered: {weak_stats['refs_registered']}")
    report.append(f"- References Cleaned: {weak_stats['refs_cleaned']}")
    report.append(f"- Callbacks Executed: {weak_stats['callbacks_executed']}")
    report.append("")

    return "\n".join(report)
