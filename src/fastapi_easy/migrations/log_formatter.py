"""
统一的日志格式化器

提供一致的日志格式和语言
"""

import logging


class MigrationLogFormatter(logging.Formatter):
    """迁移系统统一的日志格式化器"""

    # 日志级别颜色和图标
    LEVEL_ICONS = {
        logging.DEBUG: "🔍",
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "🔴",
    }

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录
        
        格式: [LEVEL] ICON MESSAGE
        """
        # 获取日志级别图标
        icon = self.LEVEL_ICONS.get(record.levelno, "")
        
        # 构建日志消息
        message = record.getMessage()
        
        # 格式化输出
        formatted = f"{icon} {message}"
        
        # 添加异常信息
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


def setup_migration_logging(
    logger_name: str = "fastapi_easy.migrations",
    level: int = logging.INFO,
) -> logging.Logger:
    """设置迁移系统的日志
    
    Args:
        logger_name: 日志记录器名称
        level: 日志级别
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # 移除现有处理器
    logger.handlers.clear()
    
    # 创建控制台处理器
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    # 设置格式化器
    formatter = MigrationLogFormatter()
    handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(handler)
    
    return logger


# 预定义的日志消息
class LogMessages:
    """统一的日志消息"""
    
    # 检测阶段
    DETECTING_CHANGES = "检测 Schema 变更..."
    CHANGES_DETECTED = "检测到 {count} 个 Schema 变更"
    NO_CHANGES = "Schema 已是最新"
    
    # 生成阶段
    GENERATING_PLAN = "生成迁移计划..."
    PLAN_GENERATED = "生成了 {count} 个迁移"
    
    # 执行阶段
    EXECUTING_MIGRATIONS = "执行迁移..."
    EXECUTING_SAFE = "执行 {count} 个低风险迁移..."
    EXECUTING_MEDIUM = "执行 {count} 个中等风险迁移..."
    EXECUTING_HIGH = "执行 {count} 个高风险迁移..."
    
    # 成功消息
    MIGRATION_SUCCESS = "迁移成功: {description}"
    EXECUTION_COMPLETE = "迁移完成: {status}"
    ROLLBACK_SUCCESS = "成功回滚 {count} 个迁移"
    
    # 警告消息
    HIGH_RISK_MIGRATIONS = "{count} 个高风险迁移需要手动审查"
    SKIPPED_MIGRATION = "跳过迁移: {reason}"
    
    # 错误消息
    MIGRATION_FAILED = "迁移失败: {error}"
    DETECTION_TIMEOUT = "Schema 检测超时 (超过 {timeout}s)"
    LOCK_ACQUISITION_FAILED = "无法获取迁移锁"
    LOCK_RELEASE_FAILED = "锁释放失败: {error}"
    
    # 锁相关
    ACQUIRING_LOCK = "获取迁移锁..."
    LOCK_ACQUIRED = "迁移锁已获取"
    RELEASING_LOCK = "释放迁移锁..."
    LOCK_RELEASED = "迁移锁已释放"
