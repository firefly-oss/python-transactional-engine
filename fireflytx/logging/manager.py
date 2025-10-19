"""
Centralized logging manager for FireflyTX.

Provides unified logging setup with JSON formatting, Java log integration,
and proper prefix management across the entire system.
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

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from .java_log_bridge import JavaLogBridge
from .json_formatter import JavaLogFormatter, PythonLogFormatter


class FireflyTXLoggingManager:
    """
    Central manager for FireflyTX logging system.

    Handles setup and coordination of Python and Java logging with proper
    JSON formatting and prefixes throughout the system.
    """

    def __init__(self, config=None):
        """
        Initialize the logging manager.

        Args:
            config: Engine configuration containing logging settings
        """
        self.config = config
        self.java_bridge: Optional[JavaLogBridge] = None
        self.configured = False

        # Default settings if no config provided
        self.log_level = logging.INFO
        self.format_type = "json"
        self.enable_java_logs = True
        self.output_file = None
        self.max_file_size_mb = 100
        self.backup_count = 5

        # Extract settings from config if available
        if config and hasattr(config, "logging"):
            logging_config = config.logging
            self.log_level = getattr(logging, logging_config.level)
            self.format_type = logging_config.format
            self.enable_java_logs = logging_config.enable_java_logs
            self.output_file = logging_config.output_file
            self.max_file_size_mb = logging_config.max_file_size_mb
            self.backup_count = logging_config.backup_count

    def setup_logging(self) -> None:
        """Setup the complete FireflyTX logging system."""
        if self.configured:
            return

        # Setup Python logging
        self._setup_python_logging()

        # Setup Java logging if enabled
        if self.enable_java_logs:
            self._setup_java_logging()

        # Configure root FireflyTX logger
        self._configure_fireflytx_loggers()

        self.configured = True

        # Log successful setup
        logger = logging.getLogger("fireflytx.logging")
        logger.info(
            "FireflyTX logging system initialized",
            extra={
                "log_level": logging.getLevelName(self.log_level),
                "format_type": self.format_type,
                "java_logs_enabled": self.enable_java_logs,
                "output_file": self.output_file,
            },
        )

    def _setup_python_logging(self) -> None:
        """Setup Python logging with JSON formatters."""
        # Get root logger and clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Create console handler
        if self.format_type == "json":
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(PythonLogFormatter())
            console_handler.setLevel(self.log_level)
            root_logger.addHandler(console_handler)
        else:
            # Use standard text formatting
            logging.basicConfig(
                level=self.log_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                stream=sys.stdout,
            )

        # Setup file logging if configured
        if self.output_file:
            self._setup_file_logging()

    def _setup_file_logging(self) -> None:
        """Setup file-based logging with rotation."""
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(output_path),
            maxBytes=self.max_file_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=self.backup_count,
            encoding="utf-8",
        )

        if self.format_type == "json":
            file_handler.setFormatter(PythonLogFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )

        file_handler.setLevel(self.log_level)

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    def _setup_java_logging(self) -> None:
        """Setup Java log bridge and integration."""
        # Initialize Java log bridge with configuration
        self.java_bridge = JavaLogBridge(enabled=True, config=self.config)

        # Setup Java logger with proper formatting
        java_logger = logging.getLogger("fireflytx.java")
        java_logger.setLevel(self.log_level)
        java_logger.handlers.clear()

        # Add console handler for Java logs
        if self.format_type == "json":
            java_console_handler = logging.StreamHandler(sys.stdout)
            java_console_handler.setFormatter(JavaLogFormatter())
            java_console_handler.setLevel(self.log_level)
            java_logger.addHandler(java_console_handler)

        # Add file handler for Java logs if configured
        if self.output_file:
            java_file_handler = logging.handlers.RotatingFileHandler(
                filename=str(Path(self.output_file).with_suffix(".java.log")),
                maxBytes=self.max_file_size_mb * 1024 * 1024,
                backupCount=self.backup_count,
                encoding="utf-8",
            )

            if self.format_type == "json":
                java_file_handler.setFormatter(JavaLogFormatter())
            else:
                java_file_handler.setFormatter(
                    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                )

            java_file_handler.setLevel(self.log_level)
            java_logger.addHandler(java_file_handler)

        # Prevent Java logs from propagating to avoid duplicates
        java_logger.propagate = False

        # Start Java log capturing
        self.java_bridge.start_capturing()

    def _configure_fireflytx_loggers(self) -> None:
        """Configure specific FireflyTX component loggers."""
        fireflytx_loggers = [
            "fireflytx.saga",
            "fireflytx.tcc",
            "fireflytx.engine",
            "fireflytx.persistence",
            "fireflytx.events",
            "fireflytx.jvm",
            "fireflytx.bridge",
            "fireflytx.logging",
        ]

        for logger_name in fireflytx_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(self.log_level)
            # Inherit handlers from root logger
            logger.propagate = True

    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger for the given name."""
        if not self.configured:
            self.setup_logging()

        return logging.getLogger(name)

    def log_with_prefix(self, logger_name: str, level: int, message: str, **kwargs) -> None:
        """Log a message with proper JSON formatting and prefix."""
        logger = self.get_logger(logger_name)

        if self.format_type == "json":
            # The JSON formatter will handle the prefix
            logger.log(level, message, extra=kwargs)
        else:
            # For text format, just log normally
            logger.log(level, message, extra=kwargs)

    def shutdown(self) -> None:
        """Shutdown the logging system gracefully."""
        if self.java_bridge:
            self.java_bridge.stop_capturing()

        # Shutdown all handlers
        logging.shutdown()

        self.configured = False

    def get_java_logs(self, count: int = 50):
        """Get recent Java log entries."""
        if self.java_bridge:
            return self.java_bridge.get_recent_logs(count)
        return []

    def get_java_logs_by_level(self, level: str, count: int = 50):
        """Get Java log entries for a specific level."""
        if self.java_bridge:
            from .java_log_bridge import JavaLogLevel

            java_level = getattr(JavaLogLevel, level.upper(), JavaLogLevel.INFO)
            return self.java_bridge.get_logs_by_level(java_level, count)
        return []


# Global logging manager instance
_logging_manager: Optional[FireflyTXLoggingManager] = None


def get_logging_manager(config=None) -> FireflyTXLoggingManager:
    """Get or create the global logging manager."""
    global _logging_manager

    if _logging_manager is None:
        _logging_manager = FireflyTXLoggingManager(config)

    return _logging_manager


def setup_fireflytx_logging(config=None) -> None:
    """Setup FireflyTX logging system."""
    manager = get_logging_manager(config)
    manager.setup_logging()


def get_fireflytx_logger(name: str) -> logging.Logger:
    """Get a FireflyTX logger with proper configuration."""
    manager = get_logging_manager()
    return manager.get_logger(f"fireflytx.{name}")


def shutdown_fireflytx_logging() -> None:
    """Shutdown the FireflyTX logging system."""
    global _logging_manager

    if _logging_manager:
        _logging_manager.shutdown()
        _logging_manager = None
