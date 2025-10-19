#!/usr/bin/env python3
"""
SAGA Event Publishing System - Python Defines, Java Executes

This module provides Python interfaces for defining event publishing behavior
while delegating the actual event processing to the Java lib-transactional-engine.

Architecture:
- Python defines event publishers and event structures
- Java lib-transactional-engine handles event publishing execution
- Python receives callbacks for custom event handling logic
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
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of SAGA events that can be published."""

    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_COMPENSATED = "step_compensated"
    SAGA_STARTED = "saga_started"
    SAGA_COMPLETED = "saga_completed"
    SAGA_FAILED = "saga_failed"
    SAGA_COMPENSATED = "saga_compensated"


@dataclass
class StepEvent:
    """
    SAGA step event data structure.

    This mirrors the Java StepEventEnvelope structure but in Python.
    Python defines the event structure, Java executes the publishing.
    """

    saga_name: str
    saga_id: str
    step_id: str
    event_type: EventType
    topic: Optional[str] = None
    key: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None

    # Execution metadata
    attempts: Optional[int] = None
    latency_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_type: Optional[str] = None

    # Automatic fields
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for Java bridge communication."""
        return {
            "sagaName": self.saga_name,
            "sagaId": self.saga_id,
            "stepId": self.step_id,
            "type": self.event_type.value,
            "topic": self.topic,
            "key": self.key,
            "payload": self.payload,
            "headers": self.headers or {},
            "attempts": self.attempts,
            "latencyMs": self.latency_ms,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "resultType": self.result_type,
            "timestamp": self.timestamp.isoformat(),
        }


class StepEventPublisher(ABC):
    """
    Abstract base class for SAGA step event publishers.

    Python defines the publishing interface, Java executes the publishing.
    Implementations define how events should be published (Kafka, SQS, etc.)
    but the actual publishing is handled by the Java engine.
    """

    @abstractmethod
    async def publish(self, event: StepEvent) -> None:
        """
        Define how to publish a SAGA step event.

        This method is called by Python but the actual publishing
        is delegated to the Java lib-transactional-engine.

        Args:
            event: The step event to publish
        """
        pass

    @abstractmethod
    def get_publisher_config(self) -> Dict[str, Any]:
        """
        Get publisher configuration for Java engine.

        Returns:
            Configuration dictionary that will be passed to Java
        """
        pass


class NoOpStepEventPublisher(StepEventPublisher):
    """
    No-operation event publisher.

    This is the default publisher when no custom publisher is configured.
    Events are logged but not published to any external system.
    """

    async def publish(self, event: StepEvent) -> None:
        """Log the event but don't publish it."""
        logger.debug(
            f"NoOp publish: {event.event_type.value} for {event.saga_name}.{event.step_id}"
        )

    def get_publisher_config(self) -> Dict[str, Any]:
        """Return configuration for no-op publisher."""
        return {"type": "noop", "enabled": False}


class KafkaStepEventPublisher(StepEventPublisher):
    """
    Kafka-based step event publisher.

    Python defines the Kafka configuration, Java executes the publishing.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        default_topic: str = "saga-events",
        key_serializer: str = "string",
        value_serializer: str = "json",
        **kafka_config,
    ):
        """
        Initialize Kafka publisher configuration.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            default_topic: Default topic for events
            key_serializer: Key serialization format
            value_serializer: Value serialization format
            **kafka_config: Additional Kafka configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.default_topic = default_topic
        self.key_serializer = key_serializer
        self.value_serializer = value_serializer
        self.kafka_config = kafka_config

    async def publish(self, event: StepEvent) -> None:
        """
        Define Kafka publishing logic.

        The actual publishing is handled by Java, this method
        defines the publishing strategy.
        """
        topic = event.topic or self.default_topic
        key = event.key or f"{event.saga_name}-{event.step_id}"

        logger.info(f"Publishing event to Kafka topic '{topic}': {event.event_type.value}")

        # The Java engine will handle the actual Kafka publishing
        # based on the configuration provided by get_publisher_config()

    def get_publisher_config(self) -> Dict[str, Any]:
        """Get Kafka publisher configuration for Java engine."""
        return {
            "type": "kafka",
            "enabled": True,
            "bootstrap_servers": self.bootstrap_servers,
            "default_topic": self.default_topic,
            "key_serializer": self.key_serializer,
            "value_serializer": self.value_serializer,
            "properties": self.kafka_config,
        }


def create_step_event(
    saga_name: str,
    saga_id: str,
    step_id: str,
    event_type: EventType,
    payload: Optional[Dict[str, Any]] = None,
    topic: Optional[str] = None,
    key: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> StepEvent:
    """
    Convenience function to create a step event.

    Args:
        saga_name: Name of the SAGA
        saga_id: Unique identifier of the SAGA execution
        step_id: Identifier of the step
        event_type: Type of event
        payload: Event payload data
        topic: Publishing topic (optional)
        key: Publishing key (optional)
        headers: Additional headers (optional)

    Returns:
        StepEvent instance
    """
    return StepEvent(
        saga_name=saga_name,
        saga_id=saga_id,
        step_id=step_id,
        event_type=event_type,
        payload=payload,
        topic=topic,
        key=key,
        headers=headers,
    )
