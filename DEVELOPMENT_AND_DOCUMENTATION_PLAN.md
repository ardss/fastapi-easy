# 开发和文档更新计划

**计划日期**: 2025-11-28  
**目标**: 完成 Phase 2 优化并更新文档  
**预期时间**: 2-3 周  
**目标评分**: 8.8/10

---

## 第一部分: 开发计划

### Phase 2: 模块化重构 (第 1-3 周)

#### Week 1: 安全配置管理 + 权限检查引擎

##### Task 2.1: 安全配置管理

**时间**: 2-3 小时  
**优先级**: 🔴 高

**实现步骤**:

1. **创建 `security_config.py`** (50-100 行)
```python
from typing import Optional
from .jwt_auth import JWTAuth
from .permission_loader import PermissionLoader
from .resource_checker import ResourcePermissionChecker
from .audit_log import AuditLogger

class SecurityConfig:
    """Unified security configuration"""
    
    def __init__(
        self,
        jwt_auth: JWTAuth,
        permission_loader: Optional[PermissionLoader] = None,
        resource_checker: Optional[ResourcePermissionChecker] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.jwt_auth = jwt_auth
        self.permission_loader = permission_loader
        self.resource_checker = resource_checker
        self.audit_logger = audit_logger
    
    def validate(self) -> None:
        """Validate configuration"""
        if not self.jwt_auth:
            raise ValueError("jwt_auth is required")
    
    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """Create config from environment variables"""
        jwt_auth = JWTAuth()
        return cls(jwt_auth=jwt_auth)
```

2. **编写单元测试** (15-20 个测试)
   - [ ] 初始化测试
   - [ ] 验证测试
   - [ ] 环境变量测试

3. **验证**:
   - [ ] 所有测试通过
   - [ ] 代码覆盖率 ≥ 95%

---

##### Task 2.2: 权限检查引擎

**时间**: 2-3 小时  
**优先级**: 🔴 高

**实现步骤**:

1. **创建 `permission_engine.py`** (100-150 行)
```python
from typing import Optional
from .permission_loader import PermissionLoader
from .resource_checker import ResourcePermissionChecker
from .permission_loader import CachedPermissionLoader

class PermissionEngine:
    """Permission checking engine"""
    
    def __init__(
        self,
        permission_loader: PermissionLoader,
        resource_checker: Optional[ResourcePermissionChecker] = None,
        enable_cache: bool = True,
    ):
        if enable_cache:
            self.permission_loader = CachedPermissionLoader(permission_loader)
        else:
            self.permission_loader = permission_loader
        
        self.resource_checker = resource_checker
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if user has permission"""
        # Load permissions
        permissions = await self.permission_loader.load_permissions(user_id)
        
        # Check basic permission
        if permission in permissions:
            return True
        
        # Check resource permission if needed
        if resource_id and self.resource_checker:
            return await self.resource_checker.check_permission(
                user_id, resource_id, permission
            )
        
        return False
```

2. **编写单元测试** (20-25 个测试)
   - [ ] 权限检查测试
   - [ ] 资源权限测试
   - [ ] 缓存测试

3. **验证**:
   - [ ] 所有测试通过
   - [ ] 代码覆盖率 ≥ 95%

---

#### Week 2: 审计日志重构

##### Task 2.3: 审计日志重构

**时间**: 2-3 小时  
**优先级**: 🟡 中

**实现步骤**:

1. **创建 `audit_storage.py`** (100-150 行)
```python
from typing import Protocol, List, Dict, Any, Optional

class AuditStorage(Protocol):
    """Protocol for audit log storage"""
    
    async def save(self, log: Dict[str, Any]) -> None:
        """Save audit log"""
        ...
    
    async def query(self, **filters) -> List[Dict[str, Any]]:
        """Query audit logs"""
        ...
    
    async def delete(self, **filters) -> int:
        """Delete audit logs"""
        ...

class MemoryAuditStorage:
    """In-memory audit log storage"""
    
    def __init__(self, max_logs: int = 10000):
        self.logs: List[Dict[str, Any]] = []
        self.max_logs = max_logs
    
    async def save(self, log: Dict[str, Any]) -> None:
        """Save audit log"""
        self.logs.append(log)
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
    
    async def query(self, **filters) -> List[Dict[str, Any]]:
        """Query audit logs"""
        # Filter implementation
        return self.logs
```

2. **编写单元测试** (15-20 个测试)
   - [ ] 存储测试
   - [ ] 查询测试
   - [ ] 删除测试

3. **验证**:
   - [ ] 所有测试通过
   - [ ] 代码覆盖率 ≥ 95%

---

#### Week 3: 集成测试 + 性能测试

##### Task 2.4: 集成测试

**时间**: 2-3 小时  
**优先级**: 🟡 中

**实现步骤**:

1. **创建集成测试** (20-30 个测试)
   - [ ] 端到端测试
   - [ ] 多模块交互测试
   - [ ] 缓存一致性测试

2. **验证**:
   - [ ] 所有集成测试通过
   - [ ] 无回归问题

---

##### Task 2.5: 性能测试

**时间**: 1-2 小时  
**优先级**: 🟡 中

**实现步骤**:

1. **创建性能测试** (5-10 个测试)
   - [ ] 权限检查性能
   - [ ] 缓存性能
   - [ ] 并发性能

2. **生成性能报告**:
   - [ ] 权限加载: < 1ms
   - [ ] 权限检查: < 1ms
   - [ ] 缓存命中: < 0.1ms

---

### 测试统计

**预期新增测试**: 70-80 个

| 模块 | 测试数 |
|------|--------|
| security_config | 15-20 |
| permission_engine | 20-25 |
| audit_storage | 15-20 |
| 集成测试 | 20-30 |
| 性能测试 | 5-10 |

**总计**: 75-105 个新测试

**预期总测试数**: 195-225 个 (当前 120 个)

---

## 第二部分: 文档更新计划

### 文档结构

```
docs/
├── security/
│   ├── 01-authentication.md (已有)
│   ├── 02-permissions.md (已有)
│   ├── 03-password-and-rate-limit.md (已有)
│   ├── 04-audit-logging.md (已有)
│   ├── 05-best-practices.md (已有)
│   ├── 06-permission-loader.md (新增) ⏳
│   ├── 07-resource-checker.md (新增) ⏳
│   ├── 08-permission-engine.md (新增) ⏳
│   ├── 09-security-config.md (新增) ⏳
│   └── 10-advanced-scenarios.md (新增) ⏳
└── examples/
    └── 06_with_permissions.py (已有)
```

---

### 新增文档详情

#### 文档 1: 权限加载器指南

**文件**: `docs/security/06-permission-loader.md`  
**长度**: 300-400 行  
**内容**:

1. **概述** (50 行)
   - 什么是权限加载器
   - 为什么需要权限加载器
   - 何时使用权限加载器

2. **基础使用** (100 行)
   - StaticPermissionLoader 使用
   - DatabasePermissionLoader 使用
   - 代码示例

3. **高级用法** (100 行)
   - CachedPermissionLoader 使用
   - 自定义加载器实现
   - 性能优化

4. **常见问题** (50 行)
   - 缓存失效
   - 权限更新
   - 性能问题

---

#### 文档 2: 资源检查器指南

**文件**: `docs/security/07-resource-checker.md`  
**长度**: 300-400 行  
**内容**:

1. **概述** (50 行)
   - 什么是资源检查器
   - 为什么需要资源检查器
   - 何时使用资源检查器

2. **基础使用** (100 行)
   - StaticResourceChecker 使用
   - 所有者检查
   - 权限检查

3. **高级用法** (100 行)
   - CachedResourceChecker 使用
   - 自定义检查器实现
   - 性能优化

4. **常见问题** (50 行)
   - 缓存失效
   - 权限更新
   - 性能问题

---

#### 文档 3: 权限检查引擎指南

**文件**: `docs/security/08-permission-engine.md`  
**长度**: 300-400 行  
**内容**:

1. **概述** (50 行)
   - 什么是权限检查引擎
   - 为什么需要权限检查引擎
   - 何时使用权限检查引擎

2. **基础使用** (100 行)
   - 初始化引擎
   - 权限检查
   - 资源权限检查

3. **高级用法** (100 行)
   - 多种权限模型
   - 权限组合逻辑
   - 性能优化

4. **常见问题** (50 行)
   - 权限冲突
   - 缓存问题
   - 性能问题

---

#### 文档 4: 安全配置指南

**文件**: `docs/security/09-security-config.md`  
**长度**: 250-350 行  
**内容**:

1. **概述** (50 行)
   - 什么是安全配置
   - 为什么需要安全配置
   - 何时使用安全配置

2. **基础使用** (100 行)
   - 创建配置
   - 配置验证
   - 环境变量配置

3. **高级用法** (50 行)
   - 多环境配置
   - 配置热更新
   - 配置扩展

4. **常见问题** (50 行)
   - 配置错误
   - 环境变量问题
   - 配置冲突

---

#### 文档 5: 高级场景指南

**文件**: `docs/security/10-advanced-scenarios.md`  
**长度**: 400-500 行  
**内容**:

1. **场景 1: 动态权限加载** (100 行)
   - 从数据库加载权限
   - 权限更新
   - 缓存管理

2. **场景 2: 资源级权限** (100 行)
   - 资源所有者检查
   - 资源级权限
   - 复杂权限逻辑

3. **场景 3: 多租户支持** (100 行)
   - 租户隔离
   - 租户级权限
   - 租户级审计日志

4. **场景 4: 性能优化** (100 行)
   - 缓存策略
   - 批量权限检查
   - 性能监控

---

### 文档统计

**新增文档**: 5 个  
**总行数**: 1,500-2,000 行  
**代码示例**: 50+ 个  
**预期时间**: 8-10 小时

---

## 第三部分: 更新现有文档

### 更新 1: 主文档 (README.md)

**更新内容**:
- [ ] 添加权限加载器链接
- [ ] 添加资源检查器链接
- [ ] 添加权限引擎链接
- [ ] 更新特性列表

**预期时间**: 1 小时

---

### 更新 2: 使用指南索引

**文件**: `docs/security/INDEX.md`  
**更新内容**:
- [ ] 添加新文档链接
- [ ] 更新导航结构
- [ ] 添加学习路径

**预期时间**: 1 小时

---

### 更新 3: 最佳实践指南

**文件**: `docs/security/05-best-practices.md`  
**更新内容**:
- [ ] 添加权限加载器最佳实践
- [ ] 添加资源检查器最佳实践
- [ ] 添加性能优化建议
- [ ] 添加安全建议

**预期时间**: 2 小时

---

## 第四部分: 示例更新

### 更新 1: 权限加载器示例

**文件**: `examples/07_with_permission_loader.py`  
**内容**:
- [ ] 使用 StaticPermissionLoader
- [ ] 使用 CachedPermissionLoader
- [ ] 自定义加载器
- [ ] 完整应用示例

**预期时间**: 1-2 小时

---

### 更新 2: 资源检查器示例

**文件**: `examples/08_with_resource_checker.py`  
**内容**:
- [ ] 使用 StaticResourceChecker
- [ ] 资源所有者检查
- [ ] 资源权限检查
- [ ] 完整应用示例

**预期时间**: 1-2 小时

---

### 更新 3: 权限引擎示例

**文件**: `examples/09_with_permission_engine.py`  
**内容**:
- [ ] 使用 PermissionEngine
- [ ] 权限检查
- [ ] 资源权限检查
- [ ] 完整应用示例

**预期时间**: 1-2 小时

---

## 第五部分: 时间表

### Week 1

| 任务 | 时间 | 状态 |
|------|------|------|
| 安全配置管理 | 2-3h | ⏳ |
| 权限检查引擎 | 2-3h | ⏳ |
| 集成测试 | 2-3h | ⏳ |
| 文档 1-2 | 4-5h | ⏳ |

**小计**: 10-14 小时

---

### Week 2

| 任务 | 时间 | 状态 |
|------|------|------|
| 审计日志重构 | 2-3h | ⏳ |
| 性能测试 | 1-2h | ⏳ |
| 文档 3-5 | 6-8h | ⏳ |
| 示例更新 | 3-6h | ⏳ |

**小计**: 12-19 小时

---

### Week 3

| 任务 | 时间 | 状态 |
|------|------|------|
| 现有文档更新 | 4-5h | ⏳ |
| 测试验证 | 2-3h | ⏳ |
| 性能基准测试 | 2-3h | ⏳ |
| 最终审查 | 2-3h | ⏳ |

**小计**: 10-14 小时

---

**总时间**: 32-47 小时 (2-3 周)

---

## 第六部分: 验收标准

### 代码验收

- [ ] 所有新代码都有单元测试
- [ ] 代码覆盖率 ≥ 95%
- [ ] 所有测试通过 (195+ 个)
- [ ] 无代码重复
- [ ] 遵循 PEP 8 风格
- [ ] 类型提示完整

### 文档验收

- [ ] 所有新文档完成
- [ ] 所有示例可运行
- [ ] 所有链接有效
- [ ] 所有代码示例正确
- [ ] 文档格式一致

### 性能验收

- [ ] 权限检查 < 1ms
- [ ] 缓存命中 < 0.1ms
- [ ] 缓存命中率 > 90%
- [ ] 内存占用 < 50MB

---

## 第七部分: 预期成果

### 代码成果

✅ 安全配置管理  
✅ 权限检查引擎  
✅ 审计日志重构  
✅ 75-105 个新测试  
✅ 195-225 个总测试  

### 文档成果

✅ 5 个新文档 (1,500-2,000 行)  
✅ 3 个新示例  
✅ 3 个现有文档更新  
✅ 50+ 个代码示例  

### 评分提升

**当前**: 8.4/10  
**目标**: 8.8/10  
**提升**: +0.4 分

---

## 第八部分: 风险管理

### 风险 1: 时间超期

**风险**: 开发时间可能超过预期  
**缓解**: 优先完成核心功能，文档可后续完成

---

### 风险 2: 测试失败

**风险**: 新代码可能有 bug  
**缓解**: 严格的代码审查，完整的单元测试

---

### 风险 3: 文档质量

**风险**: 文档可能不够清晰  
**缓解**: 多次审查，用户反馈

---

## 总结

**开发计划**: 3 周完成 Phase 2 优化  
**文档计划**: 同步更新 5 个新文档 + 3 个示例  
**预期成果**: 评分从 8.4/10 提升到 8.8/10  
**总工作量**: 32-47 小时

---

**计划完成** ✅

