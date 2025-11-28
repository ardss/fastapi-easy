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
            logger.error(f"❌ Migration failed: {e}")
            raise
        finally:
            # 7. Release Lock
            logger.info("🔓 Releasing migration lock...")
            await self.lock.release()
    
    def get_history(self, limit: int = 10):
        """Get migration history"""
        return self.storage.get_migration_history(limit)
