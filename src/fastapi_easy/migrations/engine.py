import logging
from typing import Optional

from sqlalchemy import Engine

from .detector import SchemaDetector
from .distributed_lock import get_lock_provider
from .executor import MigrationExecutor
from .generator import MigrationGenerator
from .storage import MigrationStorage
from .types import MigrationPlan

logger = logging.getLogger(__name__)

class MigrationEngine:
    """The main entry point for the migration system"""
    
    def __init__(
        self, 
        engine: Engine, 
        metadata,
        mode: str = "safe",
        auto_backup: bool = False
    ):
        # 验证 mode 参数
        valid_modes = {"safe", "auto", "aggressive", "dry_run"}
        if mode not in valid_modes:
            raise ValueError(
                f"Invalid mode '{mode}'. "
                f"Must be one of {valid_modes}"
            )
        
        # 验证 engine 连接
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            raise RuntimeError(
                f"Cannot connect to database: {e}"
            )
        
        # 验证 metadata
        if not metadata or not metadata.tables:
            logger.warning(
                "Metadata has no tables. "
                "This might indicate a configuration issue."
            )
        
        self.engine = engine
        self.metadata = metadata
        self.mode = mode
        
        # Core components
        self.detector = SchemaDetector(engine, metadata)
        self.generator = MigrationGenerator(engine)
        self.executor = MigrationExecutor(engine, auto_backup)
        self.storage = MigrationStorage(engine)
        self.lock = get_lock_provider(engine)
        
        # Initialize storage
        self.storage.initialize()
        
    async def auto_migrate(self) -> MigrationPlan:
        """Automatically detect and apply migrations"""
        
        # 1. Acquire Lock
        logger.info("🔒 Acquiring migration lock...")
        if not await self.lock.acquire():
            logger.warning("⏳ Could not acquire lock, assuming another instance is migrating.")
            return MigrationPlan(migrations=[], status="locked")
            
        try:
            logger.info("🔄 Checking for schema changes...")
            
            # 2. Detect changes
            changes = await self.detector.detect_changes()
            
            if not changes:
                logger.info("✅ Schema is up to date")
                return MigrationPlan(migrations=[], status="up_to_date")
                
            logger.info(f"⚠️ Detected {len(changes)} schema changes")
            
            # 3. Generate plan
            plan = self.generator.generate_plan(changes)
            
            # 4. Log plan
            for migration in plan.migrations:
                logger.info(f"  [{migration.risk_level.value}] {migration.description}")
            
            # 5. Execute migrations
            logger.info(f"🚀 Executing migrations in '{self.mode}' mode...")
            plan, executed_migrations = await self.executor.execute_plan(plan, mode=self.mode)
            
            # 6. Record successfully executed migrations
            for migration in executed_migrations:
                self.storage.record_migration(
                    version=migration.version,
                    description=migration.description,
                    rollback_sql=migration.downgrade_sql,
                    risk_level=migration.risk_level.value
                )
            
            logger.info(f"✅ Migration completed: {plan.status}")
            return plan
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"❌ 迁移失败: {error_msg}\n"
                f"\n调试步骤:\n"
                f"  1. 检查数据库连接: fastapi-easy migrate status\n"
                f"  2. 查看详细日志: 设置 LOG_LEVEL=DEBUG\n"
                f"  3. 运行 dry-run: fastapi-easy migrate plan --dry-run\n"
                f"  4. 查看完整错误: {error_msg}",
                exc_info=True
            )
            raise
        finally:
            # 7. Release Lock
            logger.info("🔓 Releasing migration lock...")
            try:
                await self.lock.release()
            except Exception as e:
                logger.error(
                    f"❌ 锁释放失败: {e}\n"
                    f"您可能需要手动清理锁文件。\n"
                    f"解决方案:\n"
                    f"  1. 检查锁文件: .fastapi_easy_migration.lock\n"
                    f"  2. 手动删除: rm .fastapi_easy_migration.lock\n"
                    f"  3. 重新运行迁移",
                    exc_info=True
                )
    
    def get_history(self, limit: int = 10):
        """Get migration history"""
        return self.storage.get_migration_history(limit)
