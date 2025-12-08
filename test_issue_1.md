# 测试依赖管理问题：bcrypt导入导致测试失败

## 问题描述
在Python 3.13环境下运行测试时，bcrypt导入会导致测试失败：
```
ImportError: PyO3 modules compiled for CPython 3.8 or older may only be initialized once per interpreter process
```

## 建议解决方案
1. 在测试环境中使用更轻量的密码哈希库
2. 添加可选依赖检查
3. 使用Mock替代真实的bcrypt进行单元测试

## 影响的文件
- `tests/unit/test_security_password.py`
- `src/fastapi_easy/security/password.py`

## 优先级
高 - 影响CI/CD流程