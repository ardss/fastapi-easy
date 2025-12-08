"""Query warmup mechanism for preloading hot data into cache"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List


class QueryWarmupStrategy:
    """Strategy for warming up cache with hot data"""

    def __init__(self, name: str):
        """Initialize warmup strategy

        Args:
            name: Strategy name
        """
        self.name = name
        self.executed = False
        self.items_warmed = 0

    async def execute(self) -> int:
        """Execute warmup strategy

        Returns:
            Number of items warmed
        """
        raise NotImplementedError


class SimpleWarmupStrategy(QueryWarmupStrategy):
    """Simple warmup strategy that preloads specific queries"""

    def __init__(
        self,
        name: str,
        queries: List[Callable[[], Awaitable[Any]]],
        cache_setter: Callable[[str, Any], Awaitable[None]],
    ):
        """Initialize simple warmup strategy

        Args:
            name: Strategy name
            queries: List of query functions to execute
            cache_setter: Function to set cache values
        """
        super().__init__(name)
        self.queries = queries
        self.cache_setter = cache_setter

    async def execute(self) -> int:
        """Execute warmup by running queries and caching results

        Returns:
            Number of items warmed
        """
        count = 0
        for query in self.queries:
            try:
                result = await query()
                if result:
                    # Cache the result
                    cache_key = f"warmup_{self.name}_{count}"
                    await self.cache_setter(cache_key, result)
                    count += 1
            except Exception:
                pass

        self.executed = True
        self.items_warmed = count
        return count


class QueryWarmupExecutor:
    """Executor for managing query warmup strategies"""

    def __init__(self):
        """Initialize warmup executor"""
        self.strategies: List[QueryWarmupStrategy] = []
        self.results: Dict[str, int] = {}

    def add_strategy(self, strategy: QueryWarmupStrategy) -> QueryWarmupExecutor:
        """Add warmup strategy

        Args:
            strategy: Warmup strategy to add

        Returns:
            Self for chaining
        """
        self.strategies.append(strategy)
        return self

    async def execute_all(self) -> Dict[str, int]:
        """Execute all warmup strategies

        Returns:
            Dictionary mapping strategy names to items warmed
        """
        tasks = [strategy.execute() for strategy in self.strategies]
        results = await asyncio.gather(*tasks)

        for strategy, count in zip(self.strategies, results):
            self.results[strategy.name] = count

        return self.results

    async def execute_sequential(self) -> Dict[str, int]:
        """Execute warmup strategies sequentially

        Returns:
            Dictionary mapping strategy names to items warmed
        """
        for strategy in self.strategies:
            count = await strategy.execute()
            self.results[strategy.name] = count

        return self.results

    def get_total_warmed(self) -> int:
        """Get total items warmed

        Returns:
            Total count of warmed items
        """
        return sum(self.results.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get warmup statistics

        Returns:
            Statistics dictionary
        """
        return {
            "total_strategies": len(self.strategies),
            "executed_strategies": len(self.results),
            "total_items_warmed": self.get_total_warmed(),
            "strategy_results": self.results,
        }


class ColdStartOptimizer:
    """Optimizer for reducing cold start time"""

    def __init__(self, warmup_executor: QueryWarmupExecutor):
        """Initialize cold start optimizer

        Args:
            warmup_executor: Warmup executor instance
        """
        self.warmup_executor = warmup_executor
        self.warmup_time = 0.0

    async def optimize(self) -> float:
        """Optimize cold start by warming up cache

        Returns:
            Time taken for warmup in seconds
        """
        import time

        start_time = time.time()
        await self.warmup_executor.execute_all()
        self.warmup_time = time.time() - start_time

        return self.warmup_time

    def get_warmup_time(self) -> float:
        """Get warmup time

        Returns:
            Warmup time in seconds
        """
        return self.warmup_time


def create_warmup_executor() -> QueryWarmupExecutor:
    """Create a query warmup executor

    Returns:
        QueryWarmupExecutor instance
    """
    return QueryWarmupExecutor()


def create_cold_start_optimizer(executor: QueryWarmupExecutor) -> ColdStartOptimizer:
    """Create a cold start optimizer

    Args:
        executor: Warmup executor instance

    Returns:
        ColdStartOptimizer instance
    """
    return ColdStartOptimizer(executor)
