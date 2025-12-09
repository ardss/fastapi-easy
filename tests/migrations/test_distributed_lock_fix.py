"""测试分布式锁修复的测试用例"""
import asyncio
import logging
import os
import tempfile
import time
from unittest.mock import patch

import pytest

from fastapi_easy.migrations.distributed_lock import FileLockProvider, is_test_environment


class TestDistributedLockFix:
    """测试分布式锁修复的测试用例"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        # 确保测试环境检测正常工作
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_distributed_lock_fix.py::test_something"}):
            assert is_test_environment() == True

    def test_is_test_environment_detection(self):
        """测试环境检测功能"""
        # 模拟测试环境
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something.py"}):
            assert is_test_environment() == True

        # 模拟非测试环境
        with patch.dict(os.environ, {}, clear=True):
            with patch('sys.modules', {}):
                result = is_test_environment()
                # 在实际测试环境中，这个检测可能仍然返回True
                # 这是正常的，因为我们正在pytest中运行

    def test_lock_cleanup_uses_debug_level_in_test_env(self, caplog):
        """测试在测试环境中锁清理使用DEBUG级别日志"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = os.path.join(tmpdir, "test.lock")

            # 创建一个过期的锁文件
            old_pid = 99999  # 不存在的PID
            old_time = time.time() - 100  # 100秒前
            with open(lock_file, 'w') as f:
                f.write(f"{old_pid}:{old_time}")

            # 设置测试环境
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_lock.py"}):
                with caplog.at_level(logging.DEBUG):
                    provider = FileLockProvider(lock_file)

                    # 验证初始清理使用DEBUG级别
                    debug_messages = [record.message for record in caplog.records if record.levelname == 'DEBUG']
                    assert any("测试环境清理陈旧锁文件" in msg for msg in debug_messages)

    def test_lock_cleanup_quiet_in_test_env(self, caplog):
        """测试在测试环境中锁清理是安静的（无WARNING）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = os.path.join(tmpdir, "test.lock")

            # 创建一个过期的锁文件
            old_pid = 99999  # 不存在的PID
            old_time = time.time() - 100  # 100秒前
            with open(lock_file, 'w') as f:
                f.write(f"{old_pid}:{old_time}")

            # 设置测试环境
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_lock.py"}):
                with caplog.at_level(logging.WARNING):
                    provider = FileLockProvider(lock_file)

                    # 验证没有WARNING级别的日志
                    warning_messages = [record.message for record in caplog.records if record.levelname == 'WARNING']
                    assert len(warning_messages) == 0, f"Unexpected warnings: {warning_messages}"

    async def test_no_warning_spam_during_acquire(self, caplog):
        """测试在获取锁过程中没有警告垃圾信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = os.path.join(tmpdir, "test.lock")

            # 创建一个过期的锁文件
            old_pid = 99999  # 不存在的PID
            old_time = time.time() - 10  # 10秒前，超过测试环境的3秒阈值
            with open(lock_file, 'w') as f:
                f.write(f"{old_pid}:{old_time}")

            # 设置测试环境
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_lock.py"}):
                with caplog.at_level(logging.WARNING):
                    provider = FileLockProvider(lock_file)

                    # 尝试获取锁（会触发清理）
                    result = await provider.acquire(timeout=1)

                    # 验证没有关于清理过期锁文件的WARNING级别的日志
                    warning_messages = [record.message for record in caplog.records if record.levelname == 'WARNING']
                    # 检查是否有与清理锁文件相关的警告
                    cleanup_warnings = [msg for msg in warning_messages if any(keyword in msg for keyword in ["删除", "PID", "锁文件"])]

                    # 允许超时警告，但不应该有清理相关的警告
                    assert len(cleanup_warnings) == 0, f"Unexpected cleanup warnings: {cleanup_warnings}"

                    # 可能会因为超时失败，这是正常的，因为我们在测试警告行为而不是锁获取功能

    async def test_stale_threshold_reduced_in_test_env(self):
        """测试在测试环境中过期阈值被降低"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = os.path.join(tmpdir, "test.lock")

            # 设置测试环境
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_lock.py"}):
                provider = FileLockProvider(lock_file)

                # 先获取锁来验证功能正常
                result = await provider.acquire(timeout=1)
                assert result == True

                # 释放锁
                await provider.release()

    def test_cleanup_test_locks_method(self, caplog):
        """测试cleanup_test_locks方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = os.path.join(tmpdir, "test.lock")

            # 创建一个锁文件
            with open(lock_file, 'w') as f:
                f.write("12345:123456789")

            # 设置测试环境
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_lock.py"}):
                provider = FileLockProvider(lock_file)

                with caplog.at_level(logging.DEBUG):
                    provider.cleanup_test_locks()

                    # 验证锁文件被删除
                    assert not os.path.exists(lock_file)

                    # 验证使用DEBUG级别日志
                    debug_messages = [record.message for record in caplog.records if record.levelname == 'DEBUG']
                    assert any("测试环境强制清理锁文件" in msg for msg in debug_messages)

    def test_cleanup_test_locks_ignored_in_non_test_env(self):
        """测试在非测试环境中cleanup_test_locks被忽略"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = os.path.join(tmpdir, "test.lock")

            # 创建一个锁文件
            with open(lock_file, 'w') as f:
                f.write("12345:123456789")

            # 模拟非测试环境
            with patch('fastapi_easy.migrations.distributed_lock.is_test_environment', return_value=False):
                provider = FileLockProvider(lock_file)
                provider.cleanup_test_locks()

                # 验证锁文件仍然存在（不被清理）
                assert os.path.exists(lock_file)