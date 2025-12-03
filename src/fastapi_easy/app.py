"""
FastAPIEasy 应用类 - 集成迁移引擎的 FastAPI 应用

提供零配置的 Schema 迁移功能
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Type

from fastapi import FastAPI
from sqlalchemy import MetaData, create_engine, text

from .migrations.engine import MigrationEngine
from .migrations.exceptions import MigrationError

logger = logging.getLogger(__name__)


class FastAPIEasy(FastAPI):
    """
    集成迁移引擎的 FastAPI 应用
    
    提供零配置的 Schema 迁移功能，支持自动检测和应用数据库迁移。
    
    示例:
        ```python
        from fastapi_easy import FastAPIEasy
        from sqlalchemy import Column, Integer, String
        from sqlalchemy.orm import declarative_base
        
        Base = declarative_base()
        
        class User(Base):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))
        
        app = FastAPIEasy(
            database_url="sqlite:///db.sqlite",
            models=[User],
            migration_mode="safe"
        )
        ```
    """
    
    def __init__(
        self,
        database_url: str,
        models: Optional[List[Type]] = None,
        migration_mode: str = "safe",
        auto_migrate: bool = True,
        **kwargs
    ):
        """
        初始化 FastAPIEasy 应用
        
        Args:
            database_url: 数据库连接字符串
                示例: "sqlite:///db.sqlite", "postgresql://user:pass@localhost/db"
            models: SQLAlchemy ORM 模型列表，用于自动检测 Schema
            migration_mode: 迁移模式
                - "safe": 仅执行安全迁移（默认）
                - "auto": 自动执行中等风险迁移
                - "aggressive": 执行所有迁移
            auto_migrate: 是否在应用启动时自动执行迁移
            **kwargs: 传递给 FastAPI 的其他参数
        """
        # 验证参数
        if not database_url:
            raise ValueError("database_url 不能为空")
        
        valid_modes = {"safe", "auto", "aggressive", "dry_run"}
        if migration_mode not in valid_modes:
            raise ValueError(
                f"migration_mode 必须是 {valid_modes} 之一，"
                f"收到: {migration_mode}"
            )
        
        # 初始化 FastAPI
        lifespan = kwargs.pop("lifespan", None)
        super().__init__(lifespan=self._create_lifespan(lifespan), **kwargs)
        
        # 存储配置
        self.database_url = database_url
        self.models = models or []
        self.migration_mode = migration_mode
        self.auto_migrate = auto_migrate
        
        # 初始化迁移引擎
        self._migration_engine: Optional[MigrationEngine] = None
        self._metadata: Optional[MetaData] = None
        
        logger.info(
            f"FastAPIEasy application initialized: "
            f"database={database_url}, "
            f"mode={migration_mode}, "
            f"auto_migrate={auto_migrate}"
        )
    
    def _create_lifespan(self, user_lifespan):
        """创建应用生命周期管理器"""
        @asynccontextmanager
        async def lifespan(app):
            # 启动事件
            try:
                await self._startup()
                logger.info("FastAPIEasy application startup completed")
            except Exception as e:
                logger.error(f"Application startup failed: {e}", exc_info=True)
                raise
            
            # 用户的启动逻辑
            if user_lifespan:
                async with user_lifespan(app):
                    yield
            else:
                yield
            
            # 关闭事件
            try:
                await self._shutdown()
                logger.info("FastAPIEasy application shutdown completed")
            except Exception as e:
                logger.error(f"Application shutdown failed: {e}", exc_info=True)
        
        return lifespan
    
    async def _startup(self):
        """应用启动时的初始化"""
        try:
            # 创建数据库引擎
            engine = create_engine(self.database_url)
            
            # 验证数据库连接
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("✅ Database connection verified")
            except (ConnectionError, OSError) as e:
                raise ValueError(f"Database connection failed: {e}")
            except Exception as e:
                raise ValueError(f"Database connection verification failed: {e}")
            
            # 创建 metadata
            metadata = MetaData()
            
            # 如果提供了模型，从模型中收集 metadata
            if self.models:
                for model in self.models:
                    if not hasattr(model, "__table__"):
                        raise TypeError(
                            f"Invalid model: {model} - missing __table__ attribute"
                        )
                    metadata.tables[model.__table__.name] = model.__table__
                logger.info(f"✅ Loaded {len(self.models)} models")
            
            self._metadata = metadata
            
            # 创建迁移引擎
            self._migration_engine = MigrationEngine(
                engine,
                metadata,
                mode=self.migration_mode
            )
            
            # 初始化存储
            try:
                self._migration_engine.storage.initialize()
                logger.info("✅ Migration storage initialized")
            except (OSError, IOError) as e:
                logger.error(f"Storage initialization failed (I/O error): {e}")
                raise
            except Exception as e:
                logger.error(f"Storage initialization failed: {e}")
                raise
            
            # 自动执行迁移
            if self.auto_migrate:
                await self._run_auto_migration()
            
        except (ValueError, TypeError) as e:
            logger.error(f"Application startup configuration error: {e}")
            raise
        except Exception as e:
            logger.error(f"Application startup failed: {e}", exc_info=True)
            raise
    
    async def _shutdown(self):
        """Application shutdown cleanup"""
        # Release resources
        if self._migration_engine:
            try:
                # Release lock
                if hasattr(self._migration_engine, "_lock_provider"):
                    lock_provider = self._migration_engine._lock_provider
                    if lock_provider and hasattr(lock_provider, "release"):
                        await lock_provider.release()
            except Exception as e:
                logger.warning(f"Failed to release lock: {e}")
    
    async def _run_auto_migration(self):
        """Automatically run migrations"""
        if not self._migration_engine:
            return
        
        try:
            logger.info(f"Starting auto migration (mode: {self.migration_mode})...")
            
            # Execute migration
            result = await self._migration_engine.auto_migrate()
            
            if result and hasattr(result, "migrations"):
                migration_count = len(result.migrations)
                if migration_count > 0:
                    logger.info(f"Successfully applied {migration_count} migrations")
                else:
                    logger.info("Schema is up to date, no migrations needed")
            else:
                logger.info("Migration completed")
        
        except MigrationError as e:
            logger.error(f"Migration failed: {e.message}")
            if e.suggestion:
                logger.error(f"Suggestion: {e.suggestion}")
            raise
        except Exception as e:
            logger.error(f"Migration process error: {e}", exc_info=True)
            raise
    
    @property
    def migration_engine(self) -> Optional[MigrationEngine]:
        """获取迁移引擎实例"""
        return self._migration_engine
    
    def get_migration_history(self, limit: int = 10) -> List[dict]:
        """
        Get migration history
        
        Args:
            limit: Maximum number of records to return
        
        Returns:
            List of migration history records
        """
        if not self._migration_engine:
            logger.warning("Migration engine not initialized")
            return []
        
        try:
            return self._migration_engine.storage.get_migration_history(limit=limit)
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
    
    async def run_migration(self, mode: Optional[str] = None) -> bool:
        """
        Manually run migration
        
        Args:
            mode: Migration mode, uses app config if not specified
        
        Returns:
            Whether the migration was successful
        """
        if not self._migration_engine:
            logger.error("Migration engine not initialized")
            return False
        
        try:
            original_mode = self._migration_engine.mode
            
            # Temporarily switch mode if specified
            if mode:
                self._migration_engine.mode = mode
            
            logger.info(f"Running manual migration (mode: {self._migration_engine.mode})...")
            result = await self._migration_engine.auto_migrate()
            
            # Restore original mode
            if mode:
                self._migration_engine.mode = original_mode
            
            return result is not None
        
        except Exception as e:
            logger.error(f"Manual migration failed: {e}", exc_info=True)
            return False
