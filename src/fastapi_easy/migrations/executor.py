import asyncio
import logging
from typing import List

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .types import ExecutionMode, Migration, MigrationPlan, RiskLevel

logger = logging.getLogger(__name__)

class MigrationExecutor:
    """Executes migrations with transaction safety"""
    
    def __init__(self, engine: Engine, auto_backup: bool = False):
        self.engine = engine
        self.auto_backup = auto_backup
        self.dialect = engine.dialect.name

    async def execute_plan(self, plan: MigrationPlan, mode: ExecutionMode = ExecutionMode.SAFE) -> tuple[MigrationPlan, List[Migration]]:
        """
        Execute a migration plan based on mode.
        
        Args:
            plan: The migration plan to execute
            mode: Execution mode (ExecutionMode enum)
                - SAFE: Only execute SAFE migrations automatically
                - AUTO: Execute SAFE and MEDIUM automatically
                - AGGRESSIVE: Execute all migrations
                - DRY_RUN: Don't execute, just log
        
        Returns:
            Tuple of (updated plan, list of successfully executed migrations)
        """
        if mode == ExecutionMode.DRY_RUN:
            logger.info("🔍 Dry-run mode: No migrations will be executed")
            for migration in plan.migrations:
                logger.info(f"  Would execute: {migration.description}")
                logger.debug(f"    SQL: {migration.upgrade_sql}")
            return plan, []
        
        # Categorize migrations by risk
        safe_migrations = [m for m in plan.migrations if m.risk_level == RiskLevel.SAFE]
        medium_migrations = [m for m in plan.migrations if m.risk_level == RiskLevel.MEDIUM]
        risky_migrations = [m for m in plan.migrations if m.risk_level == RiskLevel.HIGH]
        
        executed = []
        
        # Execute based on mode
        if mode in [ExecutionMode.SAFE, ExecutionMode.AUTO, ExecutionMode.AGGRESSIVE]:
            # Always execute safe migrations
            if safe_migrations:
                logger.info(f"🔄 Executing {len(safe_migrations)} SAFE migrations...")
                for migration in safe_migrations:
                    try:
                        if await self._execute_migration(migration):
                            executed.append(migration)
                    except Exception as e:
                        logger.error(f"  ❌ Migration failed, stopping execution: {e}")
                        raise  # Re-raise to stop execution on failure
        
        if mode in [ExecutionMode.AUTO, ExecutionMode.AGGRESSIVE]:
            # Execute medium risk migrations
            if medium_migrations:
                logger.info(f"⚠️ Executing {len(medium_migrations)} MEDIUM risk migrations...")
                for migration in medium_migrations:
                    try:
                        if await self._execute_migration(migration):
                            executed.append(migration)
                    except Exception as e:
                        logger.error(f"  ❌ Migration failed, stopping execution: {e}")
                        raise
        
        if mode == ExecutionMode.AGGRESSIVE:
            # Execute high risk migrations
            if risky_migrations:
                logger.warning(f"🔴 Executing {len(risky_migrations)} HIGH risk migrations...")
                for migration in risky_migrations:
                    try:
                        if await self._execute_migration(migration):
                            executed.append(migration)
                    except Exception as e:
                        logger.error(f"  ❌ Migration failed, stopping execution: {e}")
                        raise
        else:
            # Warn about unexecuted risky migrations
            if risky_migrations:
                logger.warning(f"⚠️ {len(risky_migrations)} HIGH risk migrations require manual review:")
                for migration in risky_migrations:
                    logger.warning(f"  - {migration.description}")
        
        plan.status = "completed" if len(executed) == len(plan.migrations) else "partial"
        return plan, executed

    async def _execute_migration(self, migration: Migration) -> bool:
        """
        Execute a single migration with transaction safety.
        
        Returns:
            True if successful
        
        Raises:
            Exception if migration fails
        """
        logger.info(f"  ▶️ Executing: {migration.description}")
        
        # Run in thread pool to avoid blocking
        await asyncio.to_thread(self._execute_sql_sync, migration.upgrade_sql)
        logger.info(f"  ✅ Success: {migration.description}")
        return True

    def _execute_sql_sync(self, sql: str):
        """Execute SQL synchronously within a transaction"""
        try:
            # 使用 engine.begin() 自动处理事务
            with self.engine.begin() as conn:
                statements = self._split_sql_statements(sql)
                for statement in statements:
                    if statement:
                        logger.debug(f"    Executing: {statement[:100]}...")
                        conn.execute(text(statement))
                # 自动提交
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            # 自动回滚
            raise
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL into individual statements, handling multi-line statements"""
        # Remove leading/trailing whitespace and split by semicolon
        statements = []
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.upper().startswith('--'):  # Skip comments
                # Skip BEGIN/COMMIT keywords as they're handled by SQLAlchemy
                if stmt.upper() not in ['BEGIN', 'BEGIN TRANSACTION', 'COMMIT']:
                    statements.append(stmt)
        return statements
