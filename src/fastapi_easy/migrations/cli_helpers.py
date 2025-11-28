"""
CLI 辅助模块

提供 CLI 命令的通用功能：
- 错误处理和显示
- 用户提示和确认
- 迁移信息格式化
"""

import sys
from typing import List

import click

from .exceptions import MigrationError
from .types import Migration, MigrationPlan, RiskLevel


class CLIErrorHandler:
    """CLI 错误处理器"""

    @staticmethod
    def handle_error(error: Exception, context: str = "") -> None:
        """处理并显示错误"""
        if isinstance(error, MigrationError):
            click.echo(f"❌ {error.get_full_message()}", err=True)
        else:
            if context:
                message = f"❌ {context}: {str(error)}"
            else:
                message = f"❌ {str(error)}"
            click.echo(message, err=True)

    @staticmethod
    def exit_with_error(message: str, code: int = 1) -> None:
        """显示错误并退出"""
        click.echo(f"❌ {message}", err=True)
        sys.exit(code)


class CLIFormatter:
    """CLI 输出格式化器"""

    @staticmethod
    def format_migration(migration: Migration) -> str:
        """格式化单个迁移"""
        risk_icon = {
            RiskLevel.SAFE: "✅",
            RiskLevel.MEDIUM: "⚠️",
            RiskLevel.HIGH: "🔴",
        }.get(migration.risk_level, "❓")

        return (
            f"{risk_icon} [{migration.risk_level.value:6}] "
            f"{migration.version} - {migration.description}"
        )

    @staticmethod
    def format_plan(plan: MigrationPlan) -> str:
        """格式化迁移计划"""
        if not plan.migrations:
            return "无待处理的迁移"

        lines = [f"检测到 {len(plan.migrations)} 个迁移:"]
        for migration in plan.migrations:
            lines.append(f"  {CLIFormatter.format_migration(migration)}")

        return "\n".join(lines)

    @staticmethod
    def format_history(history: List[dict]) -> str:
        """格式化迁移历史"""
        if not history:
            return "无迁移历史"

        lines = ["迁移历史:"]
        lines.append(
            "版本        | 描述              | 状态    | 时间"
        )
        lines.append("-" * 60)

        for record in history:
            version = record.get("version", "")[:12]
            description = record.get("description", "")[:15]
            status = record.get("status", "")[:6]
            applied_at = str(record.get("applied_at", ""))[:10]

            lines.append(
                f"{version:12} | {description:15} | "
                f"{status:6} | {applied_at}"
            )

        return "\n".join(lines)


class CLIConfirm:
    """CLI 确认对话框"""

    @staticmethod
    def confirm_migration(
        plan: MigrationPlan, force: bool = False
    ) -> bool:
        """确认执行迁移"""
        if force:
            return True

        click.echo("⚠️  这将执行以下迁移:")
        for migration in plan.migrations:
            click.echo(f"  {CLIFormatter.format_migration(migration)}")
        click.echo("")

        return click.confirm("是否继续?")

    @staticmethod
    def confirm_rollback(steps: int, force: bool = False) -> bool:
        """确认回滚迁移"""
        if force:
            return True

        click.echo(f"⚠️  这将回滚 {steps} 个迁移")
        click.echo("⚠️  数据可能会丢失，请确保已备份")
        click.echo("")

        return click.confirm("是否继续?")

    @staticmethod
    def confirm_clear_cache(force: bool = False) -> bool:
        """确认清理缓存"""
        if force:
            return True

        click.echo("⚠️  这将清理所有缓存文件")
        return click.confirm("是否继续?")


class CLIProgress:
    """CLI 进度显示"""

    @staticmethod
    def show_step(step: int, total: int, message: str) -> None:
        """显示步骤进度"""
        click.echo(f"[{step}/{total}] {message}")

    @staticmethod
    def show_success(message: str) -> None:
        """显示成功消息"""
        click.echo(f"✅ {message}")

    @staticmethod
    def show_warning(message: str) -> None:
        """显示警告消息"""
        click.echo(f"⚠️  {message}")

    @staticmethod
    def show_info(message: str) -> None:
        """显示信息消息"""
        click.echo(f"ℹ️  {message}")
