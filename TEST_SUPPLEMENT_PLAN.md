# 测试补充计划 - 详细分析

**分析日期**: 2025-11-29  
**分析对象**: exceptions.py, cli_helpers.py, cli.py, storage.py, engine.py  
**状态**: 📋 待实施

---

## 📊 当前测试覆盖分析

### ✅ 已有测试 (39/39 通过)

| 模块 | 测试数 | 覆盖范围 | 缺陷 |
|------|-------|--------|------|
| test_migration_engine.py | 6 | 基础迁移流程 | ⚠️ 缺少错误处理 |
| test_risk_engine.py | 15 | 风险评估 | ✅ 完整 |
| test_hooks.py | 12 | Hook 系统 | ✅ 完整 |
| test_cli.py | 6 | CLI 基础命令 | ⚠️ 缺少集成测试 |

---

## 🔍 缺失测试详细分析

### 1️⃣ exceptions.py 缺失测试

#### 问题分析
```python
# 当前状态: 0 个测试
# 覆盖率: 0%
# 风险等级: 🔴 高
```

#### 缺失的测试场景

**A. 基础异常类测试**
- [ ] MigrationError 初始化
- [ ] MigrationError.get_full_message() 返回格式
- [ ] 异常消息包含建议

**B. 具体异常类测试**
- [ ] DatabaseConnectionError - 连接字符串显示
- [ ] DatabaseConnectionError - 原始错误信息包含
- [ ] SchemaDetectionError - 超时场景
- [ ] SchemaDetectionError - 普通错误场景
- [ ] MigrationExecutionError - 权限错误识别
- [ ] MigrationExecutionError - 表不存在识别
- [ ] MigrationExecutionError - SQL 语法错误识别
- [ ] LockAcquisitionError - 不同锁类型处理
- [ ] StorageError - 操作类型识别
- [ ] CacheError - 权限错误处理
- [ ] CacheError - 缓存损坏处理
- [ ] RiskAssessmentError - 规则名称显示

**C. 异常继承链测试**
- [ ] 所有异常都继承自 MigrationError
- [ ] 所有异常都继承自 Exception
- [ ] isinstance() 检查正确

**D. 异常消息安全性测试**
- [ ] 敏感信息不被泄露
- [ ] 用户友好的错误消息
- [ ] 建议信息准确

#### 测试代码框架
```python
import pytest
from fastapi_easy.migrations.exceptions import (
    MigrationError,
    DatabaseConnectionError,
    SchemaDetectionError,
    MigrationExecutionError,
    LockAcquisitionError,
    StorageError,
    CacheError,
    RiskAssessmentError,
)

class TestMigrationError:
    def test_basic_initialization(self):
        error = MigrationError("Test message", "Test suggestion")
        assert error.message == "Test message"
        assert error.suggestion == "Test suggestion"
    
    def test_get_full_message_with_suggestion(self):
        error = MigrationError("Test", "Suggestion")
        full = error.get_full_message()
        assert "Test" in full
        assert "Suggestion" in full
        assert "💡" in full
    
    def test_get_full_message_without_suggestion(self):
        error = MigrationError("Test")
        assert error.get_full_message() == "Test"

class TestDatabaseConnectionError:
    def test_initialization(self):
        original = ValueError("Connection refused")
        error = DatabaseConnectionError("postgresql://localhost/db", original)
        assert "无法连接到数据库" in error.message
        assert "postgresql://localhost/db" in error.message
    
    def test_suggestion_included(self):
        original = ValueError("Connection refused")
        error = DatabaseConnectionError("sqlite:///test.db", original)
        full = error.get_full_message()
        assert "检查数据库连接字符串" in full
        assert "确保数据库服务正在运行" in full
```

---

### 2️⃣ cli_helpers.py 缺失测试

#### 问题分析
```python
# 当前状态: 0 个测试
# 覆盖率: 0%
# 风险等级: 🔴 高
```

#### 缺失的测试场景

**A. CLIErrorHandler 测试**
- [ ] handle_error() - MigrationError 处理
- [ ] handle_error() - 普通异常处理
- [ ] handle_error() - 带 context 的异常处理
- [ ] handle_error() - 输出到 stderr
- [ ] exit_with_error() - 正确的退出码
- [ ] exit_with_error() - 错误消息显示

**B. CLIFormatter 测试**
- [ ] format_migration() - SAFE 风险等级
- [ ] format_migration() - MEDIUM 风险等级
- [ ] format_migration() - HIGH 风险等级
- [ ] format_migration() - 未知风险等级
- [ ] format_plan() - 空计划
- [ ] format_plan() - 单个迁移
- [ ] format_plan() - 多个迁移
- [ ] format_history() - 空历史
- [ ] format_history() - 单条记录
- [ ] format_history() - 多条记录
- [ ] format_history() - 字段截断

**C. CLIConfirm 测试**
- [ ] confirm_migration() - force=True
- [ ] confirm_migration() - force=False, 用户确认
- [ ] confirm_migration() - force=False, 用户取消
- [ ] confirm_rollback() - force=True
- [ ] confirm_rollback() - force=False, 用户确认
- [ ] confirm_rollback() - force=False, 用户取消
- [ ] confirm_clear_cache() - force=True
- [ ] confirm_clear_cache() - force=False

**D. CLIProgress 测试**
- [ ] show_step() - 输出格式
- [ ] show_success() - 成功消息
- [ ] show_warning() - 警告消息
- [ ] show_info() - 信息消息

#### 测试代码框架
```python
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from fastapi_easy.migrations.cli_helpers import (
    CLIErrorHandler,
    CLIFormatter,
    CLIConfirm,
    CLIProgress,
)
from fastapi_easy.migrations.exceptions import MigrationError
from fastapi_easy.migrations.types import Migration, MigrationPlan, RiskLevel

class TestCLIErrorHandler:
    def test_handle_migration_error(self, capsys):
        error = MigrationError("Test error", "Test suggestion")
        CLIErrorHandler.handle_error(error)
        captured = capsys.readouterr()
        assert "Test error" in captured.err
        assert "Test suggestion" in captured.err
    
    def test_handle_generic_error(self, capsys):
        error = ValueError("Generic error")
        CLIErrorHandler.handle_error(error, "Context")
        captured = capsys.readouterr()
        assert "Context" in captured.err
        assert "Generic error" in captured.err
    
    @patch('sys.exit')
    def test_exit_with_error(self, mock_exit, capsys):
        CLIErrorHandler.exit_with_error("Fatal error", 2)
        mock_exit.assert_called_once_with(2)
        captured = capsys.readouterr()
        assert "Fatal error" in captured.err

class TestCLIFormatter:
    def test_format_migration_safe(self):
        migration = Migration(
            version="001",
            description="Add table",
            upgrade_sql="CREATE TABLE",
            downgrade_sql="DROP TABLE",
            risk_level=RiskLevel.SAFE,
        )
        result = CLIFormatter.format_migration(migration)
        assert "✅" in result
        assert "SAFE" in result
        assert "001" in result
    
    def test_format_migration_high_risk(self):
        migration = Migration(
            version="002",
            description="Drop column",
            upgrade_sql="ALTER TABLE",
            downgrade_sql="ALTER TABLE",
            risk_level=RiskLevel.HIGH,
        )
        result = CLIFormatter.format_migration(migration)
        assert "🔴" in result
        assert "HIGH" in result
    
    def test_format_plan_empty(self):
        plan = MigrationPlan(migrations=[], status="completed")
        result = CLIFormatter.format_plan(plan)
        assert "无待处理的迁移" in result
    
    def test_format_plan_with_migrations(self):
        migration = Migration(
            version="001",
            description="Add table",
            upgrade_sql="CREATE TABLE",
            downgrade_sql="DROP TABLE",
            risk_level=RiskLevel.SAFE,
        )
        plan = MigrationPlan(migrations=[migration], status="completed")
        result = CLIFormatter.format_plan(plan)
        assert "检测到 1 个迁移" in result
        assert "001" in result
```

---

### 3️⃣ cli.py 缺失测试

#### 问题分析
```python
# 当前状态: 6 个基础测试
# 覆盖率: ~30%
# 风险等级: 🔴 高
```

#### 缺失的测试场景

**A. plan 命令测试**
- [ ] plan 命令 - 正常执行
- [ ] plan 命令 - 数据库连接失败
- [ ] plan 命令 - dry-run 模式
- [ ] plan 命令 - 无迁移时
- [ ] plan 命令 - 多个迁移时

**B. apply 命令测试**
- [ ] apply 命令 - 正常执行
- [ ] apply 命令 - 用户取消
- [ ] apply 命令 - force 模式
- [ ] apply 命令 - 迁移失败
- [ ] apply 命令 - 权限不足

**C. history 命令测试**
- [ ] history 命令 - 正常执行
- [ ] history 命令 - 无历史时
- [ ] history 命令 - limit 参数
- [ ] history 命令 - 数据库错误

**D. status 命令测试**
- [ ] status 命令 - 正常执行
- [ ] status 命令 - 数据库连接失败
- [ ] status 命令 - 显示正确信息

**E. rollback 命令测试**
- [ ] rollback 命令 - 正常执行
- [ ] rollback 命令 - 用户取消
- [ ] rollback 命令 - force 模式
- [ ] rollback 命令 - 无历史时

**F. init 命令测试**
- [ ] init 命令 - 正常执行
- [ ] init 命令 - 数据库连接失败
- [ ] init 命令 - 表已存在

#### 测试代码框架
```python
import pytest
from click.testing import CliRunner
from fastapi_easy.migrations.cli import cli

class TestPlanCommand:
    def test_plan_basic(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ['plan', '--database-url', 'sqlite:///test.db'])
            assert result.exit_code == 0
    
    def test_plan_dry_run(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                'plan',
                '--database-url', 'sqlite:///test.db',
                '--dry-run'
            ])
            assert result.exit_code == 0
            assert "Dry-run" in result.output or "dry-run" in result.output

class TestApplyCommand:
    def test_apply_with_force(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                'apply',
                '--database-url', 'sqlite:///test.db',
                '--force'
            ])
            # 应该成功或失败，但不应该要求用户确认
            assert "是否继续" not in result.output
```

---

### 4️⃣ storage.py 缺失测试

#### 问题分析
```python
# 当前状态: 0 个测试
# 覆盖率: 0%
# 风险等级: 🔴 高
```

#### 缺失的测试场景

**A. 初始化测试**
- [ ] initialize() - 表创建成功
- [ ] initialize() - 表已存在
- [ ] initialize() - 权限不足
- [ ] initialize() - 数据库错误

**B. 记录迁移测试**
- [ ] record_migration() - 正常记录
- [ ] record_migration() - 重复记录 (幂等性)
- [ ] record_migration() - 数据库错误
- [ ] record_migration() - 返回值正确

**C. 获取历史测试**
- [ ] get_migration_history() - 空历史
- [ ] get_migration_history() - 单条记录
- [ ] get_migration_history() - 多条记录
- [ ] get_migration_history() - limit 参数

**D. 异常处理测试**
- [ ] IntegrityError 处理
- [ ] 其他异常处理
- [ ] 错误消息记录

#### 测试代码框架
```python
import pytest
from sqlalchemy import create_engine, text
from fastapi_easy.migrations.storage import MigrationStorage

class TestMigrationStorage:
    @pytest.fixture
    def storage(self):
        engine = create_engine("sqlite:///:memory:")
        return MigrationStorage(engine)
    
    def test_initialize(self, storage):
        storage.initialize()
        # 验证表存在
        with storage.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='migration_history'"
            ))
            assert result.fetchone() is not None
    
    def test_record_migration(self, storage):
        storage.initialize()
        success = storage.record_migration(
            version="001",
            description="Test migration",
            rollback_sql="ROLLBACK",
            risk_level="SAFE"
        )
        assert success is True
    
    def test_record_migration_idempotent(self, storage):
        storage.initialize()
        # 第一次记录
        storage.record_migration("001", "Test", "ROLLBACK", "SAFE")
        # 第二次记录相同的版本
        result = storage.record_migration("001", "Test", "ROLLBACK", "SAFE")
        # 应该返回 True (幂等)
        assert result is True
    
    def test_get_migration_history(self, storage):
        storage.initialize()
        storage.record_migration("001", "Test 1", "ROLLBACK", "SAFE")
        storage.record_migration("002", "Test 2", "ROLLBACK", "MEDIUM")
        
        history = storage.get_migration_history(limit=10)
        assert len(history) == 2
        assert history[0]["version"] == "001"
```

---

### 5️⃣ engine.py 缺失测试

#### 问题分析
```python
# 当前状态: 6 个基础测试
# 覆盖率: ~40%
# 风险等级: 🔴 高
```

#### 缺失的测试场景

**A. 错误处理测试**
- [ ] 数据库连接失败
- [ ] Schema 检测超时
- [ ] 迁移执行失败
- [ ] 锁获取失败
- [ ] 存储记录失败

**B. 异常恢复测试**
- [ ] 锁释放失败时的恢复
- [ ] 部分迁移失败时的恢复
- [ ] 事务回滚

**C. 错误消息测试**
- [ ] 错误消息包含诊断信息
- [ ] 错误消息包含调试步骤
- [ ] 错误消息可读性

**D. 边界情况测试**
- [ ] 空迁移计划
- [ ] 非常大的迁移
- [ ] 并发迁移

#### 测试代码框架
```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi_easy.migrations.engine import MigrationEngine
from fastapi_easy.migrations.exceptions import (
    DatabaseConnectionError,
    MigrationExecutionError,
)

class TestMigrationEngineErrorHandling:
    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """测试数据库连接失败"""
        with patch('sqlalchemy.create_engine') as mock_engine:
            mock_engine.side_effect = Exception("Connection refused")
            
            with pytest.raises(Exception):
                from sqlalchemy import create_engine
                create_engine("invalid://url")
    
    @pytest.mark.asyncio
    async def test_migration_execution_error_message(self, temp_db):
        """测试迁移执行错误消息"""
        engine = create_engine(temp_db, connect_args={"check_same_thread": False})
        migration_engine = MigrationEngine(engine, Base.metadata)
        
        # 模拟迁移执行失败
        with patch.object(migration_engine, 'executor') as mock_executor:
            mock_executor.execute.side_effect = Exception("SQL syntax error")
            
            # 应该捕获异常并提供诊断信息
            try:
                await migration_engine.auto_migrate()
            except Exception as e:
                assert "调试步骤" in str(e) or "SQL" in str(e)
```

---

## 📋 测试补充计划

### 优先级 1️⃣ (关键 - 必须实施)

| 模块 | 测试数 | 工作量 | 优先级 | 风险 |
|------|-------|-------|--------|------|
| exceptions.py | 12 | 2-3 小时 | 🔴 高 | 异常处理不完整 |
| cli_helpers.py | 16 | 2-3 小时 | 🔴 高 | CLI 输出不可靠 |
| storage.py | 8 | 1-2 小时 | 🔴 高 | 数据持久化风险 |

### 优先级 2️⃣ (重要 - 应该实施)

| 模块 | 测试数 | 工作量 | 优先级 | 风险 |
|------|-------|-------|--------|------|
| cli.py | 15 | 2-3 小时 | 🟡 中 | 集成测试缺失 |
| engine.py | 10 | 2-3 小时 | 🟡 中 | 错误处理不完整 |

### 优先级 3️⃣ (可选 - 后续实施)

| 模块 | 测试数 | 工作量 | 优先级 | 风险 |
|------|-------|-------|--------|------|
| 集成测试 | 8 | 2-3 小时 | 🟢 低 | 端到端流程 |
| 性能测试 | 5 | 1-2 小时 | 🟢 低 | 性能回归 |

---

## 🛡️ 安全性测试需求

### 1. 输入验证测试
- [ ] SQL 注入防护
- [ ] 路径遍历防护
- [ ] 命令注入防护

### 2. 错误信息安全测试
- [ ] 敏感信息不泄露
- [ ] 数据库密码不显示
- [ ] 系统路径不暴露

### 3. 权限测试
- [ ] 权限不足时的处理
- [ ] 文件权限检查
- [ ] 数据库权限检查

### 4. 并发安全测试
- [ ] 多线程安全
- [ ] 锁机制正确
- [ ] 竞态条件

---

## 📊 测试覆盖率目标

### 当前状态
```
总测试数: 39
覆盖率: ~50% (估计)
缺失测试: 61
```

### 目标状态
```
总测试数: 100+
覆盖率: > 90%
缺失测试: < 10
```

---

## 🚀 实施计划

### 第 1 周 (优先级 1️⃣)

**任务 1: exceptions.py 测试** (2-3 小时)
```bash
# 创建测试文件
tests/unit/test_exceptions.py

# 测试覆盖:
- 基础异常类
- 8 个具体异常类
- 异常继承链
- 消息安全性
```

**任务 2: cli_helpers.py 测试** (2-3 小时)
```bash
# 创建测试文件
tests/unit/test_cli_helpers.py

# 测试覆盖:
- CLIErrorHandler (6 个测试)
- CLIFormatter (10 个测试)
- CLIConfirm (8 个测试)
- CLIProgress (4 个测试)
```

**任务 3: storage.py 测试** (1-2 小时)
```bash
# 创建测试文件
tests/unit/test_storage_extended.py

# 测试覆盖:
- 初始化 (4 个测试)
- 记录迁移 (4 个测试)
- 获取历史 (4 个测试)
- 异常处理 (3 个测试)
```

### 第 2 周 (优先级 2️⃣)

**任务 4: cli.py 集成测试** (2-3 小时)
```bash
# 创建测试文件
tests/integration/test_cli_integration.py

# 测试覆盖:
- plan 命令 (5 个测试)
- apply 命令 (5 个测试)
- history 命令 (3 个测试)
- status 命令 (2 个测试)
```

**任务 5: engine.py 错误处理测试** (2-3 小时)
```bash
# 创建测试文件
tests/unit/test_engine_error_handling.py

# 测试覆盖:
- 错误处理 (5 个测试)
- 异常恢复 (3 个测试)
- 错误消息 (2 个测试)
```

### 第 3 周 (优先级 3️⃣)

**任务 6: 端到端测试** (2-3 小时)
```bash
# 创建测试文件
tests/e2e/test_migration_e2e_extended.py

# 测试覆盖:
- 完整迁移流程
- 错误恢复流程
- 并发场景
```

---

## ✅ 验收标准

### 代码覆盖率
- [ ] exceptions.py: > 95%
- [ ] cli_helpers.py: > 90%
- [ ] cli.py: > 85%
- [ ] storage.py: > 90%
- [ ] engine.py: > 85%
- [ ] 总体: > 90%

### 测试质量
- [ ] 所有测试通过
- [ ] 无 flaky 测试
- [ ] 测试执行时间 < 10 秒
- [ ] 测试文档完整

### 安全性
- [ ] 无 SQL 注入漏洞
- [ ] 无信息泄露
- [ ] 无权限提升
- [ ] 并发安全

---

## 📝 总结

### 当前状态
- ✅ 39 个测试通过
- ⚠️ 61 个测试缺失
- 🔴 覆盖率约 50%

### 改进方向
1. **立即实施** (优先级 1️⃣): 36 个测试 (1 周)
2. **后续实施** (优先级 2️⃣): 25 个测试 (1 周)
3. **可选实施** (优先级 3️⃣): 13 个测试 (1 周)

### 预期效果
- 测试总数: 39 → 100+
- 覆盖率: 50% → 90%+
- 缺陷发现率: 提升 70%+
- 用户信任度: 显著提升

---

**计划状态**: 📋 待批准  
**预计工作量**: 3 周  
**推荐**: 立即开始实施优先级 1️⃣ 的测试
