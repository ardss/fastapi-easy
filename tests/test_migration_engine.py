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

@pytest.mark.asyncio
async def test_migration_engine_detects_changes():
    # 1. Setup in-memory DB
    engine = create_engine("sqlite:///:memory:")
    
    # 2. Create initial schema (empty)
    # We don't call Base.metadata.create_all(engine) so the table is missing
    
    # 3. Initialize Migration Engine
    migration_engine = MigrationEngine(engine, Base.metadata)
    
    # 4. Run detection
    plan = await migration_engine.auto_migrate()
    
    # 5. Verify results
    assert len(plan.migrations) == 1
    assert plan.migrations[0].risk_level == RiskLevel.SAFE
    assert "Create table 'users'" in plan.migrations[0].description
    assert "CREATE TABLE users" in plan.migrations[0].upgrade_sql

@pytest.mark.asyncio
async def test_migration_engine_detects_new_column():
    # 1. Setup in-memory DB
    engine = create_engine("sqlite:///:memory:")
    
    # 2. Create initial schema manually (simulating old state)
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR)"))
        conn.commit()
        
    # 3. Initialize Migration Engine with User model (which has 'age')
    migration_engine = MigrationEngine(engine, Base.metadata)
    
    # 4. Run detection
    plan = await migration_engine.auto_migrate()
    
    # 5. Verify results
    assert len(plan.migrations) == 1
    migration = plan.migrations[0]
    assert migration.risk_level == RiskLevel.SAFE  # Nullable integer is safe
    assert "Add nullable column 'users.age'" in migration.description
    assert "ALTER TABLE users ADD COLUMN age INTEGER" in migration.upgrade_sql

@pytest.mark.asyncio
async def test_migration_engine_detects_type_change_sqlite():
    # 1. Setup in-memory DB
    engine = create_engine("sqlite:///:memory:")
    
    # 2. Create initial schema manually with different type
    # age is VARCHAR in DB, but Integer in Model
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, age VARCHAR)"))
        conn.commit()
        
    # 3. Initialize Migration Engine
    migration_engine = MigrationEngine(engine, Base.metadata)
    
    # 4. Run detection
    plan = await migration_engine.auto_migrate()
    
    # 5. Verify results
    assert len(plan.migrations) == 1
    migration = plan.migrations[0]
    
    # Type change is High Risk
    assert migration.risk_level == RiskLevel.HIGH
    assert "Change column 'users.age' type" in migration.description
    
    # Verify Copy-Swap SQL
    sql = migration.upgrade_sql
    assert "BEGIN TRANSACTION" in sql
    assert "CREATE TABLE users_new_" in sql
    assert "INSERT INTO users_new_" in sql
    assert "DROP TABLE users" in sql
    assert "ALTER TABLE users_new_" in sql
    assert "COMMIT" in sql
