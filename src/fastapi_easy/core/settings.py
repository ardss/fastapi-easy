"""
统一配置管理系统

提供类型安全、环境感知、可验证的配置管理。
支持配置继承、默认值设置和配置验证。
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, get_type_hints

try:
    import yaml
except ImportError:
    yaml = None
    # yaml is optional - if not available, YAML config files won't be supported

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseSettings")


class ConfigSource(Enum):
    """配置来源"""

    DEFAULT = "default"
    ENV = "environment"
    FILE = "file"
    ARGS = "arguments"


@dataclass
class ConfigField:
    """配置字段定义"""

    name: Optional[str] = None  # Will be set automatically when used in dataclasses
    type: Optional[Type[Any]] = None  # Will be inferred from type hint
    default: Any = None
    required: bool = True
    description: str = ""
    env_var: Optional[str] = None
    choices: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    validator: Optional[Callable[[Any], bool]] = None


class BaseSettings(ABC):
    """
    基础配置类

    提供配置加载、验证和类型转换功能。
    """

    def __init__(self, **kwargs: Any) -> None:
        """初始化配置"""
        self._config_data: Dict[str, Any] = {}
        self._load_config(**kwargs)

    def _load_config(self, **kwargs: Any) -> None:
        """加载配置"""
        # 1. 加载默认值
        self._load_defaults()

        # 2. 从配置文件加载
        self._load_from_file()

        # 3. 从环境变量加载
        self._load_from_env()

        # 4. 从参数加载（最高优先级）
        self._config_data.update(kwargs)

        # 5. 验证配置
        self._validate_config()

    def _load_defaults(self) -> None:
        """加载默认值"""
        for field_info in self._get_config_fields():
            if field_info.default is not None:
                self._config_data[field_info.name] = field_info.default

    def _load_from_file(self) -> None:
        """从配置文件加载"""
        config_file = os.environ.get("FASTAPI_EASY_CONFIG_FILE")
        if not config_file:
            return

        config_path = Path(config_file)
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_file}")
            return

        try:
            with open(config_path, encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif config_path.suffix.lower() == ".json":
                    data = json.load(f)
                else:
                    logger.warning(f"Unsupported config file format: {config_path.suffix}")
                    return

            if data:
                self._config_data.update(data.get(self.__class__.__name__.lower(), {}))

        except Exception as e:
            logger.error(f"Failed to load config file {config_file}: {e}")

    def _load_from_env(self):
        """从环境变量加载"""
        for field_info in self._get_config_fields():
            env_var = field_info.env_var or f"FASTAPI_EASY_{field_info.name.upper()}"
            env_value = os.getenv(env_var)

            if env_value is not None:
                # 类型转换
                try:
                    converted_value = self._convert_value(env_value, field_info.type)
                    self._config_data[field_info.name] = converted_value
                except ValueError as e:
                    logger.error(f"Invalid environment variable {env_var}: {e}")

    def _convert_value(self, value: str, target_type: Type) -> Any:
        """类型转换"""
        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == list:
            return value.split(",")
        else:
            return value

    def _validate_config(self):
        """验证配置"""
        for field_info in self._get_config_fields():
            value = self._config_data.get(field_info.name)

            # 检查必填字段
            if field_info.required and value is None:
                raise ValueError(f"Required field '{field_info.name}' is missing")

            if value is None:
                continue

            # 类型检查
            if not isinstance(value, field_info.type):
                try:
                    value = field_info.type(value)
                    self._config_data[field_info.name] = value
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Field '{field_info.name}' must be of type {field_info.type.__name__}"
                    ) from e

            # 选择项检查
            if field_info.choices and value not in field_info.choices:
                raise ValueError(
                    f"Field '{field_info.name}' must be one of {field_info.choices}, got {value}"
                )

            # 数值范围检查
            if isinstance(value, (int, float)):
                if field_info.min_value is not None and value < field_info.min_value:
                    raise ValueError(
                        f"Field '{field_info.name}' must be >= {field_info.min_value}, got {value}"
                    )
                if field_info.max_value is not None and value > field_info.max_value:
                    raise ValueError(
                        f"Field '{field_info.name}' must be <= {field_info.max_value}, got {value}"
                    )

            # 自定义验证
            if field_info.validator:
                try:
                    field_info.validator(value)
                except Exception as e:
                    raise ValueError(f"Validation failed for field '{field_info.name}': {e}") from e

    @classmethod
    def _get_config_fields(cls) -> List[ConfigField]:
        """获取配置字段定义"""
        if not hasattr(cls, "_config_fields"):
            cls._config_fields = cls._build_config_fields()
        return cls._config_fields

    @classmethod
    def _build_config_fields(cls) -> List[ConfigField]:
        """构建配置字段定义"""
        config_fields = []
        type_hints = get_type_hints(cls)

        # 从类属性获取配置定义
        for attr_name, attr_value in cls.__dict__.items():
            if isinstance(attr_value, ConfigField):
                config_field = attr_value
                config_field.name = attr_name
                if config_field.type is Any and attr_name in type_hints:
                    config_field.type = type_hints[attr_name]
                config_fields.append(config_field)

        return config_fields

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config_data.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置值"""
        self._config_data[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self._config_data.copy()

    @classmethod
    def from_file(cls: Type[T], config_file: str) -> T:
        """从文件创建配置"""
        os.environ["FASTAPI_EASY_CONFIG_FILE"] = config_file
        return cls()

    @classmethod
    def from_dict(cls: Type[T], config_data: Dict[str, Any]) -> T:
        """从字典创建配置"""
        return cls(**config_data)


@dataclass
class DatabaseConfig(BaseSettings):
    """数据库配置"""

    host: str = ConfigField(
        type=str, default="localhost", description="Database host", env_var="FASTAPI_EASY_DB_HOST"
    )

    port: int = ConfigField(
        type=int,
        default=5432,
        description="Database port",
        env_var="FASTAPI_EASY_DB_PORT",
        min_value=1,
        max_value=65535,
    )

    database: str = ConfigField(
        type=str,
        default="fastapi_easy",
        description="Database name",
        env_var="FASTAPI_EASY_DB_NAME",
        required=True,
    )

    username: str = ConfigField(
        type=str,
        default="postgres",
        description="Database username",
        env_var="FASTAPI_EASY_DB_USER",
    )

    password: str = ConfigField(
        type=str,
        default="",
        description="Database password",
        env_var="FASTAPI_EASY_DB_PASSWORD",
        required=False,
    )

    driver: str = ConfigField(
        type=str,
        default="postgresql+asyncpg",
        description="Database driver",
        env_var="FASTAPI_EASY_DB_DRIVER",
        choices=["postgresql+asyncpg", "mysql+aiomysql", "sqlite+aiosqlite"],
    )

    pool_size: int = ConfigField(
        type=int,
        default=10,
        description="Connection pool size",
        env_var="FASTAPI_EASY_DB_POOL_SIZE",
        min_value=1,
        max_value=100,
    )

    max_overflow: int = ConfigField(
        type=int,
        default=20,
        description="Max overflow connections",
        env_var="FASTAPI_EASY_DB_MAX_OVERFLOW",
        min_value=0,
    )

    echo: bool = ConfigField(
        type=bool, default=False, description="Enable SQL echo", env_var="FASTAPI_EASY_DB_ECHO"
    )

    @property
    def url(self) -> str:
        """构建数据库连接URL"""
        if self.driver.startswith("sqlite"):
            return f"{self.driver}:///{self.database}"

        password_part = f":{self.password}" if self.password else ""
        return (
            f"{self.driver}://{self.username}{password_part}@"
            f"{self.host}:{self.port}/{self.database}"
        )


@dataclass
class SecurityConfig(BaseSettings):
    """安全配置"""

    secret_key: str = ConfigField(
        type=str,
        default=None,  # Force user to set secure secret key
        description="JWT secret key - MUST be set in production",
        env_var="FASTAPI_EASY_SECRET_KEY",
        required=True,
    )

    algorithm: str = ConfigField(
        type=str,
        default="HS256",
        description="JWT algorithm",
        env_var="FASTAPI_EASY_JWT_ALGORITHM",
        choices=["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"],
    )

    access_token_expire_minutes: int = ConfigField(
        type=int,
        default=30,
        description="Access token expiration in minutes",
        env_var="FASTAPI_EASY_ACCESS_TOKEN_EXPIRE",
        min_value=1,
    )

    refresh_token_expire_days: int = ConfigField(
        type=int,
        default=7,
        description="Refresh token expiration in days",
        env_var="FASTAPI_EASY_REFRESH_TOKEN_EXPIRE",
        min_value=1,
    )

    password_min_length: int = ConfigField(
        type=int,
        default=8,
        description="Minimum password length",
        env_var="FASTAPI_EASY_PASSWORD_MIN_LENGTH",
        min_value=4,
    )

    max_login_attempts: int = ConfigField(
        type=int,
        default=5,
        description="Maximum login attempts before lockout",
        env_var="FASTAPI_EASY_MAX_LOGIN_ATTEMPTS",
        min_value=1,
    )

    lockout_duration_minutes: int = ConfigField(
        type=int,
        default=15,
        description="Account lockout duration in minutes",
        env_var="FASTAPI_EASY_LOCKOUT_DURATION",
        min_value=1,
    )

    cors_origins: List[str] = ConfigField(
        type=list,
        default=["*"],
        description="CORS allowed origins",
        env_var="FASTAPI_EASY_CORS_ORIGINS",
    )


@dataclass
class CacheConfig(BaseSettings):
    """缓存配置"""

    redis_url: str = ConfigField(
        type=str,
        default="redis://localhost:6379/0",
        description="Redis connection URL",
        env_var="FASTAPI_EASY_REDIS_URL",
    )

    default_ttl: int = ConfigField(
        type=int,
        default=3600,
        description="Default cache TTL in seconds",
        env_var="FASTAPI_EASY_CACHE_TTL",
        min_value=1,
    )

    max_keys: int = ConfigField(
        type=int,
        default=10000,
        description="Maximum cache keys",
        env_var="FASTAPI_EASY_CACHE_MAX_KEYS",
        min_value=1,
    )

    enable_metrics: bool = ConfigField(
        type=bool,
        default=True,
        description="Enable cache metrics",
        env_var="FASTAPI_EASY_CACHE_METRICS",
    )


@dataclass
class LoggingConfig(BaseSettings):
    """日志配置"""

    level: str = ConfigField(
        type=str,
        default="INFO",
        description="Log level",
        env_var="FASTAPI_EASY_LOG_LEVEL",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )

    format: str = ConfigField(
        type=str,
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
        env_var="FASTAPI_EASY_LOG_FORMAT",
    )

    file_path: Optional[str] = ConfigField(
        type=str, default=None, description="Log file path", env_var="FASTAPI_EASY_LOG_FILE"
    )

    max_file_size: int = ConfigField(
        type=int,
        default=10485760,  # 10MB
        description="Max log file size in bytes",
        env_var="FASTAPI_EASY_LOG_MAX_SIZE",
        min_value=1024,
    )

    backup_count: int = ConfigField(
        type=int,
        default=5,
        description="Number of log file backups",
        env_var="FASTAPI_EASY_LOG_BACKUP_COUNT",
        min_value=1,
    )


@dataclass
class AppSettings(BaseSettings):
    """应用主配置"""

    # 应用基础配置
    app_name: str = ConfigField(
        type=str,
        default="FastAPI-Easy",
        description="Application name",
        env_var="FASTAPI_EASY_APP_NAME",
    )

    version: str = ConfigField(
        type=str,
        default="1.0.0",
        description="Application version",
        env_var="FASTAPI_EASY_APP_VERSION",
    )

    debug: bool = ConfigField(
        type=bool, default=False, description="Debug mode", env_var="FASTAPI_EASY_DEBUG"
    )

    environment: str = ConfigField(
        type=str,
        default="development",
        description="Environment name",
        env_var="FASTAPI_EASY_ENVIRONMENT",
        choices=["development", "testing", "staging", "production"],
    )

    # API配置
    api_prefix: str = ConfigField(
        type=str, default="/api/v1", description="API prefix", env_var="FASTAPI_EASY_API_PREFIX"
    )

    docs_url: Optional[str] = ConfigField(
        type=str, default="/docs", description="API docs URL", env_var="FASTAPI_EASY_DOCS_URL"
    )

    redoc_url: Optional[str] = ConfigField(
        type=str, default="/redoc", description="ReDoc URL", env_var="FASTAPI_EASY_REDOC_URL"
    )

    # 子配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def __post_init__(self):
        """初始化后处理"""
        # 根据环境调整配置
        if self.environment == "production":
            self.logging.level = "WARNING"
            self.debug = False
        elif self.environment == "development":
            self.logging.level = "DEBUG"
            self.debug = True

    @classmethod
    def create(cls, **kwargs) -> AppSettings:
        """创建应用配置"""
        return cls(**kwargs)


# 全局配置实例
settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """获取全局配置实例"""
    global settings
    if settings is None:
        settings = AppSettings.create()
    return settings


def init_settings(config_file: Optional[str] = None, **kwargs) -> AppSettings:
    """初始化全局配置"""
    global settings
    if config_file:
        settings = AppSettings.from_file(config_file, **kwargs)
    else:
        settings = AppSettings.create(**kwargs)
    return settings
