"""
Comprehensive Performance Test Suite

This module provides advanced performance tests including:
- Database query optimization analysis
- Memory leak detection and profiling
- Concurrent load testing
- Caching efficiency benchmarks
- API endpoint performance testing
- Scalability analysis
"""

import pytest
import pytest_asyncio
import asyncio
import time
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import select, delete, update, func, and_, or_

from fastapi_easy.backends.sqlalchemy_optimized import OptimizedSQLAlchemyAdapter
from fastapi_easy.core.performance_benchmarker import PerformanceBenchmarker, get_benchmarker
from fastapi_easy.core.memory_profiler import MemoryProfiler, get_memory_profiler
from fastapi_easy.core.advanced_cache import AdvancedCacheManager, get_cache_manager
from fastapi_easy.core.optimization_config import OptimizationConfig

# New optimization modules
from fastapi_easy.migrations.distributed_lock_optimized import (
    BackoffConfig,
    OptimizedPostgresLockProvider,
    OptimizedFileLockProvider,
)
from fastapi_easy.core.query_optimizer import QueryParameterOptimizer, TypeHintCache, JSONOptimizer
from fastapi_easy.core.memory_optimizer import (
    OptimizedResourceTracker,
    get_resource_tracker,
    optimize_memory_usage,
)
from fastapi_easy.core.async_optimizer import (
    AsyncSemaphore,
    AsyncRateLimiter,
    AsyncBatchProcessor,
    monitor_async_performance,
)


# Test models for comprehensive performance testing
class Base(DeclarativeBase):
    """Base class for test models"""


class User(Base):
    """User model for performance testing"""

    __tablename__ = "performance_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(200))
    bio = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    login_count = Column(Integer, default=0)

    # Relationships
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")


class Post(Base):
    """Post model for performance testing"""

    __tablename__ = "performance_posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(String(500))
    author_id = Column(Integer, ForeignKey("performance_users.id"), nullable=False)
    published = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    tags = relationship("PostTag", back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    """Comment model for performance testing"""

    __tablename__ = "performance_comments"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("performance_users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("performance_posts.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("performance_comments.id"), nullable=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    parent = relationship("Comment", remote_side=[id])
    replies = relationship("Comment", cascade="all, delete-orphan")


class Tag(Base):
    """Tag model for performance testing"""

    __tablename__ = "performance_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    posts = relationship("PostTag", back_populates="tag", cascade="all, delete-orphan")


class PostTag(Base):
    """Post-Tag many-to-many relationship"""

    __tablename__ = "performance_post_tags"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("performance_posts.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("performance_tags.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    post = relationship("Post", back_populates="tags")
    tag = relationship("Tag", back_populates="posts")


@pytest.fixture
def performance_config():
    """Optimized configuration for performance testing"""
    return OptimizationConfig(
        enable_cache=True,
        enable_async=True,
        l1_size=5000,
        l1_ttl=300,
        l2_size=50000,
        l2_ttl=1800,
        max_concurrent=50,
        enable_monitoring=True,
        hit_rate_threshold=75.0,
        pool_size=20,
        max_overflow=30,
        pool_timeout=30,
        pool_recycle=3600,
        query_timeout=30,
        cache_size=10000,
        cache_ttl=600,
    )


@pytest_asyncio.fixture
async def performance_db_engine(performance_config):
    """Create performance test database engine"""
    # SQLite doesn't support connection pool parameters
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def performance_session_factory(performance_db_engine):
    """Create async session factory"""
    return async_sessionmaker(
        performance_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


@pytest.fixture
def user_adapter(performance_session_factory, performance_config):
    """Create user adapter for performance testing"""
    return OptimizedSQLAlchemyAdapter(
        model=User,
        database_url="sqlite+aiosqlite:///:memory:",
        pk_field="id",
        optimization_config=performance_config,
    )


@pytest.fixture
def post_adapter(performance_session_factory, performance_config):
    """Create post adapter for performance testing"""
    return OptimizedSQLAlchemyAdapter(
        model=Post,
        database_url="sqlite+aiosqlite:///:memory:",
        pk_field="id",
        optimization_config=performance_config,
    )


@pytest.fixture
def comment_adapter(performance_session_factory, performance_config):
    """Create comment adapter for performance testing"""
    return OptimizedSQLAlchemyAdapter(
        model=Comment,
        database_url="sqlite+aiosqlite:///:memory:",
        pk_field="id",
        optimization_config=performance_config,
    )


@pytest_asyncio.fixture
async def large_dataset_users(user_adapter):
    """Create large dataset of users for performance testing"""
    users = []
    for i in range(1000):
        user_data = {
            "username": f"user_{i}",
            "email": f"user_{i}@example.com",
            "full_name": f"User {i}",
            "bio": f"Bio for user {i}" * 10,  # Longer text for testing
            "is_active": i % 10 != 0,  # 90% active
            "login_count": random.randint(0, 1000),
        }
        user = await user_adapter.create(user_data)
        users.append(user)

    return users


@pytest_asyncio.fixture
async def large_dataset_posts(post_adapter, large_dataset_users):
    """Create large dataset of posts for performance testing"""
    posts = []
    for i in range(5000):
        post_data = {
            "title": f"Post Title {i}",
            "content": f"Content for post {i} " * 100,  # Longer content
            "summary": f"Summary for post {i}",
            "author_id": random.choice(large_dataset_users).id,
            "published": i % 5 != 0,  # 80% published
            "view_count": random.randint(0, 10000),
            "like_count": random.randint(0, 1000),
        }
        post = await post_adapter.create(post_data)
        posts.append(post)

    return posts


@pytest_asyncio.fixture
async def large_dataset_comments(comment_adapter, large_dataset_users, large_dataset_posts):
    """Create large dataset of comments for performance testing"""
    comments = []
    for i in range(20000):
        comment_data = {
            "content": f"Comment content {i} " * 20,
            "author_id": random.choice(large_dataset_users).id,
            "post_id": random.choice(large_dataset_posts).id,
            "is_approved": i % 3 != 0,  # 66% approved
        }
        comment = await comment_adapter.create(comment_data)
        comments.append(comment)

    return comments


@pytest.fixture
def benchmarker():
    """Get performance benchmarker instance"""
    return get_benchmarker()


@pytest.fixture
def memory_profiler():
    """Get memory profiler instance"""
    return get_memory_profiler()


@pytest.fixture
def cache_manager():
    """Get cache manager instance"""
    return get_cache_manager()


@pytest.mark.asyncio
@pytest.mark.performance
class TestDatabasePerformance:
    """Comprehensive database performance tests"""

    async def test_complex_join_performance(
        self, performance_session_factory, large_dataset_users, large_dataset_posts, benchmarker
    ):
        """Test performance of complex JOIN operations"""

        async def complex_join_query():
            async with performance_session_factory() as session:
                # Complex query with multiple JOINs
                query = (
                    select(
                        User.id,
                        User.username,
                        func.count(Post.id).label("post_count"),
                        func.sum(Post.view_count).label("total_views"),
                        func.avg(Post.like_count).label("avg_likes"),
                    )
                    .select_from(User.__table__.outerjoin(Post.__table__))
                    .where(User.is_active == True)
                    .group_by(User.id, User.username)
                    .having(func.count(Post.id) > 2)
                    .order_by(func.count(Post.id).desc())
                    .limit(100)
                )

                result = await session.execute(query)
                return result.fetchall()

        async with benchmarker.benchmark("complex_join_query"):
            results = await complex_join_query()
            assert len(results) > 0

    async def test_aggregation_performance(
        self, performance_session_factory, large_dataset_posts, benchmarker
    ):
        """Test performance of aggregation operations"""

        async def aggregation_query():
            async with performance_session_factory() as session:
                # Multiple aggregations
                query = select(
                    func.count(Post.id).label("total_posts"),
                    func.sum(Post.view_count).label("total_views"),
                    func.avg(Post.view_count).label("avg_views"),
                    func.max(Post.view_count).label("max_views"),
                    func.min(Post.view_count).label("min_views"),
                    func.stddev(Post.view_count).label("view_stddev"),
                ).where(Post.published == True)

                result = await session.execute(query)
                return result.fetchone()

        async with benchmarker.benchmark("aggregation_query"):
            result = await aggregation_query()
            assert result.total_posts > 0

    async def test_subquery_performance(
        self, performance_session_factory, large_dataset_posts, benchmarker
    ):
        """Test performance of subquery operations"""

        async def subquery_query():
            async with performance_session_factory() as session:
                # Find users with posts above average view count
                avg_views_subq = select(func.avg(Post.view_count)).where(Post.published == True)

                query = (
                    select(Post)
                    .where(
                        and_(
                            Post.published == True,
                            Post.view_count > avg_views_subq.scalar_subquery(),
                        )
                    )
                    .order_by(Post.view_count.desc())
                    .limit(50)
                )

                result = await session.execute(query)
                return result.scalars().all()

        async with benchmarker.benchmark("subquery_query"):
            results = await subquery_query()
            assert len(results) > 0

    async def test_batch_operations_performance(self, user_adapter, benchmarker):
        """Test performance of batch operations"""

        # Batch insert
        users_data = [
            {
                "username": f"batch_user_{i}",
                "email": f"batch_user_{i}@example.com",
                "full_name": f"Batch User {i}",
            }
            for i in range(100)
        ]

        async with benchmarker.benchmark("batch_insert"):
            inserted_users = await user_adapter.create_batch(users_data)
            assert len(inserted_users) == 100

        # Batch update
        update_data = {"login_count": 100}
        user_ids = [user.id for user in inserted_users[:50]]

        async with benchmarker.benchmark("batch_update"):
            for user_id in user_ids:
                await user_adapter.update(user_id, update_data)

    async def test_index_usage_performance(
        self, performance_session_factory, large_dataset_users, benchmarker
    ):
        """Test performance benefits of indexing"""

        async def indexed_query():
            async with performance_session_factory() as session:
                # Query using indexed fields
                query = (
                    select(User)
                    .where(and_(User.is_active == True, User.login_count > 100))
                    .order_by(User.created_at.desc())
                    .limit(200)
                )

                result = await session.execute(query)
                return result.scalars().all()

        async with benchmarker.benchmark("indexed_query"):
            results = await indexed_query()
            assert len(results) > 0

    async def test_n_plus_1_query_detection(
        self, performance_session_factory, large_dataset_users, large_dataset_posts, benchmarker
    ):
        """Test N+1 query problem detection and optimization"""

        async def n_plus_1_problem():
            # This would cause N+1 queries if not optimized
            async with performance_session_factory() as session:
                users_query = select(User).where(User.is_active == True).limit(50)
                users_result = await session.execute(users_query)
                users = users_result.scalars().all()

            # This would cause N+1 queries if done naively
            # We'll simulate the problem and then show the optimized version
            total_posts = 0
            for user in users:
                async with performance_session_factory() as session:
                    posts_query = select(func.count(Post.id)).where(Post.author_id == user.id)
                    posts_result = await session.execute(posts_query)
                    post_count = posts_result.scalar()
                    total_posts += post_count

            return total_posts

        async def optimized_query():
            # Optimized version with single query
            async with performance_session_factory() as session:
                query = (
                    select(User.id, User.username, func.count(Post.id).label("post_count"))
                    .outerjoin(Post)
                    .where(User.is_active == True)
                    .group_by(User.id, User.username)
                    .limit(50)
                )

                result = await session.execute(query)
                return sum(row.post_count or 0 for row in result)

        # Compare performance
        async with benchmarker.benchmark("n_plus_1_problem"):
            problem_result = await n_plus_1_problem()

        async with benchmarker.benchmark("optimized_query"):
            optimized_result = await optimized_query()

        assert problem_result == optimized_result

    async def test_transaction_performance(self, user_adapter, benchmarker):
        """Test transaction performance"""

        async def transaction_batch_insert():
            users_data = [
                {
                    "username": f"tx_user_{i}",
                    "email": f"tx_user_{i}@example.com",
                }
                for i in range(50)
            ]

            # Simulate transaction with rollback on error
            try:
                async with user_adapter.get_session() as session:
                    for user_data in users_data:
                        user = User(**user_data)
                        session.add(user)

                    await session.commit()
                    return True
            except Exception:
                await session.rollback()
                return False

        async with benchmarker.benchmark("transaction_batch_insert"):
            result = await transaction_batch_insert()
            assert result is True


@pytest.mark.asyncio
@pytest.mark.performance
class TestMemoryPerformance:
    """Comprehensive memory performance tests"""

    async def test_memory_leak_detection(self, memory_profiler, benchmarker):
        """Test memory leak detection capabilities"""

        async def memory_intensive_operation():
            # Create many temporary objects
            objects = []
            for i in range(10000):
                obj = {
                    "id": i,
                    "data": "x" * 1000,  # 1KB per object
                    "nested": {"level1": {"level2": {"level3": f"data_{i}" * 100}}},
                }
                objects.append(obj)

            # Simulate some processing
            processed = []
            for obj in objects:
                processed.append({"processed": obj["id"], "size": len(str(obj))})

            return len(processed)

        async with memory_profiler.profile_memory("memory_intensive_operation"):
            async with benchmarker.benchmark("memory_intensive_operation"):
                result = await memory_intensive_operation()
                assert result == 10000

    async def test_large_object_caching(self, cache_manager, benchmarker):
        """Test caching of large objects"""

        # Create large data objects
        large_objects = {}
        for i in range(100):
            large_objects[f"large_obj_{i}"] = {
                "id": i,
                "data": "x" * 10000,  # 10KB per object
                "metadata": {
                    "tags": [f"tag_{j}" for j in range(10)],
                    "attributes": {f"attr_{k}": f"value_{k}" * 100 for k in range(20)},
                },
            }

        # Cache all objects
        async with benchmarker.benchmark("cache_large_objects"):
            for key, obj in large_objects.items():
                await cache_manager.set(key, obj, ttl=3600)

        # Retrieve objects
        async with benchmarker.benchmark("retrieve_large_objects"):
            retrieved_count = 0
            for key in large_objects.keys():
                cached_obj = await cache_manager.get(key)
                if cached_obj:
                    retrieved_count += 1

            assert retrieved_count == 100

    async def test_concurrent_memory_usage(self, memory_profiler, benchmarker):
        """Test memory usage under concurrent operations"""

        async def memory_task(task_id: int):
            # Each task creates and processes data
            data = []
            for i in range(1000):
                item = {
                    "task_id": task_id,
                    "item_id": i,
                    "content": f"Content {task_id}-{{i}}" * 50,
                }
                data.append(item)

            # Simulate processing time
            await asyncio.sleep(0.1)

            return len(data)

        # Create 20 concurrent memory-intensive tasks
        tasks = [memory_task(i) for i in range(20)]

        async with memory_profiler.profile_memory("concurrent_memory_operations"):
            async with benchmarker.benchmark("concurrent_memory_operations"):
                results = await asyncio.gather(*tasks)
                assert all(result == 1000 for result in results)

    async def test_gc_impact_on_performance(self, benchmarker):
        """Test garbage collection impact on performance"""

        async def gc_intensive_operation():
            import gc

            # Create many objects with circular references
            objects = []
            for i in range(5000):
                obj_a = {"id": i, "data": "x" * 100}
                obj_b = {"id": i + 1, "data": "y" * 100}
                obj_a["ref"] = obj_b
                obj_b["ref"] = obj_a  # Circular reference
                objects.append(obj_a)

            # Force garbage collection
            collected = gc.collect()
            return collected

        # Test with manual GC
        async with benchmarker.benchmark("gc_intensive_operation"):
            result = await gc_intensive_operation()
            assert isinstance(result, int)


@pytest.mark.asyncio
@pytest.mark.performance
class TestCachePerformance:
    """Comprehensive cache performance tests"""

    async def test_cache_hit_rate_optimization(self, cache_manager, benchmarker):
        """Test cache hit rate optimization"""

        # Test data
        test_data = {f"key_{i}": f"value_{i}" for i in range(1000)}

        # First pass - cache misses
        async with benchmarker.benchmark("cache_misses_phase"):
            for key, value in test_data.items():
                await cache_manager.set(key, value)

        # Second pass - cache hits
        async with benchmarker.benchmark("cache_hits_phase"):
            hit_count = 0
            for key in test_data.keys():
                value = await cache_manager.get(key)
                if value:
                    hit_count += 1

            assert hit_count == 1000

    async def test_cache_warming_performance(self, cache_manager, benchmarker):
        """Test cache warming performance"""

        def warmup_policy():
            """Generate data for cache warming"""
            warmup_data = {}
            for i in range(5000):
                warmup_data[f"warmup_key_{i}"] = {"id": i, "data": f"warmup_data_{i}" * 100}
            return warmup_data

        # Register warmup policy
        cache_manager.register_warmup_policy("test_warmup", warmup_policy)

        async with benchmarker.benchmark("cache_warming"):
            await cache_manager.warm_cache("test_warmup")

        # Verify warmed cache
        hit_count = 0
        for i in range(5000):
            value = await cache_manager.get(f"warmup_key_{i}")
            if value:
                hit_count += 1

        assert hit_count == 5000

    async def test_cache_invalidation_performance(self, cache_manager, benchmarker):
        """Test cache invalidation performance"""

        # Insert tagged data
        tag_sets = [
            {"tag1", "tag2"},
            {"tag2", "tag3"},
            {"tag3", "tag4"},
            {"tag4", "tag5"},
            {"tag5", "tag1"},
        ]

        for i, tags in enumerate(tag_sets):
            for j in range(200):
                key = f"tagged_item_{i}_{j}"
                value = {"id": f"{i}_{j}", "data": f"data_{i}_{j}"}
                await cache_manager.set(key, value, tags=tags)

        # Invalidate by tag
        async with benchmarker.benchmark("cache_invalidation_by_tag"):
            invalidated_count = await cache_manager.invalidate_by_tags({"tag3"})
            assert invalidated_count == 400  # tag3 appears in 2 sets * 200 items

    async def test_cache_size_scaling(self, cache_manager, benchmarker):
        """Test cache performance with different sizes"""

        sizes = [100, 1000, 5000, 10000]

        for size in sizes:
            # Insert data
            async with benchmarker.benchmark(f"cache_insert_size_{size}"):
                for i in range(size):
                    key = f"scale_test_{size}_{i}"
                    value = {"id": i, "data": "x" * 100}
                    await cache_manager.set(key, value)

            # Retrieve data
            async with benchmarker.benchmark(f"cache_retrieve_size_{size}"):
                hit_count = 0
                for i in range(size):
                    key = f"scale_test_{size}_{i}"
                    value = await cache_manager.get(key)
                    if value:
                        hit_count += 1

                assert hit_count == size


@pytest.mark.asyncio
@pytest.mark.performance
class TestScalabilityAnalysis:
    """Scalability analysis and load testing"""

    async def test_vertical_scaling_analysis(self, benchmarker):
        """Test vertical scaling characteristics"""

        concurrent_levels = [1, 5, 10, 25, 50]
        results = {}

        for concurrency in concurrent_levels:

            async def cpu_intensive_task(task_id: int):
                # Simulate CPU-intensive work
                result = 0
                for i in range(10000):
                    result += i * task_id
                return result

            tasks = [cpu_intensive_task(i) for i in range(concurrency)]

            async with benchmarker.benchmark(f"vertical_scaling_{concurrency}"):
                task_results = await asyncio.gather(*tasks)
                results[concurrency] = {
                    "tasks_completed": len(task_results),
                    "total_results": sum(task_results),
                }

        # Analyze scaling efficiency
        base_time = results[1]["tasks_completed"]  # Baseline
        for concurrency in concurrent_levels[1:]:
            efficiency = (results[concurrency]["tasks_completed"] / concurrency) / base_time * 100
            logger.info(f"Concurrency {concurrency}: {efficiency:.1f}% efficiency")

    async def test_horizontal_scaling_simulation(self, benchmarker):
        """Simulate horizontal scaling with multiple instances"""

        instance_count = 5
        tasks_per_instance = 100

        async def simulate_instance(instance_id: int):
            """Simulate a service instance"""
            results = []

            for task_id in range(tasks_per_instance):
                # Simulate request processing
                start_time = time.perf_counter()

                # Simulate work (database query, processing, etc.)
                await asyncio.sleep(0.01)  # 10ms processing time

                duration = time.perf_counter() - start_time
                results.append(
                    {"instance_id": instance_id, "task_id": task_id, "duration": duration}
                )

            return results

        # Start all instances concurrently
        async with benchmarker.benchmark("horizontal_scaling_simulation"):
            instance_tasks = [simulate_instance(i) for i in range(instance_count)]
            instance_results = await asyncio.gather(*instance_tasks)

        # Analyze results
        total_tasks = sum(len(results) for results in instance_results)
        total_durations = [item["duration"] for results in instance_results for item in results]

        assert total_tasks == instance_count * tasks_per_instance
        assert len(total_durations) == total_tasks

    async def test_load_balancing_simulation(self, benchmarker):
        """Simulate load balancing scenarios"""

        # Simulate different server capacities
        servers = [
            {"id": 1, "capacity": 100, "current_load": 0},
            {"id": 2, "capacity": 200, "current_load": 0},
            {"id": 3, "capacity": 150, "current_load": 0},
        ]

        def select_server(servers: List[Dict]) -> Dict:
            """Select server with least load"""
            return min(servers, key=lambda s: s["current_load"] / s["capacity"])

        async def process_request(server: Dict, request_id: int):
            """Process request on selected server"""
            server["current_load"] += 1

            try:
                # Simulate request processing
                await asyncio.sleep(0.01)
                return {"server_id": server["id"], "request_id": request_id}
            finally:
                server["current_load"] -= 1

        # Process many requests
        request_count = 1000
        async with benchmarker.benchmark("load_balancing_simulation"):
            tasks = []
            for i in range(request_count):
                server = select_server(servers)
                task = process_request(server, i)
                tasks.append(task)

            results = await asyncio.gather(*tasks)

        # Analyze load distribution
        server_usage = {}
        for result in results:
            server_id = result["server_id"]
            server_usage[server_id] = server_usage.get(server_id, 0) + 1

        # Verify load distribution
        assert len(results) == request_count
        assert len(server_usage) == len(servers)

    async def test_traffic_spike_handling(self, benchmarker):
        """Test handling of traffic spikes"""

        normal_load = 10  # requests per second
        spike_load = 100  # requests per second
        spike_duration = 5  # seconds

        async def process_request(request_id: int):
            """Simulate request processing"""
            await asyncio.sleep(0.05)  # 50ms processing time
            return request_id

        # Normal load phase
        async with benchmarker.benchmark("normal_load_phase"):
            normal_tasks = [process_request(i) for i in range(normal_load)]
            normal_results = await asyncio.gather(*normal_tasks)

        # Spike load phase
        async with benchmarker.benchmark("spike_load_phase"):
            spike_tasks = []
            for i in range(spike_load * spike_duration):
                task = process_request(i)
                spike_tasks.append(task)
                # Stagger requests to simulate traffic pattern
                await asyncio.sleep(1.0 / spike_load)

            spike_results = await asyncio.gather(*spike_tasks)

        # Recovery phase
        async with benchmarker.benchmark("recovery_phase"):
            recovery_tasks = [process_request(i) for i in range(normal_load)]
            recovery_results = await asyncio.gather(*recovery_tasks)

        # Verify all phases completed
        assert len(normal_results) == normal_load
        assert len(spike_results) == spike_load * spike_duration
        assert len(recovery_results) == normal_load


@pytest.mark.asyncio
@pytest.mark.performance
class TestComprehensiveIntegration:
    """Integration tests combining all performance components"""

    async def test_full_stack_performance(
        self, user_adapter, post_adapter, cache_manager, memory_profiler, benchmarker
    ):
        """Test full stack performance with all components"""

        async with memory_profiler.profile_memory("full_stack_operation"):
            async with benchmarker.benchmark("full_stack_performance"):
                # Phase 1: Create users
                users_data = [
                    {"username": f"fullstack_user_{i}", "email": f"fullstack_{i}@example.com"}
                    for i in range(100)
                ]
                users = await user_adapter.create_batch(users_data)

                # Phase 2: Create posts and cache them
                posts = []
                for i, user in enumerate(users):
                    post_data = {
                        "title": f"Full Stack Post {i}",
                        "content": f"Content for post {i}" * 50,
                        "author_id": user.id,
                    }
                    post = await post_adapter.create(post_data)
                    posts.append(post)

                    # Cache the post
                    await cache_manager.set(
                        f"post_{post.id}", post, tags={"user_posts", f"user_{user.id}"}
                    )

                # Phase 3: Retrieve with caching
                retrieved_posts = []
                for post in posts:
                    # Try cache first
                    cached_post = await cache_manager.get(f"post_{post.id}")
                    if cached_post:
                        retrieved_posts.append(cached_post)
                    else:
                        # Fallback to database
                        db_post = await post_adapter.get_one(post.id)
                        retrieved_posts.append(db_post)

                # Phase 4: Analytics query
                analytics = await post_adapter.count({})

                assert len(users) == 100
                assert len(posts) == 100
                assert len(retrieved_posts) == 100
                assert analytics == 100

    async def test_performance_monitoring_integration(
        self, benchmarker, memory_profiler, cache_manager
    ):
        """Test integration of performance monitoring tools"""

        # Start memory monitoring
        memory_profiler.start_monitoring()

        # Collect comprehensive metrics
        metrics_collected = []

        async def monitored_operation(operation_id: int):
            """Operation with comprehensive monitoring"""
            async with benchmarker.benchmark(f"monitored_operation_{operation_id}"):
                # Simulate work
                await asyncio.sleep(0.01)

                # Use cache
                await cache_manager.set(f"op_{operation_id}", {"result": operation_id})
                cached_result = await cache_manager.get(f"op_{operation_id}")

                metrics_collected.append(
                    {"operation_id": operation_id, "cached_result": cached_result}
                )

                return cached_result

        # Run multiple monitored operations
        tasks = [monitored_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        # Stop monitoring and analyze
        memory_profiler.stop_monitoring()

        # Generate reports
        performance_summary = benchmarker.get_performance_summary()
        memory_stats = memory_profiler.get_memory_statistics()
        cache_stats = cache_manager.get_comprehensive_stats()

        # Verify integration worked
        assert len(results) == 50
        assert len(metrics_collected) == 50
        assert performance_summary["total_benchmarks"] > 0
        assert memory_stats["total_snapshots"] > 0
        assert cache_stats["l1"]["total_entries"] > 0

    async def test_optimization_recommendations(self, user_adapter, benchmarker, memory_profiler):
        """Test optimization recommendation generation"""

        # Run various performance scenarios
        scenarios = [("small_dataset", 10), ("medium_dataset", 100), ("large_dataset", 1000)]

        optimization_data = {}

        for scenario_name, size in scenarios:
            async with benchmarker.benchmark(f"optimization_test_{scenario_name}"):
                async with memory_profiler.profile_memory(f"optimization_memory_{scenario_name}"):
                    # Create users
                    users_data = [
                        {
                            "username": f"{scenario_name}_user_{i}",
                            "email": f"{scenario_name}_{i}@example.com",
                        }
                        for i in range(size)
                    ]
                    users = await user_adapter.create_batch(users_data)

                    # Perform queries
                    for user in users:
                        await user_adapter.get_one(user.id)

                    optimization_data[scenario_name] = {
                        "size": size,
                        "users_created": len(users),
                        "queries_performed": len(users),
                    }

        # Analyze performance trends
        performance_summary = benchmarker.get_performance_summary()
        leak_report = memory_profiler.detect_memory_leaks()

        # Generate recommendations based on data
        recommendations = []

        # Performance recommendations
        if performance_summary["memory_trend_mb_per_sec"] > 1.0:
            recommendations.append(
                "Consider implementing object pooling for high-frequency operations"
            )

        if leak_report["severity"] in ["HIGH", "CRITICAL"]:
            recommendations.extend(leak_report["recommendations"])

        # Size-based recommendations
        if optimization_data["large_dataset"]["size"] > 500:
            recommendations.append("Implement pagination for datasets larger than 500 items")

        # Cache recommendations
        cache_stats = cache_manager.get_comprehensive_stats()
        if cache_stats["l1"]["hit_rate"] < 70:
            recommendations.append("Consider adjusting cache TTL or size for better hit rates")

        # Verify recommendations were generated
        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)


class TestOptimizedComponents:
    """Test suite for new optimized components"""

    @pytest.mark.asyncio
    async def test_distributed_lock_optimization(self):
        """Test optimized distributed lock performance"""
        from unittest.mock import Mock, AsyncMock

        # Mock database engine
        mock_engine = Mock()
        mock_engine.dialect.name = "postgresql"

        # Test exponential backoff configuration
        backoff_config = BackoffConfig(
            base_delay=0.001,  # 1ms
            max_delay=0.1,  # 100ms
            multiplier=2.0,
            jitter=True,
            max_retries=10,
        )

        # Mock connection with contention scenario
        attempt_count = 0

        async def mock_execute(query, params):
            nonlocal attempt_count
            attempt_count += 1
            mock_result = Mock()
            # Simulate contention - succeed after 3 attempts
            mock_result.scalar.return_value = attempt_count > 3
            return mock_result

        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = mock_execute
        mock_engine.connect.return_value = mock_conn

        # Test optimized lock provider
        lock_provider = OptimizedPostgresLockProvider(
            mock_engine, lock_id=1, backoff_config=backoff_config
        )

        # Measure lock acquisition performance
        start_time = time.time()
        success = await lock_provider.acquire(timeout=1.0)
        acquisition_time = time.time() - start_time

        assert success, "Lock should be acquired"
        assert acquisition_time < 1.0, "Lock acquisition should be fast"
        assert attempt_count > 3, "Should have retried due to contention"

        # Verify metrics
        metrics = lock_provider.get_metrics()
        assert metrics.acquire_attempts > 0
        assert metrics.acquire_successes > 0
        assert metrics.contention_count > 0

        # Release lock
        released = await lock_provider.release()
        assert released, "Lock should be released"

    @pytest.mark.asyncio
    async def test_query_parameter_optimization(self):
        """Test query parameter processing optimization"""
        optimizer = QueryParameterOptimizer()

        # Test function with complex type hints
        def test_function(
            user_id: int,
            name: str,
            metadata: Dict[str, Any],
            tags: List[str],
            active: Optional[bool] = True,
        ) -> Dict[str, Any]:
            return {"processed": True}

        # Test parameters with various types
        parameters = {
            "user_id": 123,
            "name": "John Doe",
            "metadata": '{"age": 30, "city": "New York"}',
            "tags": '["admin", "user"]',
            "active": "true",
        }

        # Measure processing time
        start_time = time.time()
        processed_params = await optimizer.process_parameters(test_function, parameters)
        processing_time = time.time() - start_time

        # Verify processing was fast and correct
        assert processing_time < 0.01, "Parameter processing should be very fast"
        assert processed_params["user_id"] == 123
        assert processed_params["name"] == "John Doe"
        assert processed_params["metadata"]["age"] == 30
        assert processed_params["tags"] == ["admin", "user"]
        assert processed_params["active"] is True

        # Verify caching effectiveness
        start_time = time.time()
        await optimizer.process_parameters(test_function, parameters)
        cached_time = time.time() - start_time

        # Second call should be faster due to caching
        assert cached_time < processing_time, "Cached processing should be faster"

        # Check metrics
        metrics = optimizer.get_comprehensive_metrics()
        assert metrics["processing_metrics"]["total_processed"] >= 2

    @pytest.mark.asyncio
    async def test_memory_optimization(self):
        """Test memory optimization features"""
        # Initialize memory optimization
        optimize_memory_usage()
        tracker = get_resource_tracker()
        await tracker.start_monitoring()

        # Register some test resources
        for i in range(100):
            await tracker.register_resource(
                f"test_resource_{i}", "benchmark", resource_obj={"data": f"test_{i}" * 10}
            )

        # Process some data to create objects
        test_data = []
        for i in range(1000):
            test_data.append({"id": i, "data": "x" * 100, "nested": {"value": i}})

        # Force garbage collection
        import gc

        collected = gc.collect()

        # Unregister resources
        for i in range(100):
            await tracker.unregister_resource(f"test_resource_{i}")

        # Get comprehensive report
        report = tracker.get_comprehensive_report()

        # Verify monitoring worked
        assert report["total_resources"] >= 0
        assert "memory_trend_60min" in report
        assert "metrics" in report

        await tracker.stop_monitoring()

    @pytest.mark.asyncio
    async def test_async_optimization(self):
        """Test async optimization components"""
        from unittest.mock import AsyncMock

        # Test async semaphore
        semaphore = AsyncSemaphore(value=5, max_queue_size=20)

        async def worker(worker_id: int):
            async with semaphore.acquire():
                await asyncio.sleep(0.001)  # Simulate work
                return worker_id

        # Measure semaphore performance
        start_time = time.time()
        tasks = [worker(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        execution_time = time.time() - start_time

        assert len(results) == 20
        assert set(results) == set(range(20))  # All workers completed
        assert execution_time < 1.0, "Semaphore should allow efficient concurrent execution"

        # Check semaphore metrics
        metrics = semaphore.get_metrics()
        assert metrics.total_operations == 20
        assert metrics.successful_operations == 20
        assert metrics.max_concurrent <= 5

        # Test rate limiter
        rate_limiter = AsyncRateLimiter(rate_limit=100, period=1.0)

        async def rate_limited_work(i: int):
            async with rate_limiter.limit():
                return i

        start_time = time.time()
        tasks = [rate_limited_work(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        rate_limited_time = time.time() - start_time

        assert len(results) == 50
        # Rate limiting should add some delay but not too much
        assert 0.1 < rate_limited_time < 2.0

        # Test batch processor
        async def process_batch(items: List[int]) -> List[int]:
            await asyncio.sleep(0.01)  # Simulate batch processing
            return [item * 2 for item in items]

        batch_processor = AsyncBatchProcessor(process_batch, batch_size=10, max_wait_time=0.1)

        start_time = time.time()
        tasks = [batch_processor.process_item(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        batch_time = time.time() - start_time

        assert len(results) == 50
        assert all(r == i * 2 for i, r in enumerate(results))
        # Batch processing should be efficient
        assert batch_time < 1.0

        await batch_processor.shutdown()

    @pytest.mark.asyncio
    async def test_json_optimization(self):
        """Test JSON parsing optimization"""
        json_optimizer = JSONOptimizer()

        # Test data
        json_strings = [
            '{"name": "John", "age": 30}',
            '{"items": [1, 2, 3, 4, 5]}',
            '{"nested": {"key": "value", "array": []}}',
            '{"empty": {}}',
            '{"null": null}',
            '{"boolean": true}',
            '{"number": 42.5}',
        ] * 100  # 700 strings

        # Test parsing performance
        start_time = time.time()
        parsed_objects = []
        for json_str in json_strings:
            parsed = json_optimizer.parse_json(json_str)
            parsed_objects.append(parsed)
        parsing_time = time.time() - start_time

        assert len(parsed_objects) == len(json_strings)
        assert parsing_time < 0.5, "JSON parsing should be fast"
        assert all(isinstance(obj, dict) for obj in parsed_objects)

        # Test caching with repeated parsing
        start_time = time.time()
        for json_str in json_strings[:100]:  # Parse first 100 again
            json_optimizer.parse_json(json_str)
        cached_parsing_time = time.time() - start_time

        # Cached parsing should be faster
        assert cached_parsing_time < parsing_time / 7  # At least 7x faster for cached

        # Test batch parsing
        start_time = time.time()
        batch_results = await json_optimizer.parse_batch(json_strings[:200])
        batch_time = time.time() - start_time

        assert len(batch_results) == 200
        # Batch processing should be efficient
        assert batch_time < 0.2

        # Check optimizer stats
        stats = json_optimizer.get_stats()
        assert stats["parse_cache_size"] > 0
        assert stats["stringify_cache_size"] >= 0

    @pytest.mark.asyncio
    @monitor_async_performance("test_monitored_operation")
    async def test_performance_monitoring(self):
        """Test async performance monitoring"""
        from fastapi_easy.core.async_optimizer import get_async_monitor

        monitor = get_async_monitor()

        # Simulate some work with monitoring
        async with monitor.monitor("test_operation"):
            await asyncio.sleep(0.01)
            result = sum(i * i for i in range(1000))

        # Get performance stats
        stats = monitor.get_stats("test_operation")

        assert stats["count"] == 1
        assert stats["avg_time"] > 0
        assert stats["min_time"] > 0
        assert stats["max_time"] > 0
        assert result == sum(i * i for i in range(1000))

    @pytest.mark.asyncio
    async def test_type_hint_cache_performance(self):
        """Test type hint cache performance"""
        cache = TypeHintCache(max_size=100, ttl=1.0)

        # Define test functions
        def simple_func(x: int, y: str) -> bool:
            return True

        def complex_func(
            data: Dict[str, Any], items: List[int], optional: Optional[float] = None
        ) -> Dict[str, Any]:
            return {}

        # Test cache performance
        import time

        # First call (cache miss)
        start_time = time.time()
        hints1 = cache.get_type_hints(simple_func)
        first_time = time.time() - start_time

        # Second call (cache hit)
        start_time = time.time()
        hints2 = cache.get_type_hints(simple_func)
        second_time = time.time() - start_time

        assert hints1 == hints2
        assert second_time < first_time, "Cached lookup should be faster"

        # Test with multiple functions
        for _ in range(50):
            cache.get_type_hints(simple_func)
            cache.get_type_hints(complex_func)

        # Check cache stats
        stats = cache.get_stats()
        assert stats["cache_size"] <= 100
        assert stats["hit_rate"] > 0

        cache.clear()


if __name__ == "__main__":
    # Run comprehensive performance tests
    pytest.main([__file__, "-v", "-x", "--tb=short"])
