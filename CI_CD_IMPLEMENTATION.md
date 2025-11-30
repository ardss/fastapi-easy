# CI/CD 实现文档

**创建日期**: 2025-11-30  
**分支**: feature/add-cicd-workflow  
**状态**: 实现完成

---

## 📋 实现概览

本文档详细说明了 FastAPI-Easy 项目的 CI/CD 流程实现。

### 已创建的文件

1. `.github/workflows/tests.yml` - 自动化测试工作流
2. `.github/workflows/lint.yml` - 代码质量检查工作流
3. `.github/workflows/deploy-docs.yml` - 文档部署工作流
4. `.pre-commit-config.yaml` - Pre-commit 钩子配置
5. `pyproject.toml` - 现代化项目配置

---

## 🔄 工作流说明

### 1. Tests 工作流 (tests.yml)

**触发条件**:
- Push 到 master, main, develop, feature/* 分支
- Pull Request 到 master, main, develop 分支

**执行步骤**:
1. 检出代码
2. 设置 Python 环境 (3.8, 3.9, 3.10, 3.11)
3. 安装依赖
4. 运行 Flake8 代码检查
5. 运行 MyPy 类型检查
6. 运行 Black 格式检查
7. 运行 isort 导入检查
8. 运行 pytest 单元测试
9. 生成覆盖率报告
10. 上传到 Codecov
11. 归档覆盖率报告

**输出**:
- 测试结果
- 覆盖率报告 (HTML)
- Codecov 集成

---

### 2. Lint 工作流 (lint.yml)

**触发条件**:
- Push 到 master, main, develop, feature/* 分支
- Pull Request 到 master, main, develop 分支

**执行步骤**:

**代码质量检查**:
1. Black 格式检查
2. isort 导入排序检查
3. Flake8 代码检查
4. MyPy 类型检查
5. Pylint 代码分析

**安全检查**:
1. Bandit 安全检查
2. Safety 依赖检查

**输出**:
- 代码质量报告
- 安全漏洞报告
- 依赖风险报告

---

### 3. Deploy Docs 工作流 (deploy-docs.yml)

**触发条件**:
- Push 到 master 或 main 分支

**执行步骤**:
1. 检出代码
2. 设置 Python 环境
3. 安装 MkDocs 依赖
4. 构建文档
5. 部署到 GitHub Pages

**输出**:
- 文档部署到 https://ardss.github.io/fastapi-easy/

---

## 🔧 Pre-commit 配置

### 安装 Pre-commit

```bash
pip install pre-commit
pre-commit install
```

### 配置的钩子

1. **Black** - 代码格式化
2. **isort** - 导入排序
3. **Flake8** - 代码检查
4. **Pre-commit hooks** - 基础检查
5. **pyupgrade** - Python 升级
6. **reorder-python-imports** - 导入重新排序

### 手动运行

```bash
# 运行所有钩子
pre-commit run --all-files

# 运行特定钩子
pre-commit run black --all-files
```

---

## 📦 pyproject.toml 配置

### 项目元数据

```toml
[project]
name = "fastapi-easy"
version = "0.1.6"
description = "Production-ready FastAPI framework"
```

### 可选依赖

```toml
[project.optional-dependencies]
dev = [...]          # 开发依赖
sqlalchemy = [...]   # SQLAlchemy 支持
tortoise = [...]     # Tortoise ORM 支持
mongo = [...]        # MongoDB 支持
sqlmodel = [...]     # SQLModel 支持
docs = [...]         # 文档依赖
```

### 工具配置

- **Black**: 行长 100，目标 Python 3.8+
- **isort**: Black 兼容配置
- **MyPy**: 严格类型检查
- **pytest**: 覆盖率配置
- **Coverage**: 覆盖率报告配置

---

## 🚀 使用指南

### 本地开发

```bash
# 1. 安装开发依赖
pip install -e ".[dev]"

# 2. 安装 pre-commit 钩子
pre-commit install

# 3. 开发代码
# ... 编写代码 ...

# 4. 提交前自动检查
git commit -m "your message"
# pre-commit 钩子会自动运行

# 5. 运行完整测试
pytest tests/ --cov=src/fastapi_easy
```

### 提交流程

```bash
# 1. 创建分支
git checkout -b feature/your-feature

# 2. 开发代码
# ... 编写代码 ...

# 3. 提交更改
git add .
git commit -m "feat: add your feature"

# 4. 推送到远程
git push origin feature/your-feature

# 5. 创建 Pull Request
# GitHub 会自动运行 CI/CD 工作流
```

### CI/CD 检查项

Pull Request 会自动运行以下检查:

- ✅ 代码格式检查 (Black)
- ✅ 导入排序检查 (isort)
- ✅ 代码质量检查 (Flake8)
- ✅ 类型检查 (MyPy)
- ✅ 单元测试 (pytest)
- ✅ 覆盖率报告
- ✅ 安全检查 (Bandit)
- ✅ 依赖检查 (Safety)

所有检查都必须通过才能合并 PR。

---

## 📊 覆盖率目标

- **当前**: 需要测定
- **目标**: > 80%
- **关键模块**: 100%

### 查看覆盖率

```bash
# 生成 HTML 覆盖率报告
pytest tests/ --cov=src/fastapi_easy --cov-report=html

# 打开报告
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

---

## 🔐 安全检查

### Bandit 安全检查

```bash
bandit -r src/fastapi_easy
```

检查项:
- SQL 注入
- 硬编码密码
- 不安全的随机数
- 不安全的反序列化

### Safety 依赖检查

```bash
safety check
```

检查项:
- 已知的安全漏洞
- 过时的依赖版本

---

## 📈 改进建议

### 短期 (已完成)
- ✅ GitHub Actions 工作流
- ✅ Pre-commit 配置
- ✅ pyproject.toml 配置

### 中期 (后续)
- [ ] 增加覆盖率到 80%+
- [ ] 添加性能基准测试
- [ ] 添加集成测试

### 长期 (可选)
- [ ] Docker 镜像构建
- [ ] 自动发布到 PyPI
- [ ] 性能监控

---

## 🎯 预期效果

### 代码质量提升
- ✅ 自动检查代码格式
- ✅ 自动检查类型
- ✅ 自动检查安全漏洞
- ✅ 自动运行测试

### 开发体验改善
- ✅ 快速反馈
- ✅ 自动修复建议
- ✅ 覆盖率追踪
- ✅ 安全保证

### 项目质量提升
- ✅ 代码一致性
- ✅ 测试覆盖
- ✅ 安全性
- ✅ 可维护性

---

## 📝 常见问题

### Q: 如何跳过 pre-commit 钩子?
A: 使用 `--no-verify` 标志:
```bash
git commit --no-verify -m "your message"
```

### Q: 如何更新 pre-commit 钩子?
A: 运行:
```bash
pre-commit autoupdate
```

### Q: 如何在本地运行完整的 CI/CD 检查?
A: 运行:
```bash
# 运行 pre-commit
pre-commit run --all-files

# 运行测试
pytest tests/ --cov=src/fastapi_easy

# 运行安全检查
bandit -r src/fastapi_easy
safety check
```

### Q: 为什么我的 PR 没有通过检查?
A: 检查 GitHub Actions 的日志:
1. 打开 Pull Request
2. 点击 "Checks" 标签
3. 查看失败的工作流
4. 点击 "Details" 查看日志

---

## 🔗 相关资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Pre-commit 文档](https://pre-commit.com/)
- [Black 文档](https://black.readthedocs.io/)
- [pytest 文档](https://docs.pytest.org/)
- [MyPy 文档](https://mypy.readthedocs.io/)

---

**最后更新**: 2025-11-30  
**维护者**: Cascade AI
