import logging
from datetime import datetime
from typing import List, Tuple

from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateTable
from sqlalchemy.sql import quoted_name

from .types import Migration, MigrationPlan, RiskLevel, SchemaChange

logger = logging.getLogger(__name__)

class MigrationGenerator:
    """Generates SQL for migrations"""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.dialect = engine.dialect.name

    def generate_plan(self, changes: List[SchemaChange]) -> MigrationPlan:
        migrations = []
        for change in changes:
            version = self._generate_version()
            
            if self.dialect == "sqlite" and change.type in ["drop_column", "change_column"]:
                # SQLite special handling
                upgrade, downgrade = self._generate_sqlite_copy_swap(change)
            else:
                upgrade = self._generate_upgrade_sql(change)
                downgrade = self._generate_downgrade_sql(change)
            
            migrations.append(Migration(
                version=version,
                description=change.description,
                risk_level=change.risk_level,
                upgrade_sql=upgrade,
                downgrade_sql=downgrade
            ))
            
        return MigrationPlan(migrations=migrations, status="pending")

    def _generate_version(self) -> str:
        """生成迁移版本号
        
        Returns:
            版本号字符串 (格式: YYYYMMDDHHmmss_xxxx)
        """
        return datetime.now().strftime("%Y%m%d%H%M%S") + "_" + self._random_string(4)

    def _random_string(self, length: int) -> str:
        """生成随机字符串
        
        Args:
            length: 字符串长度
            
        Returns:
            随机字符串
        """
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase, k=length))

    def _generate_upgrade_sql(self, change: SchemaChange) -> str:
        if change.type == "create_table":
            # Use SQLAlchemy's compiler
            return str(CreateTable(change.column_obj).compile(self.engine)).strip() + ";"
            
        elif change.type == "add_column":
            col_def = self._get_column_definition(change.column_obj)
            return f"ALTER TABLE {change.table} ADD COLUMN {col_def};"
            
        elif change.type == "drop_column":
            return f"ALTER TABLE {change.table} DROP COLUMN {change.column};"
            
        return "-- Unknown change type"

    def _generate_downgrade_sql(self, change: SchemaChange) -> str:
        if change.type == "create_table":
            return f"DROP TABLE {change.table};"
        elif change.type == "add_column":
            if self.dialect == "sqlite":
                 return "-- SQLite cannot drop column easily (requires copy-swap)"
            return f"ALTER TABLE {change.table} DROP COLUMN {change.column};"
        elif change.type == "drop_column":
            return "-- Cannot auto-rollback column drop without backup"
        return ""

    def _get_column_definition(self, column) -> str:
        # Compile column definition using SQLAlchemy
        from sqlalchemy.schema import CreateColumn
        return str(CreateColumn(column).compile(self.engine))

    def _generate_sqlite_copy_swap(self, change: SchemaChange) -> Tuple[str, str]:
        """
        Generates Copy-Swap-Drop SQL for SQLite.
        
        Strategy:
        1. Create new table with desired schema (temp name)
        2. Copy data from old table to new table
        3. Drop old table
        4. Rename new table to old table name
        
        Args:
            change: The detected schema change.
            
        Returns:
            Tuple of (upgrade_sql, downgrade_sql)
        """
        table_name = change.table
        temp_table_name = f"{table_name}_new_{self._random_string(4)}"
        
        # 1. Get the full CREATE TABLE statement for the NEW schema
        # FIX: Explicitly check for None to avoid SQLAlchemy boolean evaluation error
        if change.column_obj is None or not hasattr(change.column_obj, "table"):
             return (
                 f"-- Error: Cannot generate copy-swap for {table_name}. Missing table metadata.",
                 "-- Error: Cannot generate downgrade"
             )
             
        new_table = change.column_obj.table
        
        # We need to temporarily rename the table in metadata to generate the CREATE statement
        # for the temp table, then switch it back.
        original_name = new_table.name
        new_table.name = temp_table_name
        create_temp_sql = str(CreateTable(new_table).compile(self.engine)).strip() + ";"
        new_table.name = original_name # Restore name
        
        # 2. Copy data
        # For add_column: copy all columns from old table that exist in new table
        # For change_column/drop_column: copy all columns except the changed/dropped one
        if change.type == "add_column":
            # When adding a column, copy all existing columns
            common_columns = [c.name for c in new_table.columns if c.name != change.column]
        else:
            # When changing/dropping, copy all columns that exist in both tables
            common_columns = [c.name for c in new_table.columns]
        
        cols_str = ", ".join(common_columns)

        # 使用 quoted_name 转义表名以防止 SQL 注入
        table_ident = quoted_name(table_name, quote=True)
        temp_table_ident = quoted_name(temp_table_name, quote=True)

        copy_sql = (
            f"INSERT INTO {temp_table_ident} ({cols_str}) "
            f"SELECT {cols_str} FROM {table_ident};"
        )

        # 3. Drop old & Rename new
        swap_sql = (
            f"DROP TABLE {table_ident}; "
            f"ALTER TABLE {temp_table_ident} RENAME TO {table_ident};"
        )
        
        upgrade_sql = f"BEGIN TRANSACTION;\n{create_temp_sql}\n{copy_sql}\n{swap_sql}\nCOMMIT;"
        
        # Downgrade is hard for copy-swap (data loss potential), marking as manual
        downgrade_sql = f"-- Automatic downgrade for Copy-Swap is not supported. Please restore from backup."
        
        return upgrade_sql, downgrade_sql
