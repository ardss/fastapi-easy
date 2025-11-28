import logging
from typing import Optional
from sqlalchemy import Engine
from .detector import SchemaDetector
from .generator import MigrationGenerator
from .types import MigrationPlan
from .locks import get_lock_provider

logger = logging.getLogger(__name__)

class MigrationEngine:
    """The main entry point for the migration system"""
    
    def __init__(self, engine: Engine, metadata):
        self.engine = engine
        self.metadata = metadata
        self.detector = SchemaDetector(engine, metadata)
        self.generator = MigrationGenerator(engine)
        self.lock = get_lock_provider(engine)
        
    async def auto_migrate(self) -> MigrationPlan:
        """Automatically detect and apply migrations"""
        
        # 1. Acquire Lock
        logger.info("🔒 Acquiring migration lock...")
        if not await self.lock.acquire():
            logger.warning("⏳ Could not acquire lock, assuming another instance is migrating.")
            # In a real scenario, we should wait and retry or check if migration completed.
            # For now, we just return up-to-date status to avoid crashing.
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
            
            # 4. Execute (Placeholder for now)
            # In Phase 1, we just print the plan
            for migration in plan.migrations:
                logger.info(f"  [{migration.risk_level}] {migration.description}")
                logger.debug(f"    SQL: {migration.upgrade_sql}")
                
            return plan
            
        finally:
            # 5. Release Lock
            logger.info("🔓 Releasing migration lock...")
            await self.lock.release()
