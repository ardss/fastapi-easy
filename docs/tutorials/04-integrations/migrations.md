# 数据库迁移指南

FastAPI-Easy 集成了智能迁移引擎，可以自动检测和应用数据库 Schema 变更，无需手动编写迁移脚本。

## 快速开始

### 最简单的方式 (3 行代码)

```python
from fastapi_easy import FastAPIEasy
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

# 创建应用，自动处理迁移
app = FastAPIEasy(
    database_url="sqlite:///db.sqlite",
    models=[User]
)
```

就这样！应用启动时会自动：
- ✅ 检测 Schema 变更
- ✅ 生成迁移脚本
- ✅ 应用迁移
- ✅ 记录迁移历史

## 迁移模式

### 1. Safe 模式 (默认，推荐用于生产)

```python
app = FastAPIEasy(
    database_url="sqlite:///db.sqlite",
    models=[User],
    migration_mode="safe"  # 默认值
)
```

**特点**:
- ✅ 仅执行安全迁移
- ✅ 避免数据丢失
- ✅ 适合生产环境

**安全迁移包括**:
- 添加新表
- 添加新列（有默认值）
- 添加索引
- 添加约束

**不执行的迁移**:
- ❌ 删除列（可能丢失数据）
- ❌ 修改列类型（可能丢失数据）
- ❌ 删除表

### 2. Auto 模式 (中等风险)

```python
app = FastAPIEasy(
    database_url="sqlite:///db.sqlite",
    models=[User],
    migration_mode="auto"
)
```

**特点**:
- ⚠️ 执行中等风险迁移
- ⚠️ 可能需要数据转换
- ⚠️ 适合开发环境

**额外执行的迁移**:
- 修改列类型（如果兼容）
- 修改列约束
- 重命名列

### 3. Aggressive 模式 (高风险)

```python
app = FastAPIEasy(
    database_url="sqlite:///db.sqlite",
    models=[User],
    migration_mode="aggressive"
)
```

**特点**:
- 🔴 执行所有迁移
- 🔴 可能导致数据丢失
- 🔴 仅用于开发或测试

**执行的迁移**:
- 删除列
- 删除表
- 任何其他变更

## 常见场景

### 场景 1: 添加新列

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    email = Column(String(100))  # 新列
```

**结果**: Safe 模式会自动添加 `email` 列

### 场景 2: 修改列类型

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))  # 从 50 改为 100
```

**结果**: 
- Safe 模式: ❌ 不执行（可能丢失数据）
- Auto 模式: ✅ 执行（如果兼容）
- Aggressive 模式: ✅ 执行

### 场景 3: 删除列

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    # name 列被删除
```

**结果**:
- Safe 模式: ❌ 不执行
- Auto 模式: ❌ 不执行
- Aggressive 模式: ✅ 执行

### 场景 4: 添加新表

```python
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

app = FastAPIEasy(
    database_url="sqlite:///db.sqlite",
    models=[User, Product]  # 添加新模型
)
```

**结果**: 所有模式都会自动创建 `products` 表

## 禁用自动迁移

如果你想手动控制迁移：

```python
app = FastAPIEasy(
    database_url="sqlite:///db.sqlite",
    models=[User],
    auto_migrate=False  # 禁用自动迁移
)

# 手动运行迁移
@app.on_event("startup")
async def startup():
    await app.run_migration(mode="safe")
```

## 查看迁移历史

```python
# 获取迁移历史
history = app.get_migration_history(limit=10)

for record in history:
    print(f"版本: {record['version']}")
    print(f"描述: {record['description']}")
    print(f"风险等级: {record['risk_level']}")
    print(f"应用时间: {record['applied_at']}")
    print()
```

## CLI 命令

FastAPI-Easy 提供了 CLI 工具来管理迁移：

### 查看迁移计划

```bash
fastapi-easy migrate plan --database-url sqlite:///db.sqlite
```

### 应用迁移

```bash
fastapi-easy migrate apply --database-url sqlite:///db.sqlite --mode safe
```

### 查看迁移历史

```bash
fastapi-easy migrate history --database-url sqlite:///db.sqlite --limit 10
```

### 查看迁移状态

```bash
fastapi-easy migrate status --database-url sqlite:///db.sqlite
```

## 支持的数据库

| 数据库 | 支持 | 备注 |
|--------|------|------|
| SQLite | ✅ | 完全支持，使用 Copy-Swap-Drop 策略 |
| PostgreSQL | ✅ | 完全支持 |
| MySQL | ✅ | 完全支持 |
| Oracle | ⚠️ | 基础支持 |
| SQL Server | ⚠️ | 基础支持 |

## 故障排除

### 问题 1: 迁移失败

**症状**: 应用启动时迁移失败

**解决方案**:
1. 检查数据库连接: `fastapi-easy migrate status --database-url <url>`
2. 查看详细错误: 设置 `LOG_LEVEL=DEBUG`
3. 运行 dry-run: `fastapi-easy migrate plan --database-url <url> --dry-run`

### 问题 2: 数据丢失

**症状**: 修改列后数据丢失

**解决方案**:
1. 使用 Safe 模式（默认）
2. 如果需要修改列，使用 Auto 或 Aggressive 模式
3. 始终在生产环境前在测试环境验证

### 问题 3: 锁定错误

**症状**: "Cannot acquire lock" 错误

**解决方案**:
1. 检查是否有其他进程在运行迁移
2. 检查锁文件: `.fastapi_easy_migration.lock`
3. 如果锁文件过期，手动删除: `rm .fastapi_easy_migration.lock`

## 最佳实践

### 1. 开发环境

```python
app = FastAPIEasy(
    database_url="sqlite:///dev.db",
    models=[User, Product],
    migration_mode="auto"  # 灵活处理变更
)
```

### 2. 测试环境

```python
app = FastAPIEasy(
    database_url="postgresql://test_user:pass@localhost/test_db",
    models=[User, Product],
    migration_mode="safe"  # 谨慎处理
)
```

### 3. 生产环境

```python
app = FastAPIEasy(
    database_url=os.getenv("DATABASE_URL"),
    models=[User, Product],
    migration_mode="safe",  # 最安全的模式
    auto_migrate=True  # 自动应用安全迁移
)
```

### 4. 版本控制

始终在版本控制中跟踪模型定义：

```bash
git add src/models.py
git commit -m "feat: 添加 email 字段到 User 模型"
```

### 5. 备份

在生产环境运行迁移前，始终备份数据库：

```bash
# PostgreSQL
pg_dump -U user -d database > backup.sql

# MySQL
mysqldump -u user -p database > backup.sql

# SQLite
cp db.sqlite db.sqlite.backup
```

## 高级用法

### 自定义迁移处理

```python
from fastapi_easy import FastAPIEasy

app = FastAPIEasy(
    database_url="sqlite:///db.sqlite",
    models=[User]
)

@app.on_event("startup")
async def custom_startup():
    # 自定义迁移逻辑
    if app.migration_engine:
        history = app.get_migration_history()
        print(f"已应用 {len(history)} 个迁移")
```

### 监听迁移事件

```python
from fastapi_easy.migrations.hooks import migration_hook

@migration_hook("before_migrate")
async def before_migrate(context):
    print("迁移开始...")

@migration_hook("after_migrate")
async def after_migrate(context):
    print("迁移完成!")
```

## 相关文档

- [错误处理](../../tutorials/02-core-features/error-handling.md)
- [最佳实践](../../best-practices/index.md)
- [完整文档](https://fastapi-easy.readthedocs.io)

## 获取帮助

- 📖 [完整文档](https://fastapi-easy.readthedocs.io)
- 🐛 [报告问题](https://github.com/fastapi-easy/fastapi-easy/issues)
- 💬 [讨论区](https://github.com/fastapi-easy/fastapi-easy/discussions)
