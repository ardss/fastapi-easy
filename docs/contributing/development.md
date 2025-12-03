# 测试指南

本指南介绍如何测试使用 fastapi-easy 构建的应用。

---

## 单元测试

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_create_item():
    adapter = AsyncMock()
    adapter.create = AsyncMock(return_value={"id": 1, "name": "Item"})
    
    result = await adapter.create({"name": "Item"})
    
    assert result["id"] == 1
```

---

## 集成测试

```python
@pytest.mark.asyncio
async def test_create_item_api(client):
    response = await client.post("/items", json={"name": "Item"})
    
    assert response.status_code == 201
    assert response.json()["name"] == "Item"
```

---

## 测试覆盖

```bash
pytest --cov=app tests/
```

---

**下一步**: [最佳实践](../best-practices/index.md) →
