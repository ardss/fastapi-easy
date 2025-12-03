"""磁盘空间检查模块"""

import logging
import os
import shutil
from pathlib import Path

from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class DiskSpaceChecker:
    """磁盘空间检查器"""

    def __init__(self, engine: Engine, min_free_space_mb: int = 100):
        self.engine = engine
        self.min_free_space_mb = min_free_space_mb

    def get_database_size(self) -> int:
        """获取数据库大小（字节）

        Returns:
            数据库文件大小（字节），如果获取失败返回 0
        """
        try:
            # 获取数据库文件路径
            url = str(self.engine.url)
            if "sqlite:///" in url:
                db_path = url.replace("sqlite:///", "")

                # 验证路径安全性
                resolved_path = Path(db_path).resolve()

                # 确保路径指向有效的文件
                if not resolved_path.is_file():
                    logger.warning(f"Invalid database path: {db_path}")
                    return 0

                return resolved_path.stat().st_size
            return 0
        except (IOError, OSError) as e:
            logger.error(f"❌ 获取数据库大小失败: {e}")
            return 0

    def estimate_copy_swap_space(self) -> int:
        """估算 Copy-Swap-Drop 所需的空间（字节）

        Returns:
            估算所需的空间大小（字节），如果估算失败返回 0
        """
        try:
            # 估算为数据库大小的 2 倍（复制 + 临时表）
            db_size = self.get_database_size()
            return db_size * 2
        except Exception as e:
            logger.error(f"❌ 估算空间失败: {e}")
            return 0

    def get_available_space(self) -> int:
        """获取可用磁盘空间（字节）

        Returns:
            可用磁盘空间大小（字节），如果获取失败返回 0
        """
        try:
            # 获取数据库所在目录
            url = str(self.engine.url)
            if "sqlite:///" in url:
                db_path = url.replace("sqlite:///", "")
                db_dir = os.path.dirname(db_path) or "."
                stat = shutil.disk_usage(db_dir)
                return stat.free
            return 0
        except (IOError, OSError) as e:
            logger.error(f"❌ 获取可用空间失败: {e}")
            return 0

    def check_space_available(self, required_space: int = None) -> bool:
        """检查是否有足够的磁盘空间"""
        try:
            if required_space is None:
                required_space = self.estimate_copy_swap_space()

            available = self.get_available_space()
            min_required = self.min_free_space_mb * 1024 * 1024

            if available < required_space + min_required:
                logger.error(
                    f"❌ 磁盘空间不足\n"
                    f"  需要: {required_space / 1024 / 1024:.2f} MB\n"
                    f"  可用: {available / 1024 / 1024:.2f} MB\n"
                    f"  最小保留: {self.min_free_space_mb} MB"
                )
                return False

            logger.info(
                f"✅ 磁盘空间充足\n"
                f"  需要: {required_space / 1024 / 1024:.2f} MB\n"
                f"  可用: {available / 1024 / 1024:.2f} MB"
            )
            return True
        except Exception as e:
            logger.error(f"❌ 空间检查失败: {e}")
            return False

    def get_space_info(self) -> dict:
        """获取空间信息"""
        return {
            "database_size_mb": self.get_database_size() / 1024 / 1024,
            "estimated_required_mb": self.estimate_copy_swap_space() / 1024 / 1024,
            "available_mb": self.get_available_space() / 1024 / 1024,
            "min_free_mb": self.min_free_space_mb,
        }
