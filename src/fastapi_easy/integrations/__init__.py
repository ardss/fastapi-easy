"""FastAPI-Easy integrations"""

from .fastapi_optimization import (
    FastAPIOptimization,
    OptimizationConfig,
    setup_optimization,
)

__all__ = [
    "FastAPIOptimization",
    "OptimizationConfig",
    "setup_optimization",
]
