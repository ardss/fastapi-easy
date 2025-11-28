"""
数据迁移 Hook 系统

支持:
- 装饰器注册机制
- 执行顺序控制
- 异步和同步回调
- 错误隔离
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HookTrigger(str, Enum):
    """Hook 触发时机"""
    BEFORE_DDL = "before_ddl"  # DDL 执行前
    AFTER_DDL = "after_ddl"    # DDL 执行后
    BEFORE_DML = "before_dml"  # DML 执行前
    AFTER_DML = "after_dml"    # DML 执行后


@dataclass
class MigrationHook:
    """迁移 Hook 定义"""
    name: str
    version: str  # 迁移版本
    trigger: HookTrigger
    callback: Callable
    priority: int = 0  # 优先级 (高优先级先执行)
    is_async: bool = False
    description: Optional[str] = None


class HookRegistry:
    """Hook 注册表"""

    def __init__(self):
        self.hooks: Dict[HookTrigger, List[MigrationHook]] = {
            trigger: [] for trigger in HookTrigger
        }
        self._hook_results: Dict[str, Any] = {}

    def register(
        self,
        name: str,
        version: str,
        trigger: HookTrigger,
        callback: Callable,
        priority: int = 0,
        description: Optional[str] = None,
    ) -> MigrationHook:
        """注册 Hook"""
        is_async = asyncio.iscoroutinefunction(callback)

        hook = MigrationHook(
            name=name,
            version=version,
            trigger=trigger,
            callback=callback,
            priority=priority,
            is_async=is_async,
            description=description,
        )

        self.hooks[trigger].append(hook)
        # 按优先级排序 (高优先级在前)
        self.hooks[trigger].sort(key=lambda h: h.priority, reverse=True)

        logger.info(
            f"Registered hook: {name} (v{version}, {trigger.value}, "
            f"priority={priority})"
        )
        return hook

    def get_hooks(self, trigger: HookTrigger) -> List[MigrationHook]:
        """获取特定触发时机的所有 Hook"""
        return self.hooks[trigger]

    def get_hooks_for_version(
        self, version: str, trigger: HookTrigger
    ) -> List[MigrationHook]:
        """获取特定版本的 Hook"""
        return [
            h for h in self.hooks[trigger] if h.version == version
        ]

    async def execute_hooks(
        self,
        trigger: HookTrigger,
        version: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行 Hook"""
        if context is None:
            context = {}

        hooks = (
            self.get_hooks_for_version(version, trigger)
            if version
            else self.get_hooks(trigger)
        )

        results = {}

        for hook in hooks:
            try:
                logger.debug(
                    f"Executing hook: {hook.name} ({trigger.value})"
                )

                if hook.is_async:
                    result = await hook.callback(context)
                else:
                    result = hook.callback(context)

                results[hook.name] = result
                logger.debug(f"Hook {hook.name} completed successfully")

            except Exception as e:
                logger.error(
                    f"Error executing hook {hook.name}: {e}",
                    exc_info=True,
                )
                # 错误隔离 - 一个 Hook 失败不影响其他
                results[hook.name] = {"error": str(e)}

        self._hook_results[trigger.value] = results
        return results

    def get_results(self, trigger: HookTrigger) -> Dict[str, Any]:
        """获取 Hook 执行结果"""
        return self._hook_results.get(trigger.value, {})

    def clear_hooks(self, trigger: Optional[HookTrigger] = None):
        """清空 Hook"""
        if trigger:
            self.hooks[trigger].clear()
        else:
            for trigger_type in HookTrigger:
                self.hooks[trigger_type].clear()


class migration_hook:
    """装饰器: 注册数据迁移 Hook"""

    _registry: Optional[HookRegistry] = None

    def __init__(
        self,
        version: str,
        trigger: HookTrigger,
        priority: int = 0,
        description: Optional[str] = None,
    ):
        self.version = version
        self.trigger = trigger
        self.priority = priority
        self.description = description

    def __call__(self, func: Callable) -> Callable:
        """装饰器实现"""
        if self._registry is None:
            self._registry = HookRegistry()

        self._registry.register(
            name=func.__name__,
            version=self.version,
            trigger=self.trigger,
            callback=func,
            priority=self.priority,
            description=self.description,
        )

        return func

    @classmethod
    def get_registry(cls) -> HookRegistry:
        """获取全局 Hook 注册表"""
        if cls._registry is None:
            cls._registry = HookRegistry()
        return cls._registry

    @classmethod
    def set_registry(cls, registry: HookRegistry):
        """设置全局 Hook 注册表"""
        cls._registry = registry


# 便捷函数
def get_hook_registry() -> HookRegistry:
    """获取全局 Hook 注册表"""
    return migration_hook.get_registry()


def register_migration_hook(
    version: str,
    trigger: HookTrigger,
    callback: Callable,
    priority: int = 0,
    description: Optional[str] = None,
) -> MigrationHook:
    """直接注册 Hook (不使用装饰器)"""
    registry = get_hook_registry()
    return registry.register(
        name=callback.__name__,
        version=version,
        trigger=trigger,
        callback=callback,
        priority=priority,
        description=description,
    )
