from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# ============================================================================
# 执行模式定义
# ============================================================================

class ExecutionMode(str, Enum):
    """迁移执行模式
    
    SAFE: 仅执行低风险迁移 (默认)
    AUTO: 执行低风险和中风险迁移
    AGGRESSIVE: 执行所有迁移 (包括高风险)
    DRY_RUN: 仅显示迁移计划，不执行
    """
    SAFE = "safe"
    AUTO = "auto"
    AGGRESSIVE = "aggressive"
    DRY_RUN = "dry_run"

# ============================================================================
# 风险级别定义
# ============================================================================

class RiskLevel(str, Enum):
    """迁移风险级别
    
    SAFE (低风险):
    - 添加可空列
    - 添加有默认值的列
    - 创建新表
    - 添加索引
    
    MEDIUM (中等风险):
    - 添加不可空列 (有默认值)
    - 修改列类型 (兼容的)
    - 删除索引
    
    HIGH (高风险):
    - 删除列 (数据丢失)
    - 删除表 (数据丢失)
    - 修改列类型 (不兼容的)
    - 添加 NOT NULL 约束 (现有数据可能违反)
    """
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"

# ============================================================================
# 迁移状态定义
# ============================================================================

class PlanStatus(str, Enum):
    """迁移计划状态
    
    UP_TO_DATE: Schema 已是最新
    PENDING: 有待执行的迁移
    COMPLETED: 所有迁移已执行
    PARTIAL: 部分迁移已执行
    FAILED: 迁移失败
    """
    UP_TO_DATE = "up_to_date"
    PENDING = "pending"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"

class RecordStatus(str, Enum):
    """迁移记录状态
    
    APPLIED: 已应用
    FAILED: 失败
    ROLLED_BACK: 已回滚
    """
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class MigrationStatus(str, Enum):
    """迁移状态 (已弃用，使用 PlanStatus 或 RecordStatus)"""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

# ============================================================================
# 统一的操作结果类型
# ============================================================================

@dataclass
class OperationResult:
    """统一的操作结果
    
    用于所有返回操作结果的函数，提供一致的 API。
    
    属性:
        success: 操作是否成功
        data: 操作返回的数据 (如果成功)
        errors: 错误列表 (如果失败)
        metadata: 额外的元数据 (如执行时间、影响行数等)
    """
    success: bool
    data: Any = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        """添加错误消息"""
        self.errors.append(error)
        self.success = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'data': self.data,
            'errors': self.errors,
            'metadata': self.metadata
        }

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
