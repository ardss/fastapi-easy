"""
高级风险评估引擎

支持:
- 智能类型兼容性检查
- 数据库特定规则
- 自定义风险规则
- 风险缓存和监控
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .types import RiskLevel, SchemaChange

logger = logging.getLogger(__name__)


class TypeCompatibility(Enum):
    """类型兼容性等级"""
    SAFE = "safe"  # 完全兼容，无数据丢失
    COMPATIBLE = "compatible"  # 兼容但可能改变数据
    INCOMPATIBLE = "incompatible"  # 不兼容，可能丢失数据


@dataclass
class RiskRule:
    """风险规则"""
    name: str
    description: str
    condition: callable  # 返回 True 表示规则匹配
    risk_level: RiskLevel
    mitigation: Optional[str] = None


class TypeCompatibilityChecker:
    """类型兼容性检查器"""

    # 类型兼容性矩阵
    COMPATIBILITY_MATRIX = {
        # 整数类型
        ("INTEGER", "BIGINT"): TypeCompatibility.SAFE,
        ("INTEGER", "SMALLINT"): TypeCompatibility.COMPATIBLE,
        ("BIGINT", "INTEGER"): TypeCompatibility.COMPATIBLE,
        ("SMALLINT", "INTEGER"): TypeCompatibility.SAFE,

        # 字符串类型
        ("VARCHAR", "VARCHAR"): TypeCompatibility.SAFE,
        ("VARCHAR", "TEXT"): TypeCompatibility.SAFE,
        ("TEXT", "VARCHAR"): TypeCompatibility.COMPATIBLE,
        ("CHAR", "VARCHAR"): TypeCompatibility.SAFE,

        # 数字类型
        ("DECIMAL", "NUMERIC"): TypeCompatibility.SAFE,
        ("FLOAT", "DOUBLE"): TypeCompatibility.SAFE,
        ("DOUBLE", "FLOAT"): TypeCompatibility.COMPATIBLE,

        # 日期类型
        ("DATE", "TIMESTAMP"): TypeCompatibility.COMPATIBLE,
        ("TIMESTAMP", "DATE"): TypeCompatibility.COMPATIBLE,

        # 布尔类型
        ("BOOLEAN", "INTEGER"): TypeCompatibility.COMPATIBLE,
        ("INTEGER", "BOOLEAN"): TypeCompatibility.COMPATIBLE,
    }

    @classmethod
    def check_compatibility(
        cls, old_type: str, new_type: str
    ) -> TypeCompatibility:
        """检查类型兼容性"""
        old_base = cls._normalize_type(old_type)
        new_base = cls._normalize_type(new_type)

        if old_base == new_base:
            return TypeCompatibility.SAFE

        # 查询兼容性矩阵
        key = (old_base, new_base)
        if key in cls.COMPATIBILITY_MATRIX:
            return cls.COMPATIBILITY_MATRIX[key]

        # 默认为不兼容
        return TypeCompatibility.INCOMPATIBLE

    @staticmethod
    def _normalize_type(type_str: str) -> str:
        """规范化类型字符串"""
        # 移除长度和参数
        base_type = type_str.split("(")[0].strip().upper()
        return base_type


class AdvancedRiskAssessor:
    """高级风险评估器"""

    def __init__(self, dialect: str):
        self.dialect = dialect
        self.type_checker = TypeCompatibilityChecker()
        self.custom_rules: List[RiskRule] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """初始化默认风险规则"""
        # SQLite 特定规则
        if self.dialect == "sqlite":
            self.add_rule(
                RiskRule(
                    name="sqlite_column_modification",
                    description="SQLite 不支持直接修改列，需要 Copy-Swap",
                    condition=lambda change: change.type in [
                        "change_column",
                        "drop_column",
                    ],
                    risk_level=RiskLevel.HIGH,
                    mitigation="使用 Copy-Swap-Drop 策略，确保备份",
                )
            )

        # 通用规则
        self.add_rule(
            RiskRule(
                name="drop_column_data_loss",
                description="删除列会导致数据丢失",
                condition=lambda change: change.type == "drop_column",
                risk_level=RiskLevel.HIGH,
                mitigation="确认数据已备份，考虑使用软删除",
            )
        )

        self.add_rule(
            RiskRule(
                name="add_not_null_column",
                description="添加 NOT NULL 列到现有数据表",
                condition=lambda change: (
                    change.type == "add_column"
                    and hasattr(change, "column_obj")
                    and change.column_obj
                    and not change.column_obj.nullable
                ),
                risk_level=RiskLevel.HIGH,
                mitigation="添加默认值或先添加可空列，再更新数据",
            )
        )

    def add_rule(self, rule: RiskRule):
        """添加自定义风险规则"""
        self.custom_rules.append(rule)
        logger.debug(f"Added risk rule: {rule.name}")

    def assess(self, change: SchemaChange) -> RiskLevel:
        """评估 Schema 变更的风险等级"""
        # 1. 检查自定义规则
        for rule in self.custom_rules:
            try:
                if rule.condition(change):
                    logger.info(
                        f"Risk rule matched: {rule.name} - {rule.description}"
                    )
                    if rule.mitigation:
                        logger.warning(f"Mitigation: {rule.mitigation}")
                    return rule.risk_level
            except Exception as e:
                logger.warning(f"Error evaluating rule {rule.name}: {e}")

        # 2. 使用默认评估逻辑
        return self._assess_by_type(change)

    def _assess_by_type(self, change: SchemaChange) -> RiskLevel:
        """根据变更类型评估风险"""
        if change.type == "create_table":
            return RiskLevel.SAFE

        elif change.type == "add_column":
            return self._assess_add_column(change)

        elif change.type == "drop_column":
            return RiskLevel.HIGH

        elif change.type == "change_column":
            return self._assess_change_column(change)

        else:
            return RiskLevel.HIGH

    def _assess_add_column(self, change: SchemaChange) -> RiskLevel:
        """评估添加列的风险"""
        if not hasattr(change, "column_obj") or not change.column_obj:
            return RiskLevel.MEDIUM

        column = change.column_obj

        # 可空列是安全的
        if column.nullable:
            return RiskLevel.SAFE

        # 有默认值的列是中等风险
        if column.default is not None or column.server_default is not None:
            return RiskLevel.MEDIUM

        # 没有默认值的 NOT NULL 列是高风险
        return RiskLevel.HIGH

    def _assess_change_column(self, change: SchemaChange) -> RiskLevel:
        """评估修改列的风险"""
        if not hasattr(change, "old_type") or not hasattr(change, "new_type"):
            return RiskLevel.HIGH

        old_type = change.old_type
        new_type = change.new_type

        # SQLite 总是高风险
        if self.dialect == "sqlite":
            return RiskLevel.HIGH

        # 检查类型兼容性
        compatibility = self.type_checker.check_compatibility(old_type, new_type)

        if compatibility == TypeCompatibility.SAFE:
            return RiskLevel.SAFE
        elif compatibility == TypeCompatibility.COMPATIBLE:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    def get_risk_summary(self, changes: List[SchemaChange]) -> Dict:
        """获取变更风险摘要"""
        summary = {
            "total": len(changes),
            "safe": 0,
            "medium": 0,
            "high": 0,
            "changes": [],
        }

        for change in changes:
            risk = self.assess(change)
            summary[risk.value] += 1
            summary["changes"].append(
                {
                    "description": change.description,
                    "risk_level": risk.value,
                    "type": change.type,
                }
            )

        return summary
