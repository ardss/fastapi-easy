import asyncio
import logging
from typing import Any, Dict, List

from sqlalchemy import Column, Engine, inspect

from .risk_engine import AdvancedRiskAssessor
from .types import RiskLevel, SchemaChange

logger = logging.getLogger(__name__)


class SchemaDetector:
    """Detects changes between ORM models and Database Schema"""

    def __init__(self, engine: Engine, metadata):
        self.engine = engine
        self.metadata = metadata
        self.dialect = engine.dialect.name
        self.risk_assessor = AdvancedRiskAssessor(self.dialect)

    async def detect_changes(self, timeout_seconds: int = 60) -> List[SchemaChange]:
        """Main detection logic with timeout control

        Args:
            timeout_seconds: Timeout in seconds for schema detection
        """
        try:
            # Run synchronous inspect in thread pool with timeout
            inspector = await asyncio.wait_for(
                asyncio.to_thread(inspect, self.engine), timeout=timeout_seconds
            )
            changes = []
        except asyncio.TimeoutError:
            logger.error(
                f"Schema detection timed out after {timeout_seconds}s. "
                f"Consider increasing timeout_seconds or checking database."
            )
            raise

        # 1. Check Tables
        for table_name, table in self.metadata.tables.items():
            if not inspector.has_table(table_name):
                changes.append(self._create_table_change(table_name))
                continue

            # 2. Check Columns
            db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}
            orm_columns = {col.name: col for col in table.columns}

            # Add Column
            for col_name, col in orm_columns.items():
                if col_name not in db_columns:
                    changes.append(self._analyze_add_column(table_name, col))

            # Drop Column
            for col_name in db_columns:
                if col_name not in orm_columns:
                    # 先创建临时 SchemaChange 对象用于风险评估
                    temp_change = SchemaChange(
                        type="drop_column",
                        table=table_name,
                        column=col_name,
                        risk_level=RiskLevel.SAFE,  # 临时值
                        description="",
                        column_obj=table.columns.get(col_name),
                    )
                    risk = self.risk_assessor.assess(temp_change)
                    changes.append(
                        SchemaChange(
                            type="drop_column",
                            table=table_name,
                            column=col_name,
                            risk_level=risk,
                            description=f"Drop column '{table_name}.{col_name}'",
                            warning="Data in this column will be lost permanently.",
                            column_obj=table.columns.get(col_name),
                        )
                    )

            # Modify Column (Type/Nullable)
            for col_name, orm_col in orm_columns.items():
                if col_name in db_columns:
                    db_col = db_columns[col_name]
                    type_changes = self._detect_column_changes(table_name, orm_col, db_col)
                    changes.extend(type_changes)

        return changes

    def _create_table_change(self, table_name: str) -> SchemaChange:
        """创建表变更对象

        Args:
            table_name: 表名

        Returns:
            SchemaChange 对象，包含风险等级
        """
        # 先创建临时 SchemaChange 对象用于风险评估
        temp_change = SchemaChange(
            type="create_table",
            table=table_name,
            risk_level=RiskLevel.SAFE,  # 临时值
            description="",
            column_obj=self.metadata.tables[table_name],
        )
        risk = self.risk_assessor.assess(temp_change)
        return SchemaChange(
            type="create_table",
            table=table_name,
            risk_level=risk,
            description=f"Create table '{table_name}'",
            column_obj=self.metadata.tables[table_name],
        )

    def _analyze_add_column(self, table_name: str, column: Column) -> SchemaChange:
        """Analyze risk of adding a column"""
        # 先创建临时 SchemaChange 对象用于风险评估
        temp_change = SchemaChange(
            type="add_column",
            table=table_name,
            column=column.name,
            risk_level=RiskLevel.SAFE,  # 临时值
            description="",
            column_obj=column,
        )
        risk = self.risk_assessor.assess(temp_change)

        description = f"Add column '{table_name}.{column.name}'"
        warning = None

        if risk == RiskLevel.SAFE:
            description = f"Add nullable column '{table_name}.{column.name}'"
        elif risk == RiskLevel.MEDIUM:
            description = f"Add column '{table_name}.{column.name}' with default"
        else:
            description = f"Add NOT NULL column '{table_name}.{column.name}' without default"
            warning = "This will fail if table has existing data."

        return SchemaChange(
            type="add_column",
            table=table_name,
            column=column.name,
            risk_level=risk,
            description=description,
            warning=warning,
            column_obj=column,
        )

    def _detect_column_changes(
        self, table_name: str, orm_col: Column, db_col: Dict[str, Any]
    ) -> List[SchemaChange]:
        """Detect changes in column definition"""
        changes = []

        # 1. Check Type
        orm_type = str(orm_col.type).upper()
        db_type = str(db_col["type"]).upper()

        # Normalize simple types
        if "VARCHAR" in orm_type and "VARCHAR" in db_type:
            pass  # Ignore length diffs for now
        elif orm_type != db_type:
            if orm_type.split("(")[0] != db_type.split("(")[0]:
                # 先创建临时 SchemaChange 对象用于风险评估
                temp_change = SchemaChange(
                    type="change_column",
                    table=table_name,
                    column=orm_col.name,
                    old_type=db_type,
                    new_type=orm_type,
                    risk_level=RiskLevel.SAFE,  # 临时值
                    description="",
                    column_obj=orm_col,
                )
                risk = self.risk_assessor.assess(temp_change)
                changes.append(
                    SchemaChange(
                        type="change_column",
                        table=table_name,
                        column=orm_col.name,
                        old_type=db_type,
                        new_type=orm_type,
                        risk_level=risk,
                        description=f"Change column '{table_name}.{orm_col.name}' type from {db_type} to {orm_type}",
                        column_obj=orm_col,
                    )
                )

        return changes
