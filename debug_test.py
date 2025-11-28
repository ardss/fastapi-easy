import asyncio
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

async def run_test():
    try:
        print("Starting test...")
        engine = create_engine("sqlite:///:memory:")
        
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, age VARCHAR)"))
            conn.commit()
            
        migration_engine = MigrationEngine(engine, Base.metadata)
        
        print("Detecting changes...")
        plan = await migration_engine.auto_migrate()
        
        print(f"Found {len(plan.migrations)} migrations")
        for m in plan.migrations:
            print(f"Migration: {m.description}")
            print(f"Upgrade SQL: {m.upgrade_sql}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
