import logging
from typing import Optional
from sqlalchemy import Engine
from .detector import SchemaDetector
from .generator import MigrationGenerator
from .types import MigrationPlan

logger = logging.getLogger(__name__)

class MigrationEngine:
    """The main entry point for the migration system"""
    
    def __init__(self, engine: Engine, metadata):
        self.engine = engine
        self.metadata = metadata
        self.detector = SchemaDetector(engine, metadata)
        self.generator = MigrationGenerator(engine)
        
    async def auto_migrate(self) -> MigrationPlan:
        """Automatically detect and apply migrations"""
        logger.info("🔄 Checking for schema changes...")
        
        # 1. Detect changes
        changes = await self.detector.detect_changes()
        
        if not changes:
            logger.info("✅ Schema is up to date")
            return MigrationPlan(migrations=[], status="up_to_date")
            
        logger.info(f"⚠️ Detected {len(changes)} schema changes")
        
        # 2. Generate plan
        plan = self.generator.generate_plan(changes)
        
        # 3. Execute (Placeholder for now)
        # In Phase 1, we just print the plan
        for migration in plan.migrations:
            logger.info(f"  [{migration.risk_level}] {migration.description}")
            logger.debug(f"    SQL: {migration.upgrade_sql}")
            
        return plan
