"""
迁移系统异常定义

统一的异常类型，便于错误处理和诊断
"""
import re


def _sanitize_error_message(error: str) -> str:
    """清理错误消息中的敏感信息
    
    Args:
        error: 原始错误消息
        
    Returns:
        清理后的错误消息
    """
    # 移除数据库连接信息
    sanitized = re.sub(
        r'(password|passwd|pwd)\s*=\s*[^\s,;]+',
        r'\1=***',
        error,
        flags=re.IGNORECASE
    )

    # 移除 IP 地址和主机名
    sanitized = re.sub(
        r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        '***',
        sanitized
    )

    return sanitized


class MigrationError(Exception):
    """迁移系统基础异常"""

    def __init__(self, message: str, suggestion: str = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)

    def get_full_message(self) -> str:
        """获取完整错误消息（包含建议）"""
        if self.suggestion:
            return f"{self.message}\n\n💡 建议: {self.suggestion}"
        return self.message


class DatabaseConnectionError(MigrationError):
    """数据库连接错误"""

    def __init__(self, database_url: str, original_error: Exception):
        message = f"无法连接到数据库: {database_url}"
        suggestion = (
            "解决方案:\n"
            "  1. 检查数据库连接字符串\n"
            "  2. 确保数据库服务正在运行\n"
            "  3. 检查网络连接\n"
            f"  4. 原始错误: {str(original_error)}"
        )
        super().__init__(message, suggestion)


class SchemaDetectionError(MigrationError):
    """Schema 检测错误"""

    def __init__(self, reason: str, timeout: int = None):
        if timeout:
            message = f"Schema 检测超时 (超过 {timeout}s)"
            suggestion = (
                "解决方案:\n"
                "  1. 增加超时时间:\n"
                "     detector = SchemaDetector(engine, metadata)\n"
                "     changes = await detector.detect_changes(timeout=120)\n"
                "  2. 检查数据库性能\n"
                "  3. 检查网络延迟"
            )
        else:
            message = f"Schema 检测失败: {reason}"
            suggestion = (
                "解决方案:\n"
                "  1. 检查数据库连接\n"
                "  2. 检查 ORM 模型定义\n"
                "  3. 查看详细日志: 设置 LOG_LEVEL=DEBUG"
            )
        super().__init__(message, suggestion)


class MigrationExecutionError(MigrationError):
    """迁移执行错误"""

    def __init__(self, migration_version: str, sql_error: str):
        message = f"迁移执行失败 (版本: {migration_version})"
        
        # 根据错误类型提供具体建议
        if "permission" in sql_error.lower():
            suggestion = (
                "权限错误 - 解决方案:\n"
                "  1. 检查数据库用户权限\n"
                "  2. 确保用户有 ALTER TABLE 权限\n"
                "  3. 重新运行迁移"
            )
        elif "table" in sql_error.lower() and "not exist" in sql_error.lower():
            suggestion = (
                "表不存在 - 解决方案:\n"
                "  1. 运行 'fastapi-easy migrate init' 初始化\n"
                "  2. 检查数据库连接\n"
                "  3. 重新运行迁移"
            )
        elif "syntax" in sql_error.lower():
            suggestion = (
                "SQL 语法错误 - 解决方案:\n"
                "  1. 检查 ORM 模型定义\n"
                "  2. 查看生成的 SQL: fastapi-easy migrate plan --dry-run\n"
                "  3. 报告 issue: https://github.com/fastapi-easy/issues"
            )
        else:
            suggestion = (
                "调试步骤:\n"
                "  1. 查看详细日志: 设置 LOG_LEVEL=DEBUG\n"
                "  2. 运行 dry-run: fastapi-easy migrate plan --dry-run\n"
                "  3. 检查数据库状态: fastapi-easy migrate status\n"
                f"  4. 原始错误: {sql_error}"
            )
        
        super().__init__(message, suggestion)


class LockAcquisitionError(MigrationError):
    """锁获取错误"""

    def __init__(self, lock_type: str, lock_info: dict = None):
        message = f"无法获取迁移锁 ({lock_type})"
        suggestion = (
            "原因: 另一个实例正在执行迁移\n\n"
            "解决方案:\n"
            "  1. 等待另一个实例完成 (通常需要几分钟)\n"
            "  2. 如果卡住，手动清理锁:\n"
        )
        
        if lock_type == "file":
            suggestion += f"     rm {lock_info.get('file', '.fastapi_easy_migration.lock')}\n"
        elif lock_type == "postgresql":
            suggestion += f"     SELECT pg_advisory_unlock({lock_info.get('id', 1)})\n"
        elif lock_type == "mysql":
            suggestion += f"     SELECT RELEASE_LOCK('{lock_info.get('name', 'fastapi_easy_migration')}')\n"
        
        suggestion += "  3. 重新运行迁移"
        
        super().__init__(message, suggestion)


class StorageError(MigrationError):
    """迁移存储错误"""

    def __init__(self, operation: str, reason: str):
        message = f"迁移历史记录失败 ({operation})"
        suggestion = (
            "解决方案:\n"
            "  1. 检查迁移表是否存在\n"
            "  2. 检查数据库权限\n"
            "  3. 运行初始化: fastapi-easy migrate init\n"
            f"  4. 原始错误: {reason}"
        )
        super().__init__(message, suggestion)


class CacheError(MigrationError):
    """缓存错误"""

    def __init__(self, operation: str, reason: str):
        message = f"缓存操作失败 ({operation})"
        
        if "permission" in reason.lower():
            suggestion = (
                "权限错误 - 解决方案:\n"
                "  1. 检查缓存目录权限\n"
                "  2. 确保有读写权限\n"
                "  3. 清理缓存: fastapi-easy cache clear"
            )
        elif "corrupted" in reason.lower() or "json" in reason.lower():
            suggestion = (
                "缓存文件损坏 - 解决方案:\n"
                "  1. 清理缓存: fastapi-easy cache clear\n"
                "  2. 重新运行迁移"
            )
        else:
            suggestion = (
                "缓存将被禁用，但迁移将继续进行\n"
                "解决方案:\n"
                "  1. 检查磁盘空间\n"
                "  2. 检查缓存目录权限\n"
                "  3. 查看详细日志: 设置 LOG_LEVEL=DEBUG"
            )
        
        super().__init__(message, suggestion)


class RiskAssessmentError(MigrationError):
    """风险评估错误"""

    def __init__(self, rule_name: str, reason: str):
        message = f"风险规则执行失败: {rule_name}"
        suggestion = (
            "处理方式: 跳过此规则，继续评估其他规则\n\n"
            "解决方案:\n"
            "  1. 检查规则实现是否正确\n"
            "  2. 查看详细日志: 设置 LOG_LEVEL=DEBUG\n"
            "  3. 报告 issue: https://github.com/fastapi-easy/issues\n"
            f"  4. 原始错误: {reason}"
        )
        super().__init__(message, suggestion)
