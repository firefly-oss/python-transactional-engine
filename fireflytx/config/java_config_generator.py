#!/usr/bin/env python3
"""
Java Configuration Generator for lib-transactional-engine Integration.

This module generates complete configuration objects that the Java lib-transactional-engine
can consume, following the "Python defines, Java executes" architecture.

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0 (the "License");
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..decorators.saga import SagaConfig, SagaStepConfig, SagaStepEventConfig
from ..events import StepEventPublisher
from ..persistence import SagaPersistenceProvider

logger = logging.getLogger(__name__)


@dataclass
class JavaSagaEngineConfig:
    """Complete SAGA engine configuration for Java lib-transactional-engine."""

    # Engine configuration
    engine_name: str
    compensation_policy: str = "STRICT_SEQUENTIAL"
    auto_optimization_enabled: bool = True
    layer_concurrency: int = 5

    # Event publishing configuration
    events: Dict[str, Any] = None

    # Persistence configuration
    persistence: Dict[str, Any] = None

    # Retry and timeout configuration
    default_retry_attempts: int = 3
    default_backoff_ms: int = 1000
    default_timeout_ms: int = 30000

    # Observability configuration
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    logging_level: str = "INFO"

    # Security configuration
    security_enabled: bool = False
    authentication_required: bool = False

    # Performance tuning
    thread_pool_size: int = 10
    max_concurrent_sagas: int = 100
    saga_state_cache_size: int = 1000


@dataclass
class JavaSagaDefinitionConfig:
    """SAGA definition configuration for Java lib-transactional-engine."""

    saga_name: str
    saga_class_name: str
    layer_concurrency: int = 5
    steps: List[Dict[str, Any]] = None
    compensation_methods: Dict[str, str] = None
    event_configuration: Dict[str, Any] = None
    callback_configuration: Dict[str, Any] = None


class JavaConfigGenerator:
    """
    Generates configuration objects for Java lib-transactional-engine.

    This class converts Python SAGA definitions, event publishers, and
    persistence providers into Java-consumable configuration objects.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_engine_config(
        self,
        engine_name: str,
        event_publisher: Optional[StepEventPublisher] = None,
        persistence_provider: Optional[SagaPersistenceProvider] = None,
        compensation_policy: str = "STRICT_SEQUENTIAL",
        auto_optimization: bool = True,
        **engine_options,
    ) -> Dict[str, Any]:
        """
        Generate complete engine configuration for Java.

        Args:
            engine_name: Name of the SAGA engine instance
            event_publisher: Event publisher implementation
            persistence_provider: Persistence provider implementation
            compensation_policy: Compensation execution policy
            auto_optimization: Enable automatic optimizations
            **engine_options: Additional engine configuration options

        Returns:
            Complete Java engine configuration dictionary
        """
        # Filter out conflicting options
        filtered_options = {
            k: v for k, v in engine_options.items() if k not in ["auto_optimization_enabled"]
        }

        config = JavaSagaEngineConfig(
            engine_name=engine_name,
            compensation_policy=compensation_policy,
            auto_optimization_enabled=auto_optimization,
            **filtered_options,
        )

        # Add event publisher configuration
        if event_publisher:
            config.events = event_publisher.get_publisher_config()
            self.logger.info(f"Added event publisher config: {config.events['type']}")
        else:
            config.events = {"type": "noop", "enabled": False}

        # Add persistence provider configuration
        if persistence_provider:
            config.persistence = persistence_provider.get_provider_config()
            self.logger.info(f"Added persistence config: {config.persistence['type']}")
        else:
            config.persistence = {"type": "noop", "enabled": False}

        # Convert to dictionary for Java consumption
        java_config = asdict(config)

        # Add metadata for Java engine
        java_config["metadata"] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator_version": "1.0.0",
            "python_architecture": "python_defines_java_executes",
            "target_engine": "lib-transactional-engine",
        }

        self.logger.debug(f"Generated engine config with {len(java_config)} top-level keys")
        return java_config

    def generate_saga_config(self, saga_class: type, saga_config: SagaConfig) -> Dict[str, Any]:
        """
        Generate SAGA definition configuration for Java.

        Args:
            saga_class: Python SAGA class
            saga_config: SAGA configuration from decorators

        Returns:
            Complete Java SAGA definition configuration
        """
        # Extract step configurations
        steps_config = []
        for step_id, step_config in saga_config.steps.items():
            step_dict = self._convert_step_config(step_config)
            steps_config.append(step_dict)

        # Generate callback configuration
        callback_config = self._generate_callback_config(saga_class, saga_config)

        # Generate event configuration
        event_config = self._generate_step_events_config(saga_config)

        java_saga_config = JavaSagaDefinitionConfig(
            saga_name=saga_config.name,
            saga_class_name=f"{saga_class.__module__}.{saga_class.__name__}",
            layer_concurrency=saga_config.layer_concurrency,
            steps=steps_config,
            compensation_methods=saga_config.compensation_methods,
            event_configuration=event_config,
            callback_configuration=callback_config,
        )

        # Convert to dictionary
        config_dict = asdict(java_saga_config)

        # Add metadata
        config_dict["metadata"] = {
            "saga_class": saga_class.__name__,
            "total_steps": len(steps_config),
            "has_compensations": len(saga_config.compensation_methods) > 0,
            "has_events": any(
                step.get("events", {}).get("enabled", False) for step in steps_config
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        self.logger.info(
            f"Generated SAGA config for '{saga_config.name}' with {len(steps_config)} steps"
        )
        return config_dict

    def _convert_step_config(self, step_config: SagaStepConfig) -> Dict[str, Any]:
        """Convert Python step configuration to Java format."""
        config = {
            "step_id": step_config.step_id,
            "depends_on": step_config.depends_on,
            "retry": {
                "attempts": step_config.retry,
                "backoff_ms": step_config.backoff_ms,
                "jitter": step_config.jitter,
                "jitter_factor": step_config.jitter_factor,
            },
            "timeout_ms": step_config.timeout_ms,
            "cpu_bound": step_config.cpu_bound,
            "idempotency_key": step_config.idempotency_key,
            "compensation": {
                "method": step_config.compensate,
                "retry_attempts": step_config.compensation_retry,
                "timeout_ms": step_config.compensation_timeout_ms,
                "critical": step_config.compensation_critical,
            },
        }

        # Add event configuration if present
        if step_config.events:
            config["events"] = self._convert_step_event_config(step_config.events)

        return config

    def _convert_step_event_config(self, event_config: SagaStepEventConfig) -> Dict[str, Any]:
        """Convert Python step event configuration to Java format."""
        return {
            "enabled": event_config.enabled,
            "topic": event_config.topic,
            "key_template": event_config.key_template,
            "include_payload": event_config.include_payload,
            "include_context": event_config.include_context,
            "include_result": event_config.include_result,
            "include_timing": event_config.include_timing,
            "custom_headers": event_config.custom_headers,
            "publish_on_start": event_config.publish_on_start,
            "publish_on_success": event_config.publish_on_success,
            "publish_on_failure": event_config.publish_on_failure,
            "publish_on_retry": event_config.publish_on_retry,
            "publish_on_compensation": event_config.publish_on_compensation,
        }

    def _generate_callback_config(
        self, saga_class: type, saga_config: SagaConfig
    ) -> Dict[str, Any]:
        """Generate callback configuration for Python method invocation."""
        callback_config = {
            "python_class": f"{saga_class.__module__}.{saga_class.__name__}",
            "callback_methods": {},
            "compensation_methods": saga_config.compensation_methods,
            "parameter_injection": {},
        }

        # Map step methods
        for step_id, step_config in saga_config.steps.items():
            method_name = self._find_method_name_for_step(saga_class, step_id)
            if method_name:
                callback_config["callback_methods"][step_id] = {
                    "method_name": method_name,
                    "is_async": self._is_async_method(saga_class, method_name),
                    "parameter_types": self._extract_parameter_types(saga_class, method_name),
                }

        return callback_config

    def _generate_step_events_config(self, saga_config: SagaConfig) -> Dict[str, Any]:
        """Generate comprehensive event configuration for all steps."""
        events_config = {
            "global_events_enabled": True,
            "default_topic": f"{saga_config.name}-events",
            "step_configurations": {},
        }

        for step_id, step_config in saga_config.steps.items():
            if step_config.events:
                events_config["step_configurations"][step_id] = self._convert_step_event_config(
                    step_config.events
                )

        return events_config

    def _find_method_name_for_step(self, saga_class: type, step_id: str) -> Optional[str]:
        """Find the method name associated with a step ID."""
        for attr_name in dir(saga_class):
            attr = getattr(saga_class, attr_name)
            if hasattr(attr, "_saga_step_config"):
                if attr._saga_step_config.step_id == step_id:
                    return attr_name
        return None

    def _is_async_method(self, saga_class: type, method_name: str) -> bool:
        """Check if a method is async."""
        import inspect

        method = getattr(saga_class, method_name, None)
        return inspect.iscoroutinefunction(method) if method else False

    def _extract_parameter_types(self, saga_class: type, method_name: str) -> List[str]:
        """Extract parameter type information for Java callback."""
        import inspect

        method = getattr(saga_class, method_name, None)
        if not method:
            return []

        signature = inspect.signature(method)
        param_types = []

        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue

            param_type = "Any"
            if param.annotation and param.annotation != inspect.Parameter.empty:
                param_type = str(param.annotation)

            param_types.append(
                {
                    "name": param_name,
                    "type": param_type,
                    "has_default": param.default != inspect.Parameter.empty,
                }
            )

        return param_types

    def generate_complete_config(
        self,
        engine_name: str,
        saga_classes: List[type],
        event_publisher: Optional[StepEventPublisher] = None,
        persistence_provider: Optional[SagaPersistenceProvider] = None,
        **engine_options,
    ) -> Dict[str, Any]:
        """
        Generate complete configuration for multiple SAGAs and engine setup.

        Args:
            engine_name: SAGA engine name
            saga_classes: List of SAGA classes to configure
            event_publisher: Event publisher implementation
            persistence_provider: Persistence provider implementation
            **engine_options: Additional engine configuration

        Returns:
            Complete configuration for Java lib-transactional-engine
        """
        # Generate engine configuration
        engine_config = self.generate_engine_config(
            engine_name=engine_name,
            event_publisher=event_publisher,
            persistence_provider=persistence_provider,
            **engine_options,
        )

        # Generate SAGA configurations
        saga_configs = []
        for saga_class in saga_classes:
            if hasattr(saga_class, "_saga_config"):
                saga_config = self.generate_saga_config(saga_class, saga_class._saga_config)
                saga_configs.append(saga_config)
            else:
                self.logger.warning(f"Class {saga_class.__name__} is not a SAGA class")

        # Combine into complete configuration
        complete_config = {
            "engine": engine_config,
            "sagas": saga_configs,
            "global_metadata": {
                "total_sagas": len(saga_configs),
                "python_version": self._get_python_version(),
                "fireflytx_version": "1.0.0",
                "configuration_schema_version": "1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        self.logger.info(f"Generated complete config for {len(saga_configs)} SAGAs")
        return complete_config

    def export_config_to_json(self, config: Dict[str, Any], file_path: str) -> None:
        """Export configuration to JSON file for Java consumption."""
        try:
            with open(file_path, "w") as f:
                json.dump(config, f, indent=2, default=str)
            self.logger.info(f"Exported configuration to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to export config to {file_path}: {e}")
            raise

    def _get_python_version(self) -> str:
        """Get Python version information."""
        import sys

        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


# Convenience functions
def generate_saga_engine_config(
    engine_name: str,
    saga_classes: List[type],
    event_publisher: Optional[StepEventPublisher] = None,
    persistence_provider: Optional[SagaPersistenceProvider] = None,
    **options,
) -> Dict[str, Any]:
    """
    Convenience function to generate complete SAGA engine configuration.

    This is the main entry point for generating Java lib-transactional-engine
    configuration from Python SAGA definitions.
    """
    generator = JavaConfigGenerator()
    return generator.generate_complete_config(
        engine_name=engine_name,
        saga_classes=saga_classes,
        event_publisher=event_publisher,
        persistence_provider=persistence_provider,
        **options,
    )
