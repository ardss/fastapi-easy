# 测试补充计划 - 快速参考

**快速查看**: 缺失的测试一览表

---

## 📊 缺失测试汇总

### exceptions.py - 12 个缺失测试 🔴

```python
# 基础异常 (3 个)
✗ test_migration_error_init
✗ test_migration_error_get_full_message_with_suggestion
✗ test_migration_error_get_full_message_without_suggestion

# 具体异常 (9 个)
✗ test_database_connection_error
✗ test_schema_detection_error_timeout
✗ test_schema_detection_error_normal
✗ test_migration_execution_error_permission
✗ test_migration_execution_error_table_not_exist
✗ test_migration_execution_error_syntax
✗ test_lock_acquisition_error
✗ test_storage_error
✗ test_cache_error
```

**工作量**: 2-3 小时  
**优先级**: 🔴 高 (安全关键)  
**风险**: 异常处理不完整

---

### cli_helpers.py - 16 个缺失测试 🔴

```python
# CLIErrorHandler (3 个)
✗ test_handle_migration_error
✗ test_handle_generic_error
✗ test_exit_with_error

# CLIFormatter (7 个)
✗ test_format_migration_safe
✗ test_format_migration_medium
✗ test_format_migration_high
✗ test_format_plan_empty
✗ test_format_plan_with_migrations
✗ test_format_history_empty
✗ test_format_history_with_records

# CLIConfirm (4 个)
✗ test_confirm_migration_force
✗ test_confirm_migration_user_yes
✗ test_confirm_rollback_user_no
✗ test_confirm_clear_cache

# CLIProgress (2 个)
✗ test_show_step
✗ test_show_success
```

**工作量**: 2-3 小时  
**优先级**: 🔴 高 (用户交互)  
**风险**: CLI 输出不可靠

---

### storage.py - 8 个缺失测试 🔴

```python
# 初始化 (2 个)
✗ test_initialize_success
✗ test_initialize_table_exists

# 记录迁移 (3 个)
✗ test_record_migration_success
✗ test_record_migration_idempotent
✗ test_record_migration_error

# 获取历史 (3 个)
✗ test_get_history_empty
✗ test_get_history_with_records
✗ test_get_history_limit
```

**工作量**: 1-2 小时  
**优先级**: 🔴 高 (数据持久化)  
**风险**: 迁移历史丢失

---

### cli.py - 15 个缺失测试 🟡

```python
# plan 命令 (3 个)
✗ test_plan_basic
✗ test_plan_dry_run
✗ test_plan_no_migrations

# apply 命令 (4 个)
✗ test_apply_with_force
✗ test_apply_user_cancel
✗ test_apply_error
✗ test_apply_permission_denied

# history 命令 (2 个)
✗ test_history_basic
✗ test_history_limit

# status 命令 (2 个)
✗ test_status_basic
✗ test_status_error

# rollback 命令 (2 个)
✗ test_rollback_basic
✗ test_rollback_user_cancel

# init 命令 (2 个)
✗ test_init_basic
✗ test_init_error
```

**工作量**: 2-3 小时  
**优先级**: 🟡 中 (集成测试)  
**风险**: 命令行集成不完整

---

### engine.py - 10 个缺失测试 🟡

```python
# 错误处理 (5 个)
✗ test_database_connection_error_handling
✗ test_schema_detection_timeout
✗ test_migration_execution_error
✗ test_lock_acquisition_error
✗ test_storage_error_handling

# 异常恢复 (3 个)
✗ test_lock_release_failure_recovery
✗ test_partial_migration_failure
✗ test_transaction_rollback

# 错误消息 (2 个)
✗ test_error_message_includes_diagnostics
✗ test_error_message_includes_debug_steps
```

**工作量**: 2-3 小时  
**优先级**: 🟡 中 (错误处理)  
**风险**: 错误诊断不完整

---

## 🎯 按优先级排序

### 优先级 1️⃣ - 立即实施 (36 个测试)

| 模块 | 测试数 | 工作量 | 关键性 |
|------|-------|-------|--------|
| exceptions.py | 12 | 2-3h | 🔴 高 |
| cli_helpers.py | 16 | 2-3h | 🔴 高 |
| storage.py | 8 | 1-2h | 🔴 高 |
| **小计** | **36** | **5-8h** | **关键** |

### 优先级 2️⃣ - 后续实施 (25 个测试)

| 模块 | 测试数 | 工作量 | 关键性 |
|------|-------|-------|--------|
| cli.py | 15 | 2-3h | 🟡 中 |
| engine.py | 10 | 2-3h | 🟡 中 |
| **小计** | **25** | **4-6h** | **重要** |

### 优先级 3️⃣ - 可选实施 (13 个测试)

| 模块 | 测试数 | 工作量 | 关键性 |
|------|-------|-------|--------|
| 集成测试 | 8 | 2-3h | 🟢 低 |
| 性能测试 | 5 | 1-2h | 🟢 低 |
| **小计** | **13** | **3-5h** | **可选** |

---

## 🚀 快速开始

### 第 1 天: exceptions.py 测试

```bash
# 创建测试文件
touch tests/unit/test_exceptions.py

# 运行测试
pytest tests/unit/test_exceptions.py -v
```

**预期**: 12 个新测试通过

### 第 2 天: cli_helpers.py 测试

```bash
# 创建测试文件
touch tests/unit/test_cli_helpers.py

# 运行测试
pytest tests/unit/test_cli_helpers.py -v
```

**预期**: 16 个新测试通过

### 第 3 天: storage.py 测试

```bash
# 创建测试文件
touch tests/unit/test_storage_extended.py

# 运行测试
pytest tests/unit/test_storage_extended.py -v
```

**预期**: 8 个新测试通过

### 第 4-5 天: cli.py 和 engine.py 测试

```bash
# 创建测试文件
touch tests/integration/test_cli_integration.py
touch tests/unit/test_engine_error_handling.py

# 运行所有测试
pytest tests/ -v --cov=src/fastapi_easy/migrations
```

**预期**: 25 个新测试通过

---

## 📈 进度跟踪

### 当前状态 (基线)
```
总测试数: 39
缺失测试: 61
覆盖率: ~50%
```

### 优先级 1️⃣ 完成后
```
总测试数: 75
缺失测试: 25
覆盖率: ~75%
```

### 优先级 2️⃣ 完成后
```
总测试数: 100
缺失测试: 0
覆盖率: ~90%+
```

---

## 🛡️ 安全性检查清单

- [ ] SQL 注入防护测试
- [ ] 敏感信息泄露测试
- [ ] 权限提升测试
- [ ] 并发安全测试
- [ ] 输入验证测试

---

## 📝 文件清单

### 需要创建的测试文件

```
tests/unit/
├── test_exceptions.py (NEW)
├── test_cli_helpers.py (NEW)
├── test_storage_extended.py (NEW)
└── test_engine_error_handling.py (NEW)

tests/integration/
├── test_cli_integration.py (NEW)
└── test_migration_e2e_extended.py (NEW)
```

### 需要修改的文件

```
tests/
├── test_migration_engine.py (补充错误处理测试)
├── test_risk_engine.py (已完整)
└── test_hooks.py (已完整)
```

---

## ✅ 验收标准

```
□ 所有测试通过 (100+)
□ 覆盖率 > 90%
□ 无 flaky 测试
□ 执行时间 < 10 秒
□ 文档完整
```

---

## 💡 建议

1. **立即开始**: 优先级 1️⃣ 的测试是关键
2. **分阶段实施**: 每天完成一个模块
3. **持续验证**: 每完成一个模块就运行测试
4. **文档更新**: 同步更新测试文档

---

**预计完成时间**: 2-3 周  
**推荐开始**: 立即  
**优先级**: 🔴 高
