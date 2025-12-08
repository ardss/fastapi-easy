# Performance Optimization Guide for FastAPI-Easy

## Overview

This guide provides comprehensive performance optimization recommendations for the FastAPI-Easy project. It covers database operations, caching strategies, async patterns, and resource management.

## 1. Database Connection Optimization

### Current Issues
- No connection pooling configuration
- Synchronous connections in async context
- Suboptimal timeout handling

### Solutions

#### Use Async Connection Pooling
```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=20,  # Adjust based on load
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True,  # Validate connections before use
)
```

#### Implement Connection Health Checks
```python
async def health_check(session):
    try:
        await session.execute(text("SELECT 1"))
        return True
    except:
        return False
```

## 2. Query Parameter Performance

### Current Issues
- Repeated type hint resolution
- No caching of model introspection
- Inefficient JSON parsing

### Solutions

#### Use the Optimized Query Parameter Handler
```python
from fastapi_easy.utils.query_params_optimized import QueryParamsOptimized

@QueryParamsOptimized(UserQuery)
async def get_users(params: UserQuery):
    return params
```

#### Enable Caching
```python
from fastapi_easy.utils.query_params_optimized import get_query_param_stats

# Monitor cache performance
stats = get_query_param_stats()
print(f"Cache hit rate: {stats['cache_hit_rate']:.2f}%")
```

## 3. Distributed Lock Optimization

### Current Issues
- Connection leaks in lock providers
- Fixed retry intervals
- No exponential backoff

### Solutions

#### Use Optimized Lock Provider
```python
from fastapi_easy.migrations.distributed_lock_optimized import (
    OptimizedPostgresLockProvider,
    LockConfig
)

config = LockConfig(
    max_retries=10,
    base_retry_delay=0.01,  # Start with 10ms
    max_retry_delay=1.0,
)

lock_provider = OptimizedPostgresLockProvider(engine, config=config)
```

#### Monitor Lock Performance
```python
stats = lock_provider.get_stats()
print(f"Success rate: {stats['success_rate']:.2f}%")
print(f"Avg acquisition time: {stats['avg_acquisition_time']:.3f}s")
```

## 4. Caching Strategy

### Implementation

#### Multi-Layer Caching
```python
from fastapi_easy.core.multilayer_cache import MultiLayerCache

cache = MultiLayerCache(
    l1_size=1000,  # In-memory cache
    l1_ttl=60,     # 1 minute
    l2_size=10000, # Redis or external cache
    l2_ttl=600,    # 10 minutes
)
```

#### Cache Invalidation Patterns
```python
# Write-through cache
async def update_item(id, data):
    result = await database.update(id, data)
    await cache.delete(f"item:{id}")
    await cache.invalidate_pattern("list:*")
    return result
```

## 5. Async/Await Optimization

### Best Practices

#### Use Async Session Managers
```python
@asynccontextmanager
async def get_db_session():
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise
```

#### Batch Operations
```python
from fastapi_easy.core.async_batch import AsyncBatchProcessor

processor = AsyncBatchProcessor(max_concurrent=10)

# Process items concurrently
results = await processor.process_concurrent(
    items,
    process_item_func,
    timeout=30.0
)
```

## 6. Memory Management

### Preventing Memory Leaks

#### Use Weak References
```python
import weakref

class ResourceManager:
    def __init__(self):
        self.resources = weakref.WeakSet()

    def register(self, resource):
        self.resources.add(resource)
```

#### Implement Cleanup Callbacks
```python
def cleanup_resources():
    # Cleanup code here
    pass

import atexit
atexit.register(cleanup_resources)
```

## 7. Performance Monitoring

### Key Metrics to Track

1. **Database Metrics**
   - Query execution time
   - Connection pool utilization
   - Cache hit rates

2. **Application Metrics**
   - Request latency
   - Throughput
   - Error rates

### Implementation Example
```python
from fastapi_easy.backends.sqlalchemy_optimized import OptimizedSQLAlchemyAdapter

adapter = OptimizedSQLAlchemyAdapter(
    model=Item,
    database_url=database_url
)

# Get performance metrics
metrics = await adapter.get_metrics()
print(f"Average query time: {metrics['avg_time']:.3f}s")
print(f"Cache hit rate: {metrics['cache_hit_rate']:.2f}%")
```

## 8. Profiling Tools

### Recommended Tools

1. **Database Profiling**
   ```bash
   # PostgreSQL
   EXPLAIN ANALYZE SELECT * FROM items;

   # Enable query logging
   ALTER SYSTEM SET log_statement = 'all';
   ```

2. **Python Profiling**
   ```python
   import cProfile
   import pstats

   profiler = cProfile.Profile()
   profiler.enable()

   # Your code here

   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative')
   stats.print_stats(10)
   ```

3. **Memory Profiling**
   ```python
   from memory_profiler import profile

   @profile
   def my_function():
       # Your code here
       pass
   ```

## 9. Configuration Recommendations

### Environment-Specific Settings

#### Development
```python
config = development_config()
# Smaller pools, shorter timeouts, caching disabled
```

#### Production
```python
config = production_config()
# Larger pools, longer timeouts, aggressive caching
```

#### High-Traffic
```python
config = high_performance_config()
# Maximum pools, extended timeouts, large cache
```

## 10. Benchmarking

### Sample Benchmark Script
```python
import asyncio
import time
from fastapi_easy.backends.sqlalchemy_optimized import create_optimized_adapter

async def benchmark(adapter, iterations=1000):
    start_time = time.time()

    tasks = []
    for i in range(iterations):
        tasks.append(adapter.get_one(i % 100))  # Hit cache frequently

    results = await asyncio.gather(*tasks)

    end_time = time.time()
    duration = end_time - start_time

    print(f"Completed {iterations} queries in {duration:.2f}s")
    print(f"QPS: {iterations / duration:.2f}")

    metrics = await adapter.get_metrics()
    print(f"Cache hit rate: {metrics['cache_hit_rate']:.2f}%")

# Run benchmark
adapter = create_optimized_adapter(Item, database_url)
await benchmark(adapter)
```

## 11. Common Performance Pitfalls

### 1. N+1 Query Problem
```python
# Bad: N+1 queries
for item in items:
    item.details = await get_details(item.id)

# Good: Batch query
item_ids = [item.id for item in items]
details = await get_details_batch(item_ids)
```

### 2. Over-fetching Data
```python
# Bad: Fetching all columns
query = select(Item)

# Good: Select only needed columns
query = select(Item.id, Item.name)
```

### 3. Inefficient Filtering
```python
# Bad: Client-side filtering
items = await get_all_items()
filtered = [i for i in items if i.price > 100]

# Good: Database-side filtering
items = await get_items(filters={"price__gt": 100})
```

## 12. Performance Checklists

### Database Optimization Checklist
- [ ] Connection pooling configured
- [ ] Indexes on frequently queried columns
- [ ] Query timeouts set
- [ ] Health checks implemented
- [ ] Slow query logging enabled

### Application Optimization Checklist
- [ ] Caching implemented
- [ ] Batch operations used
- [ ] Async/await properly used
- [ ] Memory leaks prevented
- [ ] Monitoring in place

### Caching Checklist
- [ ] Cache hit rate > 70%
- [ ] TTL configured appropriately
- [ ] Cache invalidation strategy
- [ ] Multi-layer caching
- [ ] Cache warming strategy

## 13. Troubleshooting

### Common Issues and Solutions

#### High Memory Usage
1. Check for memory leaks in resource tracking
2. Reduce cache sizes
3. Implement periodic cleanup
4. Use memory profiling tools

#### Slow Queries
1. Check query execution plans
2. Add missing indexes
3. Optimize ORM queries
4. Consider query caching

#### Connection Pool Exhaustion
1. Increase pool size
2. Check for connection leaks
3. Implement connection health checks
4. Use connection timeouts

#### Low Cache Hit Rate
1. Review cache keys
2. Adjust TTL values
3. Implement cache warming
4. Check cache invalidation logic

## 14. Further Reading

- [SQLAlchemy Performance Guide](https://docs.sqlalchemy.org/en/20/orm/performance.html)
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/advanced/performance/)
- [Python Asyncio Best Practices](https://docs.python.org/3/library/asyncio-dev.html)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)

## Conclusion

By implementing these optimizations, you can significantly improve the performance of your FastAPI-Easy application. Start with the most impactful changes (connection pooling, caching, and query optimization) and gradually implement more advanced optimizations as needed.

Remember to measure before and after each optimization to ensure you're getting the expected performance improvements.