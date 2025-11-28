from typing import Any, Optional
from sqlalchemy import Column
from .types import RiskLevel, SchemaChange

class RiskAssessor:
    """Evaluates the risk level of schema changes"""
    
    def __init__(self, dialect: str):
        self.dialect = dialect

    def assess(self, change_type: str, **kwargs) -> RiskLevel:
        method_name = f"_assess_{change_type}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(**kwargs)
        return RiskLevel.HIGH  # Default to high risk for unknown changes

    def _assess_create_table(self, **kwargs) -> RiskLevel:
        return RiskLevel.SAFE

    def _assess_add_column(self, column: Column, **kwargs) -> RiskLevel:
        if column.nullable:
            return RiskLevel.SAFE
        
        if column.default is not None or column.server_default is not None:
            return RiskLevel.MEDIUM
            
        return RiskLevel.HIGH

    def _assess_drop_column(self, **kwargs) -> RiskLevel:
        return RiskLevel.HIGH

    def _assess_change_column(self, old_type: str, new_type: str, **kwargs) -> RiskLevel:
        # SQLite type changes are always high risk due to copy-swap
        if self.dialect == "sqlite":
            return RiskLevel.HIGH
            
        # TODO: Implement smarter type compatibility check
        # e.g. VARCHAR(50) -> VARCHAR(100) is SAFE
        # INTEGER -> VARCHAR is MEDIUM (usually safe but changes data)
        # VARCHAR -> INTEGER is HIGH (data loss)
        
        return RiskLevel.HIGH
