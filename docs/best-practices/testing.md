# 测试策略

编写高质量测试，确保代码可靠性。

---

## 🎯 测试目标

- ✅ 单元测试覆盖率 > 80%
- ✅ 集成测试覆盖关键流程
- ✅ 测试异常情况和边界条件
- ✅ 保持测试独立性和可重复性

---

## 1. 测试环境配置

### 1.1 安装测试依赖

```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

### 1.2 配置 pytest

**pytest.ini**:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    -v
```

---

## 2. 单元测试

### 2.1 测试 Pydantic Schema

```python
from app.schemas import ItemCreate, ItemResponse

def test_item_create_schema():
    """测试创建 schema 验证"""
    data = {"name": "Apple", "price": 1.5}
    item = ItemCreate(**data)
    assert item.name == "Apple"
    assert item.price == 1.5

def test_item_create_validation():
    """测试 schema 验证失败"""
    import pytest
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        ItemCreate(name="Apple", price="invalid")
```

### 2.2 测试业务逻辑

```python
from app.services import ItemService

async def test_calculate_discount():
    """测试折扣计算"""
    service = ItemService()
    price = 100
    discount = 0.2
    
    result = await service.calculate_discount(price, discount)
    assert result == 80
```

---

## 3. 集成测试

### 3.1 配置测试客户端

**conftest.py**:
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

# 测试数据库
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture
async def test_db():
    """创建测试数据库"""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def test_session(test_db):
    """创建测试会话"""
    async_session = sessionmaker(
        test_db, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest.fixture
async def client(test_session):
    """创建测试客户端"""
    async def override_get_db():
        yield test_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
```

### 3.2 测试 CRUD 端点

```python
import pytest

@pytest.mark.asyncio
async def test_create_item(client):
    """测试创建项目"""
    response = await client.post(
        "/items",
        json={"name": "Apple", "price": 1.5}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Apple"
    assert data["price"] == 1.5
    assert "id" in data

@pytest.mark.asyncio
async def test_get_items(client):
    """测试获取项目列表"""
    # 先创建一些数据
    await client.post("/items", json={"name": "Apple", "price": 1.5})
    await client.post("/items", json={"name": "Banana", "price": 2.0})
    
    # 测试获取列表
    response = await client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

@pytest.mark.asyncio
async def test_get_item(client):
    """测试获取单个项目"""
    # 先创建
    create_response = await client.post(
        "/items",
        json={"name": "Apple", "price": 1.5}
    )
    item_id = create_response.json()["id"]
    
    # 测试获取
    response = await client.get(f"/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["name"] == "Apple"

@pytest.mark.asyncio
async def test_update_item(client):
    """测试更新项目"""
    # 先创建
    create_response = await client.post(
        "/items",
        json={"name": "Apple", "price": 1.5}
    )
    item_id = create_response.json()["id"]
    
    # 测试更新
    response = await client.put(
        f"/items/{item_id}",
        json={"name": "Orange", "price": 2.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Orange"
    assert data["price"] == 2.0

@pytest.mark.asyncio
async def test_delete_item(client):
    """测试删除项目"""
    # 先创建
    create_response = await client.post(
        "/items",
        json={"name": "Apple", "price": 1.5}
    )
    item_id = create_response.json()["id"]
    
    # 测试删除
    response = await client.delete(f"/items/{item_id}")
    assert response.status_code == 204
    
    # 验证已删除
    get_response = await client.get(f"/items/{item_id}")
    assert get_response.status_code == 404
```

---

## 4. 测试异常情况

### 4.1 测试验证错误

```python
@pytest.mark.asyncio
async def test_create_item_invalid_data(client):
    """测试创建项目 - 无效数据"""
    response = await client.post(
        "/items",
        json={"name": "Apple"}  # 缺少 price
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_item_invalid_price(client):
    """测试创建项目 - 无效价格"""
    response = await client.post(
        "/items",
        json={"name": "Apple", "price": -1}
    )
    assert response.status_code == 422
```

### 4.2 测试 404 错误

```python
@pytest.mark.asyncio
async def test_get_nonexistent_item(client):
    """测试获取不存在的项目"""
    response = await client.get("/items/99999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
```

### 4.3 测试权限错误

```python
@pytest.mark.asyncio
async def test_unauthorized_access(client):
    """测试未授权访问"""
    response = await client.delete("/items/1")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_forbidden_access(client):
    """测试禁止访问"""
    # 使用普通用户 token
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await client.delete("/admin/items/1", headers=headers)
    assert response.status_code == 403
```

---

## 5. 测试 Fixtures

### 5.1 数据 Fixtures

```python
@pytest.fixture
async def sample_items(test_session):
    """创建示例数据"""
    items = [
        Item(name="Apple", price=1.5),
        Item(name="Banana", price=2.0),
        Item(name="Orange", price=1.8),
    ]
    test_session.add_all(items)
    await test_session.commit()
    return items

@pytest.mark.asyncio
async def test_with_sample_data(client, sample_items):
    """使用示例数据测试"""
    response = await client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
```

### 5.2 认证 Fixtures

```python
@pytest.fixture
async def admin_token():
    """创建管理员 token"""
    from app.security import create_access_token
    return create_access_token(
        subject="admin@example.com",
        roles=["admin"]
    )

@pytest.mark.asyncio
async def test_admin_access(client, admin_token):
    """测试管理员访问"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/admin/dashboard", headers=headers)
    assert response.status_code == 200
```

---

## 6. 测试覆盖率

### 6.1 运行测试并生成覆盖率报告

```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### 6.2 查看覆盖率报告

```bash
# 在浏览器中打开
open htmlcov/index.html
```

### 6.3 覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| 核心逻辑 | > 90% |
| API 端点 | > 85% |
| 工具函数 | > 80% |
| 总体 | > 80% |

---

## 7. 持续集成

### 7.1 GitHub Actions 配置

**.github/workflows/test.yml**:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run tests
      run: pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

---

## 8. 测试最佳实践

### 8.1 测试命名

```python
# ✅ 好：清晰的测试名称
def test_create_item_with_valid_data():
    pass

def test_create_item_with_missing_price_raises_validation_error():
    pass

# ❌ 不好：模糊的测试名称
def test_item():
    pass

def test_error():
    pass
```

### 8.2 测试独立性

```python
# ✅ 好：每个测试独立
@pytest.mark.asyncio
async def test_create_item(client):
    response = await client.post("/items", json={"name": "Apple", "price": 1.5})
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_get_items(client):
    # 创建自己的测试数据
    await client.post("/items", json={"name": "Apple", "price": 1.5})
    response = await client.get("/items")
    assert response.status_code == 200

# ❌ 不好：测试之间有依赖
item_id = None

@pytest.mark.asyncio
async def test_create_item(client):
    global item_id
    response = await client.post("/items", json={"name": "Apple", "price": 1.5})
    item_id = response.json()["id"]

@pytest.mark.asyncio
async def test_get_item(client):
    # 依赖上一个测试
    response = await client.get(f"/items/{item_id}")
```

### 8.3 使用参数化测试

```python
import pytest

@pytest.mark.parametrize("name,price,expected_status", [
    ("Apple", 1.5, 201),
    ("Banana", 2.0, 201),
    ("", 1.5, 422),  # 空名称
    ("Apple", -1, 422),  # 负价格
    ("Apple", 0, 422),  # 零价格
])
@pytest.mark.asyncio
async def test_create_item_validation(client, name, price, expected_status):
    """参数化测试创建验证"""
    response = await client.post(
        "/items",
        json={"name": name, "price": price}
    )
    assert response.status_code == expected_status
```

---

## 9. 测试检查清单

- [ ] 单元测试覆盖核心逻辑
- [ ] 集成测试覆盖所有 API 端点
- [ ] 测试异常情况和边界条件
- [ ] 测试覆盖率 > 80%
- [ ] 使用 fixtures 管理测试数据
- [ ] 测试独立且可重复
- [ ] 配置 CI/CD 自动运行测试
- [ ] 定期审查和更新测试

---

## 10. 相关资源

- [pytest 文档](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [httpx](https://www.python-httpx.org/)

---

**下一步**: [故障排查 →](troubleshooting.md)
