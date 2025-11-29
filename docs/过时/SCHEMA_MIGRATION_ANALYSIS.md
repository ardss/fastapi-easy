# 数据库Schema变更问题深入分析

**问题**: 在开发过程中，如果修改了 ORM 模型的字段(添加、删除、修改列)，fastapi-easy 如何处理？会不会导致潜在问题？

**分析日期**: 2025-11-28

**重要性**: 🔴 高(生产环境关键问题)

---

## 🔍 问题场景分析

### 场景 1: 添加新字段

**初始状态** (v1):
```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
```

**开发过程中** (v2):
```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
    stock = Column(Integer)  # 新增字段
```

**潜在问题**:
- 数据库表中没有 `stock` 列 → ORM 查询失败
- 应用启动时会抛出异常
- 需要数据库迁移

### 场景 2: 删除字段

**初始状态** (v1):
```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
    description = Column(String)  # 要删除的字段
```

**开发过程中** (v2):
```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
```

**潜在问题**:
- 数据库表中仍然存在 `description` 列
- 数据丢失风险
- 需要数据库迁移和数据备份

### 场景 3: 修改字段类型

**初始状态** (v1):
```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    price = Column(Float)  # Float 类型
```

**开发过程中** (v2):
```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    price = Column(Numeric(10, 2))  # 改为 Numeric
```

**潜在问题**:
- 类型不匹配导致查询失败
- 数据转换问题
- 需要数据库迁移

### 场景 4: 修改字段约束

**初始状态** (v1):
```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)  # 允许 NULL
```

**开发过程中** (v2):
```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # 不允许 NULL
```

**潜在问题**:
- 现有数据中可能有 NULL 值
- 数据库约束冲突
- 需要数据库迁移

---

## 🛠️ 解决方案

### 方案 1: 使用 Alembic (推荐)

**Alembic** 是SQLAlchemy 官方的数据库迁移工具，提供：
- 自动生成迁移脚本
- 支持向前和向后迁移
- 版本控制
- Schema 版本管理

**使用步骤**:
```python
# 初始化 Alembic
alembic init alembic

# 生成迁移脚本
alembic revision --autogenerate -m "Add stock column"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

**与 fastapi-easy 集成**:
```python
# 在应用启动时自动应用迁移
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

def apply_migrations():
    """自动应用数据库迁移"""
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        operations = Operations(context)

        # 执行迁移
        for revision in script.walk_revisions():
            if not context.get_current_revision() or \
               revision.revision > context.get_current_revision():
                operations.invoke(revision.upgrade)
```

### 方案 2: Schema 验证

**在应用启动时验证 Schema**:

```python
def validate_schema():
    """验证数据库 Schema 与 ORM 模型是否匹配"""
    inspector = inspect(engine)

    for table in Base.metadata.tables.values():
        db_columns = {col['name']: col for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name not in db_columns:
                raise ValueError(
                    f"Column {column.name} not found in table {table.name}. "
                    f"Please run migrations: alembic upgrade head"
                )

            db_column = db_columns[column.name]

            # 验证列类型
            if str(column.type) != str(db_column['type']):
                raise ValueError(
                    f"Column {column.name} type mismatch in table {table.name}. "
                    f"Expected {column.type}, got {db_column['type']}"
                )

            # 验证 nullable
            if column.nullable != db_column['nullable']:
                raise ValueError(
                    f"Column {column.name} nullable mismatch in table {table.name}. "
                    f"Expected nullable={column.nullable}, got {db_column['nullable']}"
                )

# 在应用启动时验证
@app.on_event("startup")
async def startup():
    validate_schema()
```

### 方案 3: CRUDRouter 中的警告

**在 CRUDRouter 中添加 Alembic 检查**:

```python
import warnings

class CRUDRouter(APIRouter):
    def __init__(self, schema, adapter, ...):
        # 检查是否设置了 Alembic
        if not os.path.exists("alembic.ini"):
            warnings.warn(
                "Alembic not found. For production use, please set up Alembic "
                "for database migrations: alembic init alembic",
                UserWarning
            )

        # 验证 Schema
        try:
            validate_schema()
        except ValueError as e:
            raise RuntimeError(
                f"Database schema validation failed: {e}. "
                f"Please run: alembic upgrade head"
            )
```

### 方案 4: 文档和指南

**新增文档**: `docs/usage/18-database-migrations.md`

```markdown
# 数据库迁移指南

## 概述

当你修改 ORM 模型的字段时，需要同步更新数据库 Schema。

## 使用 Alembic

### 1. 安装 Alembic

\`\`\`bash
pip install alembic
\`\`\`

### 2. 初始化 Alembic

\`\`\`bash
alembic init alembic
\`\`\`

### 3. 配置 Alembic

编辑 `alembic/env.py`:

\`\`\`python
from sqlalchemy import engine_from_config
from sqlalchemy.pool import StaticPool
from alembic import context
from app.models import Base  # 导入你的 Base

target_metadata = Base.metadata

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=StaticPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
\`\`\`

### 4. 生成迁移脚本

修改 ORM 模型后:

\`\`\`bash
alembic revision --autogenerate -m "Add stock column"
\`\`\`

### 5. 执行迁移

\`\`\`bash
alembic upgrade head
\`\`\`

### 6. 回滚迁移

\`\`\`bash
alembic downgrade -1
\`\`\`
```

---

## 📋 关键风险点

| 风险点 | 影响 | 解决方案 |
|------|------|--------|
| 字段添加 | ORM 查询失败 | 使用 Alembic 迁移 |
| 字段删除 | 数据丢失 | 使用 Alembic 迁移 + 备份 |
| 字段类型修改 | 类型不匹配 | 使用 Alembic 迁移 |
| 字段约束修改 | 数据库约束冲突 | 使用 Alembic 迁移 |

---

## 🎯 建议

### 立即行动 (优先级: 🔴 高)

1. **添加 Schema 验证**: 在应用启动时验证 Schema
2. **添加 Alembic 检查**: 在 CRUDRouter 中检查 Alembic 配置
3. **添加文档**: 创建数据库迁移指南

### 中期行动 (优先级: 🟡 中)

4. **自动迁移**: 在应用启动时自动应用迁移
5. **迁移监控**: 添加迁移历史和监控
6. **数据备份**: 在迁移前自动备份

### 长期行动 (优先级: 🟢 低)

7. **迁移测试**: 添加迁移测试套件
8. **迁移文档**: 详细的迁移最佳实践
9. **迁移工具**: 开发自动化迁移工具

---

## 📚 参考资源

- [Alembic 官方文档](https://alembic.sqlalchemy.org/)
- [SQLAlchemy ORM 文档](https://docs.sqlalchemy.org/en/14/orm/)
- [数据库迁移最佳实践](https://en.wikipedia.org/wiki/Schema_migration)
