# FastAPI-Easy 文档指南

本文档说明如何构建、验证和部署 FastAPI-Easy 文档。

---

## 📚 文档结构

```
docs/
├── index.md                    # 首页
├── getting-started.md          # 快速开始
├── guides/                     # 用户指南 (11 个主题)
│   ├── index.md               # 用户指南概览
│   ├── quick-start.md
│   ├── database-integration.md
│   ├── querying.md
│   ├── permissions-basic.md
│   ├── error-handling.md
│   ├── hooks-advanced.md
│   ├── caching.md
│   ├── migrations.md
│   ├── graphql-integration.md
│   └── websocket-integration.md
├── reference/                  # 参考文档
│   ├── api.md
│   ├── architecture.md
│   ├── configuration.md
│   └── ...
├── security/                   # 安全指南
│   ├── index.md
│   ├── authentication.md
│   └── permissions.md
├── development/                # 开发指南
│   ├── contributing.md
│   └── testing.md
└── stylesheets/               # 自定义样式
    └── extra.css
```

---

## 🚀 本地构建

### 前置要求

```bash
# 安装 Python 3.10+
python --version

# 安装依赖
pip install mkdocs mkdocs-material pymdown-extensions mkdocstrings[python]
```

### 构建文档

#### Linux/macOS

```bash
# 方法 1: 使用脚本
chmod +x scripts/build-docs.sh
./scripts/build-docs.sh

# 方法 2: 直接使用 mkdocs
mkdocs serve
```

#### Windows

```bash
# 方法 1: 使用脚本
scripts\build-docs.bat

# 方法 2: 直接使用 mkdocs
mkdocs serve
```

### 访问文档

打开浏览器访问: http://localhost:8000

---

## 🔨 构建输出

```bash
# 生成静态 HTML 文件
mkdocs build

# 输出目录
site/
├── index.html
├── getting-started/
├── guides/
├── reference/
├── security/
├── development/
└── ...
```

---

## ✅ 验证文档

### 语法检查

```bash
# 使用 mkdocs 的严格模式
mkdocs build --strict

# 检查 Markdown 格式
pip install markdownlint-cli
markdownlint docs/**/*.md
```

### 链接检查

```bash
# 检查文档中的链接
pip install markdown-link-check
find docs -name "*.md" -exec markdown-link-check {} \;
```

### 拼写检查

```bash
# 检查拼写
pip install pyspelling
pyspelling -c .spellcheck.yaml
```

---

## 🌐 自动部署

### GitHub Actions 工作流

文档在以下情况下自动构建和部署:

1. **推送到 main/master 分支** - 当 docs 目录或 mkdocs.yml 变更时
2. **拉取请求** - 验证文档构建成功

### 工作流配置

位置: `.github/workflows/deploy-docs.yml`

**功能**:
- ✅ 验证 Markdown 结构
- ✅ 构建文档
- ✅ 检查输出统计
- ✅ 上传到 GitHub Pages
- ✅ 发送通知

### 部署 URL

- **主站**: https://ardss.github.io/fastapi-easy/
- **分支**: https://ardss.github.io/fastapi-easy/branch-name/

---

## 📝 编写文档

### 文档模板

```markdown
# 页面标题

**预计阅读时间**: X 分钟

---

## 简介

简要介绍本页内容。

---

## 核心概念

### 概念 1

详细说明...

### 概念 2

详细说明...

---

## 示例代码

\`\`\`python
# 代码示例
\`\`\`

---

## 最佳实践

- ✅ 做法 1
- ✅ 做法 2
- ❌ 不要做 1

---

## 常见问题

### Q: 问题 1？

**A**: 答案...

---

## 下一步

- **[相关主题](link)** - 描述
- **[另一个主题](link)** - 描述

---

## 参考

- [外部链接](url)
- [API 文档](../reference/api.md)
```

### 最佳实践

1. **清晰的结构** - 使用标题和子标题组织内容
2. **代码示例** - 提供可运行的代码示例
3. **链接** - 链接到相关文档和外部资源
4. **表格** - 使用表格展示对比信息
5. **提示框** - 使用 admonition 突出重要信息

### Markdown 扩展

```markdown
# 提示框

!!! note
    这是一个提示框

!!! warning
    这是一个警告框

!!! danger
    这是一个危险警告

# 代码标签

=== "Python"

    \`\`\`python
    # Python 代码
    \`\`\`

=== "JavaScript"

    \`\`\`javascript
    // JavaScript 代码
    \`\`\`

# 任务列表

- [x] 完成的任务
- [ ] 未完成的任务
```

---

## 🎨 自定义样式

### 修改主题

编辑 `mkdocs.yml`:

```yaml
theme:
  name: material
  language: zh
  palette:
    - scheme: default
      primary: indigo
      accent: deep purple
  font:
    text: Inter
    code: JetBrains Mono
```

### 自定义 CSS

编辑 `docs/stylesheets/extra.css`:

```css
/* 自定义样式 */
:root {
  --md-primary-fg-color: #3f51b5;
  --md-accent-fg-color: #7c4dff;
}
```

---

## 📊 文档统计

### 当前文档

| 类别 | 数量 | 状态 |
|------|------|------|
| 首页 | 1 | ✅ |
| 快速开始 | 1 | ✅ |
| 用户指南 | 11 | ✅ |
| 参考文档 | 4 | ✅ |
| 安全指南 | 3 | ✅ |
| 开发指南 | 2 | ✅ |
| **总计** | **22** | **✅** |

### 文档质量

- **覆盖率**: 100% (所有主要功能)
- **更新频率**: 每次发布更新
- **链接检查**: 自动验证
- **拼写检查**: 定期检查

---

## 🔄 更新流程

### 1. 编写文档

```bash
# 创建新文档
touch docs/guides/new-topic.md

# 编辑文档
vim docs/guides/new-topic.md
```

### 2. 本地验证

```bash
# 启动本地服务器
mkdocs serve

# 在浏览器中查看: http://localhost:8000
```

### 3. 更新导航

编辑 `mkdocs.yml` 的 `nav` 部分:

```yaml
nav:
  - "首页": index.md
  - "用户指南":
    - "新主题": guides/new-topic.md
```

### 4. 提交变更

```bash
git add docs/ mkdocs.yml
git commit -m "docs: 添加新主题"
git push
```

### 5. 自动部署

GitHub Actions 会自动:
- 构建文档
- 验证链接
- 部署到 GitHub Pages

---

## 🐛 故障排查

### 问题: 文档构建失败

**解决方案**:
1. 检查 Python 版本: `python --version` (需要 3.10+)
2. 重新安装依赖: `pip install -r requirements.txt`
3. 检查 mkdocs.yml 语法: `mkdocs build --strict`

### 问题: 链接断裂

**解决方案**:
1. 检查文件是否存在
2. 检查链接路径是否正确
3. 使用相对路径: `../reference/api.md`

### 问题: 样式不正确

**解决方案**:
1. 清除缓存: `rm -rf site/`
2. 重新构建: `mkdocs build`
3. 检查 CSS 文件: `docs/stylesheets/extra.css`

---

## 📚 相关资源

- **[MkDocs 官方文档](https://www.mkdocs.org/)**
- **[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)**
- **[Markdown 指南](https://www.markdownguide.org/)**
- **[GitHub Pages](https://pages.github.com/)**

---

## 🤝 贡献文档

我们欢迎文档贡献！请遵循以下步骤:

1. Fork 项目
2. 创建分支: `git checkout -b docs/your-topic`
3. 编写文档
4. 本地验证: `mkdocs serve`
5. 提交 PR

详见 [贡献指南](docs/development/contributing.md)

---

## 📞 联系我们

- **GitHub Issues**: [报告问题](https://github.com/ardss/fastapi-easy/issues)
- **GitHub Discussions**: [讨论](https://github.com/ardss/fastapi-easy/discussions)
- **Email**: 1339731209@qq.com

---

**最后更新**: 2025-12-03  
**维护者**: FastAPI-Easy Team
