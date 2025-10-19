#!/usr/bin/env python3
"""
Helper utilities for common functionality.

Provides utility functions for retry logic, timeouts, JSON handling, and ID generation.
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

import asyncio
import functools
import json
import threading
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, TypeVar

T = TypeVar("T")


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for tracking transactions."""
    timestamp = int(time.time() * 1000)  # Milliseconds
    unique_id = str(uuid.uuid4()).replace("-", "")[:12]  # First 12 chars without dashes
    return f"{timestamp}-{unique_id}"


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator for functions.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Exponential backoff multiplier
        exceptions: Tuple of exceptions to catch and retry on
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise the exception
                        break

                    # Wait before next attempt
                    time.sleep(delay)
                    delay = min(delay * backoff_multiplier, max_delay)

            # Re-raise the last exception
            raise last_exception

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Async retry decorator for async functions.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Exponential backoff multiplier
        exceptions: Tuple of exceptions to catch and retry on
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise the exception
                        break

                    # Wait before next attempt
                    await asyncio.sleep(delay)
                    delay = min(delay * backoff_multiplier, max_delay)

            # Re-raise the last exception
            raise last_exception

        return wrapper

    return decorator


def timeout(seconds: float) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Timeout decorator for functions.

    Args:
        seconds: Timeout duration in seconds
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                # Timeout occurred
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")

            if exception[0]:
                raise exception[0]

            return result[0]

        return wrapper

    return decorator


def async_timeout(seconds: float) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Async timeout decorator for async functions.

    Args:
        seconds: Timeout duration in seconds
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)

        return wrapper

    return decorator


class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles non-serializable objects safely."""

    def default(self, obj):
        """Convert non-serializable objects to serializable equivalents."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, "__dict__"):
            # For objects with __dict__, try to serialize the dict
            try:
                return obj.__dict__
            except:
                return str(obj)
        else:
            # For anything else, convert to string
            return str(obj)


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """
    Safely serialize an object to JSON string.

    Handles non-serializable objects by converting them to strings.
    """
    try:
        return json.dumps(obj, cls=SafeJSONEncoder, **kwargs)
    except Exception:
        # Fallback to string representation
        return json.dumps({"error": "serialization_failed", "repr": str(obj)})


def safe_json_loads(json_str: str, **kwargs) -> Any:
    """
    Safely deserialize a JSON string to object.

    Returns None if deserialization fails.
    """
    try:
        return json.loads(json_str, **kwargs)
    except Exception:
        return None


def chunks(lst: list, chunk_size: int):
    """
    Split a list into chunks of specified size.

    Args:
        lst: List to split
        chunk_size: Size of each chunk

    Yields:
        List chunks
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def deep_merge_dicts(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        base: Base dictionary
        update: Dictionary to merge into base

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def get_current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


def format_duration_ms(duration_ms: int) -> str:
    """
    Format duration in milliseconds to human-readable string.

    Args:
        duration_ms: Duration in milliseconds

    Returns:
        Formatted duration string
    """
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    elif duration_ms < 60000:
        return f"{duration_ms / 1000:.1f}s"
    elif duration_ms < 3600000:
        minutes = duration_ms // 60000
        seconds = (duration_ms % 60000) // 1000
        return f"{minutes}m {seconds}s"
    else:
        hours = duration_ms // 3600000
        minutes = (duration_ms % 3600000) // 60000
        return f"{hours}h {minutes}m"


def is_valid_correlation_id(correlation_id: str) -> bool:
    """
    Validate correlation ID format.

    Args:
        correlation_id: Correlation ID to validate

    Returns:
        True if valid format
    """
    if not correlation_id or not isinstance(correlation_id, str):
        return False

    # Basic validation: should have timestamp and unique part
    parts = correlation_id.split("-")
    if len(parts) != 2:
        return False

    try:
        # First part should be a timestamp (digits)
        int(parts[0])
        # Second part should be alphanumeric
        return parts[1].isalnum() and len(parts[1]) == 12
    except ValueError:
        return False


def sanitize_for_logging(data: Any, max_length: int = 1000) -> str:
    """
    Sanitize data for safe logging.

    Args:
        data: Data to sanitize
        max_length: Maximum length of output string

    Returns:
        Sanitized string safe for logging
    """
    try:
        # Convert to string representation
        if isinstance(data, str):
            result = data
        else:
            result = safe_json_dumps(data, indent=None)

        # Truncate if too long
        if len(result) > max_length:
            result = result[: max_length - 3] + "..."

        # Remove sensitive patterns (basic patterns)
        sensitive_patterns = ["password", "secret", "token", "key", "auth"]

        result_lower = result.lower()
        for pattern in sensitive_patterns:
            if pattern in result_lower:
                # Simple redaction - replace values after sensitive keys
                import re

                pattern_regex = rf'("{pattern}"[^"]*"[^"]*"[^"]*")([^"]*)'
                result = re.sub(pattern_regex, r"\1[REDACTED]", result, flags=re.IGNORECASE)

        return result

    except Exception:
        # Fallback to simple string conversion
        return str(data)[:max_length]


class CircuitBreaker:
    """
    Simple circuit breaker implementation for fault tolerance.

    States:
    - CLOSED: Normal operation, requests are allowed
    - OPEN: Failing fast, requests are rejected
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(
        self, failure_threshold: int = 5, recovery_timeout: float = 60.0, success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap function with circuit breaker."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if (
                    self.last_failure_time
                    and time.time() - self.last_failure_time > self.recovery_timeout
                ):
                    self.state = "HALF_OPEN"
                    self.success_count = 0
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise e

        return wrapper

    def _on_success(self):
        """Handle successful call."""
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "CLOSED"
                self.failure_count = 0
        elif self.state == "CLOSED":
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold or self.state == "HALF_OPEN":
            self.state = "OPEN"


def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """
    Calculate exponential backoff delay.

    Args:
        attempt: Attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds
    """
    delay = base_delay * (2**attempt)
    return min(delay, max_delay)
