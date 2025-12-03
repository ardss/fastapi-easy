---
description: 文档分析与同步工作流 - 分析项目文档与代码的一致性，并生成更新建议
---

# 文档分析与同步工作流

## 目标

分析 FastAPI-Easy 项目的文档与代码的一致性，识别过时文档，并生成更新建议。

## 前置条件

- 项目已初始化
- 所有源代码已完成
- 文档目录存在

## 工作流步骤

### 1. 文档结构分析

// turbo
```bash
# 分析文档目录结构
find docs -type f -name "*.md" | wc -l
echo "=== 文档统计 ==="
find docs -type f -name "*.md" | head -20
```

### 2. 代码与文档映射分析

使用 Windsurf Fast Context 进行智能扫描：

```bash
# 扫描主要功能模块
echo "=== 扫描核心功能 ==="
grep -r "class CRUDRouter" src/fastapi_easy/core/ --include="*.py"
grep -r "def " src/fastapi_easy/core/crud_router.py | head -10
```

### 3. 文档过时性检测

使用 Fast Context 扫描：

**扫描 1: 检测文档中的过时 API**
- 搜索: "已弃用的 API 或功能"
- 查找: 文档中提到的已移除功能
- 生成: 过时文档列表

**扫描 2: 检测文档中的版本不匹配**
- 搜索: "版本号和功能对应关系"
- 查找: 文档中的版本与实际版本不符
- 生成: 版本不匹配列表

**扫描 3: 检测文档中的代码示例错误**
- 搜索: "代码示例和实现的差异"
- 查找: 文档示例与实际代码不符
- 生成: 错误示例列表

### 4. 文档覆盖率分析

```bash
# 检查哪些功能没有文档
echo "=== 检查功能覆盖 ==="
grep -r "def " src/fastapi_easy/core/*.py | wc -l
grep -r "def " docs/ | wc -l
```

### 5. 生成分析报告

生成 `DOCUMENTATION_ANALYSIS_REPORT.md`，包含：

- 📊 文档统计
  - 总文档数
  - 各类别文档数
  - 过时文档数

- 🔍 一致性分析
  - API 一致性评分
  - 示例代码准确性
  - 版本对应关系

- ⚠️ 问题清单
  - 过时文档列表
  - 缺失文档列表
  - 错误示例列表

- 📝 更新建议
  - 优先级排序
  - 工作量估计
  - 更新计划

### 6. 生成更新计划

根据分析结果，生成 `DOCUMENTATION_UPDATE_PLAN.md`：

- 第 1 阶段: 修复关键文档 (1-2 周)
  - [ ] 更新 API 文档
  - [ ] 修复代码示例
  - [ ] 更新版本信息

- 第 2 阶段: 补充缺失文档 (2-3 周)
  - [ ] 添加新功能文档
  - [ ] 补充最佳实践
  - [ ] 完善 FAQ

- 第 3 阶段: 文档优化 (1-2 周)
  - [ ] 改进文档结构
  - [ ] 增强可读性
  - [ ] 添加图表和示例

### 7. 创建文档更新工作流

创建 `doc-update.md` 工作流，用于快速更新文档：

```bash
# 运行文档更新工作流
/doc-update
```

## 输出文件

- `DOCUMENTATION_ANALYSIS_REPORT.md` - 详细分析报告
- `DOCUMENTATION_UPDATE_PLAN.md` - 更新计划
- `DOCUMENTATION_SYNC_STATUS.md` - 同步状态跟踪

## 预期结果

✅ 完成后应该有：

- 清晰的文档与代码一致性评分
- 过时文档的完整清单
- 缺失文档的优先级列表
- 具体的更新计划和时间表
- 改进后的文档覆盖率

## 后续步骤

1. 根据分析报告更新文档
2. 建立文档更新流程
3. 定期进行文档同步检查
4. 在 CI/CD 中集成文档检查

## 相关工作流

- `/code-quality-check` - 代码质量检查
- `/run-tests-and-fix` - 测试和修复
- `/doc-update` - 文档更新 (待创建)

