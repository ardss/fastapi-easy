# 测试断言质量问题：错误处理测试过于宽泛

## 问题描述
多个错误处理测试使用了过于宽泛的异常捕获，例如：
```python
try:
    await migration_engine.auto_migrate()
except Exception:
    pass  # 只是捕获而不验证
```

这种做法的问题：
1. 无法验证具体的异常类型
2. 无法验证错误消息的正确性
3. 可能掩盖实际的错误

## 影响的文件
- `tests/unit/migrations/test_engine_error_handling.py`
- 其他错误处理测试文件

## 建议解决方案
1. 使用具体的异常类型（如`pytest.raises(ExpectedException)`）
2. 验证错误消息内容
3. 检查错误发生后的状态

## 优先级
中 - 影响测试的准确性和可靠性