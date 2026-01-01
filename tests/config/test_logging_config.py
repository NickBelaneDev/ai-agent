import pytest
import logging
from src.config.logging_config import setup_logging

def test_setup_logging_defaults():
    """Test setup_logging with default arguments."""
    logger = setup_logging("test_logger_default")
    
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger_default"
    assert logger.level == logging.INFO
    assert len(logger.handlers) > 0
    assert isinstance(logger.handlers[0], logging.StreamHandler)

def test_setup_logging_custom_level():
    """Test setup_logging with a custom log level."""
    logger = setup_logging("test_logger_debug", log_level=logging.DEBUG)
    
    assert logger.level == logging.DEBUG
    assert logger.handlers[0].level == logging.DEBUG

def test_setup_logging_idempotency():
    """Test that calling setup_logging multiple times doesn't add duplicate handlers."""
    name = "test_logger_idempotent"
    
    # First call
    logger1 = setup_logging(name)
    num_handlers_initial = len(logger1.handlers)
    
    # Second call
    logger2 = setup_logging(name)
    
    assert logger1 is logger2
    assert len(logger2.handlers) == num_handlers_initial
