"""
新架构演示

展示如何使用优化后的架构创建应用。
"""

import asyncio
from typing import List, Optional
from dataclasses import dataclass

from pydantic import BaseModel
from fastapi import FastAPI, Depends

# 导入新的架构组件
from src.fastapi_easy.core.settings import AppSettings, init_settings
from src.fastapi_easy.core.container import DIContainer, LifetimeScope, injectable
from src.fastapi_easy.core.factory import ApplicationFactory, get_factory
from src.fastapi_easy.core.exceptions import (
    BaseException,
    NotFoundError,
    ValidationError,
    BusinessRuleError
)
from src.fastapi_easy.core.interfaces import (
    IRepository,
    ICacheService,
    IEventBus,
    QueryOptions,
    QueryFilter,
    QueryOperator
)
from src.fastapi_easy.middleware.exception_handler import ExceptionHandlingMiddleware


# 1. 定义业务模型
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    age: int


class UserCreate(BaseModel):
    name: str
    email: str
    age: int


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None


# 2. 实现服务接口
@injectable(LifetimeScope.SINGLETON)
class UserRepository(IRepository[User]):
    """用户仓储实现"""

    def __init__(self):
        # 模拟数据存储
        self._users: dict[int, User] = {}
        self._next_id = 1

    async def get_by_id(self, id: int) -> Optional[User]:
        return self._users.get(id)

    async def get_one(self, options: QueryOptions) -> Optional[User]:
        for user in self._users.values():
            if self._matches_filters(user, options.filters):
                return user
        return None

    async def get_many(self, options: QueryOptions):
        filtered_users = [
            user for user in self._users.values()
            if self._matches_filters(user, options.filters)
        ]

        # 排序
        if options.sorts:
            # 简化排序实现
            pass

        # 分页
        if options.pagination:
            skip = options.pagination.skip
            limit = options.pagination.limit
            filtered_users = filtered_users[skip:skip + limit]

        return filtered_users

    async def create(self, entity: User) -> User:
        entity.id = self._next_id
        self._next_id += 1
        self._users[entity.id] = entity
        return entity

    async def create_many(self, entities: List[User]) -> List[User]:
        created = []
        for entity in entities:
            created_entity = await self.create(entity)
            created.append(created_entity)
        return created

    async def update(self, id: int, updates: dict) -> Optional[User]:
        if id not in self._users:
            return None

        user = self._users[id]
        user_data = user.dict()
        user_data.update(updates)
        updated_user = User(**user_data)
        self._users[id] = updated_user
        return updated_user

    async def update_many(self, updates: dict, options: Optional[QueryOptions] = None) -> int:
        count = 0
        for user_id, user in self._users.items():
            if options is None or self._matches_filters(user, options.filters):
                user_data = user.dict()
                user_data.update(updates)
                self._users[user_id] = User(**user_data)
                count += 1
        return count

    async def delete(self, id: int) -> bool:
        if id in self._users:
            del self._users[id]
            return True
        return False

    async def delete_many(self, options: QueryOptions) -> int:
        to_delete = [
            user_id for user_id, user in self._users.items()
            if self._matches_filters(user, options.filters)
        ]

        for user_id in to_delete:
            del self._users[user_id]

        return len(to_delete)

    async def count(self, options: QueryOptions) -> int:
        return len([
            user for user in self._users.values()
            if self._matches_filters(user, options.filters)
        ])

    async def exists(self, options: QueryOptions) -> bool:
        return any(
            self._matches_filters(user, options.filters)
            for user in self._users.values()
        )

    def _matches_filters(self, user: User, filters: List[QueryFilter]) -> bool:
        """检查用户是否匹配过滤器"""
        if not filters:
            return True

        for filter_obj in filters:
            user_value = getattr(user, filter_obj.field, None)

            if filter_obj.operator == QueryOperator.EQ:
                if user_value != filter_obj.value:
                    return False
            elif filter_obj.operator == QueryOperator.LIKE:
                if not isinstance(user_value, str) or filter_obj.value not in user_value:
                    return False

        return True


@injectable(LifetimeScope.SINGLETON)
class UserService:
    """用户服务"""

    def __init__(
        self,
        user_repository: UserRepository,
        cache_service: Optional[ICacheService] = None,
        event_bus: Optional[IEventBus] = None
    ):
        self.user_repository = user_repository
        self.cache_service = cache_service
        self.event_bus = event_bus

    async def get_user(self, user_id: int) -> User:
        """获取用户"""
        # 先从缓存获取
        if self.cache_service:
            cached_user = await self.cache_service.get(f"user:{user_id}")
            if cached_user:
                return cached_user

        # 从仓储获取
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        # 缓存用户
        if self.cache_service:
            await self.cache_service.set(f"user:{user_id}", user, ttl=300)

        return user

    async def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        # 业务规则验证
        if user_data.age < 18:
            raise BusinessRuleError("User must be at least 18 years old")

        # 检查邮箱是否已存在
        existing_options = QueryOptions(
            filters=[QueryFilter("email", QueryOperator.EQ, user_data.email)]
        )
        if await self.user_repository.exists(existing_options):
            raise ValidationError("email", "Email already exists")

        # 创建用户
        user = User(**user_data.dict())
        created_user = await self.user_repository.create(user)

        # 发布事件
        if self.event_bus:
            await self.event_bus.publish("user.created", created_user.dict())

        return created_user

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """更新用户"""
        updates = user_data.dict(exclude_unset=True)

        if not updates:
            raise ValidationError("data", "No valid fields to update")

        updated_user = await self.user_repository.update(user_id, updates)
        if not updated_user:
            raise NotFoundError("User", user_id)

        # 清除缓存
        if self.cache_service:
            await self.cache_service.delete(f"user:{user_id}")

        # 发布事件
        if self.event_bus:
            await self.event_bus.publish("user.updated", updated_user.dict())

        return updated_user

    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        deleted = await self.user_repository.delete(user_id)

        if deleted:
            # 清除缓存
            if self.cache_service:
                await self.cache_service.delete(f"user:{user_id}")

            # 发布事件
            if self.event_bus:
                await self.event_bus.publish("user.deleted", {"id": user_id})

        return deleted

    async def list_users(
        self,
        name_filter: Optional[str] = None,
        min_age: Optional[int] = None,
        skip: int = 0,
        limit: int = 10
    ) -> List[User]:
        """列出用户"""
        filters = []

        if name_filter:
            filters.append(QueryFilter("name", QueryOperator.LIKE, name_filter))

        if min_age is not None:
            filters.append(QueryFilter("age", QueryOperator.GTE, min_age))

        options = QueryOptions(
            filters=filters,
            pagination=QueryPagination(skip=skip, limit=limit)
        )

        return await self.user_repository.get_many(options)


# 3. 配置应用
def create_app() -> FastAPI:
    """创建FastAPI应用"""
    # 初始化设置
    settings = AppSettings.create(
        app_name="Architecture Demo",
        debug=True,
        api_prefix="/api/v1"
    )
    init_settings(settings)

    # 创建应用工厂
    factory = ApplicationFactory(settings)

    # 注册服务到容器
    container = factory.container
    container.register_singleton(UserService)
    container.register_singleton(UserRepository)

    # 创建FastAPI应用
    app = factory.create_app()

    # 添加异常处理中间件
    app.add_middleware(ExceptionHandlingMiddleware)

    # 定义API路由
    @app.post("/users", response_model=User)
    async def create_user(user_data: UserCreate, user_service: UserService = Depends()):
        return await user_service.create_user(user_data)

    @app.get("/users/{user_id}", response_model=User)
    async def get_user(user_id: int, user_service: UserService = Depends()):
        return await user_service.get_user(user_id)

    @app.put("/users/{user_id}", response_model=User)
    async def update_user(
        user_id: int,
        user_data: UserUpdate,
        user_service: UserService = Depends()
    ):
        return await user_service.update_user(user_id, user_data)

    @app.delete("/users/{user_id}")
    async def delete_user(user_id: int, user_service: UserService = Depends()):
        await user_service.delete_user(user_id)
        return {"message": "User deleted successfully"}

    @app.get("/users", response_model=List[User])
    async def list_users(
        name: Optional[str] = None,
        min_age: Optional[int] = None,
        skip: int = 0,
        limit: int = 10,
        user_service: UserService = Depends()
    ):
        return await user_service.list_users(name, min_age, skip, limit)

    return app


# 4. 运行示例
if __name__ == "__main__":
    import uvicorn

    app = create_app()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )