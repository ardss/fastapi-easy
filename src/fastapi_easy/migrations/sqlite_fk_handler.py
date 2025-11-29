"""SQLite 外键处理模块"""
import logging
import re

from sqlalchemy import Engine, text

logger = logging.getLogger(__name__)


class SQLiteForeignKeyHandler:
    """SQLite 外键处理器"""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def disable_foreign_keys(self) -> bool:
        """禁用外键约束"""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("PRAGMA foreign_keys = OFF"))
            logger.info("✅ 禁用 SQLite 外键约束")
            return True
        except Exception as e:
            logger.error(f"❌ 禁用外键失败: {e}")
            return False
    
    def enable_foreign_keys(self) -> bool:
        """启用外键约束"""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("PRAGMA foreign_keys = ON"))
            logger.info("✅ 启用 SQLite 外键约束")
            return True
        except Exception as e:
            logger.error(f"❌ 启用外键失败: {e}")
            return False
    
    def get_foreign_keys(self, table_name: str) -> list:
        """获取表的外键约束"""
        try:
            # 验证表名安全性 - 只允许字母、数字、下划线
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
                raise ValueError(
                    f"Invalid table name: {table_name}. "
                    "Only alphanumeric and underscore allowed."
                )

            with self.engine.connect() as conn:
                # PRAGMA 不支持参数化，但表名已验证
                result = conn.execute(
                    text(f"PRAGMA foreign_key_list({table_name})")
                )
                return result.fetchall()
        except Exception as e:
            logger.error(f"❌ 获取外键失败: {e}")
            return []
    
    def check_foreign_key_integrity(self) -> bool:
        """检查外键完整性"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("PRAGMA foreign_key_check"))
                violations = result.fetchall()
                if violations:
                    logger.warning(f"⚠️ 发现 {len(violations)} 个外键违规")
                    return False
                logger.info("✅ 外键完整性检查通过")
                return True
        except Exception as e:
            logger.error(f"❌ 外键检查失败: {e}")
            return False
