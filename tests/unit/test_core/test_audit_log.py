"""Unit tests for audit logging"""

import pytest
from datetime import datetime
from fastapi_easy.core.audit_log import (
    AuditAction,
    AuditLog,
    AuditLogger,
    AuditLogContext,
    AuditLogConfig,
    AuditLogDecorator,
)


class TestAuditLog:
    """Test AuditLog"""
    
    def test_audit_log_initialization(self):
        """Test audit log initialization"""
        log = AuditLog(
            entity_type="User",
            entity_id=1,
            action=AuditAction.CREATE,
            user_id=10,
        )
        
        assert log.entity_type == "User"
        assert log.entity_id == 1
        assert log.action == AuditAction.CREATE
        assert log.user_id == 10
        assert log.timestamp is not None
    
    def test_audit_log_with_changes(self):
        """Test audit log with changes"""
        changes = {"name": ("old_name", "new_name")}
        log = AuditLog(
            entity_type="User",
            entity_id=1,
            action=AuditAction.UPDATE,
            changes=changes,
        )
        
        assert log.changes == changes
    
    def test_audit_log_to_dict(self):
        """Test converting audit log to dictionary"""
        log = AuditLog(
            entity_type="User",
            entity_id=1,
            action=AuditAction.CREATE,
            user_id=10,
        )
        
        log_dict = log.to_dict()
        
        assert log_dict["entity_type"] == "User"
        assert log_dict["entity_id"] == 1
        assert log_dict["action"] == AuditAction.CREATE
        assert log_dict["user_id"] == 10


class TestAuditLogger:
    """Test AuditLogger"""
    
    def test_logger_initialization(self):
        """Test logger initialization"""
        logger = AuditLogger()
        
        assert logger.logs == []
    
    def test_log_operation(self):
        """Test logging an operation"""
        logger = AuditLogger()
        
        log = logger.log(
            entity_type="User",
            entity_id=1,
            action=AuditAction.CREATE,
            user_id=10,
        )
        
        assert len(logger.logs) == 1
        assert log.entity_type == "User"
    
    def test_get_logs_all(self):
        """Test getting all logs"""
        logger = AuditLogger()
        
        logger.log("User", 1, AuditAction.CREATE, user_id=10)
        logger.log("User", 2, AuditAction.CREATE, user_id=10)
        logger.log("Product", 1, AuditAction.UPDATE, user_id=11)
        
        logs = logger.get_logs()
        
        assert len(logs) == 3
    
    def test_get_logs_by_entity_type(self):
        """Test filtering logs by entity type"""
        logger = AuditLogger()
        
        logger.log("User", 1, AuditAction.CREATE)
        logger.log("User", 2, AuditAction.CREATE)
        logger.log("Product", 1, AuditAction.UPDATE)
        
        logs = logger.get_logs(entity_type="User")
        
        assert len(logs) == 2
        assert all(log.entity_type == "User" for log in logs)
    
    def test_get_logs_by_entity_id(self):
        """Test filtering logs by entity ID"""
        logger = AuditLogger()
        
        logger.log("User", 1, AuditAction.CREATE)
        logger.log("User", 1, AuditAction.UPDATE)
        logger.log("User", 2, AuditAction.CREATE)
        
        logs = logger.get_logs(entity_id=1)
        
        assert len(logs) == 2
        assert all(log.entity_id == 1 for log in logs)
    
    def test_get_logs_by_user_id(self):
        """Test filtering logs by user ID"""
        logger = AuditLogger()
        
        logger.log("User", 1, AuditAction.CREATE, user_id=10)
        logger.log("User", 2, AuditAction.CREATE, user_id=10)
        logger.log("User", 3, AuditAction.CREATE, user_id=11)
        
        logs = logger.get_logs(user_id=10)
        
        assert len(logs) == 2
        assert all(log.user_id == 10 for log in logs)
    
    def test_get_logs_by_action(self):
        """Test filtering logs by action"""
        logger = AuditLogger()
        
        logger.log("User", 1, AuditAction.CREATE)
        logger.log("User", 1, AuditAction.UPDATE)
        logger.log("User", 1, AuditAction.DELETE)
        
        logs = logger.get_logs(action=AuditAction.UPDATE)
        
        assert len(logs) == 1
        assert logs[0].action == AuditAction.UPDATE
    
    def test_get_entity_history(self):
        """Test getting entity history"""
        logger = AuditLogger()
        
        logger.log("User", 1, AuditAction.CREATE)
        logger.log("User", 1, AuditAction.UPDATE)
        logger.log("User", 1, AuditAction.UPDATE)
        logger.log("User", 2, AuditAction.CREATE)
        
        history = logger.get_entity_history("User", 1)
        
        assert len(history) == 3
        assert all(log.entity_id == 1 for log in history)
    
    def test_get_user_actions(self):
        """Test getting user actions"""
        logger = AuditLogger()
        
        logger.log("User", 1, AuditAction.CREATE, user_id=10)
        logger.log("User", 2, AuditAction.CREATE, user_id=10)
        logger.log("User", 3, AuditAction.CREATE, user_id=11)
        
        actions = logger.get_user_actions(10)
        
        assert len(actions) == 2
        assert all(log.user_id == 10 for log in actions)
    
    def test_clear_logs(self):
        """Test clearing logs"""
        logger = AuditLogger()
        
        logger.log("User", 1, AuditAction.CREATE)
        logger.log("User", 2, AuditAction.CREATE)
        
        assert len(logger.logs) == 2
        
        logger.clear()
        
        assert len(logger.logs) == 0
    
    def test_export_logs(self):
        """Test exporting logs"""
        logger = AuditLogger()
        
        logger.log("User", 1, AuditAction.CREATE, user_id=10)
        logger.log("User", 2, AuditAction.UPDATE, user_id=11)
        
        exported = logger.export_logs()
        
        assert len(exported) == 2
        assert all(isinstance(log, dict) for log in exported)
        assert exported[0]["entity_type"] == "User"


class TestAuditLogContext:
    """Test AuditLogContext"""
    
    def test_context_initialization(self):
        """Test context initialization"""
        context = AuditLogContext(
            user_id=10,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        
        assert context.user_id == 10
        assert context.ip_address == "192.168.1.1"
        assert context.user_agent == "Mozilla/5.0"


class TestAuditLogConfig:
    """Test AuditLogConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = AuditLogConfig()
        
        assert config.enabled is True
        assert config.log_reads is False
        assert config.log_changes_only is True
        assert config.max_logs == 10000
        assert config.retention_days == 90
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = AuditLogConfig(
            enabled=False,
            log_reads=True,
            log_changes_only=False,
            max_logs=5000,
            retention_days=30,
        )
        
        assert config.enabled is False
        assert config.log_reads is True
        assert config.log_changes_only is False
        assert config.max_logs == 5000
        assert config.retention_days == 30


class TestAuditLogDecorator:
    """Test AuditLogDecorator"""
    
    def test_decorator_initialization(self):
        """Test decorator initialization"""
        logger = AuditLogger()
        config = AuditLogConfig()
        decorator = AuditLogDecorator(logger, config)
        
        assert decorator.logger == logger
        assert decorator.config == config
    
    @pytest.mark.asyncio
    async def test_track_operation(self):
        """Test tracking operation"""
        logger = AuditLogger()
        config = AuditLogConfig()
        decorator = AuditLogDecorator(logger, config)
        
        @decorator.track_operation("User", AuditAction.CREATE)
        async def create_user():
            class User:
                id = 1
            return User()
        
        result = await create_user()
        
        assert result.id == 1
        assert len(logger.logs) == 1
        assert logger.logs[0].action == AuditAction.CREATE
