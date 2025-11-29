import logging
import time
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .types import OperationResult, RecordStatus

logger = logging.getLogger(__name__)

class MigrationStorage:
    """Manages migration history in the database"""
    
    TABLE_NAME = "_fastapi_easy_migrations"
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.metadata = MetaData()
        
        # Define migration history table
        self.table = Table(
            self.TABLE_NAME,
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('version', String(100), unique=True, nullable=False),
            Column('description', String(500)),
            Column('applied_at', DateTime, default=datetime.now),
            Column('rollback_sql', String(10000)),
            Column('risk_level', String(20)),
            Column('status', String(20), default='applied'),
        )
    
    def initialize(self, max_retries: int = 3):
        """Create migration history table if it doesn't exist"""
        for attempt in range(max_retries):
            try:
                self.metadata.create_all(self.engine, checkfirst=True)
                logger.debug(
                    f"✅ Migration history table '{self.TABLE_NAME}' ready"
                )
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Failed to initialize storage "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    time.sleep(1)
                else:
                    logger.error(
                        f"Failed to initialize storage after "
                        f"{max_retries} attempts: {e}"
                    )
                    raise

    def record_migration(
        self,
        version: str,
        description: str,
        rollback_sql: str,
        risk_level: str
    ) -> OperationResult:
        """Record a successful migration
        
        Returns:
            OperationResult with success status
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text(f"""
                        INSERT INTO {self.TABLE_NAME}
                        (version, description, applied_at,
                         rollback_sql, risk_level, status)
                        VALUES (:version, :description, :applied_at,
                                :rollback_sql, :risk_level, :status)
                    """),
                    {
                        "version": version,
                        "description": description,
                        "applied_at": datetime.now(),
                        "rollback_sql": rollback_sql,
                        "risk_level": risk_level,
                        "status": RecordStatus.APPLIED.value,
                    }
                )
            logger.info(f"📝 Recorded migration: {version}")
            return OperationResult(
                success=True,
                data={"version": version},
                metadata={"idempotent": False}
            )

        except IntegrityError:
            # 迁移已记录，这不是错误（幂等性）
            logger.warning(
                f"Migration {version} already recorded (idempotent)"
            )
            return OperationResult(
                success=True,
                data={"version": version},
                metadata={"idempotent": True}
            )

        except Exception as e:
            # 记录失败不应阻止迁移
            logger.warning(
                f"⚠️ Failed to record migration {version} in history: {e}\n"
                f"迁移已执行，但历史记录失败。"
                f"这不会影响迁移本身，但会影响回滚功能。"
            )
            return OperationResult(
                success=False,
                errors=[str(e)],
                metadata={"non_blocking": True}
            )
    
    def get_applied_versions(self) -> List[str]:
        """Get list of applied migration versions
        
        Returns:
            List of applied migration version strings
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        f"SELECT version FROM {self.TABLE_NAME} "
                        f"WHERE status = 'applied' ORDER BY applied_at"
                    )
                )
                return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"Could not fetch migration history: {e}")
            return []
    
    def get_migration_history(self, limit: int = 10) -> List[dict]:
        """Get recent migration history"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(f"""
                        SELECT version, description, applied_at, risk_level, status 
                        FROM {self.TABLE_NAME} 
                        ORDER BY applied_at DESC 
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
                return [
                    {
                        "version": row[0],
                        "description": row[1],
                        "applied_at": row[2],
                        "risk_level": row[3],
                        "status": row[4],
                    }
                    for row in result
                ]
        except Exception as e:
            logger.warning(f"Could not fetch migration history: {e}")
            return []
