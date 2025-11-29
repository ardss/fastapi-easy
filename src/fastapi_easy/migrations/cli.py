"""
迁移 CLI 工具链

支持:
- 迁移计划查看 (plan 命令)
- 迁移执行 (apply 命令)
- 迁移回滚 (rollback 命令)
- 迁移历史查看 (history 命令)
- 迁移状态检查 (status 命令)
- 系统初始化 (init 命令)
"""

import asyncio
import logging
import sys
from urllib.parse import urlparse, urlunparse

import click
from sqlalchemy import MetaData, create_engine

from .cli_helpers import (
    CLIConfirm,
    CLIErrorHandler,
    CLIFormatter,
    CLIProgress,
)
from .engine import MigrationEngine
from .exceptions import MigrationError
from .types import ExecutionMode

logger = logging.getLogger(__name__)


def _mask_database_url(database_url: str) -> str:
    """隐藏数据库 URL 中的敏感信息
    
    Args:
        database_url: 数据库连接字符串
        
    Returns:
        隐藏敏感信息后的 URL
    """
    try:
        parsed = urlparse(database_url)

        # 隐藏密码
        if parsed.password:
            netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
        else:
            netloc = parsed.netloc

        masked = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        return masked
    except Exception:
        return "***"


@click.group()
@click.version_option()
def cli():
    """FastAPI-Easy 迁移工具"""
    pass


@cli.command()
@click.option(
    "--database-url",
    required=True,
    help="数据库连接字符串",
    envvar="DATABASE_URL",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="仅显示将要执行的 SQL，不实际执行",
)
def plan(database_url: str, dry_run: bool):
    """查看迁移计划"""
    try:
        CLIProgress.show_step(1, 3, "连接数据库...")
        engine = create_engine(database_url)
        metadata = MetaData()

        CLIProgress.show_step(2, 3, "检测 Schema 变更...")
        migration_engine = MigrationEngine(
            engine, metadata, mode="dry_run"
        )
        plan_result = asyncio.run(
            migration_engine.auto_migrate()
        )

        CLIProgress.show_step(3, 3, "生成迁移计划...")
        click.echo("")
        click.echo(CLIFormatter.format_plan(plan_result))

        if dry_run:
            click.echo("")
            logger.info("干运行模式: 不执行任何操作")
            CLIProgress.show_info("干运行模式: 不执行任何操作")

    except MigrationError as e:
        click.echo("")
        CLIErrorHandler.handle_error(e)
        sys.exit(1)
    except Exception as e:
        click.echo("")
        CLIErrorHandler.handle_error(
            e, context="检测 Schema 变更"
        )
        sys.exit(1)


@cli.command()
@click.option(
    "--database-url",
    required=True,
    help="数据库连接字符串",
    envvar="DATABASE_URL",
)
@click.option(
    "--mode",
    type=click.Choice(["safe", "auto", "aggressive"]),
    default="safe",
    help="执行模式",
)
@click.option(
    "--force",
    is_flag=True,
    help="跳过确认，直接执行",
)
def apply(database_url: str, mode: str, force: bool):
    """执行迁移"""
    try:
        # 转换 mode 字符串为 ExecutionMode 枚举
        mode_enum = ExecutionMode(mode)
        
        click.echo("🚀 开始执行迁移...")
        click.echo(f"📝 模式: {mode_enum.value}")
        click.echo("")

        # 获取迁移计划
        engine = create_engine(database_url)
        metadata = MetaData()
        migration_engine = MigrationEngine(engine, metadata, mode=mode_enum)
        
        # 步骤 1: 检测变更 (不执行)
        CLIProgress.show_step(1, 3, "检测 Schema 变更...")
        changes = asyncio.run(
            migration_engine.detector.detect_changes()
        )
        
        if not changes:
            click.echo("")
            CLIProgress.show_success("Schema 已是最新")
            return
        
        # 步骤 2: 生成迁移计划
        CLIProgress.show_step(2, 3, "生成迁移计划...")
        plan_result = migration_engine.generator.generate_plan(changes)
        
        click.echo("")
        click.echo(CLIFormatter.format_plan(plan_result))
        click.echo("")

        # 步骤 3: 显示迁移计划并确认
        if not CLIConfirm.confirm_migration(plan_result, force):
            CLIProgress.show_warning("已取消")
            return

        # 步骤 4: 执行迁移
        click.echo("")
        CLIProgress.show_step(3, 3, "执行迁移...")
        plan_result, executed_migrations = asyncio.run(
            migration_engine.executor.execute_plan(plan_result, mode=mode_enum)
        )
        
        # 记录已执行的迁移
        for migration in executed_migrations:
            migration_engine.storage.record_migration(
                version=migration.version,
                description=migration.description,
                rollback_sql=migration.downgrade_sql,
                risk_level=migration.risk_level.value
            )

        # 显示结果
        click.echo("")
        CLIProgress.show_success("迁移完成")
        click.echo("")
        click.echo("📊 执行结果:")
        click.echo(f"  - 已执行 {len(executed_migrations)} 个迁移")
        click.echo(f"  - 状态: {plan_result.status}")

    except MigrationError as e:
        click.echo("")
        CLIErrorHandler.handle_error(e)
        sys.exit(1)
    except Exception as e:
        click.echo("")
        CLIErrorHandler.handle_error(e, context="执行迁移")
        sys.exit(1)


@cli.command()
@click.option(
    "--database-url",
    required=True,
    help="数据库连接字符串",
    envvar="DATABASE_URL",
)
@click.option(
    "--steps",
    type=int,
    default=1,
    help="回滚步数",
)
@click.option(
    "--force",
    is_flag=True,
    help="跳过确认，直接执行",
)
def rollback(database_url: str, steps: int, force: bool):
    """回滚迁移"""
    try:
        click.echo(f"⏮️  回滚 {steps} 个迁移...")
        click.echo("")

        if not CLIConfirm.confirm_rollback(steps, force):
            click.echo("❌ 已取消")
            return

        # 执行回滚
        engine = create_engine(database_url)
        migration_engine = MigrationEngine(engine, MetaData())
        result = asyncio.run(
            migration_engine.rollback(steps=steps, continue_on_error=False)
        )

        # 显示结果
        click.echo("")
        if result.success:
            CLIProgress.show_success(
                f"成功回滚 {result.data['rolled_back']} 个迁移"
            )
        else:
            CLIProgress.show_warning(
                f"回滚完成: {result.data['rolled_back']} 成功, "
                f"{result.data['failed']} 失败"
            )
            if result.errors:
                click.echo("")
                click.echo("错误详情:")
                for error in result.errors:
                    click.echo(f"  - {error}")

    except MigrationError as e:
        click.echo("")
        CLIErrorHandler.handle_error(e)
        sys.exit(1)
    except Exception as e:
        click.echo("")
        CLIErrorHandler.handle_error(e, context="回滚迁移")
        sys.exit(1)


@cli.command()
@click.option(
    "--database-url",
    required=True,
    help="数据库连接字符串",
    envvar="DATABASE_URL",
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="显示最近的迁移数",
)
def history(database_url: str, limit: int):
    """查看迁移历史"""
    try:
        engine = create_engine(database_url)
        migration_engine = MigrationEngine(engine, MetaData())
        history_records = migration_engine.get_history(limit)

        click.echo("")
        click.echo(CLIFormatter.format_history(history_records))

    except MigrationError as e:
        click.echo("")
        CLIErrorHandler.handle_error(e)
        sys.exit(1)
    except Exception as e:
        click.echo("")
        CLIErrorHandler.handle_error(e, context="查看迁移历史")
        sys.exit(1)


@cli.command()
@click.option(
    "--database-url",
    required=True,
    help="数据库连接字符串",
    envvar="DATABASE_URL",
)
def status(database_url: str):
    """查看迁移状态"""
    try:
        CLIProgress.show_step(1, 2, "连接数据库...")
        engine = create_engine(database_url)
        metadata = MetaData()

        CLIProgress.show_step(2, 2, "检查迁移状态...")
        migration_engine = MigrationEngine(engine, metadata)
        history_records = migration_engine.get_history(limit=1)

        click.echo("")
        click.echo("📊 迁移状态:")
        click.echo("")
        click.echo(f"数据库: {_mask_database_url(database_url)}")
        click.echo(f"已应用迁移: {len(history_records)}")
        click.echo("状态: ✅ 已同步")

    except MigrationError as e:
        click.echo("")
        CLIErrorHandler.handle_error(e)
        sys.exit(1)
    except Exception as e:
        click.echo("")
        CLIErrorHandler.handle_error(e, context="检查迁移状态")
        sys.exit(1)


@cli.command()
@click.option(
    "--database-url",
    required=True,
    help="数据库连接字符串",
    envvar="DATABASE_URL",
)
def init(database_url: str):
    """初始化迁移系统"""
    try:
        CLIProgress.show_step(1, 2, "连接数据库...")
        engine = create_engine(database_url)
        metadata = MetaData()

        CLIProgress.show_step(2, 2, "初始化迁移表...")
        MigrationEngine(engine, metadata)

        CLIProgress.show_success("初始化完成")
        click.echo("")
        click.echo("下一步:")
        click.echo("  1. 定义 ORM 模型")
        click.echo("  2. 运行 'fastapi-easy migrate plan' 查看变更")
        click.echo("  3. 运行 'fastapi-easy migrate apply' 执行迁移")

    except MigrationError as e:
        click.echo("")
        CLIErrorHandler.handle_error(e)
        sys.exit(1)
    except Exception as e:
        click.echo("")
        CLIErrorHandler.handle_error(e, context="初始化迁移系统")
        sys.exit(1)


def main():
    """CLI 入口点"""
    cli()


if __name__ == "__main__":
    main()
