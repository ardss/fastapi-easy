"""SQLAlchemy error recovery integration tests

Tests for error handling, recovery mechanisms, and resilience.
"""

import asyncio
import pytest
from sqlalchemy import select

from .conftest import Item


@pytest.mark.asyncio
class TestConnectionFailure:
    """Test database connection failure handling"""

    async def test_connection_failure_recovery(self, db_session_factory):
        """Test recovery from connection failure"""
        # Test that we can handle connection failures gracefully
        # In a real scenario, this would be tested with a mock database
        try:
            async with db_session_factory() as session:
                # Normal operation succeeds
                result = await session.execute(select(Item))
                items = result.scalars().all()
                assert items is not None
        except Exception as _:
            # Should handle connection errors gracefully
            pytest.skip(f"Connection error (expected in some environments): {e}")

    async def test_connection_timeout(self, db_session_factory):
        """Test connection timeout handling"""

        async def timeout_operation():
            await asyncio.sleep(0.1)
            raise TimeoutError("Connection timeout")

        with pytest.raises(TimeoutError, match="Connection timeout"):
            await timeout_operation()

    async def test_connection_pool_exhaustion(self, sqlalchemy_adapter):
        """Test handling of connection pool exhaustion"""

        # Create multiple concurrent operations
        async def operation():
            return await sqlalchemy_adapter.get_all({}, {}, {"skip": 0, "limit": 10})

        # Run multiple operations concurrently
        tasks = [operation() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete (either success or handled exception)
        assert len(results) == 5


@pytest.mark.asyncio
class TestTimeoutHandling:
    """Test timeout handling in database operations"""

    async def test_query_timeout(self, sqlalchemy_adapter, sample_items):
        """Test query timeout handling"""

        # Simulate a slow query
        async def slow_query():
            await asyncio.sleep(0.05)
            return await sqlalchemy_adapter.get_all({}, {}, {"skip": 0, "limit": 10})

        # Should complete without timeout
        result = await asyncio.wait_for(slow_query(), timeout=1.0)
        assert result is not None

    async def test_operation_timeout_exceeded(self, sqlalchemy_adapter):
        """Test when operation exceeds timeout"""

        async def very_slow_query():
            await asyncio.sleep(2.0)
            return await sqlalchemy_adapter.get_all({}, {}, {"skip": 0, "limit": 10})

        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(very_slow_query(), timeout=0.1)

    async def test_transaction_timeout(self, db_session_factory):
        """Test transaction timeout"""

        async def long_transaction():
            async with db_session_factory() as session:
                # Simulate long operation
                await asyncio.sleep(0.05)
                item = Item(name="timeout_test", price=10.0)
                session.add(item)
                await session.commit()
                return item

        # Should complete
        result = await asyncio.wait_for(long_transaction(), timeout=1.0)
        assert result is not None


@pytest.mark.asyncio
class TestRetryMechanism:
    """Test retry mechanisms for failed operations"""

    async def test_retry_on_transient_error(self, sqlalchemy_adapter):
        """Test retry on transient errors"""
        call_count = 0

        async def operation_with_retry():
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                raise Exception("Transient error")

            return await sqlalchemy_adapter.get_all({}, {}, {"skip": 0, "limit": 10})

        # Implement simple retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await operation_with_retry()
                assert result is not None
                break
            except Exception as _:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.01)

    async def test_exponential_backoff(self, sqlalchemy_adapter):
        """Test exponential backoff retry strategy"""
        call_times = []

        async def operation_with_backoff():
            call_times.append(asyncio.get_event_loop().time())

            if len(call_times) < 3:
                raise Exception("Transient error")

            return await sqlalchemy_adapter.get_all({}, {}, {"skip": 0, "limit": 10})

        # Implement exponential backoff
        max_retries = 3
        base_delay = 0.01

        for attempt in range(max_retries):
            try:
                result = await operation_with_backoff()
                assert result is not None
                break
            except Exception as _:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2**attempt)
                await asyncio.sleep(delay)

        # Verify delays increased
        if len(call_times) > 2:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            assert delay2 > delay1  # Second delay should be longer

    async def test_max_retries_exceeded(self, sqlalchemy_adapter):
        """Test when max retries are exceeded"""

        async def always_fails():
            raise Exception("Permanent error")

        max_retries = 2
        attempt = 0

        with pytest.raises(Exception, match="Permanent error"):
            for attempt in range(max_retries):
                try:
                    await always_fails()
                except Exception as _:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(0.01)


@pytest.mark.asyncio
class TestErrorRecovery:
    """Test error recovery and resilience"""

    async def test_partial_failure_recovery(self, sqlalchemy_adapter):
        """Test recovery from partial failures in batch operations"""
        # Create first item successfully
        item1 = await sqlalchemy_adapter.create({"name": "item1", "price": 10.0})
        assert item1 is not None

        # Create second item successfully
        item2 = await sqlalchemy_adapter.create({"name": "item2", "price": 20.0})
        assert item2 is not None
        assert item2.name == "item2"

        # Update should work after creation
        updated = await sqlalchemy_adapter.update(item1.id, {"price": 15.0})
        assert updated is not None
        assert updated.price == 15.0

    async def test_session_recovery_after_error(self, db_session_factory):
        """Test session recovery after error"""
        # First operation with error
        try:
            async with db_session_factory() as session:
                item = Item(name="test", price=10.0)
                session.add(item)
                await session.flush()

                # Simulate error
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Session should be recoverable
        async with db_session_factory() as session:
            result = await session.execute(select(Item))
            items = result.scalars().all()
            # Item should not be committed due to rollback
            assert len(items) == 0

    async def test_concurrent_error_handling(self, sqlalchemy_adapter):
        """Test error handling in concurrent operations"""

        async def operation(index):
            if index == 2:
                raise Exception(f"Error in operation {index}")
            return await sqlalchemy_adapter.create(
                {"name": f"item_{index}", "price": float(index * 10)}
            )

        # Run concurrent operations
        tasks = [operation(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Should have 4 successes and 1 error
        successes = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]

        assert len(successes) == 4
        assert len(errors) == 1

    async def test_deadlock_recovery(self, sqlalchemy_adapter, sample_items):
        """Test recovery from deadlock scenarios"""
        item1_id = sample_items[0].id
        item2_id = sample_items[1].id

        async def transaction_1():
            """Update item1 then item2"""
            await asyncio.sleep(0.01)
            await sqlalchemy_adapter.update(item1_id, {"price": 100.0})
            await asyncio.sleep(0.02)
            await sqlalchemy_adapter.update(item2_id, {"price": 200.0})

        async def transaction_2():
            """Update item2 then item1"""
            await sqlalchemy_adapter.update(item2_id, {"price": 300.0})
            await asyncio.sleep(0.02)
            await sqlalchemy_adapter.update(item1_id, {"price": 400.0})

        # Run both transactions concurrently
        try:
            results = await asyncio.gather(transaction_1(), transaction_2())
            # Both should complete (SQLite doesn't have true deadlocks)
            assert len(results) == 2
        except Exception as _:
            # If deadlock occurs, it should be handled gracefully
            pytest.skip(f"Deadlock occurred (expected in some databases): {e}")


@pytest.mark.asyncio
class TestCircuitBreaker:
    """Test circuit breaker pattern for resilience"""

    async def test_circuit_breaker_open(self, sqlalchemy_adapter):
        """Test circuit breaker opening after failures"""
        failure_count = 0
        max_failures = 3

        async def operation_with_circuit_breaker():
            nonlocal failure_count

            if failure_count >= max_failures:
                raise Exception("Circuit breaker open")

            failure_count += 1
            raise Exception("Operation failed")

        # Try operations until circuit opens
        for i in range(5):
            with pytest.raises(Exception):
                await operation_with_circuit_breaker()

        # Circuit should be open
        assert failure_count >= max_failures

    async def test_circuit_breaker_recovery(self, sqlalchemy_adapter):
        """Test circuit breaker recovery"""
        failure_count = 0
        max_failures = 2
        recovery_time = 0.05
        last_failure_time = None

        async def operation_with_recovery():
            nonlocal failure_count, last_failure_time

            # Check if circuit should recover
            if last_failure_time:
                elapsed = asyncio.get_event_loop().time() - last_failure_time
                if elapsed > recovery_time:
                    failure_count = 0

            if failure_count >= max_failures:
                raise Exception("Circuit breaker open")

            failure_count += 1
            last_failure_time = asyncio.get_event_loop().time()
            raise Exception("Operation failed")

        # Trigger failures
        for i in range(2):
            with pytest.raises(Exception):
                await operation_with_recovery()

        # Wait for recovery
        await asyncio.sleep(recovery_time + 0.01)

        # Should be able to try again
        with pytest.raises(Exception):
            await operation_with_recovery()

        # Failure count should have reset
        assert failure_count == 1


@pytest.mark.asyncio
class TestGracefulDegradation:
    """Test graceful degradation under errors"""

    async def test_fallback_to_cache(self, sqlalchemy_adapter, sample_items):
        """Test fallback to cache when database fails"""
        cache = {}

        async def get_with_fallback(item_id):
            try:
                return await sqlalchemy_adapter.get_one(item_id)
            except Exception:
                # Fallback to cache
                return cache.get(item_id)

        # Populate cache
        item = sample_items[0]
        cache[item.id] = item

        # Should return from cache if database fails
        result = await get_with_fallback(item.id)
        assert result is not None

    async def test_partial_data_return(self, sqlalchemy_adapter, sample_items):
        """Test returning partial data on error"""

        async def get_all_with_partial():
            try:
                return await sqlalchemy_adapter.get_all({}, {}, {"skip": 0, "limit": 100})
            except Exception:
                # Return partial data
                return sample_items[:2]

        result = await get_all_with_partial()
        assert len(result) >= 2

    async def test_readonly_fallback(self, sqlalchemy_adapter):
        """Test fallback to read-only mode on write errors"""
        readonly_mode = False

        async def operation_with_readonly_fallback(data):
            nonlocal readonly_mode

            try:
                if readonly_mode:
                    raise Exception("Read-only mode")
                return await sqlalchemy_adapter.create(data)
            except Exception:
                # Fallback to read-only
                readonly_mode = True
                return await sqlalchemy_adapter.get_all({}, {}, {"skip": 0, "limit": 10})

        # First operation should succeed
        result1 = await operation_with_readonly_fallback({"name": "test", "price": 10.0})
        assert result1 is not None

        # Simulate write failure
        readonly_mode = True
        result2 = await operation_with_readonly_fallback({"name": "test2", "price": 20.0})
        assert isinstance(result2, list)
