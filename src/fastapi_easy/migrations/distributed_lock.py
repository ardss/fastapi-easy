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

    def __init__(self, engine: Engine, lock_id: int = 1, max_connection_age: int = 300):
        self.engine = engine
        self.lock_id = lock_id
        self.acquired = False
        self._connection = None
        self.max_connection_age = max_connection_age  # 最大连接持有时间（秒）
        self._connection_created_at = None

    async def acquire(self, timeout: int = 30) -> bool:
        """使用 pg_advisory_lock 获取锁
        
        Args:
            timeout: 获取锁的超时时间（秒）
            
        Returns:
            True 表示成功获取锁，False 表示失败
        """
        start_time = time.time()
        conn = None

        try:
            # 创建单个连接用于整个获取过程
            conn = self.engine.connect()

            while time.time() - start_time < timeout:
                try:
                    # 使用参数化查询防止 SQL 注入
                    result = conn.execute(
                        text("SELECT pg_try_advisory_lock(:lock_id)"),
                        {"lock_id": self.lock_id}
                    )
                    locked = result.scalar()

                    if locked:
                        self.acquired = True
                        self._connection = conn  # 保存连接以供释放使用
                        self._connection_created_at = time.time()  # 记录连接创建时间
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

        finally:
            # 如果未获取锁，关闭连接
            if conn and not self.acquired:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")

    async def release(self) -> bool:
        """释放 PostgreSQL 锁"""
        if not self.acquired or not self._connection:
            return False

        try:
            # 检查连接年龄，防止长期占用
            if self._connection_created_at:
                age = time.time() - self._connection_created_at
                if age > self.max_connection_age:
                    logger.warning(
                        f"Connection held for {age}s (max: {self.max_connection_age}s), "
                        f"forcing close"
                    )
            
            self._connection.execute(
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
        finally:
            # 释放连接
            if self._connection:
                try:
                    self._connection.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
                finally:
                    self._connection = None
                    self._connection_created_at = None

    async def is_locked(self) -> bool:
        """检查锁状态"""
        return self.acquired


class MySQLLockProvider(LockProvider):
    """MySQL 分布式锁提供者"""

    def __init__(self, engine: Engine, lock_name: str = "fastapi_easy_migration"):
        self.engine = engine
        self.lock_name = lock_name
        self.acquired = False
        self._connection = None

    async def acquire(self, timeout: int = 30) -> bool:
        """使用 GET_LOCK 获取锁
        
        Args:
            timeout: 获取锁的超时时间（秒）
            
        Returns:
            True 表示成功获取锁，False 表示失败
        """
        try:
            conn = self.engine.connect()
            # 使用参数化查询防止 SQL 注入
            result = conn.execute(
                text("SELECT GET_LOCK(:lock_name, :timeout)"),
                {"lock_name": self.lock_name, "timeout": timeout}
            )
            locked = result.scalar()

            if locked == 1:
                self.acquired = True
                self._connection = conn  # 保存连接以保持锁
                logger.info(f"✅ MySQL lock acquired ({self.lock_name})")
                return True
            elif locked == 0:
                logger.warning("Timeout acquiring MySQL lock")
                conn.close()
                return False
            else:
                logger.error(f"Error acquiring MySQL lock: {locked}")
                conn.close()
                return False

        except Exception as e:
            logger.error(f"Error acquiring MySQL lock: {e}")
            return False

    async def release(self) -> bool:
        """释放 MySQL 锁
        
        Returns:
            True 表示成功释放锁，False 表示失败
        """
        if not self.acquired or not self._connection:
            return False

        try:
            # 使用参数化查询防止 SQL 注入
            result = self._connection.execute(
                text("SELECT RELEASE_LOCK(:lock_name)"),
                {"lock_name": self.lock_name}
            )
            released = result.scalar()

            if released == 1:
                self.acquired = False
                logger.info(f"🔓 MySQL lock released ({self.lock_name})")
                return True
            else:
                logger.warning("Failed to release MySQL lock")
                return False

        except Exception as e:
            logger.error(f"Error releasing MySQL lock: {e}")
            return False
        finally:
            if self._connection:
                self._connection.close()
                self._connection = None

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
        self._pid = None

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
                # 写入进程ID和时间戳
                lock_data = f"{os.getpid()}:{time.time()}"
                os.write(fd, lock_data.encode())
                os.close(fd)
                self.acquired = True
                self._pid = os.getpid()
                logger.info(f"✅ File lock acquired ({self.lock_file})")
                return True

            except FileExistsError:
                # 检查锁是否过期
                try:
                    with open(self.lock_file, 'r') as f:
                        content = f.read()
                        if ':' in content:
                            pid, timestamp = content.split(':')
                            lock_age = time.time() - float(timestamp)
                            # 如果锁超过 2 倍超时时间，认为过期
                            if lock_age > timeout * 2:
                                try:
                                    # 尝试检查进程是否仍在运行
                                    # 信号 0 不发送信号，只检查进程是否存在
                                    os.kill(int(pid), 0)
                                    logger.warning(
                                        f"进程 {pid} 仍在运行，不删除锁文件 (age: {lock_age}s)"
                                    )
                                except (ProcessLookupError, ValueError, OSError):
                                    # 进程不存在，可以删除锁文件
                                    logger.warning(
                                        f"进程 {pid} 已终止，删除过期锁文件 (age: {lock_age}s)"
                                    )
                                    try:
                                        os.remove(self.lock_file)
                                    except OSError:
                                        pass
                                    continue
                except (ValueError, OSError):
                    pass
                # 锁文件已存在且有效，等待后重试
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
                # 验证是否是我们的锁
                try:
                    with open(self.lock_file, 'r') as f:
                        content = f.read()
                        if ':' in content:
                            pid = int(content.split(':')[0])
                            if pid != self._pid:
                                logger.warning(
                                    f"Lock file PID mismatch: "
                                    f"expected {self._pid}, got {pid}"
                                )
                                return False
                except (ValueError, OSError):
                    pass

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
