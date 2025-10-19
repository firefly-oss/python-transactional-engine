"""
JSON logging formatter for FireflyTX with proper prefixes.

Provides consistent JSON-formatted logging across the entire FireflyTX system
with appropriate prefixes for Python and Java log entries.
"""

"""
Copyright (c) 2025 Firefly Software Solutions Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional


class FireflyTXJSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for FireflyTX logging system.

    Formats all log entries as JSON with appropriate prefixes:
    - fireflytx::bridge::log for Python components
    - fireflytx::lib-transactional-engine::log for Java components
    """

    def __init__(self, prefix: Optional[str] = None, include_extra: bool = True):
        """
        Initialize the JSON formatter.

        Args:
            prefix: Log prefix to use. If None, defaults to fireflytx::bridge::log
            include_extra: Whether to include extra fields from log records
        """
        super().__init__()
        self.prefix = prefix or "fireflytx::bridge::log"
        self.include_extra = include_extra

        # Fields to exclude from extra data
        self.excluded_fields = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "getMessage",
            "message",
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON with proper prefix.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log entry as string
        """
        # Create base log data
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "prefix": self.prefix,
        }

        # Add thread information if available
        if hasattr(record, "thread") and record.thread:
            log_data["thread"] = getattr(record, "threadName", str(record.thread))

        # Add module and function information
        if record.filename:
            log_data["module"] = record.filename
        if record.funcName and record.funcName != "<module>":
            log_data["function"] = record.funcName
        if record.lineno:
            log_data["line"] = record.lineno

        # Add extra fields if enabled
        if self.include_extra:
            extra_data = self._extract_extra_fields(record)
            if extra_data:
                log_data.update(extra_data)

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Return JSON string
        return json.dumps(log_data, separators=(",", ":"), default=str)

    def _extract_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Extract extra fields from log record.

        Args:
            record: The log record

        Returns:
            Dictionary of extra fields
        """
        extra = {}

        # Get all record attributes
        for key, value in record.__dict__.items():
            if key not in self.excluded_fields and not key.startswith("_"):
                # Skip None values and empty strings
                if value is not None and value != "":
                    extra[key] = value

        return extra


class JavaLogFormatter(FireflyTXJSONFormatter):
    """
    Specialized JSON formatter for Java log entries.

    Uses the fireflytx::lib-transactional-engine::log prefix and includes
    Java-specific fields like saga_id, correlation_id, etc.
    """

    def __init__(self, include_extra: bool = True):
        super().__init__(
            prefix="fireflytx::lib-transactional-engine::log", include_extra=include_extra
        )


class PythonLogFormatter(FireflyTXJSONFormatter):
    """
    Specialized JSON formatter for Python log entries.

    Uses the fireflytx::bridge::log prefix for Python components.
    """

    def __init__(self, include_extra: bool = True):
        super().__init__(prefix="fireflytx::bridge::log", include_extra=include_extra)


def create_json_handler(
    level: int = logging.INFO, formatter_type: str = "python", stream=None
) -> logging.Handler:
    """
    Create a logging handler with JSON formatting.

    Args:
        level: Logging level
        formatter_type: Type of formatter ("python" or "java")
        stream: Output stream (defaults to sys.stdout)

    Returns:
        Configured logging handler
    """
    import sys

    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setLevel(level)

    if formatter_type == "java":
        formatter = JavaLogFormatter()
    else:
        formatter = PythonLogFormatter()

    handler.setFormatter(formatter)
    return handler


def configure_json_logging(
    logger_name: str = "fireflytx", level: int = logging.INFO, enable_java_logs: bool = True
) -> logging.Logger:
    """
    Configure JSON logging for FireflyTX.

    Args:
        logger_name: Name of the logger to configure
        level: Logging level
        enable_java_logs: Whether to enable Java log handling

    Returns:
        Configured logger
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Add Python log handler
    python_handler = create_json_handler(level, "python")
    logger.addHandler(python_handler)

    # Configure Java log handling if enabled
    if enable_java_logs:
        java_logger = logging.getLogger(f"{logger_name}.java")
        java_logger.setLevel(level)
        java_logger.handlers.clear()

        java_handler = create_json_handler(level, "java")
        java_logger.addHandler(java_handler)

        # Prevent propagation to avoid duplicate logs
        java_logger.propagate = False

    return logger
