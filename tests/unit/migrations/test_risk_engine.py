"""
高级风险评估引擎测试
"""

import pytest
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base

from fastapi_easy.migrations.risk_engine import (
    AdvancedRiskAssessor,
    TypeCompatibility,
    TypeCompatibilityChecker,
)
from fastapi_easy.migrations.types import RiskLevel, SchemaChange

Base = declarative_base()


class TestTypeCompatibilityChecker:
    """类型兼容性检查器测试"""

    def test_same_type_is_safe(self):
        """相同类型应该是安全的"""
        result = TypeCompatibilityChecker.check_compatibility("VARCHAR", "VARCHAR")
        assert result == TypeCompatibility.SAFE

    def test_integer_to_bigint_is_safe(self):
        """INTEGER 到 BIGINT 是安全的"""
        result = TypeCompatibilityChecker.check_compatibility("INTEGER", "BIGINT")
        assert result == TypeCompatibility.SAFE

    def test_bigint_to_integer_is_compatible(self):
        """BIGINT 到 INTEGER 是兼容的"""
        result = TypeCompatibilityChecker.check_compatibility("BIGINT", "INTEGER")
        assert result == TypeCompatibility.COMPATIBLE

    def test_varchar_to_text_is_safe(self):
        """VARCHAR 到 TEXT 是安全的"""
        result = TypeCompatibilityChecker.check_compatibility("VARCHAR", "TEXT")
        assert result == TypeCompatibility.SAFE

    def test_incompatible_types(self):
        """不兼容的类型"""
        result = TypeCompatibilityChecker.check_compatibility("INTEGER", "TEXT")
        assert result == TypeCompatibility.INCOMPATIBLE

    def test_normalize_type_removes_length(self):
        """规范化类型应该移除长度"""
        normalized = TypeCompatibilityChecker._normalize_type("VARCHAR(255)")
        assert normalized == "VARCHAR"


class TestAdvancedRiskAssessor:
    """高级风险评估器测试"""

    def test_create_table_is_safe(self):
        """创建表是安全的"""
        assessor = AdvancedRiskAssessor("postgresql")
        change = SchemaChange(
            type="create_table",
            table="users",
            column=None,
            description="Create table 'users'",
            risk_level=RiskLevel.SAFE,
        )
        risk = assessor.assess(change)
        assert risk == RiskLevel.SAFE

    def test_drop_column_is_high_risk(self):
        """删除列是高风险的"""
        assessor = AdvancedRiskAssessor("postgresql")
        change = SchemaChange(
            type="drop_column",
            table="users",
            column="age",
            description="Drop column 'users.age'",
            risk_level=RiskLevel.HIGH,
        )
        risk = assessor.assess(change)
        assert risk == RiskLevel.HIGH

    def test_add_nullable_column_is_safe(self):
        """添加可空列是安全的"""
        assessor = AdvancedRiskAssessor("postgresql")

        class MockColumn:
            nullable = True
            default = None
            server_default = None

        change = SchemaChange(
            type="add_column",
            table="users",
            column="age",
            description="Add nullable column 'users.age'",
            column_obj=MockColumn(),
            risk_level=RiskLevel.SAFE,
        )
        risk = assessor.assess(change)
        assert risk == RiskLevel.SAFE

    def test_add_not_null_column_without_default_is_high_risk(self):
        """添加 NOT NULL 列（无默认值）是高风险的"""
        assessor = AdvancedRiskAssessor("postgresql")

        class MockColumn:
            nullable = False
            default = None
            server_default = None

        change = SchemaChange(
            type="add_column",
            table="users",
            column="age",
            description="Add NOT NULL column 'users.age'",
            column_obj=MockColumn(),
            risk_level=RiskLevel.HIGH,
        )
        risk = assessor.assess(change)
        assert risk == RiskLevel.HIGH

    def test_sqlite_column_change_is_high_risk(self):
        """SQLite 列修改是高风险的"""
        assessor = AdvancedRiskAssessor("sqlite")
        change = SchemaChange(
            type="change_column",
            table="users",
            column="age",
            old_type="VARCHAR",
            new_type="INTEGER",
            description="Change column 'users.age' type",
            risk_level=RiskLevel.HIGH,
        )
        risk = assessor.assess(change)
        assert risk == RiskLevel.HIGH

    def test_postgresql_safe_type_change(self):
        """PostgreSQL 安全的类型修改"""
        assessor = AdvancedRiskAssessor("postgresql")
        change = SchemaChange(
            type="change_column",
            table="users",
            column="age",
            old_type="INTEGER",
            new_type="BIGINT",
            description="Change column 'users.age' type",
            risk_level=RiskLevel.SAFE,
        )
        risk = assessor.assess(change)
        assert risk == RiskLevel.SAFE

    def test_postgresql_incompatible_type_change(self):
        """PostgreSQL 不兼容的类型修改"""
        assessor = AdvancedRiskAssessor("postgresql")
        change = SchemaChange(
            type="change_column",
            table="users",
            column="age",
            old_type="INTEGER",
            new_type="TEXT",
            description="Change column 'users.age' type",
            risk_level=RiskLevel.HIGH,
        )
        risk = assessor.assess(change)
        assert risk == RiskLevel.HIGH

    def test_get_risk_summary(self):
        """获取风险摘要"""
        assessor = AdvancedRiskAssessor("postgresql")

        changes = [
            SchemaChange(
                type="create_table",
                table="users",
                column=None,
                description="Create table 'users'",
                risk_level=RiskLevel.SAFE,
            ),
            SchemaChange(
                type="drop_column",
                table="users",
                column="age",
                description="Drop column 'users.age'",
                risk_level=RiskLevel.HIGH,
            ),
        ]

        summary = assessor.get_risk_summary(changes)

        assert summary["total"] == 2
        assert summary["safe"] == 1
        assert summary["high"] == 1
        assert len(summary["changes"]) == 2

    def test_custom_rule_matching(self):
        """自定义规则匹配"""
        from fastapi_easy.migrations.risk_engine import RiskRule

        assessor = AdvancedRiskAssessor("postgresql")

        # 添加自定义规则
        custom_rule = RiskRule(
            name="test_rule",
            description="Test rule",
            condition=lambda change: change.type == "create_table",
            risk_level=RiskLevel.MEDIUM,
        )
        assessor.add_rule(custom_rule)

        change = SchemaChange(
            type="create_table",
            table="users",
            column=None,
            description="Create table 'users'",
            risk_level=RiskLevel.SAFE,
        )

        # 自定义规则应该覆盖默认规则
        risk = assessor.assess(change)
        assert risk == RiskLevel.MEDIUM
