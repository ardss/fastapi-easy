"""
分布式锁机制

支持多种数据库的分布式锁:
- PostgreSQL: pg_advisory_lock
- MySQL: GET_LOCK
- SQLite: 文件锁
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class LockProvider(ABC):
    """分布式锁提供者基类"""

    @abstractmethod
    async def acquire(self, timeout: int = 30) -> bool:
        """获取锁"""
        pass

    @abstractmethod
    async def release(self) -> bool:
        """释放锁"""
        pass

    @abstractmethod
    async def is_locked(self) -> bool:
        """检查是否已锁定"""
        pass


class PostgresLockProvider(LockProvider):
    """PostgreSQL 分布式锁提供者"""

    def __init__(self, engine: Engine, lock_id: int = 1):
        self.engine = engine
        self.lock_id = lock_id
        self.acquired = False

    async def acquire(self, timeout: int = 30) -> bool:
        """使用 pg_advisory_lock 获取锁"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                with self.engine.connect() as conn:
                    # pg_advisory_lock 是阻塞的，所以我们使用 pg_try_advisory_lock
                    result = conn.execute(
                        text(f"SELECT pg_try_advisory_lock({self.lock_id})")
                    )
                    locked = result.scalar()

                    if locked:
                        self.acquired = True
                        logger.info(
                            f"✅ PostgreSQL lock acquired (ID: {self.lock_id})"
                        )
                        return True

                # 等待后重试
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error acquiring PostgreSQL lock: {e}")
                return False

        logger.warning(f"Timeout acquiring PostgreSQL lock after {timeout}s")
        return False

    async def release(self) -> bool:
        """释放 PostgreSQL 锁"""
        if not self.acquired:
            return False

        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text(f"SELECT pg_advisory_unlock({self.lock_id})")
                )
                self.acquired = False
                logger.info(
                    f"🔓 PostgreSQL lock released (ID: {self.lock_id})"
                )
                return True
        except Exception as e:
            logger.error(f"Error releasing PostgreSQL lock: {e}")
            return False

    async def is_locked(self) -> bool:
        """检查锁状态"""
        return self.acquired


class MySQLLockProvider(LockProvider):
    """MySQL 分布式锁提供者"""

    def __init__(self, engine: Engine, lock_name: str = "fastapi_easy_migration"):
        self.engine = engine
        self.lock_name = lock_name
        self.acquired = False

    async def acquire(self, timeout: int = 30) -> bool:
        """使用 GET_LOCK 获取锁"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT GET_LOCK('{self.lock_name}', {timeout})")
                )
                locked = result.scalar()

                if locked == 1:
                    self.acquired = True
                    logger.info(f"✅ MySQL lock acquired ({self.lock_name})")
                    return True
                elif locked == 0:
                    logger.warning(f"Timeout acquiring MySQL lock")
                    return False
                else:
                    logger.error(f"Error acquiring MySQL lock: {locked}")
                    return False

        except Exception as e:
            logger.error(f"Error acquiring MySQL lock: {e}")
            return False

    async def release(self) -> bool:
        """释放 MySQL 锁"""
        if not self.acquired:
            return False

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT RELEASE_LOCK('{self.lock_name}')")
                )
                released = result.scalar()

                if released == 1:
                    self.acquired = False
                    logger.info(f"🔓 MySQL lock released ({self.lock_name})")
                    return True
                else:
                    logger.warning(f"Failed to release MySQL lock")
                    return False

        except Exception as e:
            logger.error(f"Error releasing MySQL lock: {e}")
            return False

    async def is_locked(self) -> bool:
        """检查锁状态"""
        return self.acquired


class FileLockProvider(LockProvider):
    """SQLite 文件锁提供者"""

    def __init__(self, lock_file: Optional[str] = None):
        if lock_file is None:
            lock_file = ".fastapi_easy_migration.lock"
        self.lock_file = lock_file
        self.acquired = False

    async def acquire(self, timeout: int = 30) -> bool:
        """使用文件锁获取锁"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # 尝试创建锁文件（原子操作）
                fd = os.open(
                    self.lock_file,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o644,
                )
                os.close(fd)
                self.acquired = True
                logger.info(f"✅ File lock acquired ({self.lock_file})")
                return True

            except FileExistsError:
                # 锁文件已存在，等待后重试
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error acquiring file lock: {e}")
                return False

        logger.warning(f"Timeout acquiring file lock after {timeout}s")
        return False

    async def release(self) -> bool:
        """释放文件锁"""
        if not self.acquired:
            return False

        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
                self.acquired = False
                logger.info(f"🔓 File lock released ({self.lock_file})")
                return True
            else:
                logger.warning(f"Lock file not found: {self.lock_file}")
                return False

        except Exception as e:
            logger.error(f"Error releasing file lock: {e}")
            return False

    async def is_locked(self) -> bool:
        """检查锁状态"""
        return self.acquired


def get_lock_provider(
    engine: Engine, lock_file: Optional[str] = None
) -> LockProvider:
    """根据数据库类型获取合适的锁提供者"""
    dialect = engine.dialect.name

    if dialect == "postgresql":
        return PostgresLockProvider(engine)
    elif dialect == "mysql":
        return MySQLLockProvider(engine)
    elif dialect == "sqlite":
        return FileLockProvider(lock_file)
    else:
        logger.warning(
            f"Unknown dialect {dialect}, using file lock as fallback"
        )
        return FileLockProvider(lock_file)
