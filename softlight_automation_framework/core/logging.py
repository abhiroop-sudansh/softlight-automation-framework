"""Logging configuration for the browser automation framework."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import structlog


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_logs: bool = False
) -> logging.Logger:
    """
    Set up logging configuration for the framework.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
        json_logs: Whether to output JSON formatted logs
    
    Returns:
        Configured logger instance
    """
    # Get numeric log level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure structlog
    if json_logs:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if not json_logs:
        console_format = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_format)
    
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        
        file_format = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)
    
    # Quiet down noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    
    # Get our framework logger
    logger = logging.getLogger("browser_automation")
    logger.setLevel(numeric_level)
    
    return logger


def get_logger(name: str = "browser_automation") -> structlog.stdlib.BoundLogger:
    """
    Get a structlog logger instance.
    
    Args:
        name: Logger name (usually module name)
    
    Returns:
        Bound logger instance
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding temporary log context."""
    
    def __init__(self, logger: structlog.stdlib.BoundLogger, **context):
        self.logger = logger
        self.context = context
        self._original_context = {}
    
    def __enter__(self):
        # Store original context and bind new context
        self._original_context = self.logger._context.copy()
        self.logger = self.logger.bind(**self.context)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original context
        self.logger._context = self._original_context
        return False


def log_step(step_number: int, action: str, result: str = None, error: str = None):
    """
    Log an agent step with consistent formatting.
    
    Args:
        step_number: Current step number
        action: Action being performed
        result: Optional result message
        error: Optional error message
    """
    logger = get_logger("browser_automation.agent")
    
    if error:
        logger.error(
            f"Step {step_number}: {action}",
            step=step_number,
            action=action,
            error=error
        )
    elif result:
        logger.info(
            f"Step {step_number}: {action}",
            step=step_number,
            action=action,
            result=result
        )
    else:
        logger.info(
            f"Step {step_number}: {action}",
            step=step_number,
            action=action
        )


def log_browser_event(event_type: str, **details):
    """
    Log browser events with consistent formatting.
    
    Args:
        event_type: Type of browser event
        **details: Additional event details
    """
    logger = get_logger("browser_automation.browser")
    logger.debug(f"Browser event: {event_type}", event_type=event_type, **details)


def log_llm_call(model: str, prompt_tokens: int = None, completion_tokens: int = None, duration_ms: int = None):
    """
    Log LLM API calls with metrics.
    
    Args:
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        duration_ms: Call duration in milliseconds
    """
    logger = get_logger("browser_automation.llm")
    logger.info(
        f"LLM call completed",
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        duration_ms=duration_ms
    )

