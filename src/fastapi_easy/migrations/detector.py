import logging
from typing import List, Dict, Any
from sqlalchemy import Engine, inspect, Table, Column
from sqlalchemy.sql import sqltypes

from .types import SchemaChange, RiskLevel

logger = logging.getLogger(__name__)

class SchemaDetector:
    """Detects changes between ORM models and Database Schema"""
    
    def __init__(self, engine: Engine, metadata):
        self.engine = engine
        self.metadata = metadata
        self.dialect = engine.dialect.name
        
    async def detect_changes(self) -> List[SchemaChange]:
        """Main detection logic"""
        # Note: inspect is synchronous, so we might run this in a thread pool if needed,
        # but for startup it's usually fine.
        inspector = inspect(self.engine)
        changes = []
        
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
                    changes.append(SchemaChange(
                        type="drop_column",
                        table=table_name,
                        column=col_name,
                        risk_level=RiskLevel.HIGH,
                        description=f"Drop column '{table_name}.{col_name}'",
                        warning="Data in this column will be lost permanently.",
                        column_obj=table.columns.get(col_name) # Might be None if dropped from ORM
                    ))
            
            # Modify Column (Type/Nullable)
            for col_name, orm_col in orm_columns.items():
                if col_name in db_columns:
                    db_col = db_columns[col_name]
                    type_changes = self._detect_column_changes(table_name, orm_col, db_col)
                    changes.extend(type_changes)
            
        return changes

    def _create_table_change(self, table_name: str) -> SchemaChange:
        return SchemaChange(
            type="create_table",
            table=table_name,
            risk_level=RiskLevel.SAFE,
            description=f"Create table '{table_name}'",
            column_obj=self.metadata.tables[table_name]
        )

    def _analyze_add_column(self, table_name: str, column: Column) -> SchemaChange:
        """Analyze risk of adding a column"""
        if column.nullable:
            return SchemaChange(
                type="add_column",
                table=table_name,
                column=column.name,
                risk_level=RiskLevel.SAFE,
                description=f"Add nullable column '{table_name}.{column.name}'",
                column_obj=column
            )
        
        if column.default is not None or column.server_default is not None:
            return SchemaChange(
                type="add_column",
                table=table_name,
                column=column.name,
                risk_level=RiskLevel.MEDIUM,
                description=f"Add column '{table_name}.{column.name}' with default",
                column_obj=column
            )
            
        return SchemaChange(
            type="add_column",
            table=table_name,
            column=column.name,
            risk_level=RiskLevel.HIGH,
            description=f"Add NOT NULL column '{table_name}.{column.name}' without default",
            warning="This will fail if table has existing data.",
            column_obj=column
        )

    def _detect_column_changes(self, table_name: str, orm_col: Column, db_col: Dict[str, Any]) -> List[SchemaChange]:
        """Detect changes in column definition"""
        changes = []
        
        # 1. Check Type
        # This is tricky because DB types and SQLAlchemy types don't always match strings.
        # We do a basic check here.
        # For SQLite, INTEGER is often INTEGER, VARCHAR is VARCHAR(length)
        
        # Simplified type check
        orm_type = str(orm_col.type).upper()
        db_type = str(db_col["type"]).upper()
        
        # Normalize simple types
        if "VARCHAR" in orm_type and "VARCHAR" in db_type:
            pass # Ignore length diffs for now
        elif orm_type != db_type:
             # Very basic check, can be improved
             # e.g. INTEGER vs INTEGER()
             if orm_type.split("(")[0] != db_type.split("(")[0]:
                changes.append(SchemaChange(
                    type="change_column",
                    table=table_name,
                    column=orm_col.name,
                    old_type=db_type,
                    new_type=orm_type,
                    risk_level=RiskLevel.HIGH,
                    description=f"Change column '{table_name}.{orm_col.name}' type from {db_type} to {orm_type}",
                    column_obj=orm_col
                ))
        
        return changes
