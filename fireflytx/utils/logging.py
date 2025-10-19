#!/usr/bin/env python3
"""
Logging utilities for transactional context.

Provides structured logging with correlation IDs and transaction context.
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
from contextvars import ContextVar
from typing import Any, Dict, Optional

from fireflytx.utils.helpers import sanitize_for_logging

# Context variables for correlation tracking
_correlation_context: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_transaction_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "transaction_context", default=None
)


def set_correlation_context(correlation_id: Optional[str]) -> None:
    """Set correlation ID in context."""
    _correlation_context.set(correlation_id)


def get_correlation_context() -> Optional[str]:
    """Get correlation ID from context."""
    return _correlation_context.get()


def set_transaction_context(context: Optional[Dict[str, Any]]) -> None:
    """Set transaction context."""
    _transaction_context.set(context)


def get_transaction_context() -> Optional[Dict[str, Any]]:
    """Get transaction context."""
    return _transaction_context.get()


class ContextualFormatter(logging.Formatter):
    """Formatter that includes correlation ID and transaction context."""

    def format(self, record):
        # Add correlation ID if available
        correlation_id = get_correlation_context()
        if correlation_id:
            record.correlation_id = correlation_id
        else:
            record.correlation_id = "N/A"

        # Add transaction context if available
        tx_context = get_transaction_context()
        if tx_context:
            record.transaction_name = tx_context.get("transaction_name", "N/A")
            record.step_name = tx_context.get("step_name", "N/A")
        else:
            record.transaction_name = "N/A"
            record.step_name = "N/A"

        return super().format(record)


def get_structured_logger(name: str) -> logging.Logger:
    """
    Get a logger with structured formatting including correlation ID.

    Args:
        name: Logger name

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    # Check if handler already exists to avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = ContextualFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] [%(transaction_name)s:%(step_name)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger


class TransactionLogger:
    """Logger specialized for transaction context."""

    def __init__(self, name: str):
        self.logger = get_structured_logger(name)
        self.name = name

    def log_transaction_start(
        self, transaction_name: str, correlation_id: str, inputs: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log transaction start."""
        set_correlation_context(correlation_id)
        set_transaction_context({"transaction_name": transaction_name, "step_name": "START"})

        message = f"Starting transaction: {transaction_name}"
        if inputs:
            sanitized_inputs = sanitize_for_logging(inputs)
            message += f" with inputs: {sanitized_inputs}"

        self.logger.info(message)

    def log_transaction_end(
        self,
        transaction_name: str,
        correlation_id: str,
        success: bool,
        duration_ms: int,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log transaction completion."""
        set_correlation_context(correlation_id)
        set_transaction_context({"transaction_name": transaction_name, "step_name": "END"})

        status = "SUCCESS" if success else "FAILURE"
        message = f"Completed transaction: {transaction_name} - Status: {status} - Duration: {duration_ms}ms"

        if success and result:
            sanitized_result = sanitize_for_logging(result)
            message += f" - Result: {sanitized_result}"
        elif error:
            message += f" - Error: {error}"

        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)

    def log_step_start(
        self,
        transaction_name: str,
        step_name: str,
        correlation_id: str,
        step_inputs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log step start."""
        set_correlation_context(correlation_id)
        set_transaction_context({"transaction_name": transaction_name, "step_name": step_name})

        message = f"Starting step: {step_name}"
        if step_inputs:
            sanitized_inputs = sanitize_for_logging(step_inputs)
            message += f" with inputs: {sanitized_inputs}"

        self.logger.info(message)

    def log_step_end(
        self,
        transaction_name: str,
        step_name: str,
        correlation_id: str,
        success: bool,
        duration_ms: int,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log step completion."""
        set_correlation_context(correlation_id)
        set_transaction_context({"transaction_name": transaction_name, "step_name": step_name})

        status = "SUCCESS" if success else "FAILURE"
        message = f"Completed step: {step_name} - Status: {status} - Duration: {duration_ms}ms"

        if success and result:
            sanitized_result = sanitize_for_logging(result)
            message += f" - Result: {sanitized_result}"
        elif error:
            message += f" - Error: {error}"

        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)

    def log_compensation_start(
        self,
        transaction_name: str,
        step_name: str,
        correlation_id: str,
        compensation_inputs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log compensation start."""
        set_correlation_context(correlation_id)
        set_transaction_context(
            {"transaction_name": transaction_name, "step_name": f"{step_name}:COMPENSATE"}
        )

        message = f"Starting compensation for step: {step_name}"
        if compensation_inputs:
            sanitized_inputs = sanitize_for_logging(compensation_inputs)
            message += f" with inputs: {sanitized_inputs}"

        self.logger.warning(message)

    def log_compensation_end(
        self,
        transaction_name: str,
        step_name: str,
        correlation_id: str,
        success: bool,
        duration_ms: int,
        error: Optional[str] = None,
    ) -> None:
        """Log compensation completion."""
        set_correlation_context(correlation_id)
        set_transaction_context(
            {"transaction_name": transaction_name, "step_name": f"{step_name}:COMPENSATE"}
        )

        status = "SUCCESS" if success else "FAILURE"
        message = f"Completed compensation for step: {step_name} - Status: {status} - Duration: {duration_ms}ms"

        if error:
            message += f" - Error: {error}"

        if success:
            self.logger.warning(message)
        else:
            self.logger.error(message)

    def log_tcc_phase_start(
        self,
        transaction_name: str,
        phase: str,
        correlation_id: str,
        participant_name: Optional[str] = None,
    ) -> None:
        """Log TCC phase start."""
        set_correlation_context(correlation_id)
        context_name = f"{phase}"
        if participant_name:
            context_name += f":{participant_name}"

        set_transaction_context({"transaction_name": transaction_name, "step_name": context_name})

        message = f"Starting {phase} phase"
        if participant_name:
            message += f" for participant: {participant_name}"

        self.logger.info(message)

    def log_tcc_phase_end(
        self,
        transaction_name: str,
        phase: str,
        correlation_id: str,
        success: bool,
        duration_ms: int,
        participant_name: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log TCC phase completion."""
        set_correlation_context(correlation_id)
        context_name = f"{phase}"
        if participant_name:
            context_name += f":{participant_name}"

        set_transaction_context({"transaction_name": transaction_name, "step_name": context_name})

        status = "SUCCESS" if success else "FAILURE"
        message = f"Completed {phase} phase - Status: {status} - Duration: {duration_ms}ms"
        if participant_name:
            message += f" for participant: {participant_name}"

        if error:
            message += f" - Error: {error}"

        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)

    def log_retry_attempt(
        self,
        transaction_name: str,
        step_name: str,
        correlation_id: str,
        attempt: int,
        max_attempts: int,
        error: str,
    ) -> None:
        """Log retry attempt."""
        set_correlation_context(correlation_id)
        set_transaction_context(
            {"transaction_name": transaction_name, "step_name": f"{step_name}:RETRY"}
        )

        message = f"Retry attempt {attempt}/{max_attempts} for step: {step_name} - Error: {error}"
        self.logger.warning(message)

    def log_timeout(
        self, transaction_name: str, step_name: str, correlation_id: str, timeout_ms: int
    ) -> None:
        """Log timeout occurrence."""
        set_correlation_context(correlation_id)
        set_transaction_context(
            {"transaction_name": transaction_name, "step_name": f"{step_name}:TIMEOUT"}
        )

        message = f"Timeout occurred for step: {step_name} after {timeout_ms}ms"
        self.logger.error(message)


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""

    def __init__(self, name: str):
        self.logger = get_structured_logger(f"{name}.performance")

    def log_execution_metrics(
        self,
        transaction_name: str,
        correlation_id: str,
        total_duration_ms: int,
        step_durations: Dict[str, int],
        success: bool,
    ) -> None:
        """Log execution performance metrics."""
        set_correlation_context(correlation_id)
        set_transaction_context({"transaction_name": transaction_name, "step_name": "METRICS"})

        status = "SUCCESS" if success else "FAILURE"
        message = f"Performance metrics for {transaction_name} - Status: {status} - Total Duration: {total_duration_ms}ms"

        if step_durations:
            step_details = []
            for step, duration in step_durations.items():
                step_details.append(f"{step}:{duration}ms")
            message += f" - Step Durations: {', '.join(step_details)}"

        self.logger.info(message)

    def log_resource_usage(
        self,
        transaction_name: str,
        correlation_id: str,
        memory_usage_mb: Optional[float] = None,
        cpu_usage_percent: Optional[float] = None,
        active_connections: Optional[int] = None,
    ) -> None:
        """Log resource usage metrics."""
        set_correlation_context(correlation_id)
        set_transaction_context({"transaction_name": transaction_name, "step_name": "RESOURCES"})

        metrics = []
        if memory_usage_mb is not None:
            metrics.append(f"Memory: {memory_usage_mb:.2f}MB")
        if cpu_usage_percent is not None:
            metrics.append(f"CPU: {cpu_usage_percent:.2f}%")
        if active_connections is not None:
            metrics.append(f"Connections: {active_connections}")

        if metrics:
            message = f"Resource usage for {transaction_name} - " + ", ".join(metrics)
            self.logger.info(message)


def configure_root_logging(
    level: str = "INFO", format_string: Optional[str] = None, include_correlation: bool = True
) -> None:
    """
    Configure root logging for the application.

    Args:
        level: Logging level
        format_string: Custom format string
        include_correlation: Whether to include correlation ID in logs
    """
    root_logger = logging.getLogger()

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set level
    root_logger.setLevel(getattr(logging, level.upper()))

    # Create handler
    handler = logging.StreamHandler()

    # Create formatter
    if format_string is None:
        if include_correlation:
            format_string = (
                "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
            )
            formatter = ContextualFormatter(fmt=format_string, datefmt="%Y-%m-%d %H:%M:%S")
        else:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            formatter = logging.Formatter(fmt=format_string, datefmt="%Y-%m-%d %H:%M:%S")
    else:
        if include_correlation:
            formatter = ContextualFormatter(fmt=format_string, datefmt="%Y-%m-%d %H:%M:%S")
        else:
            formatter = logging.Formatter(fmt=format_string, datefmt="%Y-%m-%d %H:%M:%S")

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
