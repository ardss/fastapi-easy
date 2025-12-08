"""
依赖注入容器

提供轻量级、高性能的依赖注入系统。
支持单例、瞬态、作用域生命周期管理。
"""

from __future__ import annotations

import inspect
import logging
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar, get_type_hints

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LifetimeScope(Enum):
    """生命周期范围"""

    SINGLETON = "singleton"  # 单例，整个应用生命周期
    TRANSIENT = "transient"  # 瞬态，每次请求都创建新实例
    SCOPED = "scoped"  # 作用域，在特定作用域内单例


@dataclass
class ServiceDescriptor:
    """服务描述符"""

    service_type: Type
    implementation_type: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    lifetime: LifetimeScope = LifetimeScope.TRANSIENT
    dependencies: Optional[Dict[str, Type]] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = {}


class ServiceScope:
    """服务作用域"""

    def __init__(self, container: DIContainer):
        self.container = container
        self._scoped_instances: Dict[Type, Any] = {}
        self._disposed = False

    def get_service(self, service_type: Type[T]) -> T:
        """获取作用域内的服务"""
        if self._disposed:
            raise RuntimeError("Service scope has been disposed")

        return self.container._resolve_service(service_type, self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

    def dispose(self):
        """释放作用域资源"""
        if self._disposed:
            return

        # 释放所有作用域实例
        for instance in self._scoped_instances.values():
            if hasattr(instance, "dispose"):
                try:
                    instance.dispose()
                except Exception as e:
                    logger.warning(f"Error disposing service instance: {e}")

        self._scoped_instances.clear()
        self._disposed = True


class DIContainer:
    """
    依赖注入容器

    功能：
    1. 服务注册和解析
    2. 生命周期管理
    3. 循环依赖检测
    4. 装饰器支持
    """

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singleton_instances: Dict[Type, Any] = {}
        self._lock = threading.RLock()
        self._resolution_stack: Dict[Type, int] = {}  # 用于循环依赖检测

    def register_singleton(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
    ) -> DIContainer:
        """注册单例服务"""
        return self._register_service(
            service_type, implementation_type, factory, instance, LifetimeScope.SINGLETON
        )

    def register_transient(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
    ) -> DIContainer:
        """注册瞬态服务"""
        return self._register_service(
            service_type, implementation_type, factory, None, LifetimeScope.TRANSIENT
        )

    def register_scoped(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
    ) -> DIContainer:
        """注册作用域服务"""
        return self._register_service(
            service_type, implementation_type, factory, None, LifetimeScope.SCOPED
        )

    def _register_service(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]],
        factory: Optional[Callable[[], T]],
        instance: Optional[T],
        lifetime: LifetimeScope,
    ) -> DIContainer:
        """注册服务"""
        with self._lock:
            # 参数验证
            if sum(x is not None for x in [implementation_type, factory, instance]) != 1:
                raise ValueError(
                    "Exactly one of implementation_type, factory, or instance must be provided"
                )

            # 如果提供了实例，检查类型兼容性
            if instance is not None and not isinstance(instance, service_type):
                raise ValueError(f"Instance {instance} is not an instance of {service_type}")

            # 如果提供了实现类型，检查继承关系
            if implementation_type is not None:
                if not issubclass(implementation_type, service_type):
                    raise ValueError(f"{implementation_type} is not a subclass of {service_type}")

            # 分析依赖关系
            dependencies = {}
            if implementation_type is not None:
                dependencies = self._analyze_dependencies(implementation_type)

            # 创建服务描述符
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type,
                factory=factory,
                instance=instance,
                lifetime=lifetime,
                dependencies=dependencies,
            )

            self._services[service_type] = descriptor

            # 如果是单例实例，直接存储
            if lifetime == LifetimeScope.SINGLETON and instance is not None:
                self._singleton_instances[service_type] = instance

            return self

    def _analyze_dependencies(self, implementation_type: Type) -> Dict[str, Type]:
        """分析类的依赖关系"""
        dependencies = {}

        try:
            # 获取构造函数签名
            sig = inspect.signature(implementation_type.__init__)
            type_hints = get_type_hints(implementation_type)

            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                # 跳过有默认值的参数
                if param.default != inspect.Parameter.empty:
                    continue

                # 获取参数类型
                param_type = type_hints.get(param_name, param.annotation)

                if param_type != inspect.Parameter.empty:
                    dependencies[param_name] = param_type

        except Exception as e:
            logger.warning(f"Failed to analyze dependencies for {implementation_type}: {e}")

        return dependencies

    def resolve(self, service_type: Type[T], scope: Optional[ServiceScope] = None) -> T:
        """解析服务"""
        return self._resolve_service(service_type, scope)

    def _resolve_service(self, service_type: Type[T], scope: Optional[ServiceScope] = None) -> T:
        """内部服务解析"""
        with self._lock:
            # 检查服务是否已注册
            if service_type not in self._services:
                # 尝试自动注册
                if self._can_auto_register(service_type):
                    self.register_transient(service_type, service_type)
                else:
                    raise ValueError(f"Service {service_type} is not registered")

            descriptor = self._services[service_type]

            # 循环依赖检测
            if service_type in self._resolution_stack:
                self._resolution_stack[service_type] += 1
                if self._resolution_stack[service_type] > 1:
                    # 构建循环依赖链
                    cycle_chain = []
                    for st, count in self._resolution_stack.items():
                        if count > 0:
                            cycle_chain.append(st.__name__)

                    raise RuntimeError(
                        f"Circular dependency detected: {' -> '.join(cycle_chain)} -> {service_type.__name__}"
                    )
            else:
                self._resolution_stack[service_type] = 1

            try:
                # 根据生命周期解析实例
                if descriptor.lifetime == LifetimeScope.SINGLETON:
                    return self._resolve_singleton(descriptor, scope)
                elif descriptor.lifetime == LifetimeScope.SCOPED:
                    return self._resolve_scoped(descriptor, scope)
                else:  # TRANSIENT
                    return self._resolve_transient(descriptor, scope)

            finally:
                # 清理解析栈
                if service_type in self._resolution_stack:
                    self._resolution_stack[service_type] -= 1
                    if self._resolution_stack[service_type] == 0:
                        del self._resolution_stack[service_type]

    def _can_auto_register(self, service_type: Type) -> bool:
        """检查是否可以自动注册"""
        # 只允许自动注册具体的类（非抽象类、非接口）
        return (
            inspect.isclass(service_type)
            and not inspect.isabstract(service_type)
            and hasattr(service_type, "__init__")
        )

    def _resolve_singleton(
        self, descriptor: ServiceDescriptor, scope: Optional[ServiceScope]
    ) -> Any:
        """解析单例服务"""
        if descriptor.service_type in self._singleton_instances:
            return self._singleton_instances[descriptor.service_type]

        # 创建实例
        instance = self._create_instance(descriptor, scope)
        self._singleton_instances[descriptor.service_type] = instance
        return instance

    def _resolve_scoped(self, descriptor: ServiceDescriptor, scope: Optional[ServiceScope]) -> Any:
        """解析作用域服务"""
        if scope is None:
            raise ValueError(f"Scoped service {descriptor.service_type} requires a service scope")

        if descriptor.service_type in scope._scoped_instances:
            return scope._scoped_instances[descriptor.service_type]

        # 创建实例
        instance = self._create_instance(descriptor, scope)
        scope._scoped_instances[descriptor.service_type] = instance
        return instance

    def _resolve_transient(
        self, descriptor: ServiceDescriptor, scope: Optional[ServiceScope]
    ) -> Any:
        """解析瞬态服务"""
        return self._create_instance(descriptor, scope)

    def _create_instance(self, descriptor: ServiceDescriptor, scope: Optional[ServiceScope]) -> Any:
        """创建服务实例"""
        # 如果有预定义实例，直接返回
        if descriptor.instance is not None:
            return descriptor.instance

        # 使用工厂方法
        if descriptor.factory is not None:
            return descriptor.factory()

        # 使用实现类型创建实例
        if descriptor.implementation_type is not None:
            return self._create_instance_with_dependencies(
                descriptor.implementation_type, descriptor.dependencies, scope
            )

        raise ValueError(f"Cannot create instance for {descriptor.service_type}")

    def _create_instance_with_dependencies(
        self,
        implementation_type: Type,
        dependencies: Dict[str, Type],
        scope: Optional[ServiceScope],
    ) -> Any:
        """创建带依赖的实例"""
        # 解析依赖
        dependency_instances = {}
        for dep_name, dep_type in dependencies.items():
            dependency_instances[dep_name] = self._resolve_service(dep_type, scope)

        # 创建实例
        try:
            return implementation_type(**dependency_instances)
        except Exception as e:
            raise RuntimeError(f"Failed to create instance of {implementation_type}: {e}") from e

    def create_scope(self) -> ServiceScope:
        """创建服务作用域"""
        return ServiceScope(self)

    def is_registered(self, service_type: Type) -> bool:
        """检查服务是否已注册"""
        return service_type in self._services

    def get_registered_services(self) -> Dict[Type, ServiceDescriptor]:
        """获取所有已注册的服务"""
        return self._services.copy()

    def clear(self):
        """清空容器"""
        with self._lock:
            # 释放所有单例实例
            for instance in self._singleton_instances.values():
                if hasattr(instance, "dispose"):
                    try:
                        instance.dispose()
                    except Exception as e:
                        logger.warning(f"Error disposing singleton instance: {e}")

            self._services.clear()
            self._singleton_instances.clear()
            self._resolution_stack.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

    def dispose(self):
        """释放容器资源"""
        self.clear()


# 全局容器实例
_global_container: Optional[DIContainer] = None
_container_lock = threading.Lock()


def get_container() -> DIContainer:
    """获取全局容器实例"""
    global _global_container
    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                _global_container = DIContainer()
    return _global_container


def init_container(container: Optional[DIContainer] = None) -> DIContainer:
    """初始化全局容器"""
    global _global_container
    with _container_lock:
        if container is not None:
            if _global_container is not None:
                _global_container.dispose()
            _global_container = container
        else:
            if _global_container is None:
                _global_container = DIContainer()
    return _global_container


# 装饰器支持
def injectable(lifetime: LifetimeScope = LifetimeScope.TRANSIENT):
    """可注入服务装饰器"""

    def decorator(cls: Type[T]) -> Type[T]:
        container = get_container()

        if lifetime == LifetimeScope.SINGLETON:
            container.register_singleton(cls, cls)
        elif lifetime == LifetimeScope.SCOPED:
            container.register_scoped(cls, cls)
        else:  # TRANSIENT
            container.register_transient(cls, cls)

        return cls

    return decorator


def inject(service_type: Type[T]) -> T:
    """依赖注入装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            container = get_container()
            service = container.resolve(service_type)
            return func(service, *args, **kwargs)

        return wrapper

    return decorator


# FastAPI集成支持
def Depends(service_type: Type[T], scope: Optional[ServiceScope] = None) -> Callable[[], T]:
    """FastAPI依赖注入支持"""

    def dependency():
        container = get_container()
        return container.resolve(service_type, scope)

    return dependency
