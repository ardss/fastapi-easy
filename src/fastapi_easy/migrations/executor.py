import asyncio
import logging
from typing import List

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .types import ExecutionMode, Migration, MigrationPlan, RiskLevel

logger = logging.getLogger(__name__)


class MigrationExecutor:
    """Executes migrations with transaction safety"""
    
    def __init__(self, engine: Engine):
        """初始化迁移执行器

        Args:
            engine: SQLAlchemy 引擎
        """
        self.engine = engine
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
            logger.info("干运行模式: 不执行任何迁移")
            for migration in plan.migrations:
                logger.info(f"将执行: {migration.description}")
                logger.debug(f"SQL: {migration.upgrade_sql}")
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
                logger.info(f"执行 {len(safe_migrations)} 个低风险迁移")
                for migration in safe_migrations:
                    try:
                        if await self._execute_migration(migration):
                            executed.append(migration)
                    except Exception as e:
                        logger.error(f"迁移失败，停止执行: {e}")
                        raise  # Re-raise to stop execution on failure

        if mode in [ExecutionMode.AUTO, ExecutionMode.AGGRESSIVE]:
            # Execute medium risk migrations
            if medium_migrations:
                logger.info(f"执行 {len(medium_migrations)} 个中等风险迁移")
                for migration in medium_migrations:
                    try:
                        if await self._execute_migration(migration):
                            executed.append(migration)
                    except Exception as e:
                        logger.error(f"迁移失败，停止执行: {e}")
                        raise

        if mode == ExecutionMode.AGGRESSIVE:
            # Execute high risk migrations
            if risky_migrations:
                logger.warning(f"执行 {len(risky_migrations)} 个高风险迁移")
                for migration in risky_migrations:
                    try:
                        if await self._execute_migration(migration):
                            executed.append(migration)
                    except Exception as e:
                        logger.error(f"迁移失败，停止执行: {e}")
                        raise
        else:
            # Warn about unexecuted risky migrations
            if risky_migrations:
                logger.warning(f"{len(risky_migrations)} 个高风险迁移需要手动审查")
                for migration in risky_migrations:
                    logger.warning(f"- {migration.description}")
        
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
        logger.info(f"执行: {migration.description}")

        # Run in thread pool to avoid blocking
        try:
            await asyncio.to_thread(
                self._execute_sql_sync, migration.upgrade_sql
            )
            logger.info(f"成功: {migration.description}")
            return True
        except Exception:
            logger.error(f"迁移失败: {migration.description}")
            # 尝试执行回滚 SQL
            if migration.downgrade_sql:
                try:
                    logger.info(f"尝试回滚: {migration.description}")
                    await asyncio.to_thread(
                        self._execute_sql_sync, migration.downgrade_sql
                    )
                    logger.info(f"回滚成功: {migration.description}")
                except Exception as rollback_error:
                    logger.error(
                        f"回滚失败: {migration.description} - {rollback_error}"
                    )
            raise

    def _execute_sql_sync(self, sql: str) -> None:
        """Execute SQL synchronously within a transaction
        
        Args:
            sql: SQL string to execute
            
        Raises:
            Exception: If SQL execution fails
        """
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
        """Split SQL into individual statements, handling multi-line statements
        
        Args:
            sql: SQL string to split
            
        Returns:
            List of individual SQL statements
        """
        # Remove leading/trailing whitespace and split by semicolon
        statements = []
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.upper().startswith('--'):  # Skip comments
                # Skip BEGIN/COMMIT keywords as they're handled by SQLAlchemy
                if stmt.upper() not in ['BEGIN', 'BEGIN TRANSACTION', 'COMMIT']:
                    statements.append(stmt)
        return statements
