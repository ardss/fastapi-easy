"""Tests for query warmup module"""

import pytest
import asyncio
from fastapi_easy.core.query_warmup import (
    QueryWarmupStrategy,
    SimpleWarmupStrategy,
    QueryWarmupExecutor,
    ColdStartOptimizer,
    create_warmup_executor,
    create_cold_start_optimizer,
)


class TestSimpleWarmupStrategy:
    """Test SimpleWarmupStrategy class"""
    
    @pytest.mark.asyncio
    async def test_warmup_execution(self):
        """Test warmup strategy execution"""
        queries = []
        cache_data = {}
        
        async def query1():
            return {"id": 1, "name": "test1"}
        
        async def query2():
            return {"id": 2, "name": "test2"}
        
        queries.append(query1)
        queries.append(query2)
        
        async def cache_setter(key, value):
            cache_data[key] = value
        
        strategy = SimpleWarmupStrategy("test", queries, cache_setter)
        count = await strategy.execute()
        
        assert count == 2
        assert strategy.executed
        assert strategy.items_warmed == 2
    
    @pytest.mark.asyncio
    async def test_warmup_with_errors(self):
        """Test warmup strategy with errors"""
        queries = []
        cache_data = {}
        
        async def query1():
            return {"id": 1}
        
        async def query2():
            raise Exception("Query error")
        
        async def query3():
            return {"id": 3}
        
        queries.extend([query1, query2, query3])
        
        async def cache_setter(key, value):
            cache_data[key] = value
        
        strategy = SimpleWarmupStrategy("test", queries, cache_setter)
        count = await strategy.execute()
        
        # Should handle errors gracefully
        assert count >= 1


class TestQueryWarmupExecutor:
    """Test QueryWarmupExecutor class"""
    
    @pytest.mark.asyncio
    async def test_add_strategy(self):
        """Test adding strategy"""
        executor = QueryWarmupExecutor()
        
        async def dummy_query():
            return {"id": 1}
        
        async def cache_setter(key, value):
            pass
        
        strategy = SimpleWarmupStrategy("test", [dummy_query], cache_setter)
        executor.add_strategy(strategy)
        
        assert len(executor.strategies) == 1
    
    @pytest.mark.asyncio
    async def test_execute_all(self):
        """Test executing all strategies"""
        executor = QueryWarmupExecutor()
        
        async def query1():
            return {"id": 1}
        
        async def query2():
            return {"id": 2}
        
        async def cache_setter(key, value):
            pass
        
        strategy1 = SimpleWarmupStrategy("strategy1", [query1], cache_setter)
        strategy2 = SimpleWarmupStrategy("strategy2", [query2], cache_setter)
        
        executor.add_strategy(strategy1).add_strategy(strategy2)
        results = await executor.execute_all()
        
        assert "strategy1" in results
        assert "strategy2" in results
    
    @pytest.mark.asyncio
    async def test_execute_sequential(self):
        """Test executing strategies sequentially"""
        executor = QueryWarmupExecutor()
        
        async def query1():
            return {"id": 1}
        
        async def cache_setter(key, value):
            pass
        
        strategy = SimpleWarmupStrategy("test", [query1], cache_setter)
        executor.add_strategy(strategy)
        
        results = await executor.execute_sequential()
        assert "test" in results
    
    def test_get_total_warmed(self):
        """Test getting total warmed items"""
        executor = QueryWarmupExecutor()
        executor.results = {"strategy1": 5, "strategy2": 3}
        
        total = executor.get_total_warmed()
        assert total == 8
    
    def test_get_stats(self):
        """Test getting warmup statistics"""
        executor = QueryWarmupExecutor()
        executor.strategies = [None, None]  # 2 strategies
        executor.results = {"strategy1": 5, "strategy2": 3}
        
        stats = executor.get_stats()
        assert stats["total_strategies"] == 2
        assert stats["executed_strategies"] == 2
        assert stats["total_items_warmed"] == 8


class TestColdStartOptimizer:
    """Test ColdStartOptimizer class"""
    
    @pytest.mark.asyncio
    async def test_optimize(self):
        """Test cold start optimization"""
        executor = QueryWarmupExecutor()
        
        async def query1():
            await asyncio.sleep(0.01)
            return {"id": 1}
        
        async def cache_setter(key, value):
            pass
        
        strategy = SimpleWarmupStrategy("test", [query1], cache_setter)
        executor.add_strategy(strategy)
        
        optimizer = ColdStartOptimizer(executor)
        warmup_time = await optimizer.optimize()
        
        assert warmup_time > 0
        assert optimizer.get_warmup_time() > 0


class TestFactoryFunctions:
    """Test factory functions"""
    
    def test_create_warmup_executor(self):
        """Test creating warmup executor"""
        executor = create_warmup_executor()
        assert isinstance(executor, QueryWarmupExecutor)
    
    def test_create_cold_start_optimizer(self):
        """Test creating cold start optimizer"""
        executor = create_warmup_executor()
        optimizer = create_cold_start_optimizer(executor)
        assert isinstance(optimizer, ColdStartOptimizer)
