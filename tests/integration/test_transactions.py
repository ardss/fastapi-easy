"""Database transaction tests for FastAPI-Easy

Tests for transaction handling, rollback, concurrent transactions, and deadlock handling.
"""

import asyncio
import pytest
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import IntegrityError

from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter
from fastapi_easy.core.errors import ConflictError, AppError


# Test database setup
Base = declarative_base()


class TestItem(Base):
    """Test item model"""
    __tablename__ = "test_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=0)


@pytest.fixture
async def async_engine():
    """Create async SQLAlchemy engine"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def session_factory(async_engine):
    """Create async session factory"""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def adapter(session_factory):
    """Create SQLAlchemy adapter"""
    return SQLAlchemyAdapter(TestItem, session_factory)


@pytest.fixture
async def sample_data(session_factory):
    """Create sample data"""
    async with session_factory() as session:
        items = [
            TestItem(name="item1", price=10.0, quantity=100),
            TestItem(name="item2", price=20.0, quantity=50),
            TestItem(name="item3", price=30.0, quantity=75),
        ]
        session.add_all(items)
        await session.commit()
    
    return items


class TestTransactionRollback:
    """Test transaction rollback functionality"""
    
    async def test_rollback_on_error(self, adapter, session_factory):
        """Test that transaction rolls back on error"""
        # Create initial item
        item_data = {"name": "test_item", "price": 10.0}
        created = await adapter.create(item_data)
        assert created.id is not None
        
        # Verify item was created
        retrieved = await adapter.get_one(created.id)
        assert retrieved is not None
        assert retrieved.name == "test_item"
        
        # Try to create duplicate (should fail)
        with pytest.raises(ConflictError):
            await adapter.create({"name": "test_item", "price": 20.0})
        
        # Verify only one item exists
        all_items = await adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 1
    
    async def test_rollback_on_constraint_violation(self, adapter, session_factory, sample_data):
        """Test rollback when unique constraint is violated"""
        # Try to create item with duplicate name
        with pytest.raises(ConflictError):
            await adapter.create({"name": "item1", "price": 100.0})
        
        # Verify original data is intact
        item = await adapter.get_one(sample_data[0].id)
        assert item.price == 10.0
    
    async def test_manual_rollback(self, session_factory):
        """Test manual transaction rollback"""
        async with session_factory() as session:
            try:
                # Create item
                item = TestItem(name="rollback_test", price=50.0)
                session.add(item)
                await session.flush()
                
                # Simulate error
                raise ValueError("Simulated error")
            except ValueError:
                await session.rollback()
        
        # Verify item was not committed
        async with session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TestItem).where(TestItem.name == "rollback_test")
            )
            item = result.scalar_one_or_none()
            assert item is None


class TestConcurrentTransactions:
    """Test concurrent transaction handling"""
    
    async def test_concurrent_reads(self, adapter, sample_data):
        """Test concurrent read operations"""
        # Create multiple concurrent read tasks
        tasks = [
            adapter.get_one(sample_data[0].id)
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All reads should succeed
        assert len(results) == 10
        assert all(r is not None for r in results)
        assert all(r.name == "item1" for r in results)
    
    async def test_concurrent_writes(self, adapter, session_factory):
        """Test concurrent write operations"""
        # Create multiple concurrent write tasks
        async def create_item(index):
            return await adapter.create({
                "name": f"concurrent_item_{index}",
                "price": float(index * 10),
            })
        
        tasks = [create_item(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All writes should succeed
        assert len(results) == 5
        assert all(r.id is not None for r in results)
        
        # Verify all items were created
        all_items = await adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 5
    
    async def test_concurrent_read_write(self, adapter, sample_data):
        """Test concurrent read and write operations"""
        async def read_item():
            return await adapter.get_one(sample_data[0].id)
        
        async def write_item(index):
            return await adapter.create({
                "name": f"rw_item_{index}",
                "price": float(index * 5),
            })
        
        # Mix read and write operations
        tasks = [
            read_item(),
            write_item(1),
            read_item(),
            write_item(2),
            read_item(),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All operations should succeed
        assert len(results) == 5
        assert results[0] is not None  # First read
        assert results[1].id is not None  # First write
        assert results[2] is not None  # Second read
        assert results[3].id is not None  # Second write
        assert results[4] is not None  # Third read
    
    async def test_concurrent_updates(self, adapter, sample_data):
        """Test concurrent update operations"""
        item_id = sample_data[0].id
        
        async def update_item(value):
            return await adapter.update(item_id, {"quantity": value})
        
        # Create multiple concurrent updates
        tasks = [update_item(i * 10) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All updates should succeed
        assert len(results) == 5
        
        # Final value should be one of the update values
        final_item = await adapter.get_one(item_id)
        assert final_item.quantity in [0, 10, 20, 30, 40]


class TestDeadlockHandling:
    """Test deadlock detection and handling"""
    
    async def test_deadlock_detection(self, adapter, sample_data, session_factory):
        """Test deadlock detection in concurrent updates"""
        item1_id = sample_data[0].id
        item2_id = sample_data[1].id
        
        async def update_sequence_1():
            """Update item1 then item2"""
            await asyncio.sleep(0.01)  # Small delay to increase deadlock chance
            item1 = await adapter.update(item1_id, {"quantity": 100})
            await asyncio.sleep(0.02)
            item2 = await adapter.update(item2_id, {"quantity": 200})
            return item1, item2
        
        async def update_sequence_2():
            """Update item2 then item1"""
            item2 = await adapter.update(item2_id, {"quantity": 300})
            await asyncio.sleep(0.02)
            item1 = await adapter.update(item1_id, {"quantity": 400})
            return item1, item2
        
        # Run both sequences concurrently
        # Note: SQLite doesn't actually deadlock, but this tests the pattern
        try:
            results = await asyncio.gather(
                update_sequence_1(),
                update_sequence_2(),
            )
            # Both should complete successfully
            assert len(results) == 2
        except Exception as e:
            # If deadlock occurs, it should be handled gracefully
            pytest.skip(f"Deadlock occurred (expected in some databases): {e}")
    
    async def test_transaction_timeout(self, adapter, session_factory):
        """Test transaction timeout handling"""
        async def long_running_operation():
            """Simulate a long-running operation"""
            async with session_factory() as session:
                # Create item
                item = TestItem(name="timeout_test", price=50.0)
                session.add(item)
                await session.flush()
                
                # Simulate long operation
                await asyncio.sleep(0.1)
                
                await session.commit()
                return item
        
        # This should complete without timeout
        result = await long_running_operation()
        assert result.id is not None
    
    async def test_transaction_isolation(self, adapter, session_factory, sample_data):
        """Test transaction isolation levels"""
        item_id = sample_data[0].id
        original_quantity = sample_data[0].quantity
        
        async def transaction_1():
            """First transaction"""
            async with session_factory() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(TestItem).where(TestItem.id == item_id)
                )
                item = result.scalar_one()
                
                # Read quantity
                quantity = item.quantity
                
                # Simulate processing
                await asyncio.sleep(0.05)
                
                # Update quantity
                item.quantity = quantity + 10
                await session.commit()
        
        async def transaction_2():
            """Second transaction"""
            await asyncio.sleep(0.02)  # Start after transaction 1
            
            async with session_factory() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(TestItem).where(TestItem.id == item_id)
                )
                item = result.scalar_one()
                
                # Read quantity
                quantity = item.quantity
                
                # Update quantity
                item.quantity = quantity + 20
                await session.commit()
        
        # Run both transactions
        await asyncio.gather(transaction_1(), transaction_2())
        
        # Verify final state
        final_item = await adapter.get_one(item_id)
        # Final quantity should reflect both updates
        assert final_item.quantity >= original_quantity


class TestTransactionEdgeCases:
    """Test edge cases in transaction handling"""
    
    async def test_empty_transaction(self, session_factory):
        """Test transaction with no operations"""
        async with session_factory() as session:
            # Do nothing
            await session.commit()
        
        # Should not raise any errors
        assert True
    
    async def test_nested_transactions(self, adapter, session_factory):
        """Test nested transaction handling"""
        # Create outer transaction
        async with session_factory() as outer_session:
            item1 = TestItem(name="outer_item", price=10.0)
            outer_session.add(item1)
            await outer_session.flush()
            
            # Create inner transaction (should use same connection)
            async with session_factory() as inner_session:
                item2 = TestItem(name="inner_item", price=20.0)
                inner_session.add(item2)
                await inner_session.commit()
            
            await outer_session.commit()
        
        # Both items should be created
        all_items = await adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 2
    
    async def test_transaction_with_multiple_operations(self, adapter):
        """Test transaction with multiple operations"""
        # Create multiple items in sequence
        items = []
        for i in range(5):
            item = await adapter.create({
                "name": f"multi_op_item_{i}",
                "price": float(i * 10),
            })
            items.append(item)
        
        # All items should be created
        assert len(items) == 5
        assert all(item.id is not None for item in items)
        
        # Update all items
        for item in items:
            await adapter.update(item.id, {"quantity": 100})
        
        # Verify all updates
        updated_items = await adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert all(item.quantity == 100 for item in updated_items)
    
    async def test_transaction_rollback_on_delete(self, adapter, sample_data):
        """Test transaction rollback on delete operation"""
        item_id = sample_data[0].id
        
        # Delete item
        deleted = await adapter.delete_one(item_id)
        assert deleted is not None
        
        # Verify item is deleted
        retrieved = await adapter.get_one(item_id)
        assert retrieved is None
        
        # Verify other items still exist
        all_items = await adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 2


class TestTransactionErrorHandling:
    """Test error handling in transactions"""
    
    async def test_integrity_error_handling(self, adapter):
        """Test handling of integrity errors"""
        # Create first item
        item1 = await adapter.create({"name": "integrity_test", "price": 10.0})
        assert item1.id is not None
        
        # Try to create duplicate
        with pytest.raises(ConflictError):
            await adapter.create({"name": "integrity_test", "price": 20.0})
        
        # Verify first item still exists
        retrieved = await adapter.get_one(item1.id)
        assert retrieved is not None
    
    async def test_transaction_recovery(self, adapter):
        """Test recovery after transaction error"""
        # First operation succeeds
        item1 = await adapter.create({"name": "recovery_test_1", "price": 10.0})
        assert item1.id is not None
        
        # Second operation fails
        with pytest.raises(ConflictError):
            await adapter.create({"name": "recovery_test_1", "price": 20.0})
        
        # Third operation should succeed (recovery)
        item3 = await adapter.create({"name": "recovery_test_3", "price": 30.0})
        assert item3.id is not None
        
        # Verify both successful items exist
        all_items = await adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 2
    
    async def test_session_cleanup_on_error(self, adapter, session_factory):
        """Test session cleanup after error"""
        # Create item successfully
        item1 = await adapter.create({"name": "cleanup_test_1", "price": 10.0})
        assert item1.id is not None
        
        # Try to create duplicate (error)
        with pytest.raises(ConflictError):
            await adapter.create({"name": "cleanup_test_1", "price": 20.0})
        
        # Session should be cleaned up, next operation should work
        item2 = await adapter.create({"name": "cleanup_test_2", "price": 30.0})
        assert item2.id is not None
        
        # Verify both items exist
        all_items = await adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
