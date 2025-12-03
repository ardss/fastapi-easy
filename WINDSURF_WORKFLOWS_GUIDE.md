# Windsurf Workflows Guide

本指南说明如何在 Windsurf IDE 中使用工作流来自动化测试和代码质量检查。

## 概述

Windsurf 工作流是一种定义重复任务序列的方式，使用 Cascade AI 来自动执行这些任务。工作流存储为 Markdown 文件，可以通过 `/workflow-name` 命令调用。

## 可用工作流

### 1. `/run-tests-and-fix`

自动运行测试并修复错误，确保代码质量。

**用途**:
- 在提交前运行所有测试
- 自动修复简单的测试失败
- 生成测试报告

**调用方式**:
```
在 Cascade 中输入: /run-tests-and-fix
```

**工作流步骤**:
1. 运行所有测试
2. 分析测试结果
3. 对每个失败的测试进行修复
4. 重新运行完整测试套件
5. 生成总结报告

**示例输出**:
```
[PASS] 992 tests passed
[FAIL] 0 tests failed
[SKIP] 23 tests skipped

✅ All tests passed! Ready to commit.
```

### 2. `/code-quality-check`

检查并改进代码质量。

**用途**:
- 检查代码格式 (Black)
- 检查 import 排序 (isort)
- 检查代码风格 (flake8)
- 检查类型注解 (mypy)

**调用方式**:
```
在 Cascade 中输入: /code-quality-check
```

**工作流步骤**:
1. 运行 Black 格式检查
2. 运行 isort import 检查
3. 运行 flake8 linting
4. 运行 mypy 类型检查
5. 自动修复可修复的问题
6. 生成质量报告

**示例输出**:
```
✅ Black: All files formatted correctly
✅ isort: All imports sorted correctly
⚠️  flake8: 5 style issues found (manual fix required)
⚠️  mypy: 3 type errors found (manual fix required)

Recommendations:
- Fix flake8 issues in core/crud_router.py
- Add type hints to migrations/engine.py
```

## 工作流存储位置

工作流文件存储在以下位置:

```
.windsurf/
└── workflows/
    ├── run-tests-and-fix.md
    └── code-quality-check.md
```

## 如何使用工作流

### 在 Cascade 中调用工作流

1. 打开 Cascade 面板
2. 输入 `/` 查看可用工作流
3. 选择要执行的工作流，例如 `/run-tests-and-fix`
4. Cascade 会按照工作流定义的步骤执行任务

### 创建自定义工作流

1. 在 Cascade 中点击 `Customizations` (右上角)
2. 选择 `Workflows` 面板
3. 点击 `+ Workflow` 按钮
4. 输入工作流名称和步骤
5. 保存工作流

### 工作流文件格式

工作流是 Markdown 文件，包含:
- 标题 (# /workflow-name)
- 描述
- 步骤列表

**示例**:
```markdown
# /my-workflow

Description of what this workflow does.

## Steps

1. First step description
   ```bash
   command to run
   ```

2. Second step description
   ```bash
   another command
   ```

3. For each item, do the following:
   a. Sub-step 1
   b. Sub-step 2
```

## 最佳实践

### 1. 在提交前运行工作流

```
1. 修改代码
2. 运行 /code-quality-check (检查代码质量)
3. 运行 /run-tests-and-fix (运行测试)
4. 提交代码
```

### 2. 组合工作流

可以在一个工作流中调用另一个工作流:

```markdown
# /pre-commit-check

Complete pre-commit quality check.

## Steps

1. Run code quality checks
   /code-quality-check

2. Run tests and fix errors
   /run-tests-and-fix

3. If all checks pass, you're ready to commit!
```

### 3. 工作流命名约定

- 使用小写字母和连字符
- 使用描述性名称
- 示例: `/run-tests-and-fix`, `/code-quality-check`, `/deploy-to-production`

## 故障排查

### 工作流不显示

**问题**: 创建的工作流不在 Cascade 中显示

**解决方案**:
1. 确保文件在 `.windsurf/workflows/` 目录中
2. 确保文件名为 `workflow-name.md`
3. 确保文件格式正确 (Markdown)
4. 重启 Windsurf IDE

### 工作流执行失败

**问题**: 工作流执行时出错

**解决方案**:
1. 检查工作流中的命令是否正确
2. 确保所有依赖都已安装
3. 查看 Cascade 的错误消息
4. 尝试手动运行命令来调试

### 工作流太长

**问题**: 工作流文件超过 12000 字符限制

**解决方案**:
1. 将工作流分成多个较小的工作流
2. 在一个工作流中调用另一个工作流
3. 简化步骤描述

## 高级用法

### 条件执行

在工作流中添加条件逻辑:

```markdown
## Steps

1. Run tests
   ```bash
   python -m pytest tests/
   ```

2. If tests pass, run code quality check
   /code-quality-check

3. If all checks pass, ask user to commit
```

### 循环执行

对多个项目执行相同操作:

```markdown
## Steps

1. For EACH file in src/fastapi_easy, do the following:
   a. Check if file has proper type annotations
   b. If not, add type annotations
   c. Run tests to verify changes
```

### 调用外部工具

在工作流中集成外部工具:

```markdown
## Steps

1. Run security scan
   ```bash
   bandit -r src/fastapi_easy
   ```

2. Run dependency check
   ```bash
   safety check
   ```

3. Generate report
   ```bash
   pip-audit
   ```
```

## 工作流示例

### 完整的提交前检查

```markdown
# /pre-commit

Complete quality check before committing.

## Steps

1. Format code
   ```bash
   black src/fastapi_easy
   isort src/fastapi_easy
   ```

2. Run code quality checks
   /code-quality-check

3. Run tests
   /run-tests-and-fix

4. If all checks pass, generate commit message
   - Summarize changes
   - List files modified
   - Suggest commit message

5. Ask user to review and commit
```

### 部署工作流

```markdown
# /deploy-production

Deploy to production environment.

## Steps

1. Verify all tests pass
   ```bash
   python -m pytest tests/ -v
   ```

2. Check code quality
   /code-quality-check

3. Build application
   ```bash
   pip install -e .
   ```

4. Run pre-deployment checks
   ```bash
   python -m pytest tests/e2e/ -v
   ```

5. Deploy to production
   ```bash
   git push origin master
   ```

6. Verify deployment
   ```bash
   curl https://api.example.com/health
   ```
```

## 相关文档

- [Windsurf 官方工作流文档](https://docs.windsurf.com/windsurf/cascade/workflows)
- [Cascade 使用指南](https://docs.windsurf.com/windsurf/cascade)
- [FastAPI-Easy 开发指南](docs/DEVELOPMENT.md)

## 常见问题

### Q: 工作流可以做什么?

A: 工作流可以:
- 运行命令和脚本
- 调用其他工作流
- 执行代码分析和修复
- 生成报告
- 与用户交互

### Q: 工作流有什么限制?

A: 工作流的限制:
- 单个工作流文件最大 12000 字符
- 不能直接修改 IDE 设置
- 不能访问 IDE 外的文件系统

### Q: 如何调试工作流?

A: 调试工作流:
1. 在 Cascade 中逐步执行
2. 查看每一步的输出
3. 手动运行命令来测试
4. 检查工作流文件的语法

### Q: 可以共享工作流吗?

A: 可以:
1. 将工作流文件提交到 Git 仓库
2. 团队成员会自动看到工作流
3. 工作流存储在 `.windsurf/workflows/` 目录中

## 支持

如有问题或建议，请:
1. 查看 [Windsurf 文档](https://docs.windsurf.com)
2. 提交 Issue 到 GitHub
3. 联系 FastAPI-Easy 团队

---

**最后更新**: 2025-12-03  
**版本**: 1.0  
**维护者**: FastAPI-Easy Team
