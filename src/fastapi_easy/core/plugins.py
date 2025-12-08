"""
插件系统

提供可扩展的插件架构，支持动态加载和卸载插件。
遵循开闭原则，支持功能的热插拔。
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import yaml

from .container import DIContainer
from .interfaces import BaseException, IPlugin, IPluginManager
from .settings import AppSettings

logger = logging.getLogger(__name__)


class PluginState(Enum):
    """插件状态"""

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ERROR = "error"
    UNLOADING = "unloading"


@dataclass
class PluginMetadata:
    """插件元数据"""

    name: str
    version: str
    description: str = ""
    author: str = ""
    email: str = ""
    homepage: str = ""
    dependencies: List[str] = field(default_factory=list)
    fastapi_easy_version: str = ">=0.1.0"
    python_version: str = ">=3.8"
    tags: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PluginMetadata:
        """从字典创建元数据"""
        return cls(**data)

    @classmethod
    def from_file(cls, file_path: str) -> PluginMetadata:
        """从文件加载元数据"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Plugin metadata file not found: {file_path}")

        try:
            with open(path, encoding="utf-8") as f:
                if path.suffix.lower() == ".json":
                    data = json.load(f)
                elif path.suffix.lower() in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                else:
                    raise ValueError(f"Unsupported metadata file format: {path.suffix}")

            return cls.from_dict(data)
        except Exception as e:
            raise ValueError(f"Failed to load plugin metadata from {file_path}: {e}") from e


@dataclass
class PluginInfo:
    """插件信息"""

    plugin: IPlugin
    metadata: PluginMetadata
    path: str
    state: PluginState = PluginState.UNLOADED
    error: Optional[Exception] = None
    load_time: Optional[float] = None
    init_time: Optional[float] = None
    config: Dict[str, Any] = field(default_factory=dict)


class PluginError(BaseException):
    """插件相关错误"""

    def __init__(self, plugin_name: str, message: str, **kwargs):
        super().__init__(
            message=f"Plugin '{plugin_name}': {message}", code="PLUGIN_ERROR", **kwargs
        )
        self.plugin_name = plugin_name


class PluginManager(IPluginManager):
    """
    插件管理器

    功能：
    1. 插件发现和加载
    2. 依赖管理
    3. 生命周期管理
    4. 配置管理
    5. 错误处理
    """

    def __init__(
        self, container: DIContainer, settings: AppSettings, plugin_dirs: Optional[List[str]] = None
    ):
        self.container = container
        self.settings = settings
        self.plugin_dirs = plugin_dirs or []
        self._plugins: Dict[str, PluginInfo] = {}
        self._dependency_graph: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()

    async def load_plugin(self, plugin_path: str) -> bool:
        """加载插件"""
        async with self._lock:
            return await self._load_plugin_internal(plugin_path)

    async def _load_plugin_internal(self, plugin_path: str) -> bool:
        """内部加载插件逻辑"""
        plugin_path = os.path.abspath(plugin_path)

        try:
            # 1. 加载元数据
            metadata = self._load_metadata(plugin_path)

            # 2. 检查插件是否已加载
            if metadata.name in self._plugins:
                logger.warning(f"Plugin '{metadata.name}' is already loaded")
                return True

            # 3. 验证依赖
            await self._validate_dependencies(metadata)

            # 4. 动态导入插件模块
            plugin_module = self._import_plugin_module(plugin_path)

            # 5. 获取插件类
            plugin_class = self._get_plugin_class(plugin_module, metadata.name)

            # 6. 创建插件实例
            plugin_instance = plugin_class()

            # 7. 验证插件接口
            if not isinstance(plugin_instance, IPlugin):
                raise PluginError(
                    metadata.name, "Plugin class does not implement IPlugin interface"
                )

            # 8. 创建插件信息
            plugin_info = PluginInfo(
                plugin=plugin_instance,
                metadata=metadata,
                path=plugin_path,
                state=PluginState.LOADED,
            )

            # 9. 注册到管理器
            self._plugins[metadata.name] = plugin_info

            # 10. 初始化插件
            await self._initialize_plugin(plugin_info)

            logger.info(f"Plugin '{metadata.name}' loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}")
            if isinstance(e, PluginError):
                raise
            raise PluginError(os.path.basename(plugin_path), f"Load failed: {e!s}", cause=e) from e

    def _load_metadata(self, plugin_path: str) -> PluginMetadata:
        """加载插件元数据"""
        # 查找元数据文件
        metadata_files = [
            "plugin.json",
            "plugin.yaml",
            "plugin.yml",
            "metadata.json",
            "metadata.yaml",
            "metadata.yml",
        ]

        for metadata_file in metadata_files:
            metadata_path = os.path.join(plugin_path, metadata_file)
            if os.path.exists(metadata_path):
                return PluginMetadata.from_file(metadata_path)

        # 如果没有找到元数据文件，尝试从代码中提取
        return self._extract_metadata_from_code(plugin_path)

    def _extract_metadata_from_code(self, plugin_path: str) -> PluginMetadata:
        """从代码中提取元数据"""
        # 简化实现，实际应该解析Python文件
        plugin_name = os.path.basename(plugin_path)
        return PluginMetadata(
            name=plugin_name, version="1.0.0", description=f"Plugin loaded from {plugin_path}"
        )

    async def _validate_dependencies(self, metadata: PluginMetadata):
        """验证插件依赖"""
        # 检查FastAPI-Easy版本兼容性
        if metadata.fastapi_easy_version:
            # 简化版本检查
            pass

        # 检查Python版本兼容性
        if metadata.python_version:
            # 简化版本检查
            pass

        # 检查插件依赖
        for dependency in metadata.dependencies:
            if dependency not in self._plugins:
                raise PluginError(metadata.name, f"Missing dependency: {dependency}")

    def _import_plugin_module(self, plugin_path: str):
        """动态导入插件模块"""
        # 查找主模块文件
        main_files = ["__init__.py", "main.py", "plugin.py"]

        for main_file in main_files:
            module_path = os.path.join(plugin_path, main_file)
            if os.path.exists(module_path):
                break
        else:
            raise PluginError(os.path.basename(plugin_path), "No main plugin file found")

        # 动态导入
        module_name = os.path.basename(plugin_path)
        spec = importlib.util.spec_from_file_location(module_name, module_path)

        if spec is None or spec.loader is None:
            raise PluginError(os.path.basename(plugin_path), "Failed to create module spec")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return module

    def _get_plugin_class(self, module, plugin_name: str) -> Type[IPlugin]:
        """获取插件类"""
        # 查找实现了IPlugin接口的类
        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            if isinstance(attr, type) and issubclass(attr, IPlugin) and attr != IPlugin:
                return attr

        raise PluginError(plugin_name, "No plugin class found that implements IPlugin interface")

    async def _initialize_plugin(self, plugin_info: PluginInfo):
        """初始化插件"""
        try:
            plugin_info.state = PluginState.INITIALIZING

            # 准备初始化上下文
            context = {
                "container": self.container,
                "settings": self.settings,
                "plugin_manager": self,
                "config": plugin_info.config,
            }

            # 调用插件初始化
            await plugin_info.plugin.initialize(context)

            # 注册插件服务到容器
            await self._register_plugin_services(plugin_info)

            plugin_info.state = PluginState.ACTIVE
            plugin_info.init_time = asyncio.get_event_loop().time()

        except Exception as e:
            plugin_info.state = PluginState.ERROR
            plugin_info.error = e
            raise PluginError(
                plugin_info.metadata.name, f"Initialization failed: {e!s}", cause=e
            ) from e

    async def _register_plugin_services(self, plugin_info: PluginInfo):
        """注册插件服务到容器"""
        # 检查插件是否提供服务
        if hasattr(plugin_info.plugin, "get_services"):
            try:
                services = plugin_info.plugin.get_services()
                for service_type, service_impl in services.items():
                    self.container.register_singleton(service_type, service_impl)
            except Exception as e:
                logger.warning(
                    f"Failed to register services for plugin {plugin_info.metadata.name}: {e}"
                )

    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        async with self._lock:
            return await self._unload_plugin_internal(plugin_name)

    async def _unload_plugin_internal(self, plugin_name: str) -> bool:
        """内部卸载插件逻辑"""
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin '{plugin_name}' is not loaded")
            return False

        plugin_info = self._plugins[plugin_name]

        # 检查是否有其他插件依赖此插件
        dependents = self._get_plugin_dependents(plugin_name)
        if dependents:
            raise PluginError(
                plugin_name, f"Cannot unload: required by plugins: {', '.join(dependents)}"
            )

        try:
            plugin_info.state = PluginState.UNLOADING

            # 调用插件清理
            await plugin_info.plugin.dispose()

            # 从容器中移除插件服务
            await self._unregister_plugin_services(plugin_info)

            # 从管理器中移除
            del self._plugins[plugin_name]

            logger.info(f"Plugin '{plugin_name}' unloaded successfully")
            return True

        except Exception as e:
            plugin_info.state = PluginState.ERROR
            plugin_info.error = e
            raise PluginError(plugin_name, f"Unload failed: {e!s}", cause=e) from e

    def _get_plugin_dependents(self, plugin_name: str) -> List[str]:
        """获取依赖指定插件的其他插件"""
        dependents = []
        for name, info in self._plugins.items():
            if plugin_name in info.metadata.dependencies:
                dependents.append(name)
        return dependents

    async def _unregister_plugin_services(self, plugin_info: PluginInfo):
        """从容器中移除插件服务"""
        # 简化实现，实际应该追踪插件注册的服务
        pass

    def get_loaded_plugins(self) -> List[IPlugin]:
        """获取已加载的插件"""
        return [info.plugin for info in self._plugins.values() if info.state == PluginState.ACTIVE]

    def get_plugin(self, name: str) -> Optional[IPlugin]:
        """获取插件"""
        info = self._plugins.get(name)
        return info.plugin if info and info.state == PluginState.ACTIVE else None

    def get_plugin_info(self, name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self._plugins.get(name)

    def list_plugins(self) -> Dict[str, PluginInfo]:
        """列出所有插件"""
        return self._plugins.copy()

    async def discover_plugins(self, directories: Optional[List[str]] = None) -> List[str]:
        """发现插件"""
        search_dirs = directories or self.plugin_dirs
        discovered = []

        for directory in search_dirs:
            if not os.path.exists(directory):
                continue

            for item in os.listdir(directory):
                plugin_path = os.path.join(directory, item)

                if os.path.isdir(plugin_path):
                    # 检查是否是有效的插件目录
                    try:
                        self._load_metadata(plugin_path)
                        discovered.append(plugin_path)
                    except Exception:
                        # 不是有效的插件目录
                        pass

        return discovered

    async def load_all_plugins(self, directories: Optional[List[str]] = None):
        """加载所有发现的插件"""
        discovered = await self.discover_plugins(directories)

        # 按依赖关系排序
        sorted_plugins = self._sort_plugins_by_dependencies(discovered)

        # 依次加载
        for plugin_path in sorted_plugins:
            try:
                await self.load_plugin(plugin_path)
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_path}: {e}")

    def _sort_plugins_by_dependencies(self, plugin_paths: List[str]) -> List[str]:
        """根据依赖关系对插件排序"""
        # 简化实现，实际应该进行拓扑排序
        return plugin_paths

    async def get_plugin_status(self, name: str) -> Dict[str, Any]:
        """获取插件状态"""
        info = self._plugins.get(name)
        if not info:
            return {"status": "not_found"}

        return {
            "status": info.state.value,
            "version": info.metadata.version,
            "description": info.metadata.description,
            "dependencies": info.metadata.dependencies,
            "load_time": info.load_time,
            "init_time": info.init_time,
            "error": str(info.error) if info.error else None,
        }

    async def reload_plugin(self, name: str) -> bool:
        """重新加载插件"""
        info = self._plugins.get(name)
        if not info:
            raise PluginError(name, "Plugin not found")

        plugin_path = info.path

        # 先卸载
        await self._unload_plugin_internal(name)

        # 再加载
        return await self._load_plugin_internal(plugin_path)
