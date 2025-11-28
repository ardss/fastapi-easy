from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime

class RiskLevel(str, Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"

class MigrationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class SchemaChange(BaseModel):
    """Represents a detected change in the schema"""
    type: str  # create_table, add_column, drop_column, etc.
    table: str
    column: Optional[str] = None
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    nullable: Optional[bool] = None
    default: Optional[Any] = None
    risk_level: RiskLevel
    description: str
    warning: Optional[str] = None
    
    # For internal use (e.g., SQLAlchemy column object)
    column_obj: Optional[Any] = None 
    
    class Config:
        arbitrary_types_allowed = True

class Migration(BaseModel):
    """Represents a single migration step"""
    version: str
    description: str
    risk_level: RiskLevel
    upgrade_sql: str
    downgrade_sql: str
    created_at: datetime = datetime.now()
    
    # For data migration hooks
    pre_hook: Optional[str] = None
    post_hook: Optional[str] = None

class MigrationPlan(BaseModel):
    """A plan containing multiple migrations"""
    migrations: List[Migration]
    status: str  # up_to_date, pending, completed, failed
    
class MigrationRecord(BaseModel):
    """Record stored in the database"""
    id: int
    version: str
    description: str
    applied_at: datetime
    rollback_sql: str
    risk_level: str
    status: str
