"""
Python decorators for TCC pattern.

This module provides decorators that convert Java TCC annotations to Python equivalents,
allowing Python classes and methods to be used with the TCC pattern.
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

import functools
import inspect
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TccParticipantConfig:
    """Configuration for a TCC participant."""

    participant_id: str
    order: int = 1
    timeout_ms: int = 30000
    try_method: Optional[str] = None
    confirm_method: Optional[str] = None
    cancel_method: Optional[str] = None


@dataclass
class TccMethodConfig:
    """Configuration for TCC methods."""

    method_type: str  # "try", "confirm", "cancel"
    timeout_ms: int = 10000
    retry: int = 3
    backoff_ms: int = 1000


@dataclass
class TccConfig:
    """Configuration for a TCC transaction."""

    name: str
    timeout_ms: int = 30000
    participants: Dict[str, TccParticipantConfig] = field(default_factory=dict)
    participant_classes: Dict[str, type] = field(default_factory=dict)


def tcc(name: str, timeout_ms: int = 30000) -> Callable:
    """
    Decorator to mark a class as a TCC transaction coordinator.

    This is the Python equivalent of the Java @Tcc annotation.

    Args:
        name: Name of the TCC transaction
        timeout_ms: Global timeout in milliseconds

    Returns:
        Decorated class with TCC metadata

    Example:
        @tcc("order-payment")
        class OrderPaymentTcc:
            @tcc_participant("payment", order=1)
            class PaymentParticipant:
                pass
    """

    def decorator(cls: type) -> type:
        # Store TCC metadata on the class
        cls._tcc_name = name
        cls._tcc_config = TccConfig(name=name, timeout_ms=timeout_ms)

        # Collect participant configurations from nested classes
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if inspect.isclass(attr) and hasattr(attr, "_tcc_participant_config"):
                participant_config = attr._tcc_participant_config
                cls._tcc_config.participants[participant_config.participant_id] = participant_config
                cls._tcc_config.participant_classes[participant_config.participant_id] = attr

                # Collect method configurations from participant
                _collect_participant_methods(attr, participant_config)

        # Collect participant configurations from methods (method-based pattern)
        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue
            attr = getattr(cls, attr_name)
            if (inspect.isfunction(attr) or inspect.ismethod(attr) or inspect.iscoroutinefunction(attr)) and hasattr(attr, "_tcc_participant_config"):
                participant_config = attr._tcc_participant_config

                # Infer confirm and cancel method names from try method name
                try_method_name = attr.__name__
                # Pattern: try_<participant_id> -> confirm_<participant_id>, cancel_<participant_id>
                if try_method_name.startswith('try_'):
                    base_name = try_method_name[4:]  # Remove 'try_' prefix
                    participant_config.confirm_method = f"confirm_{base_name}"
                    participant_config.cancel_method = f"cancel_{base_name}"

                cls._tcc_config.participants[participant_config.participant_id] = participant_config

        logger.debug(
            f"Registered TCC: {name} with {len(cls._tcc_config.participants)} participants"
        )
        return cls

    return decorator


def tcc_participant(participant_id: str, order: int = 1, timeout_ms: int = 30000) -> Callable:
    """
    Decorator to mark a nested class or method as a TCC participant.

    This is the Python equivalent of the Java @TccParticipant annotation.

    Args:
        participant_id: Unique identifier for the participant
        order: Execution order (lower numbers execute first)
        timeout_ms: Timeout for participant operations in milliseconds

    Returns:
        Decorated class or method with participant metadata

    Example (class-based):
        @tcc_participant("payment", order=1)
        class PaymentParticipant:
            @try_method
            async def reserve_payment(self, request):
                pass

    Example (method-based):
        @tcc_participant("payment", order=1)
        async def try_payment(self, request):
            pass
    """

    def decorator(target):
        if inspect.isfunction(target) or inspect.iscoroutinefunction(target):
            # Method-based participant - mark as try method
            config = TccParticipantConfig(
                participant_id=participant_id,
                order=order,
                timeout_ms=timeout_ms,
                try_method=target.__name__
            )
            target._tcc_participant_config = config
            target._is_tcc_try_method = True
            logger.debug(f"Registered TCC participant method: {participant_id} (order: {order})")
            return target
        else:
            # Class-based participant
            config = TccParticipantConfig(participant_id=participant_id, order=order, timeout_ms=timeout_ms)
            target._tcc_participant_config = config
            logger.debug(f"Registered TCC participant class: {participant_id} (order: {order})")
            return target

    return decorator


def try_method(
    func=None, *, timeout_ms: int = 10000, retry: int = 3, backoff_ms: int = 1000
) -> Callable:
    """
    Decorator to mark a method as a TCC try method.

    This is the Python equivalent of the Java @TryMethod annotation.

    Args:
        func: Function being decorated (when used without parentheses)
        timeout_ms: Method timeout in milliseconds
        retry: Number of retry attempts
        backoff_ms: Backoff time between retries

    Returns:
        Decorated method with try metadata

    Example:
        @try_method(timeout_ms=5000, retry=2)
        async def reserve_payment(self, request):
            # Reserve payment amount
            pass

        # Or without parameters:
        @try_method
        async def reserve_payment(self, request):
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Store try method configuration
        config = TccMethodConfig(
            method_type="try", timeout_ms=timeout_ms, retry=retry, backoff_ms=backoff_ms
        )
        func._tcc_method_config = config

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(f"Executing TCC try method: {func.__name__}")
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                logger.debug(f"TCC try method {func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(f"TCC try method {func.__name__} failed: {e}")
                raise

        return wrapper

    # Handle both @try_method and @try_method() usage
    if func is None:
        # Called with parameters: @try_method(timeout_ms=5000)
        return decorator
    else:
        # Called without parameters: @try_method
        return decorator(func)


def confirm_method(
    func=None, *, timeout_ms: int = 5000, retry: int = 2, backoff_ms: int = 500
) -> Callable:
    """
    Decorator to mark a method as a TCC confirm method.

    This is the Python equivalent of the Java @ConfirmMethod annotation.

    Args:
        func: Function being decorated (when used without parentheses)
        timeout_ms: Method timeout in milliseconds
        retry: Number of retry attempts
        backoff_ms: Backoff time between retries

    Returns:
        Decorated method with confirm metadata

    Example:
        @confirm_method(timeout_ms=3000)
        async def confirm_payment(self, reservation_result):
            # Confirm the payment reservation
            pass

        # Or without parameters:
        @confirm_method
        async def confirm_payment(self, reservation_result):
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Store confirm method configuration
        config = TccMethodConfig(
            method_type="confirm", timeout_ms=timeout_ms, retry=retry, backoff_ms=backoff_ms
        )
        func._tcc_method_config = config

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(f"Executing TCC confirm method: {func.__name__}")
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                logger.debug(f"TCC confirm method {func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(f"TCC confirm method {func.__name__} failed: {e}")
                raise

        return wrapper

    # Handle both @confirm_method and @confirm_method() usage
    if func is None:
        # Called with parameters: @confirm_method(timeout_ms=3000)
        return decorator
    else:
        # Called without parameters: @confirm_method
        return decorator(func)


def cancel_method(
    func=None, *, timeout_ms: int = 5000, retry: int = 5, backoff_ms: int = 500
) -> Callable:
    """
    Decorator to mark a method as a TCC cancel method.

    This is the Python equivalent of the Java @CancelMethod annotation.

    Args:
        func: Function being decorated (when used without parentheses)
        timeout_ms: Method timeout in milliseconds
        retry: Number of retry attempts (usually higher for cancel)
        backoff_ms: Backoff time between retries

    Returns:
        Decorated method with cancel metadata

    Example:
        @cancel_method(retry=3)
        async def cancel_payment(self, reservation_result):
            # Cancel/release the payment reservation
            pass

        # Or without parameters:
        @cancel_method
        async def cancel_payment(self, reservation_result):
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Store cancel method configuration
        config = TccMethodConfig(
            method_type="cancel", timeout_ms=timeout_ms, retry=retry, backoff_ms=backoff_ms
        )
        func._tcc_method_config = config

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(f"Executing TCC cancel method: {func.__name__}")
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                logger.debug(f"TCC cancel method {func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(f"TCC cancel method {func.__name__} failed: {e}")
                raise

        return wrapper

    # Handle both @cancel_method and @cancel_method() usage
    if func is None:
        # Called with parameters: @cancel_method(retry=3)
        return decorator
    else:
        # Called without parameters: @cancel_method
        return decorator(func)


def from_try(field_name: Optional[str] = None) -> Callable:
    """
    Decorator for parameter injection from try method result.

    This is the Python equivalent of the Java @FromTry annotation.

    Args:
        field_name: Optional field name to extract from try result

    Returns:
        Decorated parameter

    Note:
        This is a placeholder for parameter injection. The actual implementation
        would be handled by the TCC execution framework.
    """

    def decorator(param):
        param._from_try = field_name or True
        return param

    return decorator


def tcc_input(field_name: Optional[str] = None) -> Callable:
    """
    Decorator for TCC input parameter injection.

    This is the Python equivalent of the Java @Input annotation for TCC.

    Args:
        field_name: Optional field name to extract from input

    Returns:
        Decorated parameter
    """

    def decorator(param):
        param._tcc_input_field = field_name
        return param

    return decorator


def tcc_header(header_name: str) -> Callable:
    """
    Decorator for TCC header parameter injection.

    This is the Python equivalent of the Java @Header annotation for TCC.

    Args:
        header_name: Name of the header to inject

    Returns:
        Decorated parameter
    """

    def decorator(param):
        param._tcc_header_name = header_name
        return param

    return decorator


def _collect_participant_methods(participant_class: type, config: TccParticipantConfig) -> None:
    """Collect TCC method configurations from a participant class."""
    for attr_name in dir(participant_class):
        attr = getattr(participant_class, attr_name)
        if hasattr(attr, "_tcc_method_config"):
            method_config = attr._tcc_method_config
            if method_config.method_type == "try":
                config.try_method = attr_name
            elif method_config.method_type == "confirm":
                config.confirm_method = attr_name
            elif method_config.method_type == "cancel":
                config.cancel_method = attr_name


# Utility functions for extracting metadata


def get_tcc_config(cls: type) -> Optional[TccConfig]:
    """Get TCC configuration from a class."""
    return getattr(cls, "_tcc_config", None)


def get_tcc_name(cls: type) -> Optional[str]:
    """Get TCC name from a class."""
    return getattr(cls, "_tcc_name", None)


def get_participant_config(cls: type) -> Optional[TccParticipantConfig]:
    """Get participant configuration from a class."""
    return getattr(cls, "_tcc_participant_config", None)


def get_tcc_method_config(method: Callable) -> Optional[TccMethodConfig]:
    """Get TCC method configuration from a method."""
    return getattr(method, "_tcc_method_config", None)


def is_tcc_class(cls: type) -> bool:
    """Check if a class is decorated with @tcc."""
    return hasattr(cls, "_tcc_name")


def is_tcc_participant(cls: type) -> bool:
    """Check if a class is decorated with @tcc_participant."""
    return hasattr(cls, "_tcc_participant_config")


def is_try_method(method: Callable) -> bool:
    """Check if a method is decorated with @try_method."""
    config = getattr(method, "_tcc_method_config", None)
    return config is not None and config.method_type == "try"


def is_confirm_method(method: Callable) -> bool:
    """Check if a method is decorated with @confirm_method."""
    config = getattr(method, "_tcc_method_config", None)
    return config is not None and config.method_type == "confirm"


def is_cancel_method(method: Callable) -> bool:
    """Check if a method is decorated with @cancel_method."""
    config = getattr(method, "_tcc_method_config", None)
    return config is not None and config.method_type == "cancel"
