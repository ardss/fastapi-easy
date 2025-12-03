"""
迁移系统统一的配置管理

提供集中的配置类和验证
"""

from dataclasses import dataclass


@dataclass
class MigrationConfig:
    """迁移系统统一的配置类"""

    # 执行配置
    mode: str = "safe"
    """执行模式: safe, auto, aggressive, dry_run"""

    auto_backup: bool = False
    """是否自动备份数据库"""

    # 检测配置
    timeout_seconds: int = 60
    """Schema 检测超时时间 (秒)"""

    auto_validate_schema: bool = True
    """是否在启动时自动验证 Schema"""

    # 锁配置
    lock_timeout_seconds: int = 300
    """获取迁移锁的超时时间 (秒)"""

    lock_retry_count: int = 3
    """获取迁移锁的重试次数"""

    lock_retry_delay_seconds: float = 1.0
    """获取迁移锁的重试延迟 (秒)"""

    # 存储配置
    migration_table_name: str = "alembic_version"
    """迁移历史表名称"""

    # 日志配置
    log_level: str = "INFO"
    """日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL"""

    log_format: str = "emoji"
    """日志格式: emoji, plain, json"""

    # 性能配置
    batch_size: int = 100
    """批量操作的批次大小"""

    max_workers: int = 4
    """最大并发工作线程数"""

    # 验证配置
    strict_mode: bool = False
    """严格模式: 任何错误都会导致迁移失败"""

    continue_on_error: bool = False
    """是否在错误时继续执行"""

    def validate(self) -> None:
        """验证配置的有效性

        Raises:
            ValueError: 配置无效时抛出异常
        """
        # 验证执行模式
        valid_modes = {"safe", "auto", "aggressive", "dry_run"}
        if self.mode not in valid_modes:
            raise ValueError(f"Invalid mode '{self.mode}'. " f"Must be one of {valid_modes}")

        # 验证超时时间
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be > 0, got {self.timeout_seconds}")

        if self.lock_timeout_seconds <= 0:
            raise ValueError(
                f"lock_timeout_seconds must be > 0, " f"got {self.lock_timeout_seconds}"
            )

        # 验证重试配置
        if self.lock_retry_count < 0:
            raise ValueError(f"lock_retry_count must be >= 0, " f"got {self.lock_retry_count}")

        if self.lock_retry_delay_seconds < 0:
            raise ValueError(
                f"lock_retry_delay_seconds must be >= 0, " f"got {self.lock_retry_delay_seconds}"
            )

        # 验证日志级别
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(
                f"Invalid log_level '{self.log_level}'. " f"Must be one of {valid_levels}"
            )

        # 验证日志格式
        valid_formats = {"emoji", "plain", "json"}
        if self.log_format not in valid_formats:
            raise ValueError(
                f"Invalid log_format '{self.log_format}'. " f"Must be one of {valid_formats}"
            )

        # 验证批次大小
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be > 0, got {self.batch_size}")

        # 验证最大工作线程数
        if self.max_workers <= 0:
            raise ValueError(f"max_workers must be > 0, got {self.max_workers}")

        # 验证互斥选项
        if self.strict_mode and self.continue_on_error:
            raise ValueError("strict_mode and continue_on_error are mutually exclusive")

    def to_dict(self) -> dict:
        """转换为字典

        Returns:
            配置字典
        """
        return {
            "mode": self.mode,
            "auto_backup": self.auto_backup,
            "timeout_seconds": self.timeout_seconds,
            "auto_validate_schema": self.auto_validate_schema,
            "lock_timeout_seconds": self.lock_timeout_seconds,
            "lock_retry_count": self.lock_retry_count,
            "lock_retry_delay_seconds": self.lock_retry_delay_seconds,
            "migration_table_name": self.migration_table_name,
            "log_level": self.log_level,
            "log_format": self.log_format,
            "batch_size": self.batch_size,
            "max_workers": self.max_workers,
            "strict_mode": self.strict_mode,
            "continue_on_error": self.continue_on_error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MigrationConfig":
        """从字典创建配置

        Args:
            data: 配置字典

        Returns:
            MigrationConfig 实例
        """
        return cls(**data)

    def __repr__(self) -> str:
        """返回字符串表示"""
        items = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"MigrationConfig({items})"

    @classmethod
    def from_file(cls, filepath: str) -> "MigrationConfig":
        """从配置文件加载配置

        Args:
            filepath: 配置文件路径 (JSON 或 YAML)

        Returns:
            MigrationConfig 实例

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持
        """
        import json
        import os

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"配置文件不存在: {filepath}")

        # 根据文件扩展名选择解析方式
        if filepath.endswith(".json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif filepath.endswith((".yaml", ".yml")):
            try:
                import yaml

                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except ImportError:
                raise ValueError("YAML 支持需要安装 PyYAML: pip install pyyaml")
        else:
            raise ValueError(f"不支持的文件格式: {filepath}. " f"支持的格式: .json, .yaml, .yml")

        return cls.from_dict(data)

    def to_file(self, filepath: str) -> None:
        """保存配置到文件

        Args:
            filepath: 配置文件路径 (JSON 或 YAML)

        Raises:
            ValueError: 文件格式不支持
        """
        import json
        import os

        # 创建目录如果不存在
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        # 根据文件扩展名选择保存方式
        if filepath.endswith(".json"):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        elif filepath.endswith((".yaml", ".yml")):
            try:
                import yaml

                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.dump(self.to_dict(), f, default_flow_style=False)
            except ImportError:
                raise ValueError("YAML 支持需要安装 PyYAML: pip install pyyaml")
        else:
            raise ValueError(f"不支持的文件格式: {filepath}. " f"支持的格式: .json, .yaml, .yml")

    def merge(self, other: "MigrationConfig") -> "MigrationConfig":
        """合并两个配置

        Args:
            other: 另一个配置对象

        Returns:
            合并后的新配置对象 (当前配置作为基础)
        """
        merged_dict = self.to_dict()
        other_dict = other.to_dict()

        # 合并配置，other 的值覆盖 self 的值
        merged_dict.update(other_dict)

        return self.from_dict(merged_dict)


# 默认配置实例
DEFAULT_CONFIG = MigrationConfig()
