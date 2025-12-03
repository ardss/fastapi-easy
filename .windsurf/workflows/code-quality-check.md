# /代码质量检查

在提交前自动检查和改进代码质量的工作流。

## 步骤

1. **使用 Black 运行代码格式检查**

   ```bash
   black --check src/fastapi_easy
   ```

2. **使用 isort 运行 import 排序检查**

   ```bash
   isort --check-only src/fastapi_easy
   ```

3. **使用 flake8 运行代码风格检查**

   ```bash
   flake8 src/fastapi_easy --count --select=E9,F63,F7,F82 --show-source --statistics
   ```

4. **使用 mypy 运行类型检查**

   ```bash
   mypy src/fastapi_easy --ignore-missing-imports
   ```

5. **如果任何检查失败，询问用户是否要自动修复：**
   - 对于 Black: `black src/fastapi_easy`
   - 对于 isort: `isort src/fastapi_easy`
   - 对于 flake8: 显示需要手动修复的具体问题
   - 对于 mypy: 显示需要手动修复的类型错误

6. **修复后，重新运行所有检查以验证**

7. **生成总结报告：**
   - 列出所有通过的检查
   - 列出任何剩余的问题
   - 提供改进建议

## 使用的工具

- **Black**: 代码格式化工具（PEP 8 合规）
- **isort**: Import 语句排序工具
- **flake8**: 代码风格检查工具
- **mypy**: 静态类型检查工具

## 最佳实践

- 提交代码前运行此工作流
- 尽可能自动修复格式问题
- 手动处理类型错误和代码风格问题
- 保持项目中代码风格的一致性
- 质量检查后使用有意义的提交消息
