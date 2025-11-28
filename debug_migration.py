import asyncio
import logging
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base
from fastapi_easy.migrations.engine import MigrationEngine

# Enable logging
logging.basicConfig(level=logging.DEBUG)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)

async def main():
    engine = create_engine("sqlite:///:memory:")
    
    migration_engine = MigrationEngine(engine, Base.metadata, mode="safe")
    plan = await migration_engine.auto_migrate()
    
    print(f"\n{'='*60}")
    print(f"Plan status: {plan.status}")
    print(f"Migrations: {len(plan.migrations)}")
    
    for i, mig in enumerate(plan.migrations):
        print(f"\nMigration {i+1}:")
        print(f"  Description: {mig.description}")
        print(f"  Risk: {mig.risk_level}")
        print(f"  SQL:\n{mig.upgrade_sql}")
    
    print(f"\n{'='*60}")
    # Check if table exists
    with engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        print(f"Tables in database: {tables}")

if __name__ == "__main__":
    asyncio.run(main())
