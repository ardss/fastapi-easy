import asyncio
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base
from fastapi_easy.migrations.detector import SchemaDetector
from fastapi_easy.migrations.generator import MigrationGenerator

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)

async def main():
    engine = create_engine("sqlite:///:memory:")
    
    detector = SchemaDetector(engine, Base.metadata)
    changes = await detector.detect_changes()
    
    print(f"Detected {len(changes)} changes:")
    for change in changes:
        print(f"  - {change.description}")
        print(f"    Type: {change.type}")
        print(f"    column_obj type: {type(change.column_obj)}")
    
    generator = MigrationGenerator(engine)
    plan = generator.generate_plan(changes)
    
    print(f"\nGenerated {len(plan.migrations)} migrations:")
    for mig in plan.migrations:
        print(f"\n{'-'*60}")
        print(f"Description: {mig.description}")
        print(f"SQL:\n{mig.upgrade_sql}")
        print(f"{'-'*60}")

if __name__ == "__main__":
    asyncio.run(main())
