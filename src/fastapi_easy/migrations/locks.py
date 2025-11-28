import abc
import asyncio
import logging
import os
import time
from typing import Optional, Any
from sqlalchemy.engine import Engine, Connection
from sqlalchemy import text

logger = logging.getLogger(__name__)

class LockProvider(abc.ABC):
    """Abstract base class for distributed locks"""
    
    def __init__(self, engine: Engine, lock_id: str = "fastapi_easy_migration"):
        self.engine = engine
        self.lock_id = lock_id
        self._connection: Optional[Connection] = None

    async def __aenter__(self):
        """Acquire lock on enter"""
        if await self.acquire():
            return self
        raise RuntimeError("Failed to acquire migration lock")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release lock on exit"""
        await self.release()

    @abc.abstractmethod
    async def acquire(self) -> bool:
        """Try to acquire the lock. Returns True if successful."""
        pass

    @abc.abstractmethod
    async def release(self):
        """Release the lock."""
        pass

class PostgresLock(LockProvider):
    """PostgreSQL Advisory Lock"""
    
    def _get_key(self) -> int:
        import hashlib
        return int(hashlib.sha256(self.lock_id.encode()).hexdigest(), 16) % (2**63 - 1)

    async def acquire(self) -> bool:
        key = self._get_key()
        try:
            # Keep connection open!
            self._connection = self.engine.connect()
            # Start transaction explicitly if needed, but advisory locks are session level usually.
            # However, SQLAlchemy connection might auto-commit or rollback.
            # Session level advisory lock survives transaction commit/rollback, 
            # but depends on the connection staying open.
            
            result = self._connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
            success = result.scalar()
            
            if not success:
                self._connection.close()
                self._connection = None
                
            return success
        except Exception as e:
            logger.error(f"Failed to acquire PG lock: {e}")
            if self._connection:
                self._connection.close()
                self._connection = None
            return False

    async def release(self):
        if not self._connection:
            return
            
        key = self._get_key()
        try:
            self._connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
        except Exception as e:
            logger.error(f"Failed to release PG lock: {e}")
        finally:
            self._connection.close()
            self._connection = None

class MySQLLock(LockProvider):
    """MySQL Named Lock"""
    
    async def acquire(self) -> bool:
        try:
            self._connection = self.engine.connect()
            result = self._connection.execute(
                text("SELECT GET_LOCK(:key, 0)"), 
                {"key": self.lock_id}
            )
            success = result.scalar() == 1
            
            if not success:
                self._connection.close()
                self._connection = None
                
            return success
        except Exception as e:
            logger.error(f"Failed to acquire MySQL lock: {e}")
            if self._connection:
                self._connection.close()
                self._connection = None
            return False

    async def release(self):
        if not self._connection:
            return

        try:
            self._connection.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": self.lock_id})
        except Exception as e:
            logger.error(f"Failed to release MySQL lock: {e}")
        finally:
            self._connection.close()
            self._connection = None

class FileLock(LockProvider):
    """Simple File Lock for SQLite/Local Dev"""
    
    def __init__(self, engine: Engine, lock_id: str = "fastapi_easy_migration"):
        super().__init__(engine, lock_id)
        self.lock_file = f"{lock_id}.lock"

    async def acquire(self) -> bool:
        if os.path.exists(self.lock_file):
            # Check if stale (older than 10 minutes)
            if time.time() - os.path.getmtime(self.lock_file) > 600:
                logger.warning("Removing stale lock file")
                try:
                    os.remove(self.lock_file)
                except OSError:
                    return False
            else:
                return False
        
        try:
            with open(self.lock_file, 'x') as f:
                f.write(str(os.getpid()))
            return True
        except FileExistsError:
            return False
        except OSError:
            return False

    async def release(self):
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except OSError as e:
            logger.error(f"Failed to release file lock: {e}")

def get_lock_provider(engine: Engine) -> LockProvider:
    dialect = engine.dialect.name
    if dialect == "postgresql":
        return PostgresLock(engine)
    elif dialect == "mysql":
        return MySQLLock(engine)
    else:
        return FileLock(engine)
