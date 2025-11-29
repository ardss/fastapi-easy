"""
FastAPIEasy 应用类 - 集成迁移引擎的 FastAPI 应用

提供零配置的 Schema 迁移功能
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Tuple, Type

from fastapi import FastAPI
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import declarative_base

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
            f"FastAPIEasy 应用初始化: "
            f"数据库={database_url}, "
            f"模式={migration_mode}, "
            f"自动迁移={auto_migrate}"
        )
    
    def _create_lifespan(self, user_lifespan):
        """创建应用生命周期管理器"""
        @asynccontextmanager
        async def lifespan(app):
            # 启动事件
            try:
                await self._startup()
                logger.info("FastAPIEasy 应用启动完成")
            except Exception as e:
                logger.error(f"应用启动失败: {e}", exc_info=True)
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
                logger.info("FastAPIEasy 应用关闭完成")
            except Exception as e:
                logger.error(f"应用关闭失败: {e}", exc_info=True)
        
        return lifespan
    
    async def _startup(self):
        """应用启动时的初始化"""
        try:
            # 创建数据库引擎
            engine = create_engine(self.database_url)
            
            # 创建 metadata
            metadata = MetaData()
            
            # 如果提供了模型，从模型中收集 metadata
            if self.models:
                for model in self.models:
                    if hasattr(model, "__table__"):
                        metadata.tables[model.__table__.name] = model.__table__
            
            self._metadata = metadata
            
            # 创建迁移引擎
            self._migration_engine = MigrationEngine(
                engine,
                metadata,
                mode=self.migration_mode
            )
            
            # 初始化存储
            self._migration_engine.storage.initialize()
            
            # 自动执行迁移
            if self.auto_migrate:
                await self._run_auto_migration()
            
        except Exception as e:
            logger.error(f"启动迁移引擎失败: {e}", exc_info=True)
            raise
    
    async def _shutdown(self):
        """应用关闭时的清理"""
        # 释放资源
        if self._migration_engine:
            try:
                # 释放锁
                if hasattr(self._migration_engine, "_lock_provider"):
                    lock_provider = self._migration_engine._lock_provider
                    if lock_provider and hasattr(lock_provider, "release"):
                        await lock_provider.release()
            except Exception as e:
                logger.warning(f"释放锁失败: {e}")
    
    async def _run_auto_migration(self):
        """自动执行迁移"""
        if not self._migration_engine:
            return
        
        try:
            logger.info(f"开始自动迁移 (模式: {self.migration_mode})...")
            
            # 执行迁移
            result = await self._migration_engine.auto_migrate()
            
            if result and hasattr(result, "migrations"):
                migration_count = len(result.migrations)
                if migration_count > 0:
                    logger.info(f"✅ 成功应用 {migration_count} 个迁移")
                else:
                    logger.info("✅ Schema 已是最新，无需迁移")
            else:
                logger.info("✅ 迁移完成")
        
        except MigrationError as e:
            logger.error(f"❌ 迁移失败: {e.message}")
            if e.suggestion:
                logger.error(f"💡 建议: {e.suggestion}")
            raise
        except Exception as e:
            logger.error(f"❌ 迁移过程出错: {e}", exc_info=True)
            raise
    
    @property
    def migration_engine(self) -> Optional[MigrationEngine]:
        """获取迁移引擎实例"""
        return self._migration_engine
    
    def get_migration_history(self, limit: int = 10) -> List[dict]:
        """
        获取迁移历史
        
        Args:
            limit: 返回的最大记录数
        
        Returns:
            迁移历史列表
        """
        if not self._migration_engine:
            logger.warning("迁移引擎未初始化")
            return []
        
        try:
            return self._migration_engine.storage.get_migration_history(limit=limit)
        except Exception as e:
            logger.error(f"获取迁移历史失败: {e}")
            return []
    
    async def run_migration(self, mode: Optional[str] = None) -> bool:
        """
        手动运行迁移
        
        Args:
            mode: 迁移模式，如果不指定则使用应用配置的模式
        
        Returns:
            是否成功
        """
        if not self._migration_engine:
            logger.error("迁移引擎未初始化")
            return False
        
        try:
            original_mode = self._migration_engine.mode
            
            # 如果指定了模式，临时切换
            if mode:
                self._migration_engine.mode = mode
            
            logger.info(f"手动运行迁移 (模式: {self._migration_engine.mode})...")
            result = await self._migration_engine.auto_migrate()
            
            # 恢复原始模式
            if mode:
                self._migration_engine.mode = original_mode
            
            return result is not None
        
        except Exception as e:
            logger.error(f"手动迁移失败: {e}", exc_info=True)
            return False
