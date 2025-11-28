import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.engine import Engine
from sqlalchemy import text, Table, Column, Integer, String, DateTime, MetaData

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
    
    def initialize(self):
        """Create migration history table if it doesn't exist"""
        try:
            self.metadata.create_all(self.engine, checkfirst=True)
            logger.debug(f"✅ Migration history table '{self.TABLE_NAME}' ready")
        except Exception as e:
            logger.error(f"Failed to initialize migration storage: {e}")
            raise
    
    def record_migration(self, version: str, description: str, rollback_sql: str, risk_level: str):
        """Record a successful migration"""
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text(f"""
                        INSERT INTO {self.TABLE_NAME} 
                        (version, description, applied_at, rollback_sql, risk_level, status)
                        VALUES (:version, :description, :applied_at, :rollback_sql, :risk_level, 'applied')
                    """),
                    {
                        "version": version,
                        "description": description,
                        "applied_at": datetime.now(),
                        "rollback_sql": rollback_sql,
                        "risk_level": risk_level,
                    }
                )
            logger.debug(f"📝 Recorded migration: {version}")
        except Exception as e:
            logger.error(f"Failed to record migration {version}: {e}")
            # Don't raise - recording failure shouldn't block migration
    
    def get_applied_versions(self) -> List[str]:
        """Get list of applied migration versions"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT version FROM {self.TABLE_NAME} WHERE status = 'applied' ORDER BY applied_at")
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
