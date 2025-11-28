import os
import tempfile

import pytest
import sqlalchemy
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.orm import declarative_base

from fastapi_easy.migrations.engine import MigrationEngine
from fastapi_easy.migrations.types import RiskLevel

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)

@pytest.fixture
def temp_db():
    """Create a temporary database for each test"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        yield f"sqlite:///{path}"
    finally:
        # Wait a bit for connections to close
        import time
        time.sleep(0.1)
        # Try to remove the file, ignore errors on Windows
        try:
            if os.path.exists(path):
                os.unlink(path)
        except (OSError, PermissionError):
            pass

@pytest.mark.asyncio
async def test_migration_engine_detects_changes(temp_db):
    """Test: Detect missing table"""
    engine = create_engine(temp_db, connect_args={"check_same_thread": False})
    migration_engine = MigrationEngine(engine, Base.metadata, mode="safe")
    
    plan = await migration_engine.auto_migrate()
    
    assert len(plan.migrations) == 1
    assert plan.migrations[0].risk_level == RiskLevel.SAFE
    assert "Create table 'users'" in plan.migrations[0].description
    assert "CREATE TABLE users" in plan.migrations[0].upgrade_sql

@pytest.mark.asyncio
async def test_migration_engine_detects_new_column(temp_db):
    """Test: Detect missing column"""
    engine = create_engine(temp_db, connect_args={"check_same_thread": False})
    
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR)"))
        conn.commit()
        
    migration_engine = MigrationEngine(engine, Base.metadata, mode="safe")
    plan = await migration_engine.auto_migrate()
    
    assert len(plan.migrations) == 1
    migration = plan.migrations[0]
    assert migration.risk_level == RiskLevel.SAFE
    assert "Add nullable column 'users.age'" in migration.description
    assert "ALTER TABLE users ADD COLUMN age INTEGER" in migration.upgrade_sql

@pytest.mark.asyncio
async def test_migration_engine_detects_type_change_sqlite(temp_db):
    """Test: Detect type change and generate Copy-Swap SQL"""
    engine = create_engine(temp_db, connect_args={"check_same_thread": False})
    
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, age VARCHAR)"))
        conn.commit()
        
    migration_engine = MigrationEngine(engine, Base.metadata, mode="safe")
    plan = await migration_engine.auto_migrate()
    
    assert len(plan.migrations) == 1
    migration = plan.migrations[0]
    
    assert migration.risk_level == RiskLevel.HIGH
    assert "Change column 'users.age' type" in migration.description
    
    sql = migration.upgrade_sql
    assert "BEGIN TRANSACTION" in sql
    assert "CREATE TABLE users_new_" in sql
    assert "INSERT INTO users_new_" in sql
    assert "DROP TABLE users" in sql
    assert "ALTER TABLE users_new_" in sql
    assert "COMMIT" in sql

@pytest.mark.asyncio
async def test_migration_engine_executes_safe_migrations(temp_db):
    """Test: Execute safe migrations in safe mode"""
    engine = create_engine(temp_db, connect_args={"check_same_thread": False})
    
    # Start with empty database
    migration_engine = MigrationEngine(engine, Base.metadata, mode="safe")
    plan = await migration_engine.auto_migrate()
    
    # Should have created the table
    assert plan.status == "completed"
    
    # Verify table exists
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
        assert result.fetchone() is not None
    
    # Verify migration history was recorded
    history = migration_engine.get_history()
    assert len(history) == 1
    assert "Create table 'users'" in history[0]["description"]

@pytest.mark.asyncio
async def test_migration_engine_skips_risky_migrations_in_safe_mode(temp_db):
    """Test: Risky migrations are not executed in safe mode"""
    engine = create_engine(temp_db, connect_args={"check_same_thread": False})
    
    # Create table with wrong type
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, age VARCHAR)"))
        conn.commit()
    
    migration_engine = MigrationEngine(engine, Base.metadata, mode="safe")
    plan = await migration_engine.auto_migrate()
    
    # Should detect the change but not execute it
    assert len(plan.migrations) == 1
    assert plan.migrations[0].risk_level == RiskLevel.HIGH
    assert plan.status == "partial"  # Not all migrations executed
    
    # Verify age is still VARCHAR
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(users)"))
        columns = {row[1]: row[2] for row in result}
        assert "VARCHAR" in columns["age"].upper()

@pytest.mark.asyncio
async def test_migration_engine_executes_risky_migrations_in_aggressive_mode(temp_db):
    """Test: Risky migrations are executed in aggressive mode"""
    engine = create_engine(temp_db, connect_args={"check_same_thread": False})
    
    # Create table with wrong type
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, age VARCHAR)"))
        conn.commit()
    
    migration_engine = MigrationEngine(engine, Base.metadata, mode="aggressive")
    plan = await migration_engine.auto_migrate()
    
    # Should execute the risky migration
    assert plan.status == "completed"
    
    # Verify age is now INTEGER
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(users)"))
        columns = {row[1]: row[2] for row in result}
        assert "INTEGER" in columns["age"].upper()
