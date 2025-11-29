# CLI 工具

FastAPI-Easy 提供了命令行工具，用于快速初始化项目、生成代码和管理应用。

---

## 什么是 CLI 工具？

CLI（Command Line Interface）工具提供了以下功能：

- ✅ **项目初始化** - 快速创建新项目
- ✅ **代码生成** - 自动生成 CRUD 路由
- ✅ **项目管理** - 管理项目配置和依赖
- ✅ **版本管理** - 查看版本信息

---

## 安装

```bash
pip install fastapi-easy[cli]
```

---

## 基础命令

### 1. 查看帮助

```bash
# 查看所有命令
fastapi-easy --help

# 查看特定命令帮助
fastapi-easy init --help
fastapi-easy generate --help
```

### 2. 查看版本

```bash
fastapi-easy --version
```

---

## 项目初始化

### 基础用法

```bash
# 创建新项目
fastapi-easy init --name my_project

# 在指定路径创建项目
fastapi-easy init --name my_project --path ./projects
```

### 交互式初始化

```bash
fastapi-easy init

# 输入项目名称
Project name: my_app

# 项目创建完成
✅ Project 'my_app' created successfully at ./my_app
```

### 生成的项目结构

```
my_project/
├── src/
│   └── main.py              # FastAPI 应用入口
├── tests/
│   └── __init__.py          # 测试目录
├── docs/
│   └── __init__.py          # 文档目录
├── requirements.txt         # 依赖列表
└── README.md               # 项目说明
```

### 生成的文件内容

**src/main.py**:
```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter

app = FastAPI()

# Your routes here

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**requirements.txt**:
```
fastapi>=0.100.0
fastapi-easy>=1.0.0
sqlalchemy>=2.0.0
uvicorn>=0.23.0
pydantic>=2.0.0
```

---

## 代码生成

### 基础用法

```bash
# 生成 CRUD 路由
fastapi-easy generate --model Item --fields "name:str,price:float,description:str"
```

### 交互式生成

```bash
fastapi-easy generate

# 输入模型名称
Model name: Product

# 输入字段（逗号分隔）
Fields (comma-separated): name, price, stock, category

# 生成完成
✅ CRUD router generated for model 'Product'
```

### 生成的代码

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional

class Item(BaseModel):
    id: Optional[int] = None
    name: str
    price: float
    description: str
    
    model_config = ConfigDict(from_attributes=True)

# CRUD Router
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAsyncBackend

router = CRUDRouter(
    schema=Item,
    backend=backend,
    prefix="/items",
    tags=["items"]
)
```

---

## 完整工作流

### 1. 创建项目

```bash
fastapi-easy init --name ecommerce_api
cd ecommerce_api
```

### 2. 生成模型

```bash
# 生成 Product 模型
fastapi-easy generate --model Product --fields "name,price,stock,category"

# 生成 Order 模型
fastapi-easy generate --model Order --fields "product_id,quantity,total_price,status"

# 生成 User 模型
fastapi-easy generate --model User --fields "username,email,password,role"
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 运行应用

```bash
python src/main.py

# 输出：
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### 5. 访问 API

```bash
# 查看 API 文档
curl http://localhost:8000/docs

# 创建项目
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Apple", "price": 1.5, "description": "Fresh apple"}'

# 获取所有项目
curl http://localhost:8000/items

# 获取单个项目
curl http://localhost:8000/items/1

# 更新项目
curl -X PUT http://localhost:8000/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Red Apple", "price": 2.0}'

# 删除项目
curl -X DELETE http://localhost:8000/items/1
```

---

## 高级用法

### 1. 自定义项目模板

```bash
# 使用自定义模板创建项目
fastapi-easy init --name my_project --template advanced
```

### 2. 生成多个模型

```bash
# 创建脚本 generate_models.sh
#!/bin/bash

fastapi-easy generate --model User --fields "username,email,password"
fastapi-easy generate --model Post --fields "title,content,author_id"
fastapi-easy generate --model Comment --fields "text,post_id,author_id"

# 运行脚本
chmod +x generate_models.sh
./generate_models.sh
```

### 3. 配置管理

```bash
# 查看配置
fastapi-easy config --show

# 设置配置
fastapi-easy config --set database_url "postgresql://user:pass@localhost/db"

# 重置配置
fastapi-easy config --reset
```

---

## 常用命令参考

| 命令 | 说明 | 示例 |
|------|------|------|
| `init` | 初始化项目 | `fastapi-easy init --name my_app` |
| `generate` | 生成 CRUD 路由 | `fastapi-easy generate --model Item --fields "name,price"` |
| `config` | 管理配置 | `fastapi-easy config --show` |
| `--version` | 显示版本 | `fastapi-easy --version` |
| `--help` | 显示帮助 | `fastapi-easy --help` |

---

## 最佳实践

### 1. 使用版本控制

```bash
# 初始化 Git 仓库
cd my_project
git init

# 添加 .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".env" >> .gitignore
echo "venv/" >> .gitignore

# 提交初始代码
git add .
git commit -m "Initial commit"
```

### 2. 虚拟环境管理

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 环境变量配置

```bash
# 创建 .env 文件
echo "DATABASE_URL=sqlite:///./test.db" > .env
echo "DEBUG=True" >> .env

# 在应用中使用
from dotenv import load_dotenv
import os

load_dotenv()
database_url = os.getenv("DATABASE_URL")
```

---

## 常见问题

**Q: 如何更新 fastapi-easy？**

A: 使用 pip 更新：
```bash
pip install --upgrade fastapi-easy
```

**Q: 如何卸载 CLI 工具？**

A: 使用 pip 卸载：
```bash
pip uninstall fastapi-easy
```

**Q: 如何自定义生成的代码？**

A: 编辑生成的文件或使用自定义模板。

**Q: 如何在 CI/CD 中使用 CLI？**

A: 在 CI/CD 脚本中调用 CLI 命令：
```bash
#!/bin/bash
fastapi-easy init --name my_app
cd my_app
pip install -r requirements.txt
python -m pytest
```

---

## 脚本示例

### 快速启动脚本

**start.sh**:
```bash
#!/bin/bash

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行应用
python src/main.py
```

### 项目生成脚本

**setup_project.sh**:
```bash
#!/bin/bash

PROJECT_NAME=$1

# 创建项目
fastapi-easy init --name $PROJECT_NAME

# 进入项目目录
cd $PROJECT_NAME

# 生成常用模型
fastapi-easy generate --model User --fields "username,email,password"
fastapi-easy generate --model Post --fields "title,content,author_id"

# 初始化 Git
git init
git add .
git commit -m "Initial commit"

echo "✅ Project '$PROJECT_NAME' setup complete!"
```

使用方法：
```bash
chmod +x setup_project.sh
./setup_project.sh my_app
```

---

## 相关资源

- [Click 文档](https://click.palletsprojects.com/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Python 虚拟环境](https://docs.python.org/3/tutorial/venv.html)

---

**完成！** 所有扩展功能文档已编写。
