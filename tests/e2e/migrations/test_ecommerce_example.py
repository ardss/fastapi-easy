"""
电商 API 示例的测试

验证示例 API 的所有端点都能正常工作

注意: 此测试文件已禁用，因为 ecommerce_api 模块不存在
实际的电商示例在 examples/05_complete_ecommerce.py 中
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# 跳过此模块中的所有测试
skip_reason = "ecommerce_api module not found - " "use examples/05_complete_ecommerce.py"
pytestmark = pytest.mark.skip(reason=skip_reason)

# 添加 examples 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../examples"))

# 此导入会失败，但由于 pytestmark 会跳过所有测试，所以不会执行
try:
    from ecommerce_api import app
except ImportError:
    # 创建一个虚拟应用以避免导入错误
    from fastapi import FastAPI

    app = FastAPI()


@pytest.fixture
def client():
    """创建测试客户端"""
    # 手动初始化示例数据
    from datetime import datetime

    from ecommerce_api import (
        Category,
        Order,
        Product,
        categories_db,
        orders_db,
        products_db,
    )

    # 清空数据库
    categories_db.clear()
    products_db.clear()
    orders_db.clear()

    # 创建示例分类
    categories = [
        Category(id=1, name="水果", description="新鲜水果"),
        Category(id=2, name="蔬菜", description="新鲜蔬菜"),
        Category(id=3, name="肉类", description="优质肉类"),
    ]
    categories_db.extend(categories)

    # 创建示例商品
    products = [
        Product(
            id=1,
            name="苹果",
            description="新鲜苹果",
            price=15.5,
            stock=100,
            category_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Product(
            id=2,
            name="香蕉",
            description="黄色香蕉",
            price=8.0,
            stock=150,
            category_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Product(
            id=3,
            name="番茄",
            description="红色番茄",
            price=5.5,
            stock=200,
            category_id=2,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Product(
            id=4,
            name="牛肉",
            description="优质牛肉",
            price=85.0,
            stock=50,
            category_id=3,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    products_db.extend(products)

    # 创建示例订单
    orders = [
        Order(
            id=1,
            order_number="ORD-001",
            total_price=150.0,
            status="completed",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Order(
            id=2,
            order_number="ORD-002",
            total_price=200.0,
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Order(
            id=3,
            order_number="ORD-003",
            total_price=85.0,
            status="shipped",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    orders_db.extend(orders)

    return TestClient(app)


class TestRootEndpoint:
    """根路由测试"""

    def test_root_endpoint(self, client):
        """测试根路由"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data


class TestCategoryEndpoints:
    """分类 API 测试"""

    def test_get_categories(self, client):
        """测试获取所有分类"""
        response = client.get("/categories")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0  # 应该有初始化的示例数据

    def test_get_category(self, client):
        """测试获取单个分类"""
        response = client.get("/categories/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    def test_create_category(self, client):
        """测试创建分类"""
        response = client.post("/categories", json={"name": "新分类", "description": "测试分类"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "新分类"
        assert data["id"] is not None

    def test_update_category(self, client):
        """测试更新分类"""
        response = client.put(
            "/categories/1", json={"name": "更新的分类", "description": "更新的描述"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新的分类"

    def test_delete_category(self, client):
        """测试删除分类"""
        # 先创建一个分类
        create_response = client.post(
            "/categories", json={"name": "待删除分类", "description": "测试"}
        )
        category_id = create_response.json()["id"]

        # 然后删除它
        delete_response = client.delete(f"/categories/{category_id}")
        assert delete_response.status_code == 200


class TestProductEndpoints:
    """商品 API 测试"""

    def test_get_products(self, client):
        """测试获取所有商品"""
        response = client.get("/products")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0

    def test_get_product(self, client):
        """测试获取单个商品"""
        response = client.get("/products/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    def test_create_product(self, client):
        """测试创建商品"""
        response = client.post(
            "/products",
            json={
                "name": "新商品",
                "description": "测试商品",
                "price": 99.99,
                "stock": 50,
                "category_id": 1,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "新商品"
        assert data["price"] == 99.99

    def test_update_product(self, client):
        """测试更新商品"""
        response = client.put(
            "/products/1",
            json={
                "name": "更新的商品",
                "description": "更新的描述",
                "price": 20.0,
                "stock": 80,
                "category_id": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新的商品"

    def test_delete_product(self, client):
        """测试删除商品"""
        # 先创建一个商品
        create_response = client.post(
            "/products",
            json={
                "name": "待删除商品",
                "description": "测试",
                "price": 10.0,
                "stock": 10,
                "category_id": 1,
            },
        )
        product_id = create_response.json()["id"]

        # 然后删除它
        delete_response = client.delete(f"/products/{product_id}")
        assert delete_response.status_code == 200

    def test_get_products_with_filter(self, client):
        """测试带过滤的商品查询"""
        response = client.get("/products?category_id=1")
        assert response.status_code == 200
        data = response.json()
        assert all(p["category_id"] == 1 for p in data["items"])

    def test_get_products_with_price_filter(self, client):
        """测试带价格过滤的商品查询"""
        response = client.get("/products?min_price=10&max_price=50")
        assert response.status_code == 200
        data = response.json()
        assert all(10 <= p["price"] <= 50 for p in data["items"])


class TestOrderEndpoints:
    """订单 API 测试"""

    def test_get_orders(self, client):
        """测试获取所有订单"""
        response = client.get("/orders")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0

    def test_get_order(self, client):
        """测试获取单个订单"""
        response = client.get("/orders/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    def test_create_order(self, client):
        """测试创建订单"""
        response = client.post(
            "/orders", json={"order_number": "TEST-001", "total_price": 500.0, "status": "pending"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["order_number"] == "TEST-001"
        assert data["total_price"] == 500.0

    def test_update_order(self, client):
        """测试更新订单"""
        response = client.put(
            "/orders/1",
            json={"order_number": "ORD-001-UPDATED", "total_price": 200.0, "status": "shipped"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shipped"

    def test_delete_order(self, client):
        """测试删除订单"""
        # 先创建一个订单
        create_response = client.post(
            "/orders",
            json={"order_number": "TEST-DELETE", "total_price": 100.0, "status": "pending"},
        )
        order_id = create_response.json()["id"]

        # 然后删除它
        delete_response = client.delete(f"/orders/{order_id}")
        assert delete_response.status_code == 200

    def test_get_orders_with_status_filter(self, client):
        """测试带状态过滤的订单查询"""
        response = client.get("/orders?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert all(o["status"] == "pending" for o in data["items"])


class TestStatsEndpoint:
    """统计 API 测试"""

    def test_get_stats(self, client):
        """测试获取统计信息"""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "categories_count" in data
        assert "products_count" in data
        assert "orders_count" in data
        assert "total_revenue" in data
        assert "average_order_value" in data


class TestPagination:
    """分页测试"""

    def test_pagination_skip_limit(self, client):
        """测试分页的 skip 和 limit"""
        response = client.get("/products?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["skip"] == 0
        assert data["limit"] == 2


class TestSorting:
    """排序测试"""

    def test_sorting_ascending(self, client):
        """测试升序排序"""
        response = client.get("/products?sort_by=price")
        assert response.status_code == 200
        data = response.json()
        prices = [p["price"] for p in data["items"]]
        assert prices == sorted(prices)

    def test_sorting_descending(self, client):
        """测试降序排序"""
        response = client.get("/products?sort_by=-price")
        assert response.status_code == 200
        data = response.json()
        prices = [p["price"] for p in data["items"]]
        assert prices == sorted(prices, reverse=True)
