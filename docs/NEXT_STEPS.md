# FastAPI-Easy 下一步开发计划

**当前状态**：Phase 1-3 完成（75% 完成度）
**最后更新**：2024年11月27日 14:20

---

## 📋 待解决的问题

### 🟡 P1 中等优先级问题

#### 1. SQL 注入风险修复
**状态**：⏳ 待处理
**影响**：安全性
**预计时间**：2-3 小时

**问题描述**：
- 在 `get_all()` 和 `count()` 中，过滤值处理需要改进
- 虽然使用了 ORM，但需要添加输入验证

**解决方案**：
```python
# 添加输入验证
def validate_filter_value(value, operator):
    """验证过滤值"""
    if operator in ["in"]:
        if isinstance(value, str):
            # 验证逗号分隔的值
            return [v.strip() for v in value.split(",")]
    return value
```

**相关文件**：
- `src/fastapi_easy/backends/sqlalchemy.py`
- `src/fastapi_easy/backends/tortoise.py`
- `src/fastapi_easy/utils/filters.py`

---

### 🟢 P2 低优先级问题

#### 2. 日志系统集成
**状态**：⏳ 待处理
**影响**：可观测性
**预计时间**：3-4 小时

**功能**：
- 添加 Python logging 集成
- 在关键操作点添加日志
- 支持日志级别配置
- 支持结构化日志

**实现**：
```python
# src/fastapi_easy/core/logger.py
import logging

logger = logging.getLogger("fastapi_easy")

# 在操作前后添加日志
logger.info(f"Creating item with data: {data}")
logger.debug(f"Operation result: {result}")
logger.error(f"Operation failed: {error}")
```

#### 3. 类型提示完善
**状态**：⏳ 待处理
**影响**：开发体验
**预计时间**：2-3 小时

**改进**：
- 使用 Protocol 定义接口
- 添加完整的类型注解
- 支持 TypedDict
- 改进 IDE 自动完成

#### 4. 多版本兼容性测试
**状态**：⏳ 待处理
**影响**：兼容性
**预计时间**：3-4 小时

**测试范围**：
- Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- FastAPI 0.100+
- Pydantic 2.0+
- SQLAlchemy 2.0+

**工具**：
- tox 多版本测试
- GitHub Actions CI/CD

---

## 🚀 Phase 4: 高级功能

**预计时间**：1-2 周
**优先级**：P1

### 4.1 软删除支持
**预计时间**：3-4 小时

**功能**：
- 添加 `is_deleted` 字段
- 自动过滤已删除项
- 恢复已删除项的功能
- 永久删除功能

**实现**：
```python
# src/fastapi_easy/core/soft_delete.py
class SoftDeleteMixin:
    """软删除混入类"""
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    
    async def soft_delete(self):
        """软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.now()
        await self.save()
    
    async def restore(self):
        """恢复"""
        self.is_deleted = False
        self.deleted_at = None
        await self.save()
```

### 4.2 批量操作
**预计时间**：3-4 小时

**功能**：
- 批量创建
- 批量更新
- 批量删除
- 事务支持

**端点**：
```
POST /api/items/bulk - 批量创建
PATCH /api/items/bulk - 批量更新
DELETE /api/items/bulk - 批量删除
```

### 4.3 权限控制集成
**预计时间**：4-5 小时

**功能**：
- 基于角色的访问控制 (RBAC)
- 基于属性的访问控制 (ABAC)
- 权限检查装饰器
- 资源所有权验证

**实现**：
```python
# src/fastapi_easy/core/permissions.py
@require_permission("items:read")
async def get_items():
    pass

@require_ownership("item_id")
async def update_item(item_id: int):
    pass
```

### 4.4 审计日志
**预计时间**：3-4 小时

**功能**：
- 记录所有操作
- 记录操作者
- 记录变更内容
- 查询审计日志

**表结构**：
```python
class AuditLog(Base):
    id = Column(Integer, primary_key=True)
    entity_type = Column(String)
    entity_id = Column(Integer)
    action = Column(String)  # create, update, delete
    user_id = Column(Integer)
    changes = Column(JSON)
    timestamp = Column(DateTime)
```

---

## 🧪 Phase 5: 测试和优化

**预计时间**：1 周
**优先级**：P2

### 5.1 性能优化
**预计时间**：3-4 小时

**优化点**：
- 数据库查询优化（N+1 问题）
- 缓存策略
- 批量操作优化
- 异步优化

### 5.2 文档完善
**预计时间**：3-4 小时

**内容**：
- API 文档（Swagger/OpenAPI）
- 开发者指南
- 贡献指南
- 常见问题 (FAQ)

### 5.3 集成测试扩展
**预计时间**：3-4 小时

**测试范围**：
- 多个 ORM 的集成测试
- 权限控制测试
- 审计日志测试
- 软删除测试

---

## 📦 Phase 6: 发布和推广

**预计时间**：1 周
**优先级**：P2

### 6.1 PyPI 发布
**预计时间**：2-3 小时

**步骤**：
1. 配置 `setup.py` 和 `setup.cfg`
2. 创建 `MANIFEST.in`
3. 生成 wheel 和 sdist
4. 上传到 PyPI

### 6.2 示例项目
**预计时间**：4-5 小时

**示例**：
- 博客系统
- 电商系统
- 任务管理系统
- 社交媒体系统

### 6.3 社区建设
**预计时间**：持续

**活动**：
- GitHub 讨论
- 问题反馈
- 贡献指南
- 社区支持

---

## 📊 优先级排序

### 立即处理（本周）
1. **SQL 注入风险修复** - 安全性关键
2. **日志系统集成** - 提高可观测性
3. **多版本兼容性测试** - 确保兼容性

### 下周处理
4. **软删除支持** - 常见需求
5. **批量操作** - 性能优化
6. **权限控制** - 安全性需求

### 两周后处理
7. **审计日志** - 合规性需求
8. **性能优化** - 优化体验
9. **文档完善** - 提高易用性

### 三周后处理
10. **PyPI 发布** - 正式发布
11. **示例项目** - 社区支持
12. **社区建设** - 长期维护

---

## 📈 预期时间表

| 阶段 | 任务 | 预计时间 | 优先级 |
|------|------|--------|------|
| P4.1 | 软删除支持 | 3-4 小时 | P1 |
| P4.2 | 批量操作 | 3-4 小时 | P1 |
| P4.3 | 权限控制 | 4-5 小时 | P1 |
| P4.4 | 审计日志 | 3-4 小时 | P1 |
| P5.1 | 性能优化 | 3-4 小时 | P2 |
| P5.2 | 文档完善 | 3-4 小时 | P2 |
| P5.3 | 集成测试 | 3-4 小时 | P2 |
| P6.1 | PyPI 发布 | 2-3 小时 | P2 |
| P6.2 | 示例项目 | 4-5 小时 | P2 |
| P6.3 | 社区建设 | 持续 | P2 |
| **总计** | | **32-42 小时** | |

---

## 🎯 成功指标

### Phase 4 完成标准
- [ ] 所有高级功能实现
- [ ] 相关测试通过率 > 95%
- [ ] 文档完整

### Phase 5 完成标准
- [ ] 性能提升 > 20%
- [ ] 文档覆盖率 100%
- [ ] 集成测试覆盖率 > 90%

### Phase 6 完成标准
- [ ] PyPI 发布成功
- [ ] 示例项目可运行
- [ ] 社区反馈积极

---

## 📝 开发建议

1. **保持测试驱动开发** - 先写测试，再实现功能
2. **增量开发** - 每个功能单独提交
3. **文档同步** - 功能完成时更新文档
4. **代码审查** - 确保代码质量
5. **性能监控** - 持续监控性能指标

---

**下一步行动**：
1. 选择 Phase 4 的第一个功能（软删除）
2. 编写单元测试
3. 实现功能
4. 编写集成测试
5. 更新文档
6. 提交代码

