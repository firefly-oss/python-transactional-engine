"""
Python decorators for SAGA pattern.

This module provides decorators that convert Java annotations to Python equivalents,
allowing Python classes and methods to be used with the SAGA pattern.
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
from typing import Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class SagaStepEventConfig:
    """Configuration for step event publishing."""

    enabled: bool = True
    topic: Optional[str] = None
    key_template: Optional[str] = None
    include_payload: bool = True
    include_context: bool = True
    include_result: bool = True
    include_timing: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)
    publish_on_start: bool = True
    publish_on_success: bool = True
    publish_on_failure: bool = True
    publish_on_retry: bool = False
    publish_on_compensation: bool = True


@dataclass
class SagaStepConfig:
    """Configuration for a saga step."""

    step_id: str
    depends_on: List[str] = field(default_factory=list)
    retry: int = 3
    backoff_ms: int = 1000
    timeout_ms: int = 30000
    jitter: bool = True
    jitter_factor: float = 0.3
    cpu_bound: bool = False
    idempotency_key: Optional[str] = None
    compensate: Optional[str] = None
    compensation_retry: int = 3
    compensation_timeout_ms: int = 10000
    compensation_critical: bool = False
    # Event publishing configuration
    events: Optional[SagaStepEventConfig] = None


@dataclass
class SagaConfig:
    """Configuration for a saga."""

    name: str
    layer_concurrency: int = 5
    steps: Dict[str, SagaStepConfig] = field(default_factory=dict)
    compensation_methods: Dict[str, str] = field(default_factory=dict)
    compensation_configs: Dict[str, "CompensationStepConfig"] = field(default_factory=dict)


def saga(name: str, layer_concurrency: int = 5) -> Callable:
    """
    Decorator to mark a class as a SAGA.

    This is the Python equivalent of the Java @Saga annotation.

    Args:
        name: Name of the saga
        layer_concurrency: Maximum concurrency within execution layers

    Returns:
        Decorated class with saga metadata

    Example:
        @saga("order-processing")
        class OrderProcessingSaga:
            pass
    """

    def decorator(cls: type) -> type:
        # Store saga metadata on the class
        cls._saga_name = name
        cls._saga_config = SagaConfig(name=name, layer_concurrency=layer_concurrency)

        # Collect step configurations from decorated methods
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, "_saga_step_config"):
                step_config = attr._saga_step_config
                cls._saga_config.steps[step_config.step_id] = step_config

            if hasattr(attr, "_compensation_for_step"):
                step_id = attr._compensation_for_step
                cls._saga_config.compensation_methods[step_id] = attr_name

                # Also collect compensation configuration if available
                if hasattr(attr, "_compensation_config"):
                    cls._saga_config.compensation_configs[step_id] = attr._compensation_config

        logger.debug(f"Registered saga: {name} with {len(cls._saga_config.steps)} steps")
        return cls

    return decorator


def step_events(
    enabled: bool = True,
    topic: Optional[str] = None,
    key_template: Optional[str] = None,
    include_payload: bool = True,
    include_context: bool = True,
    include_result: bool = True,
    include_timing: bool = True,
    custom_headers: Optional[Dict[str, str]] = None,
    publish_on_start: bool = True,
    publish_on_success: bool = True,
    publish_on_failure: bool = True,
    publish_on_retry: bool = False,
    publish_on_compensation: bool = True,
) -> Callable:
    """
    Decorator to configure event publishing for a SAGA step.

    This decorator configures how events are published during step execution.
    Python defines the event configuration, Java executes the publishing.

    Args:
        enabled: Whether event publishing is enabled for this step
        topic: Custom topic for step events (defaults to SAGA-level topic)
        key_template: Template for event keys (e.g., "{saga_id}-{step_id}")
        include_payload: Include step payload in events
        include_context: Include SAGA context in events
        include_result: Include step results in events
        include_timing: Include timing information in events
        custom_headers: Custom headers to add to events
        publish_on_start: Publish event when step starts
        publish_on_success: Publish event when step succeeds
        publish_on_failure: Publish event when step fails
        publish_on_retry: Publish event on step retry
        publish_on_compensation: Publish event during compensation

    Returns:
        Decorated method with event configuration

    Example:
        @step_events(topic="payment-events", key_template="{saga_id}-payment")
        @saga_step("process-payment")
        async def process_payment(self, order_id: str) -> PaymentResult:
            # Implementation
            pass
    """

    def decorator(func: Callable) -> Callable:
        event_config = SagaStepEventConfig(
            enabled=enabled,
            topic=topic,
            key_template=key_template,
            include_payload=include_payload,
            include_context=include_context,
            include_result=include_result,
            include_timing=include_timing,
            custom_headers=custom_headers or {},
            publish_on_start=publish_on_start,
            publish_on_success=publish_on_success,
            publish_on_failure=publish_on_failure,
            publish_on_retry=publish_on_retry,
            publish_on_compensation=publish_on_compensation,
        )

        # Store event configuration on the method
        func._step_event_config = event_config

        return func

    return decorator


def saga_step(
    step_id: str,
    depends_on: Optional[Union[str, List[str]]] = None,
    retry: int = 3,
    backoff_ms: int = 1000,
    timeout_ms: int = 30000,
    jitter: bool = True,
    jitter_factor: float = 0.3,
    cpu_bound: bool = False,
    idempotency_key: Optional[str] = None,
    compensate: Optional[str] = None,
    compensation_retry: int = 3,
    compensation_timeout_ms: int = 10000,
    compensation_critical: bool = False,
    critical: Optional[bool] = None,  # Alias for compensation_critical
) -> Callable:
    """
    Decorator to mark a method as a SAGA step.

    This is the Python equivalent of the Java @SagaStep annotation.

    Args:
        step_id: Unique identifier for the step
        depends_on: Step IDs this step depends on
        retry: Number of retry attempts
        backoff_ms: Backoff time between retries
        timeout_ms: Step timeout in milliseconds
        jitter: Enable jitter in retry backoff
        jitter_factor: Jitter factor for backoff randomization
        cpu_bound: Whether this is a CPU-bound operation
        idempotency_key: Key for idempotent execution
        compensate: Name of the compensation method
        compensation_retry: Number of compensation retry attempts
        compensation_timeout_ms: Compensation timeout in milliseconds
        compensation_critical: Whether compensation failure is critical

    Returns:
        Decorated method with step metadata

    Example:
        @saga_step("validate-payment", retry=5, timeout_ms=10000)
        async def validate_payment(self, order_id: str) -> PaymentResult:
            # Implementation
            pass
    """
    # Normalize depends_on to a list
    deps = []
    if depends_on is not None:
        if isinstance(depends_on, str):
            deps = [depends_on]
        else:
            deps = list(depends_on)

    # Handle critical parameter as alias for compensation_critical
    final_compensation_critical = critical if critical is not None else compensation_critical

    def decorator(func: Callable) -> Callable:
        # Get event configuration if it exists (from @step_events decorator)
        event_config = getattr(func, "_step_event_config", None)

        # Create step configuration
        config = SagaStepConfig(
            step_id=step_id,
            depends_on=deps,
            retry=retry,
            backoff_ms=backoff_ms,
            timeout_ms=timeout_ms,
            jitter=jitter,
            jitter_factor=jitter_factor,
            cpu_bound=cpu_bound,
            idempotency_key=idempotency_key,
            compensate=compensate,
            compensation_retry=compensation_retry,
            compensation_timeout_ms=compensation_timeout_ms,
            compensation_critical=final_compensation_critical,
            events=event_config,
        )

        # Store configuration on the method
        func._saga_step_config = config

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Add step execution logging
            logger.debug(f"Executing saga step: {step_id}")
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                logger.debug(f"Saga step {step_id} completed successfully")
                return result
            except Exception as e:
                logger.error(f"Saga step {step_id} failed: {e}")
                raise

        return wrapper

    return decorator


@dataclass
class CompensationStepConfig:
    """Configuration for a compensation step."""

    for_step_id: str
    retry: int = 3
    timeout_ms: int = 10000
    critical: bool = False
    backoff_ms: int = 1000
    jitter: bool = True
    jitter_factor: float = 0.3


def compensation_step(
    for_step_id: str,
    retry: int = 3,
    timeout_ms: int = 10000,
    critical: bool = False,
    backoff_ms: int = 1000,
    jitter: bool = True,
    jitter_factor: float = 0.3,
) -> Callable:
    """
    Decorator to mark a method as a compensation step.

    This is the Python equivalent of the Java @CompensationSagaStep annotation.

    Args:
        for_step_id: The step ID this method compensates for
        retry: Number of retry attempts for compensation
        timeout_ms: Compensation timeout in milliseconds
        critical: Whether compensation failure is critical (should halt saga)
        backoff_ms: Backoff time between retries in milliseconds
        jitter: Enable jitter in retry backoff
        jitter_factor: Jitter factor for backoff randomization

    Returns:
        Decorated method with compensation metadata

    Example:
        @compensation_step("charge-payment", retry=5, timeout_ms=15000, critical=True)
        async def refund_payment(self, payment_result: PaymentResult) -> None:
            # Compensation logic
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Create compensation configuration
        config = CompensationStepConfig(
            for_step_id=for_step_id,
            retry=retry,
            timeout_ms=timeout_ms,
            critical=critical,
            backoff_ms=backoff_ms,
            jitter=jitter,
            jitter_factor=jitter_factor,
        )

        # Store configuration on the method
        func._compensation_for_step = for_step_id
        func._compensation_config = config

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(
                f"Executing compensation for step: {for_step_id} "
                f"(retry={retry}, timeout={timeout_ms}ms, critical={critical})"
            )
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                logger.debug(f"Compensation for step {for_step_id} completed successfully")
                return result
            except Exception as e:
                logger.error(
                    f"Compensation for step {for_step_id} failed: {e} "
                    f"(critical={critical})"
                )
                raise

        return wrapper

    return decorator


def from_step(step_id: str) -> Callable:
    """
    Decorator for parameter injection from another step's result.

    This is the Python equivalent of the Java @FromStep annotation.

    Args:
        step_id: The step ID to get the result from

    Returns:
        Decorated parameter

    Note:
        This is a placeholder for parameter injection. The actual implementation
        would be handled by the step execution framework.
    """

    def decorator(param):
        param._from_step = step_id
        return param

    return decorator


def input_param(field_name: Optional[str] = None) -> Callable:
    """
    Decorator for input parameter injection.

    This is the Python equivalent of the Java @Input annotation.

    Args:
        field_name: Optional field name to extract from input

    Returns:
        Decorated parameter
    """

    def decorator(param):
        param._input_field = field_name
        return param

    return decorator


def header_param(header_name: str) -> Callable:
    """
    Decorator for header parameter injection.

    This is the Python equivalent of the Java @Header annotation.

    Args:
        header_name: Name of the header to inject

    Returns:
        Decorated parameter
    """

    def decorator(param):
        param._header_name = header_name
        return param

    return decorator


def variable_param(variable_name: str) -> Callable:
    """
    Decorator for context variable parameter injection.

    This is the Python equivalent of the Java @Variable annotation.

    Args:
        variable_name: Name of the context variable

    Returns:
        Decorated parameter
    """

    def decorator(param):
        param._variable_name = variable_name
        return param

    return decorator


# Utility functions for extracting metadata


def get_saga_config(cls: type) -> Optional[SagaConfig]:
    """Get saga configuration from a class."""
    return getattr(cls, "_saga_config", None)


def get_saga_name(cls: type) -> Optional[str]:
    """Get saga name from a class."""
    return getattr(cls, "_saga_name", None)


def get_step_config(method: Callable) -> Optional[SagaStepConfig]:
    """Get step configuration from a method."""
    return getattr(method, "_saga_step_config", None)


def is_saga_class(cls: type) -> bool:
    """Check if a class is decorated with @saga."""
    return hasattr(cls, "_saga_name")


def is_saga_step(method: Callable) -> bool:
    """Check if a method is decorated with @saga_step."""
    return hasattr(method, "_saga_step_config")


def is_compensation_step(method: Callable) -> bool:
    """Check if a method is decorated with @compensation_step."""
    return hasattr(method, "_compensation_for_step")
