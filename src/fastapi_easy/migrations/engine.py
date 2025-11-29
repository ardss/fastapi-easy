import asyncio
import logging
from typing import Optional

from sqlalchemy import Engine

from .detector import SchemaDetector
from .distributed_lock import get_lock_provider
from .executor import MigrationExecutor
from .generator import MigrationGenerator
from .hooks import HookTrigger, get_hook_registry
from .storage import MigrationStorage
from .types import ExecutionMode, MigrationPlan, OperationResult

logger = logging.getLogger(__name__)

class MigrationEngine:
    """The main entry point for the migration system"""
    
    def __init__(
        self,
        engine: Engine,
        metadata,
        mode: ExecutionMode = ExecutionMode.SAFE
    ):
        """Initialize the migration engine

        Args:
            engine: SQLAlchemy engine
            metadata: SQLAlchemy metadata
            mode: Execution mode (SAFE, DRY_RUN, FORCE)
        """
        if not isinstance(mode, ExecutionMode):
            raise TypeError(
                f"mode must be ExecutionMode enum, "
                f"got {type(mode).__name__}"
            )

        self.engine = engine
        self.metadata = metadata
        self.mode = mode
        self.detector = SchemaDetector(engine, metadata)
        self.generator = MigrationGenerator(engine)
        self.executor = MigrationExecutor(engine)
        self.storage = MigrationStorage(engine)
        self.lock = get_lock_provider(engine)

        # Initialize storage
        self.storage.initialize()

    async def auto_migrate(self) -> MigrationPlan:
        """Automatically detect and apply migrations"""

        # 1. Acquire Lock
        logger.info("获取迁移锁...")
        if not await self.lock.acquire():
            logger.warning("无法获取锁，假设另一个实例正在迁移")
            return MigrationPlan(migrations=[], status="locked")

        try:
            # 2. Execute BEFORE_DDL Hook
            hook_registry = get_hook_registry()
            await hook_registry.execute_hooks(
                HookTrigger.BEFORE_DDL,
                context={"mode": self.mode}
            )

            logger.info("检测 Schema 变更...")

            # 3. Detect changes
            changes = await self.detector.detect_changes()

            if not changes:
                logger.info("Schema 已同步")
                return MigrationPlan(migrations=[], status="up_to_date")

            logger.info(f"检测到 {len(changes)} 个变更")

            # 4. Generate plan
            plan = self.generator.generate_plan(changes)

            # 5. Log plan
            for migration in plan.migrations:
                logger.info(
                    f"  [{migration.risk_level.value}] "
                    f"{migration.description}"
                )

            # 6. Execute migrations
            logger.info(f"执行迁移 (模式: {self.mode})")
            plan, executed_migrations = await self.executor.execute_plan(
                plan, mode=self.mode
            )

            # 7. Execute AFTER_DDL Hook
            await hook_registry.execute_hooks(
                HookTrigger.AFTER_DDL,
                context={
                    "plan": plan,
                    "executed": executed_migrations,
                    "status": plan.status
                }
            )

            # 8. Record successfully executed migrations
            for migration in executed_migrations:
                self.storage.record_migration(
                    version=migration.version,
                    description=migration.description,
                    rollback_sql=migration.downgrade_sql,
                    risk_level=migration.risk_level.value
                )

            logger.info(f"迁移完成: {plan.status}")
            return plan

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"迁移失败: {error_msg}\n"
                f"调试步骤:\n"
                f"  1. 检查数据库连接\n"
                f"  2. 查看详细日志: 设置 LOG_LEVEL=DEBUG\n"
                f"  3. 运行 dry-run 模式\n"
                f"  4. 查看完整错误: {error_msg}",
                exc_info=True
            )
            raise
        finally:
            # 7. Release Lock with retry
            logger.info("释放迁移锁...")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.lock.release()
                    logger.info("迁移锁已释放")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"锁释放失败 (尝试 {attempt + 1}/{max_retries}), "
                            f"重试中..."
                        )
                        await asyncio.sleep(1)
                    else:
                        logger.error(
                            f"锁释放失败: {e}\n"
                            f"您可能需要手动清理锁文件。\n"
                            f"解决方案:\n"
                            f"  1. 检查锁文件: .fastapi_easy_migration.lock\n"
                            f"  2. 手动删除: rm .fastapi_easy_migration.lock\n"
                            f"  3. 重新运行迁移",
                            exc_info=True
                        )
    
    def get_history(self, max_items: int = 10):
        """Get migration history
        
        Args:
            max_items: Maximum number of migration records to return
        """
        return self.storage.get_migration_history(limit=max_items)
    
    async def rollback(self, steps: int = 1, continue_on_error: bool = False) -> OperationResult:
        """
        回滚指定数量的迁移
        
        Args:
            steps: 要回滚的迁移数量
            continue_on_error: 是否在错误时继续回滚
        
        Returns:
            OperationResult with:
                success: bool
                data: {
                    'rolled_back': int,  # 成功回滚的数量
                    'failed': int,       # 失败的数量
                }
                errors: [...]  # 错误列表
        """
        result = OperationResult(success=False)
        
        # 验证参数
        if steps <= 0:
            logger.error("❌ 回滚步数必须大于 0")
            result.add_error("回滚步数必须大于 0")
            return result
        
        # 获取迁移历史
        history = self.storage.get_migration_history(limit=steps)
        
        if not history:
            logger.warning("⚠️ 没有可回滚的迁移")
            result.add_error("没有可回滚的迁移")
            return result
        
        # 获取锁
        logger.info(f"🔒 获取迁移锁...")
        if not await self.lock.acquire():
            logger.warning("⏳ 无法获取锁，假设另一个实例正在迁移")
            result.add_error("无法获取迁移锁")
            return result
        
        try:
            logger.info(f"⏮️ 准备回滚 {len(history)} 个迁移...")
            
            # 按相反顺序执行回滚
            for record in reversed(history):
                version = record.get("version")
                description = record.get("description", "Unknown")
                rollback_sql = record.get("rollback_sql")
                
                if not rollback_sql:
                    logger.warning(f"⚠️ 迁移 {version} 没有回滚 SQL，跳过")
                    continue
                
                try:
                    logger.info(f"  回滚 {version}: {description}")
                    
                    # 执行回滚 SQL
                    from sqlalchemy import text
                    with self.engine.begin() as conn:
                        for statement in rollback_sql.split(";"):
                            statement = statement.strip()
                            if statement:
                                conn.execute(text(statement))
                    
                    logger.info(f"  ✅ 成功回滚 {version}")
                    if result.data is None:
                        result.data = {'rolled_back': 0, 'failed': 0}
                    result.data['rolled_back'] += 1
                
                except Exception as e:
                    logger.error(f"  ❌ 回滚 {version} 失败: {e}")
                    if result.data is None:
                        result.data = {'rolled_back': 0, 'failed': 0}
                    result.data['failed'] += 1
                    result.add_error(f"{version}: {str(e)}")
                    
                    if not continue_on_error:
                        raise
                    else:
                        logger.warning(f"继续回滚下一个迁移...")
            
            if result.data is None:
                result.data = {'rolled_back': 0, 'failed': 0}
            result.success = result.data['failed'] == 0
            if result.success:
                logger.info(f"✅ 成功回滚 {result.data['rolled_back']} 个迁移")
            else:
                logger.warning(f"⚠️ 回滚完成: {result.data['rolled_back']} 成功, {result.data['failed']} 失败")
            
            return result
        
        except Exception as e:
            logger.error(f"❌ 回滚失败: {e}", exc_info=True)
            result.add_error(str(e))
            return result
        
        finally:
            # 释放锁 (带重试机制)
            logger.info("释放迁移锁...")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.lock.release()
                    logger.info("迁移锁已释放")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"锁释放失败 (尝试 {attempt + 1}/{max_retries}), "
                            f"重试中..."
                        )
                        await asyncio.sleep(1)
                    else:
                        logger.error(f"锁释放失败: {e}")
