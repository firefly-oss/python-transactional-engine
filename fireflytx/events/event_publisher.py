"""
Event publisher for distributed transaction events.
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
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List

from ..core.saga_context import SagaContext
from ..core.tcc_context import TccContext


class EventPublisher(ABC):
    """Abstract base class for event publishing."""

    @abstractmethod
    async def publish_saga_event(
        self, event_type: str, context: SagaContext, data: Dict[str, Any]
    ) -> None:
        """Publish a SAGA event."""
        pass

    @abstractmethod
    async def publish_tcc_event(
        self, event_type: str, context: TccContext, data: Dict[str, Any]
    ) -> None:
        """Publish a TCC event."""
        pass


class InMemoryEventPublisher(EventPublisher):
    """In-memory event publisher for testing and development."""

    def __init__(self):
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._published_events: List[Dict[str, Any]] = []
        self._logger = logging.getLogger(__name__)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to events of a specific type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def publish_saga_event(
        self, event_type: str, context: SagaContext, data: Dict[str, Any]
    ) -> None:
        """Publish a SAGA event."""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context.to_dict(),
            "data": data,
            "event_category": "saga",
        }

        self._published_events.append(event)
        self._logger.info(f"Published SAGA event: {event_type}")

        # Notify handlers
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    self._logger.error(f"Error in event handler: {e}")

    async def publish_tcc_event(
        self, event_type: str, context: TccContext, data: Dict[str, Any]
    ) -> None:
        """Publish a TCC event."""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context.to_dict(),
            "data": data,
            "event_category": "tcc",
        }

        self._published_events.append(event)
        self._logger.info(f"Published TCC event: {event_type}")

        # Notify handlers
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    self._logger.error(f"Error in event handler: {e}")

    def get_published_events(self) -> List[Dict[str, Any]]:
        """Get all published events."""
        return self._published_events.copy()

    def clear_events(self) -> None:
        """Clear published events."""
        self._published_events.clear()


class RedisEventPublisher(EventPublisher):
    """Redis-based event publisher."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        import redis.asyncio as redis

        self._redis = redis.from_url(redis_url)
        self._logger = logging.getLogger(__name__)

    async def publish_saga_event(
        self, event_type: str, context: SagaContext, data: Dict[str, Any]
    ) -> None:
        """Publish a SAGA event via Redis."""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context.to_dict(),
            "data": data,
            "event_category": "saga",
        }

        channel = f"transactional.saga.{event_type}"
        await self._redis.publish(channel, str(event))
        self._logger.info(f"Published SAGA event to Redis: {event_type}")

    async def publish_tcc_event(
        self, event_type: str, context: TccContext, data: Dict[str, Any]
    ) -> None:
        """Publish a TCC event via Redis."""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context.to_dict(),
            "data": data,
            "event_category": "tcc",
        }

        channel = f"transactional.tcc.{event_type}"
        await self._redis.publish(channel, str(event))
        self._logger.info(f"Published TCC event to Redis: {event_type}")

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.close()


def create_event_publisher(provider: str = "memory", **kwargs) -> EventPublisher:
    """Factory function to create event publishers."""
    if provider == "memory":
        return InMemoryEventPublisher()
    elif provider == "redis":
        return RedisEventPublisher(kwargs.get("connection_string", "redis://localhost:6379"))
    else:
        raise ValueError(f"Unknown event publisher provider: {provider}")
