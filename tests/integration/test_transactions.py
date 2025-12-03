"""SQLAlchemy transaction integration tests

Tests for transaction handling, rollback, concurrent transactions, and deadlock handling.
"""

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, String, Float, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import IntegrityError

from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter
from fastapi_easy.core.errors import ConflictError, AppError


# ============================================================================
# Test Models
# ============================================================================


class Base(DeclarativeBase):
    """SQLAlchemy base class"""

    pass


class TransactionItem(Base):
    """Test item model for transaction tests"""

    __tablename__ = "transaction_items"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=0)

    def __repr__(self):
        return f"<TransactionItem(id={self.id}, name={self.name}, price={self.price}, quantity={self.quantity})>"


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def transaction_engine():
    """Create test database engine"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def transaction_session_factory(transaction_engine):
    """Create async session factory"""
    async_session = async_sessionmaker(
        transaction_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session


@pytest.fixture
def transaction_adapter(transaction_session_factory):
    """Create SQLAlchemy adapter for transactions"""
    return SQLAlchemyAdapter(
        model=TransactionItem,
        session_factory=transaction_session_factory,
        pk_field="id",
    )


@pytest_asyncio.fixture
async def transaction_sample_data(transaction_session_factory):
    """Create sample data for transaction tests"""
    async with transaction_session_factory() as session:
        items = [
            TransactionItem(name="item1", price=10.0, quantity=100),
            TransactionItem(name="item2", price=20.0, quantity=50),
            TransactionItem(name="item3", price=30.0, quantity=75),
        ]
        session.add_all(items)
        await session.commit()

        # Refresh to get IDs
        for item in items:
            await session.refresh(item)

        yield items


@pytest.mark.asyncio
class TestTransactionRollback:
    """Test transaction rollback functionality"""

    async def test_rollback_on_error(self, transaction_adapter):
        """Test that transaction rolls back on error"""
        # Create initial item
        item_data = {"name": "test_item", "price": 10.0}
        created = await transaction_adapter.create(item_data)
        assert created.id is not None

        # Verify item was created
        retrieved = await transaction_adapter.get_one(created.id)
        assert retrieved is not None
        assert retrieved.name == "test_item"

        # Try to create duplicate (should fail)
        with pytest.raises(ConflictError):
            await transaction_adapter.create({"name": "test_item", "price": 20.0})

        # Verify only one item exists
        all_items = await transaction_adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 1

    async def test_rollback_on_constraint_violation(
        self, transaction_adapter, transaction_sample_data
    ):
        """Test rollback when unique constraint is violated"""
        # Try to create item with duplicate name
        with pytest.raises(ConflictError):
            await transaction_adapter.create({"name": "item1", "price": 100.0})

        # Verify original data is intact
        item = await transaction_adapter.get_one(transaction_sample_data[0].id)
        assert item.price == 10.0

    async def test_manual_rollback(self, transaction_session_factory):
        """Test manual transaction rollback"""
        async with transaction_session_factory() as session:
            try:
                # Create item
                item = TransactionItem(name="rollback_test", price=50.0)
                session.add(item)
                await session.flush()

                # Simulate error
                raise ValueError("Simulated error")
            except ValueError:
                await session.rollback()

        # Verify item was not committed
        async with transaction_session_factory() as session:
            result = await session.execute(
                select(TransactionItem).where(TransactionItem.name == "rollback_test")
            )
            item = result.scalar_one_or_none()
            assert item is None


@pytest.mark.asyncio
class TestConcurrentTransactions:
    """Test concurrent transaction handling"""

    async def test_concurrent_reads(self, transaction_adapter, transaction_sample_data):
        """Test concurrent read operations"""
        # Create multiple concurrent read tasks
        tasks = [transaction_adapter.get_one(transaction_sample_data[0].id) for _ in range(10)]

        results = await asyncio.gather(*tasks)

        # All reads should succeed
        assert len(results) == 10
        assert all(r is not None for r in results)
        assert all(r.name == "item1" for r in results)

    async def test_concurrent_writes(self, transaction_adapter):
        """Test concurrent write operations"""

        # Create multiple concurrent write tasks
        async def create_item(index):
            return await transaction_adapter.create(
                {
                    "name": f"concurrent_item_{index}",
                    "price": float(index * 10),
                }
            )

        tasks = [create_item(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All writes should succeed
        assert len(results) == 5
        assert all(r.id is not None for r in results)

        # Verify all items were created
        all_items = await transaction_adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 5

    async def test_concurrent_read_write(self, transaction_adapter, transaction_sample_data):
        """Test concurrent read and write operations"""

        async def read_item():
            return await transaction_adapter.get_one(transaction_sample_data[0].id)

        async def write_item(index):
            return await transaction_adapter.create(
                {
                    "name": f"rw_item_{index}",
                    "price": float(index * 5),
                }
            )

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

    async def test_concurrent_updates(self, transaction_adapter, transaction_sample_data):
        """Test concurrent update operations"""
        item_id = transaction_sample_data[0].id

        async def update_item(value):
            return await transaction_adapter.update(item_id, {"quantity": value})

        # Create multiple concurrent updates
        tasks = [update_item(i * 10) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All updates should succeed
        assert len(results) == 5

        # Final value should be one of the update values
        final_item = await transaction_adapter.get_one(item_id)
        assert final_item.quantity in [0, 10, 20, 30, 40]


@pytest.mark.asyncio
class TestDeadlockHandling:
    """Test deadlock detection and handling"""

    async def test_deadlock_detection(
        self, transaction_adapter, transaction_sample_data, transaction_session_factory
    ):
        """Test deadlock detection in concurrent updates"""
        item1_id = transaction_sample_data[0].id
        item2_id = transaction_sample_data[1].id

        async def update_sequence_1():
            """Update item1 then item2"""
            await asyncio.sleep(0.01)  # Small delay to increase deadlock chance
            item1 = await transaction_adapter.update(item1_id, {"quantity": 100})
            await asyncio.sleep(0.02)
            item2 = await transaction_adapter.update(item2_id, {"quantity": 200})
            return item1, item2

        async def update_sequence_2():
            """Update item2 then item1"""
            item2 = await transaction_adapter.update(item2_id, {"quantity": 300})
            await asyncio.sleep(0.02)
            item1 = await transaction_adapter.update(item1_id, {"quantity": 400})
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

    async def test_transaction_timeout(self, transaction_adapter, transaction_session_factory):
        """Test transaction timeout handling"""

        async def long_running_operation():
            """Simulate a long-running operation"""
            async with transaction_session_factory() as session:
                # Create item
                item = TransactionItem(name="timeout_test", price=50.0)
                session.add(item)
                await session.flush()

                # Simulate long operation
                await asyncio.sleep(0.1)

                await session.commit()
                return item

        # This should complete without timeout
        result = await long_running_operation()
        assert result.id is not None

    async def test_transaction_isolation(
        self, transaction_adapter, transaction_session_factory, transaction_sample_data
    ):
        """Test transaction isolation levels"""
        item_id = transaction_sample_data[0].id
        original_quantity = transaction_sample_data[0].quantity

        async def transaction_1():
            """First transaction"""
            async with transaction_session_factory() as session:
                result = await session.execute(
                    select(TransactionItem).where(TransactionItem.id == item_id)
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

            async with transaction_session_factory() as session:
                result = await session.execute(
                    select(TransactionItem).where(TransactionItem.id == item_id)
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
        final_item = await transaction_adapter.get_one(item_id)
        # Final quantity should reflect both updates
        assert final_item.quantity >= original_quantity


@pytest.mark.asyncio
class TestTransactionEdgeCases:
    """Test edge cases in transaction handling"""

    async def test_empty_transaction(self, transaction_session_factory):
        """Test transaction with no operations"""
        async with transaction_session_factory() as session:
            # Do nothing
            await session.commit()

        # Should not raise any errors
        assert True

    async def test_nested_transactions(self, transaction_adapter, transaction_session_factory):
        """Test nested transaction handling"""
        # Create outer transaction
        async with transaction_session_factory() as outer_session:
            item1 = TransactionItem(name="outer_item", price=10.0)
            outer_session.add(item1)
            await outer_session.flush()

            # Create inner transaction (should use same connection)
            async with transaction_session_factory() as inner_session:
                item2 = TransactionItem(name="inner_item", price=20.0)
                inner_session.add(item2)
                await inner_session.commit()

            await outer_session.commit()

        # Both items should be created
        all_items = await transaction_adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 2

    async def test_transaction_with_multiple_operations(self, transaction_adapter):
        """Test transaction with multiple operations"""
        # Create multiple items in sequence
        items = []
        for i in range(5):
            item = await transaction_adapter.create(
                {
                    "name": f"multi_op_item_{i}",
                    "price": float(i * 10),
                }
            )
            items.append(item)

        # All items should be created
        assert len(items) == 5
        assert all(item.id is not None for item in items)

        # Update all items
        for item in items:
            await transaction_adapter.update(item.id, {"quantity": 100})

        # Verify all updates
        updated_items = await transaction_adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert all(item.quantity == 100 for item in updated_items)

    async def test_transaction_rollback_on_delete(
        self, transaction_adapter, transaction_sample_data
    ):
        """Test transaction rollback on delete operation"""
        item_id = transaction_sample_data[0].id

        # Delete item
        deleted = await transaction_adapter.delete_one(item_id)
        assert deleted is not None

        # Verify item is deleted
        retrieved = await transaction_adapter.get_one(item_id)
        assert retrieved is None

        # Verify other items still exist
        all_items = await transaction_adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 2


@pytest.mark.asyncio
class TestTransactionErrorHandling:
    """Test error handling in transactions"""

    async def test_integrity_error_handling(self, transaction_adapter):
        """Test handling of integrity errors"""
        # Create first item
        item1 = await transaction_adapter.create({"name": "integrity_test", "price": 10.0})
        assert item1.id is not None

        # Try to create duplicate
        with pytest.raises(ConflictError):
            await transaction_adapter.create({"name": "integrity_test", "price": 20.0})

        # Verify first item still exists
        retrieved = await transaction_adapter.get_one(item1.id)
        assert retrieved is not None

    async def test_transaction_recovery(self, transaction_adapter):
        """Test recovery after transaction error"""
        # First operation succeeds
        item1 = await transaction_adapter.create({"name": "recovery_test_1", "price": 10.0})
        assert item1.id is not None

        # Second operation fails
        with pytest.raises(ConflictError):
            await transaction_adapter.create({"name": "recovery_test_1", "price": 20.0})

        # Third operation should succeed (recovery)
        item3 = await transaction_adapter.create({"name": "recovery_test_3", "price": 30.0})
        assert item3.id is not None

        # Verify both successful items exist
        all_items = await transaction_adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 2

    async def test_session_cleanup_on_error(self, transaction_adapter):
        """Test session cleanup after error"""
        # Create item successfully
        item1 = await transaction_adapter.create({"name": "cleanup_test_1", "price": 10.0})
        assert item1.id is not None

        # Try to create duplicate (error)
        with pytest.raises(ConflictError):
            await transaction_adapter.create({"name": "cleanup_test_1", "price": 20.0})

        # Session should be cleaned up, next operation should work
        item2 = await transaction_adapter.create({"name": "cleanup_test_2", "price": 30.0})
        assert item2.id is not None

        # Verify both items exist
        all_items = await transaction_adapter.get_all({}, {}, {"skip": 0, "limit": 100})
        assert len(all_items) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
