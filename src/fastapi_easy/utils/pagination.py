"""Pagination utilities for FastAPI-Easy"""

from typing import Dict, Any, TypeVar, List
from dataclasses import dataclass

T = TypeVar("T")


@dataclass
class PaginationParams:
    """Pagination parameters"""
    
    skip: int = 0
    limit: int = 10
    
    def validate(self, max_limit: int = 100, max_skip: int = 1000000) -> None:
        """Validate pagination parameters
        
        Args:
            max_limit: Maximum allowed limit
            max_skip: Maximum allowed skip value
            
        Raises:
            ValueError: If parameters are invalid
        """
        if self.skip < 0:
            raise ValueError("skip must be >= 0")
        
        if self.skip > max_skip:
            raise ValueError(f"skip must be <= {max_skip}")
        
        if self.limit <= 0:
            raise ValueError("limit must be > 0")
        
        if self.limit > max_limit:
            raise ValueError(f"limit must be <= {max_limit}")
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary"""
        return {"skip": self.skip, "limit": self.limit}


def paginate(
    items: List[T],
    skip: int = 0,
    limit: int = 10,
) -> Dict[str, Any]:
    """Paginate a list of items
    
    Args:
        items: List of items
        skip: Number of items to skip
        limit: Maximum number of items to return
        
    Returns:
        Dictionary with paginated data and metadata
    """
    total = len(items)
    paginated_items = items[skip : skip + limit]
    
    return {
        "data": paginated_items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "page": (skip // limit) + 1 if limit > 0 else 1,
        "pages": (total + limit - 1) // limit if limit > 0 else 1,
    }
