# 自动化测试和修复工作流

本文档描述了 FastAPI-Easy 项目的自动化测试和代码质量保证工作流。

## 概述

该工作流包括三个主要部分：

1. **本地测试** - 在提交前在本地运行测试
2. **自动化 CI/CD** - 在 GitHub 上自动运行测试
3. **代码质量检查** - 自动检查代码风格和类型

---

## 1. 本地测试

### 快速运行所有测试

```bash
python -m pytest tests/ -v
```

### 运行特定测试类型

```bash
# 仅运行单元测试
python -m pytest tests/ -m unit -v

# 仅运行集成测试
python -m pytest tests/ -m integration -v

# 仅运行端到端测试
python -m pytest tests/ -m e2e -v
```

### 运行带覆盖率的测试

```bash
python -m pytest tests/ --cov=src/fastapi_easy --cov-report=html
```

### 使用自动化脚本运行测试和修复

```bash
# 基础运行
python scripts/run_tests_and_fix.py

# 运行特定级别的测试
python scripts/run_tests_and_fix.py --level unit
python scripts/run_tests_and_fix.py --level integration
python scripts/run_tests_and_fix.py --level e2e
python scripts/run_tests_and_fix.py --level all

# 包含覆盖率报告
python scripts/run_tests_and_fix.py --coverage

# 详细输出
python scripts/run_tests_and_fix.py --verbose
```

---

## 2. 自动化 CI/CD (GitHub Actions)

### 工作流文件

位置: `.github/workflows/test.yml`

### 工作流触发条件

- 推送到 `master` 或 `develop` 分支
- 创建拉取请求到 `master` 或 `develop` 分支

### 工作流步骤

#### 测试任务 (test)

在多个操作系统和 Python 版本上运行：

- **操作系统**: Ubuntu, Windows, macOS
- **Python 版本**: 3.8, 3.9, 3.10, 3.11

**步骤**:
1. 检出代码
2. 设置 Python 环境
3. 安装依赖
4. 运行 pytest（包含覆盖率）
5. 上传覆盖率到 Codecov

#### 代码质量任务 (lint)

在 Ubuntu 上运行代码质量检查：

**检查工具**:
- **flake8** - PEP 8 风格检查
- **black** - 代码格式化
- **isort** - import 排序
- **mypy** - 类型检查

---

## 3. 代码质量检查

### 本地代码质量检查

#### 安装工具

```bash
pip install flake8 black isort mypy
```

#### 运行检查

```bash
# PEP 8 风格检查
flake8 src/fastapi_easy

# 代码格式化检查
black --check src/fastapi_easy

# Import 排序检查
isort --check-only src/fastapi_easy

# 类型检查
mypy src/fastapi_easy --ignore-missing-imports
```

#### 自动修复

```bash
# 自动格式化代码
black src/fastapi_easy

# 自动排序 imports
isort src/fastapi_easy
```

### Pre-commit 钩子

位置: `.pre-commit-config.yaml`

#### 安装 pre-commit

```bash
pip install pre-commit
pre-commit install
```

#### 手动运行 pre-commit

```bash
pre-commit run --all-files
```

---

## 4. 测试报告

### 本地报告

运行 `run_tests_and_fix.py` 后会生成 `test_report.txt`

### GitHub Actions 报告

- **测试结果** - 显示在 PR 检查中
- **覆盖率** - 上传到 Codecov
- **代码质量** - 显示在 PR 检查中

---

## 5. 最佳实践

### 提交前检查清单

- [ ] 运行 `pytest tests/` 确保所有测试通过
- [ ] 运行 `black src/fastapi_easy` 格式化代码
- [ ] 运行 `isort src/fastapi_easy` 排序 imports
- [ ] 运行 `flake8 src/fastapi_easy` 检查风格
- [ ] 运行 `mypy src/fastapi_easy` 检查类型

### 快速命令

```bash
# 一键运行所有检查
python scripts/run_tests_and_fix.py --coverage && \
black src/fastapi_easy && \
isort src/fastapi_easy && \
flake8 src/fastapi_easy && \
mypy src/fastapi_easy --ignore-missing-imports
```

### 处理测试失败

1. **查看失败详情**
   ```bash
   pytest tests/ -v --tb=long
   ```

2. **运行特定失败的测试**
   ```bash
   pytest tests/path/to/test_file.py::TestClass::test_method -v
   ```

3. **调试模式**
   ```bash
   pytest tests/ -v --pdb  # 在失败处进入调试器
   ```

---

## 6. 故障排查

### 测试超时

如果测试超时（> 5 分钟）：

```bash
# 增加超时时间
pytest tests/ --timeout=600
```

### 导入错误

如果出现导入错误：

```bash
# 确保安装了开发依赖
pip install -e ".[dev]"

# 检查 Python 路径
python -c "import sys; print(sys.path)"
```

### 覆盖率问题

如果覆盖率报告不完整：

```bash
# 清除缓存
rm -rf .pytest_cache .coverage htmlcov/

# 重新运行
pytest tests/ --cov=src/fastapi_easy --cov-report=html
```

---

## 7. 配置说明

### pytest.ini

- **testpaths** - 测试目录
- **markers** - 测试标记（unit, integration, e2e）
- **asyncio_mode** - 异步测试模式
- **addopts** - 默认选项

### pyproject.toml

- **[tool.pytest.ini_options]** - pytest 配置
- **[tool.coverage.run]** - 覆盖率配置
- **[tool.black]** - black 配置
- **[tool.isort]** - isort 配置

---

## 8. 相关文档

- [开发指南](docs/DEVELOPMENT.md)
- [贡献指南](CONTRIBUTING.md)
- [代码审查指南](docs/CODE_REVIEW.md)

---

**最后更新**: 2025-12-03  
**维护者**: FastAPI-Easy Team
