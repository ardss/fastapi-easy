# 任务 1.1: 权限控制模块 - 开发启动

**启动日期**: 2025-11-28  
**任务**: 实现权限控制模块  
**优先级**: 🔴 极高  
**状态**: 🚀 开发中

---

## 任务确认

### 任务目标

实现一个完整的、生产就绪的权限控制系统，让库自动处理权限控制。

### 核心功能

1. ✅ JWT 认证 (Token 生成、验证、刷新)
2. ✅ 角色权限 (Role-Based Access Control)
3. ✅ 资源权限 (Resource-Based Access Control)
4. ✅ 自动应用到所有 CRUD 路由

### 预计时间

**1-2 周** (10-16 天)

---

## 现有代码分析

### 已存在的实现

#### 1. 权限基础 (core/permissions.py)
- ✅ Permission 枚举 (CREATE, READ, UPDATE, DELETE, ADMIN)
- ✅ Role 枚举 (ADMIN, EDITOR, VIEWER, USER)
- ✅ PermissionDeniedError 异常
- ✅ RoleBasedAccessControl 类 (基础实现)

**现有代码**:
```python
class Permission(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ADMIN = "admin"

class RoleBasedAccessControl:
    def has_permission(self, role: str, permission: str) -> bool:
        # 检查角色是否有权限
```

#### 2. 配置系统 (core/config.py)
- ✅ CRUDConfig 类
- ❌ 缺少权限配置

**需要扩展**:
```python
@dataclass
class CRUDConfig:
    enable_permissions: bool = False  # 新增
    permission_rules: Dict[str, List[str]] = None  # 新增
```

#### 3. 错误处理 (core/errors.py)
- ✅ AppError 基类
- ✅ ErrorCode 枚举
- ✅ PermissionDeniedError (403)

### 现有项目结构

```
src/fastapi_easy/
├── core/
│   ├── permissions.py (已存在，需扩展)
│   ├── config.py (已存在，需扩展)
│   ├── crud_router.py (需修改)
│   ├── errors.py (已存在)
│   └── ...
├── security/ (空目录，待填充)
│   ├── __init__.py (待创建)
│   ├── jwt_auth.py (待创建)
│   ├── models.py (待创建)
│   ├── decorators.py (待创建)
│   └── exceptions.py (待创建)
└── ...
```

---

## 开发计划

### 阶段 1: 设计和规划 (1-2 天) ✅ 已完成

- ✅ 权限模型: 基于操作 (read/create/update/delete)
- ✅ 权限存储: 配置文件 (第一版本)
- ✅ 用户信息: JWT Token (第一版本)
- ✅ 错误处理: 403 Forbidden, 401 Unauthorized
- ✅ 权限检查位置: 路由级别

### 阶段 2: 核心模块实现 (3-5 天) 🚀 开始

**2.1 创建项目结构**
- [ ] 创建 security 模块文件

**2.2 实现 JWT 认证**
- [ ] JWTAuth 类
- [ ] 登录端点
- [ ] 刷新端点
- [ ] 登出端点

**2.3 实现角色权限检查**
- [ ] RoleBasedPermission 类
- [ ] 权限装饰器

**2.4 实现自动应用到 CRUD 路由**
- [ ] 修改 CRUDRouter
- [ ] 修改 CRUDConfig

### 阶段 3: 安全性实现 (2-3 天)

- [ ] 密码哈希
- [ ] Token 签名
- [ ] 登录尝试限制
- [ ] 权限审计日志

### 阶段 4: 测试 (2-3 天)

- [ ] 单元测试
- [ ] 集成测试
- [ ] 安全测试

### 阶段 5: 文档和示例 (1-2 天)

- [ ] 权限控制文档
- [ ] 权限配置文档
- [ ] 安全最佳实践文档
- [ ] 示例代码

### 阶段 6: 代码审查和优化 (1 天)

- [ ] 代码质量检查
- [ ] 性能优化
- [ ] 安全审计

---

## 立即开始的任务

### 第一步: 创建 security 模块文件

需要创建以下文件:

1. `src/fastapi_easy/security/__init__.py`
2. `src/fastapi_easy/security/models.py` - 数据模型
3. `src/fastapi_easy/security/jwt_auth.py` - JWT 认证
4. `src/fastapi_easy/security/exceptions.py` - 异常定义
5. `src/fastapi_easy/security/decorators.py` - 装饰器

### 第二步: 扩展现有代码

1. 修改 `core/config.py` - 添加权限配置
2. 修改 `core/permissions.py` - 扩展权限检查
3. 修改 `core/crud_router.py` - 集成权限检查

### 第三步: 实现 JWT 认证

1. 实现 JWTAuth 类
2. 实现登录端点
3. 实现刷新端点
4. 实现登出端点

---

## 关键决策已确定

✅ **权限模型**: 基于操作 (read/create/update/delete)
✅ **权限存储**: 配置文件 (第一版本)
✅ **用户信息**: JWT Token (第一版本)
✅ **错误处理**: 403 Forbidden (无权限), 401 Unauthorized (未认证)
✅ **权限检查位置**: 路由级别 (最早)

---

## 依赖库

需要的外部库:

```
PyJWT>=2.8.0  # JWT Token 处理
bcrypt>=4.0.0  # 密码哈希
python-dotenv>=1.0.0  # 环境变量
```

---

## 下一步行动

**立即开始**:

1. 创建 security 模块文件
2. 实现 JWT 认证基础
3. 实现权限检查基础
4. 编写单元测试

**预计完成时间**: 3-5 天

---

**状态**: 🚀 开发中  
**最后更新**: 2025-11-28  
**下一个检查点**: 完成阶段 2.1 (创建项目结构)
