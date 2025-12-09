"""
Schema 哈希缓存系统

支持:
- 本地文件缓存
- Redis 缓存 (可选)
- 缓存失效检测
- 缓存监控
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SchemaCacheProvider(ABC):
    """Schema 缓存提供者基类"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取缓存"""

    @abstractmethod
    async def set(self, key: str, value: Dict[str, Any]) -> bool:
        """设置缓存"""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""

    @abstractmethod
    async def clear(self) -> bool:
        """清空所有缓存"""


class FileSchemaCacheProvider(SchemaCacheProvider):
    """基于文件的 Schema 缓存提供者"""

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = ".fastapi_easy_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"Schema cache directory: {self.cache_dir}")

    def _get_cache_file(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用哈希避免文件名过长
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed_key}.json"

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """从文件获取缓存"""
        try:
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                with open(cache_file) as f:
                    data = json.load(f)
                logger.debug(f"Cache hit: {key}")
                return data
            else:
                logger.debug(f"Cache miss: {key}")
                return None
        except OSError as e:
            logger.error(f"File read failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Cache read failed: {e}")
            return None

    async def set(self, key: str, value: Dict[str, Any]) -> bool:
        """将缓存写入文件"""
        try:
            cache_file = self._get_cache_file(key)
            with open(cache_file, "w") as f:
                json.dump(value, f, indent=2)
            logger.debug(f"Cache set: {key}")
            return True
        except OSError as e:
            logger.error(f"文件写入失败: {e}")
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"数据序列化失败: {e}")
            return False
        except Exception as e:
            logger.error(f"缓存写入失败: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存文件"""
        try:
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"Cache deleted: {key}")
            return True
        except OSError as e:
            logger.error(f"文件删除失败: {e}")
            return False
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
            return False

    async def clear(self) -> bool:
        """清空所有缓存 - 使用流式处理防止内存占用过高"""
        try:
            count = 0
            batch_size = 100  # 每 100 个文件让出控制权一次

            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    count += 1

                    # 定期让出控制权，防止阻塞事件循环
                    if count % batch_size == 0:
                        await asyncio.sleep(0)
                        logger.debug(f"Cleared {count} cache files, " f"yielding control...")
                except OSError as e:
                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")
                    continue

            logger.info(f"Cleared {count} cache files")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


class RedisSchemaCacheProvider(SchemaCacheProvider):
    """基于 Redis 的 Schema 缓存提供者"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self._initialize()

    def _initialize(self):
        """初始化 Redis 连接"""
        try:
            import redis

            self.redis_client = redis.from_url(self.redis_url)
            self.redis_client.ping()
            logger.info(f"Redis cache connected: {self.redis_url}")
        except ImportError:
            logger.warning("Redis not installed. Install with: pip install redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """从 Redis 获取缓存"""
        if not self.redis_client:
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                logger.debug(f"Cache hit: {key}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss: {key}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error reading from Redis: {e}")
            return None
        except (ConnectionError, OSError) as e:
            logger.error(f"Connection error reading from Redis: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading from Redis: {e}")
            return None

    async def set(self, key: str, value: Dict[str, Any], ttl: int = 3600) -> bool:
        """将缓存写入 Redis"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.setex(key, ttl, json.dumps(value))
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization error writing to Redis: {e}")
            return False
        except (ConnectionError, OSError) as e:
            logger.error(f"Connection error writing to Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Error writing to Redis: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除 Redis 缓存"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return True
        except (ConnectionError, OSError) as e:
            logger.error(f"Connection error deleting from Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting from Redis: {e}")
            return False

    async def clear(self) -> bool:
        """清空所有缓存"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.flushdb()
            logger.info("All Redis caches cleared")
            return True
        except (ConnectionError, OSError) as e:
            logger.error(f"Connection error clearing Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Error clearing Redis: {e}")
            return False


class SchemaHashCalculator:
    """Schema 哈希计算器"""

    @staticmethod
    def calculate_hash(schema_dict: Dict[str, Any]) -> str:
        """计算 Schema 的哈希值"""
        # 转换为 JSON 字符串并排序键以确保一致性
        schema_json = json.dumps(schema_dict, sort_keys=True)
        return hashlib.sha256(schema_json.encode()).hexdigest()

    @staticmethod
    def create_cache_key(database_url: str, schema_name: str) -> str:
        """创建缓存键"""
        key = f"{database_url}:{schema_name}"
        return hashlib.sha256(key.encode()).hexdigest()


class SchemaCacheManager:
    """Schema 缓存管理器"""

    def __init__(
        self,
        provider: Optional[SchemaCacheProvider] = None,
        use_redis: bool = False,
    ):
        if provider:
            self.provider = provider
        elif use_redis:
            self.provider = RedisSchemaCacheProvider()
        else:
            self.provider = FileSchemaCacheProvider()

        self.stats_lock = threading.Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "deletes": 0,
        }

    async def get_cached_schema(
        self, database_url: str, schema_name: str
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的 Schema"""
        cache_key = SchemaHashCalculator.create_cache_key(database_url, schema_name)
        cached = await self.provider.get(cache_key)

        with self.stats_lock:
            if cached:
                self.stats["hits"] += 1
                logger.debug(f"Schema cache hit: {schema_name}")
            else:
                self.stats["misses"] += 1
                logger.debug(f"Schema cache miss: {schema_name}")

        return cached

    async def cache_schema(
        self,
        database_url: str,
        schema_name: str,
        schema_dict: Dict[str, Any],
    ) -> bool:
        """缓存 Schema"""
        cache_key = SchemaHashCalculator.create_cache_key(database_url, schema_name)
        cache_data = {
            "schema": schema_dict,
            "hash": SchemaHashCalculator.calculate_hash(schema_dict),
            "timestamp": datetime.now().isoformat(),
        }

        success = await self.provider.set(cache_key, cache_data)
        if success:
            with self.stats_lock:
                self.stats["writes"] += 1
            logger.debug(f"Schema cached: {schema_name}")
        return success

    async def invalidate_schema(self, database_url: str, schema_name: str) -> bool:
        """使 Schema 缓存失效"""
        cache_key = SchemaHashCalculator.create_cache_key(database_url, schema_name)
        success = await self.provider.delete(cache_key)
        if success:
            with self.stats_lock:
                self.stats["deletes"] += 1
            logger.debug(f"Schema cache invalidated: {schema_name}")
        return success

    async def clear_all_caches(self) -> bool:
        """清空所有缓存"""
        return await self.provider.clear()

    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0

        return {
            **self.stats,
            "total_requests": total,
            "hit_rate": f"{hit_rate:.2f}%",
        }
