"""
工厂模式实现

提供各种组件的工厂类，支持灵活的配置和扩展。
遵循开闭原则，便于新增组件类型。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from .settings import AppSettings
from .container import DIContainer, LifetimeScope
from .exceptions import BaseException
from .adapters import ORMAdapter
from .crud_router import CRUDRouter

T = TypeVar("T")


class ComponentType(Enum):
    """组件类型"""

    ROUTER = "router"
    MIDDLEWARE = "middleware"
    ADAPTER = "adapter"
    SERVICE = "service"
    HOOK = "hook"


@dataclass
class ComponentSpec:
    """组件规格"""

    component_type: ComponentType
    name: str
    implementation: Optional[Type] = None
    factory: Optional[Callable] = None
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    singleton: bool = True


class ComponentFactory(ABC):
    """组件工厂基类"""

    @abstractmethod
    def create(self, spec: ComponentSpec, container: DIContainer) -> Any:
        """创建组件"""
        pass

    @abstractmethod
    def can_create(self, component_type: ComponentType) -> bool:
        """检查是否可以创建指定类型的组件"""
        pass


class CRUDRouterFactory(ComponentFactory):
    """CRUD路由工厂"""

    def can_create(self, component_type: ComponentType) -> bool:
        return component_type == ComponentType.ROUTER

    def create(self, spec: ComponentSpec, container: DIContainer) -> CRUDRouter:
        """创建CRUD路由"""
        config = spec.config

        # 获取必需的参数
        schema = config.get("schema")
        if not schema:
            raise ValueError("Schema is required for CRUD router")

        # 获取适配器
        adapter = config.get("adapter")
        if not adapter:
            adapter_name = config.get("adapter_name", "sqlalchemy")
            adapter = self._create_adapter(adapter_name, config, container)

        # 创建路由配置
        router_config = config.get("router_config", {})

        # 创建CRUD路由
        router = CRUDRouter(schema=schema, adapter=adapter, **router_config)

        return router

    def _create_adapter(
        self, adapter_name: str, config: Dict[str, Any], container: DIContainer
    ) -> ORMAdapter:
        """创建适配器"""
        # 这里可以根据适配器名称创建不同的适配器
        # 简化实现，实际应该有适配器工厂
        if adapter_name == "sqlalchemy":
            from ..backends.sqlalchemy import SQLAlchemyAdapter

            model_class = config.get("model_class")
            get_db = config.get("get_db")
            return SQLAlchemyAdapter(model_class, get_db)
        else:
            raise ValueError(f"Unknown adapter: {adapter_name}")


class MiddlewareFactory(ComponentFactory):
    """中间件工厂"""

    def can_create(self, component_type: ComponentType) -> bool:
        return component_type == ComponentType.MIDDLEWARE

    def create(self, spec: ComponentSpec, container: DIContainer) -> Any:
        """创建中间件"""
        middleware_name = spec.name
        config = spec.config

        if middleware_name == "exception_handler":
            from ..middleware.exception_handler import ExceptionHandlingMiddleware

            return ExceptionHandlingMiddleware(
                app=None,  # 将在应用创建时设置
                include_traceback=config.get("include_traceback", False),
                log_errors=config.get("log_errors", True),
            )
        elif middleware_name == "circuit_breaker":
            from ..middleware.exception_handler import CircuitBreakerMiddleware

            return CircuitBreakerMiddleware(
                app=None,  # 将在应用创建时设置
                failure_threshold=config.get("failure_threshold", 5),
                recovery_timeout=config.get("recovery_timeout", 60),
            )
        else:
            raise ValueError(f"Unknown middleware: {middleware_name}")


class ServiceFactory(ComponentFactory):
    """服务工厂"""

    def can_create(self, component_type: ComponentType) -> bool:
        return component_type == ComponentType.SERVICE

    def create(self, spec: ComponentSpec, container: DIContainer) -> Any:
        """创建服务"""
        if spec.factory:
            return spec.factory(**spec.config)
        elif spec.implementation:
            # 解析依赖
            dependencies = {}
            for dep_name in spec.dependencies:
                dependencies[dep_name] = container.resolve(dep_name)

            return spec.implementation(**dependencies)
        else:
            raise ValueError(f"No implementation or factory for service: {spec.name}")


class ComponentRegistry:
    """组件注册表"""

    def __init__(self):
        self._factories: List[ComponentFactory] = []
        self._specs: Dict[str, ComponentSpec] = {}

        # 注册默认工厂
        self.register_factory(CRUDRouterFactory())
        self.register_factory(MiddlewareFactory())
        self.register_factory(ServiceFactory())

    def register_factory(self, factory: ComponentFactory):
        """注册组件工厂"""
        self._factories.append(factory)

    def register_component(self, spec: ComponentSpec):
        """注册组件规格"""
        self._specs[spec.name] = spec

    def create_component(self, name: str, container: DIContainer) -> Any:
        """创建组件"""
        if name not in self._specs:
            raise ValueError(f"Component spec not found: {name}")

        spec = self._specs[name]

        # 找到合适的工厂
        for factory in self._factories:
            if factory.can_create(spec.component_type):
                component = factory.create(spec, container)

                # 注册到容器
                if spec.singleton:
                    container.register_singleton(type(component), instance=component)
                else:
                    container.register_transient(type(component), type(component))

                return component

        raise ValueError(f"No factory found for component: {name}")

    def get_spec(self, name: str) -> Optional[ComponentSpec]:
        """获取组件规格"""
        return self._specs.get(name)


class ApplicationFactory:
    """
    应用工厂

    负责创建和配置FastAPI应用，支持组件化开发。
    """

    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or AppSettings.create()
        self.container = DIContainer()
        self.component_registry = ComponentRegistry()
        self._app: Optional[FastAPI] = None

        # 注册基础服务
        self._register_base_services()

    def _register_base_services(self):
        """注册基础服务"""
        # 注册设置
        self.container.register_singleton(AppSettings, instance=self.settings)

        # 注册组件注册表
        self.container.register_singleton(ComponentRegistry, instance=self.component_registry)

    def create_app(self, **fastapi_kwargs) -> FastAPI:
        """创建FastAPI应用"""
        if self._app is not None:
            return self._app

        # 设置FastAPI参数
        app_kwargs = {
            "title": self.settings.app_name,
            "version": self.settings.version,
            "debug": self.settings.debug,
            **fastapi_kwargs,
        }

        # 处理API前缀
        if "prefix" not in app_kwargs:
            app_kwargs["prefix"] = self.settings.api_prefix

        # 创建FastAPI应用
        app = FastAPI(**app_kwargs)

        # 配置中间件
        self._configure_middleware(app)

        # 配置路由
        self._configure_routes(app)

        # 配置异常处理
        self._configure_exception_handlers(app)

        self._app = app
        return app

    def _configure_middleware(self, app: FastAPI):
        """配置中间件"""
        # 这里可以根据配置加载不同的中间件
        # 简化实现
        pass

    def _configure_routes(self, app: FastAPI):
        """配置路由"""
        # 从组件注册表获取路由组件并注册
        for name, spec in self.component_registry._specs.items():
            if spec.component_type == ComponentType.ROUTER:
                router = self.component_registry.create_component(name, self.container)
                if isinstance(router, APIRouter):
                    app.include_router(router)

    def _configure_exception_handlers(self, app: FastAPI):
        """配置异常处理器"""
        from .exceptions import BaseException

        @app.exception_handler(BaseException)
        async def handle_base_exception(request, exc: BaseException):
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    def register_crud_router(
        self,
        name: str,
        schema: Type[BaseModel],
        adapter: Optional[ORMAdapter] = None,
        adapter_config: Optional[Dict[str, Any]] = None,
        **router_kwargs,
    ) -> "ApplicationFactory":
        """注册CRUD路由组件"""
        config = {
            "schema": schema,
            "adapter": adapter,
            "adapter_config": adapter_config or {},
            "router_config": router_kwargs,
        }

        spec = ComponentSpec(component_type=ComponentType.ROUTER, name=name, config=config)

        self.component_registry.register_component(spec)
        return self

    def register_service(
        self,
        name: str,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        singleton: bool = True,
        dependencies: Optional[List[str]] = None,
        **config,
    ) -> "ApplicationFactory":
        """注册服务组件"""
        spec = ComponentSpec(
            component_type=ComponentType.SERVICE,
            name=name,
            implementation=implementation,
            factory=factory,
            config=config,
            dependencies=dependencies or [],
            singleton=singleton,
        )

        self.component_registry.register_component(spec)
        return self

    def register_middleware(self, name: str, **config) -> "ApplicationFactory":
        """注册中间件组件"""
        spec = ComponentSpec(component_type=ComponentType.MIDDLEWARE, name=name, config=config)

        self.component_registry.register_component(spec)
        return self

    def get_service(self, service_type: Type[T]) -> T:
        """获取服务实例"""
        return self.container.resolve(service_type)

    def create_scope(self):
        """创建服务作用域"""
        return self.container.create_scope()


# 全局应用工厂
_global_factory: Optional[ApplicationFactory] = None


def get_factory() -> ApplicationFactory:
    """获取全局应用工厂"""
    global _global_factory
    if _global_factory is None:
        _global_factory = ApplicationFactory()
    return _global_factory


def init_factory(settings: Optional[AppSettings] = None) -> ApplicationFactory:
    """初始化全局应用工厂"""
    global _global_factory
    _global_factory = ApplicationFactory(settings)
    return _global_factory


# 便捷函数
def create_app(settings: Optional[AppSettings] = None, **kwargs) -> FastAPI:
    """创建FastAPI应用（便捷函数）"""
    factory = init_factory(settings)
    return factory.create_app(**kwargs)
