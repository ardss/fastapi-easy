"""类型比较器 - 支持复杂类型的 Schema 变更检测"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import ARRAY, JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.types import TypeEngine

logger = logging.getLogger(__name__)


class TypeComparator(ABC):
    """类型比较器基类"""
    
    @abstractmethod
    def compare(self, old_type: TypeEngine, new_type: TypeEngine) -> bool:
        """
        比较两个类型是否相同
        
        Args:
            old_type: 旧类型
            new_type: 新类型
        
        Returns:
            True 表示相同，False 表示不同
        """
        pass
    
    @abstractmethod
    def get_migration_sql(self, column_name: str, old_type: TypeEngine, new_type: TypeEngine) -> Optional[str]:
        """
        获取类型变更的 SQL
        
        Args:
            column_name: 列名
            old_type: 旧类型
            new_type: 新类型
        
        Returns:
            迁移 SQL，如果无法迁移则返回 None
        """
        pass


class DefaultTypeComparator(TypeComparator):
    """默认类型比较器"""
    
    def compare(self, old_type: TypeEngine, new_type: TypeEngine) -> bool:
        """比较两个类型"""
        old_str = str(old_type)
        new_str = str(new_type)
        return old_str == new_str
    
    def get_migration_sql(self, column_name: str, old_type: TypeEngine, new_type: TypeEngine) -> Optional[str]:
        """获取类型变更的 SQL"""
        return None


class JSONTypeComparator(TypeComparator):
    """JSON 类型比较器"""
    
    def compare(self, old_type: TypeEngine, new_type: TypeEngine) -> bool:
        """比较两个 JSON 类型"""
        return isinstance(old_type, JSON) and isinstance(new_type, JSON)
    
    def get_migration_sql(self, column_name: str, old_type: TypeEngine, new_type: TypeEngine) -> Optional[str]:
        """JSON 类型通常不需要迁移"""
        return None


class ArrayTypeComparator(TypeComparator):
    """数组类型比较器"""
    
    def compare(self, old_type: TypeEngine, new_type: TypeEngine) -> bool:
        """比较两个数组类型"""
        if not (isinstance(old_type, ARRAY) and isinstance(new_type, ARRAY)):
            return False
        
        # 比较元素类型
        old_item_type = str(old_type.item_type)
        new_item_type = str(new_type.item_type)
        return old_item_type == new_item_type
    
    def get_migration_sql(self, column_name: str, old_type: TypeEngine, new_type: TypeEngine) -> Optional[str]:
        """数组类型通常不需要迁移"""
        return None


class StringTypeComparator(TypeComparator):
    """字符串类型比较器"""
    
    def compare(self, old_type: TypeEngine, new_type: TypeEngine) -> bool:
        """比较两个字符串类型"""
        if not (isinstance(old_type, String) and isinstance(new_type, String)):
            return False
        
        # 比较长度
        old_length = getattr(old_type, 'length', None)
        new_length = getattr(new_type, 'length', None)
        
        # 如果长度都为 None（无限制），则相同
        if old_length is None and new_length is None:
            return True
        
        # 如果长度不同，则不同
        return old_length == new_length
    
    def get_migration_sql(self, column_name: str, old_type: TypeEngine, new_type: TypeEngine) -> Optional[str]:
        """获取字符串类型变更的 SQL"""
        old_length = getattr(old_type, 'length', None)
        new_length = getattr(new_type, 'length', None)
        
        if old_length == new_length:
            return None
        
        # 扩大长度是安全的，缩小长度可能丢失数据
        if new_length is None or (old_length and new_length and new_length > old_length):
            return f"ALTER TABLE {{table}} MODIFY {column_name} VARCHAR({new_length})"
        
        return None


class NumericTypeComparator(TypeComparator):
    """数值类型比较器"""
    
    def compare(self, old_type: TypeEngine, new_type: TypeEngine) -> bool:
        """比较两个数值类型"""
        old_is_numeric = isinstance(old_type, (Integer, Float))
        new_is_numeric = isinstance(new_type, (Integer, Float))
        
        if not (old_is_numeric and new_is_numeric):
            return False
        
        # Integer 和 Float 之间可以兼容
        return True
    
    def get_migration_sql(self, column_name: str, old_type: TypeEngine, new_type: TypeEngine) -> Optional[str]:
        """获取数值类型变更的 SQL"""
        # Integer 到 Float 是安全的
        if isinstance(old_type, Integer) and isinstance(new_type, Float):
            return f"ALTER TABLE {{table}} MODIFY {column_name} FLOAT"
        
        return None


class TypeComparatorRegistry:
    """类型比较器注册表"""
    
    def __init__(self):
        self.comparators: List[TypeComparator] = [
            JSONTypeComparator(),
            ArrayTypeComparator(),
            StringTypeComparator(),
            NumericTypeComparator(),
            DefaultTypeComparator(),
        ]
    
    def register(self, comparator: TypeComparator, priority: int = 0) -> None:
        """
        注册类型比较器
        
        Args:
            comparator: 比较器实例
            priority: 优先级（高优先级先执行）
        """
        self.comparators.insert(0, comparator)
        logger.info(f"注册类型比较器: {comparator.__class__.__name__}")
    
    def compare(self, old_type: TypeEngine, new_type: TypeEngine) -> bool:
        """比较两个类型
        
        Args:
            old_type: 旧类型
            new_type: 新类型
            
        Returns:
            True 表示类型相同，False 表示不同
        """
        for comparator in self.comparators:
            if comparator.compare(old_type, new_type):
                return True
        return False
    
    def get_migration_sql(self, column_name: str, old_type: TypeEngine, new_type: TypeEngine) -> Optional[str]:
        """获取类型变更的 SQL
        
        Args:
            column_name: 列名
            old_type: 旧类型
            new_type: 新类型
            
        Returns:
            迁移 SQL，如果无法迁移则返回 None
        """
        for comparator in self.comparators:
            sql = comparator.get_migration_sql(column_name, old_type, new_type)
            if sql:
                return sql
        return None


# 全局注册表
_global_registry = TypeComparatorRegistry()


def register_type_comparator(comparator: TypeComparator) -> None:
    """注册全局类型比较器"""
    _global_registry.register(comparator)


def compare_types(old_type: TypeEngine, new_type: TypeEngine) -> bool:
    """比较两个类型"""
    return _global_registry.compare(old_type, new_type)


def get_type_migration_sql(column_name: str, old_type: TypeEngine, new_type: TypeEngine) -> Optional[str]:
    """获取类型变更的 SQL"""
    return _global_registry.get_migration_sql(column_name, old_type, new_type)
