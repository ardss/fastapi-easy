"""Unit tests for logging system"""

import pytest
import logging
from fastapi_easy.core.logger import (
    LogLevel,
    LogFormatter,
    StructuredLogger,
    OperationLogger,
    LoggerConfig,
    get_logger,
    get_operation_logger,
)


class TestLogLevel:
    """Test LogLevel enumeration"""
    
    def test_log_levels(self):
        """Test log level values"""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"


class TestLogFormatter:
    """Test LogFormatter"""
    
    def test_formatter_initialization(self):
        """Test formatter initialization"""
        formatter = LogFormatter()
        
        assert formatter is not None
    
    def test_format_log_record(self):
        """Test formatting log record"""
        formatter = LogFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        formatted = formatter.format(record)
        
        assert "Test message" in formatted
        assert "INFO" in formatted
        assert "test" in formatted


class TestStructuredLogger:
    """Test StructuredLogger"""
    
    def test_logger_initialization(self):
        """Test logger initialization"""
        logger = StructuredLogger(name="test_logger")
        
        assert logger.logger is not None
        assert logger.use_json is True
    
    def test_logger_debug(self, caplog):
        """Test debug logging"""
        logger = StructuredLogger(name="test_debug", level=LogLevel.DEBUG)
        
        with caplog.at_level(logging.DEBUG):
            logger.debug("Debug message")
        
        assert "Debug message" in caplog.text
    
    def test_logger_info(self, caplog):
        """Test info logging"""
        logger = StructuredLogger(name="test_info")
        
        with caplog.at_level(logging.INFO):
            logger.info("Info message")
        
        assert "Info message" in caplog.text
    
    def test_logger_warning(self, caplog):
        """Test warning logging"""
        logger = StructuredLogger(name="test_warning")
        
        with caplog.at_level(logging.WARNING):
            logger.warning("Warning message")
        
        assert "Warning message" in caplog.text
    
    def test_logger_error(self, caplog):
        """Test error logging"""
        logger = StructuredLogger(name="test_error")
        
        with caplog.at_level(logging.ERROR):
            logger.error("Error message")
        
        assert "Error message" in caplog.text
    
    def test_logger_critical(self, caplog):
        """Test critical logging"""
        logger = StructuredLogger(name="test_critical")
        
        with caplog.at_level(logging.CRITICAL):
            logger.critical("Critical message")
        
        assert "Critical message" in caplog.text
    
    def test_logger_with_extra_fields(self, caplog):
        """Test logging with extra fields"""
        logger = StructuredLogger(name="test_extra")
        
        with caplog.at_level(logging.INFO):
            logger.info("Message with fields", extra_fields={"user_id": 123})
        
        assert "Message with fields" in caplog.text
    
    def test_logger_with_exception(self, caplog):
        """Test logging with exception"""
        logger = StructuredLogger(name="test_exception")
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            with caplog.at_level(logging.ERROR):
                logger.error("Error occurred", exception=e)
        
        assert "Error occurred" in caplog.text


class TestOperationLogger:
    """Test OperationLogger"""
    
    def test_operation_logger_initialization(self):
        """Test operation logger initialization"""
        logger = StructuredLogger(name="test_op")
        op_logger = OperationLogger(logger)
        
        assert op_logger.logger == logger
    
    def test_log_create(self, caplog):
        """Test logging create operation"""
        logger = StructuredLogger(name="test_create")
        op_logger = OperationLogger(logger)
        
        with caplog.at_level(logging.INFO):
            op_logger.log_create("User", 1, user_id=10)
        
        assert "Created User" in caplog.text
    
    def test_log_read(self, caplog):
        """Test logging read operation"""
        logger = StructuredLogger(name="test_read", level=LogLevel.DEBUG)
        op_logger = OperationLogger(logger)
        
        with caplog.at_level(logging.DEBUG):
            op_logger.log_read("User", 1, user_id=10)
        
        assert "Read User" in caplog.text
    
    def test_log_update(self, caplog):
        """Test logging update operation"""
        logger = StructuredLogger(name="test_update")
        op_logger = OperationLogger(logger)
        
        with caplog.at_level(logging.INFO):
            op_logger.log_update("User", 1, changes={"name": "John"}, user_id=10)
        
        assert "Updated User" in caplog.text
    
    def test_log_delete(self, caplog):
        """Test logging delete operation"""
        logger = StructuredLogger(name="test_delete")
        op_logger = OperationLogger(logger)
        
        with caplog.at_level(logging.WARNING):
            op_logger.log_delete("User", 1, user_id=10)
        
        assert "Deleted User" in caplog.text
    
    def test_log_error(self, caplog):
        """Test logging error operation"""
        logger = StructuredLogger(name="test_op_error")
        op_logger = OperationLogger(logger)
        
        error = ValueError("Test error")
        
        with caplog.at_level(logging.ERROR):
            op_logger.log_error("CREATE", "User", error, user_id=10)
        
        assert "Error during CREATE" in caplog.text


class TestLoggerConfig:
    """Test LoggerConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = LoggerConfig()
        
        assert config.enabled is True
        assert config.level == LogLevel.INFO
        assert config.use_json is True
        assert config.log_operations is True
        assert config.log_errors is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = LoggerConfig(
            enabled=False,
            level=LogLevel.DEBUG,
            use_json=False,
            log_operations=False,
            log_errors=False,
        )
        
        assert config.enabled is False
        assert config.level == LogLevel.DEBUG
        assert config.use_json is False
        assert config.log_operations is False
        assert config.log_errors is False


class TestGlobalLogger:
    """Test global logger functions"""
    
    def test_get_logger(self):
        """Test getting logger instance"""
        logger = get_logger()
        
        assert logger is not None
        assert isinstance(logger, StructuredLogger)
    
    def test_get_logger_singleton(self):
        """Test logger singleton behavior"""
        logger1 = get_logger()
        logger2 = get_logger()
        
        assert logger1 is logger2
    
    def test_get_operation_logger(self):
        """Test getting operation logger"""
        op_logger = get_operation_logger()
        
        assert op_logger is not None
        assert isinstance(op_logger, OperationLogger)
