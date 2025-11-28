from typing import Optional
from fastapi import FastAPI
from sqlalchemy import create_engine
from .migrations.engine import MigrationEngine
from .core.config import CRUDConfig

class FastAPI_Easy:
    """
    Main entry point for FastAPI-Easy.
    Handles initialization of the migration engine and other global services.
    """
    
    _instance = None
    
    def __init__(self, app: FastAPI, database_url: str):
        self.app = app
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.migration_engine: Optional[MigrationEngine] = None
        
        # Hook into startup
        app.add_event_handler("startup", self._startup)
        
        FastAPI_Easy._instance = self

    @classmethod
    def init_app(cls, app: FastAPI, database_url: str) -> "FastAPI_Easy":
        return cls(app, database_url)

    @classmethod
    def get_instance(cls):
        return cls._instance

    async def _startup(self):
        """Startup hook"""
        # We need to collect metadata from all registered CRUDRouters
        # For now, we assume users import their models and Base is populated.
        # In a real scenario, we might need a central registry for models.
        
        # TODO: Better way to get the global Base metadata
        # For now, we rely on the user passing it or finding it.
        # This is a temporary limitation of Phase 1.
        pass
        
    def set_metadata(self, metadata):
        """Manually set metadata for migration engine"""
        self.migration_engine = MigrationEngine(self.engine, metadata)
        
    async def run_migrations(self):
        if self.migration_engine:
            await self.migration_engine.auto_migrate()
