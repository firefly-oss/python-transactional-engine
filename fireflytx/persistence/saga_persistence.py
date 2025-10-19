"""
SAGA persistence provider for state management.
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
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.saga_context import SagaContext

logger = logging.getLogger(__name__)


class SagaPersistenceProvider(ABC):
    """Abstract base class for SAGA persistence."""

    @abstractmethod
    async def save_saga_state(
        self, correlation_id: str, context: SagaContext, state: Dict[str, Any]
    ) -> None:
        """Save SAGA state."""
        pass

    @abstractmethod
    async def load_saga_state(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Load SAGA state."""
        pass

    @abstractmethod
    async def delete_saga_state(self, correlation_id: str) -> None:
        """Delete SAGA state."""
        pass

    @abstractmethod
    async def list_active_sagas(self) -> List[str]:
        """List active SAGA correlation IDs."""
        pass


class NoOpSagaPersistenceProvider(SagaPersistenceProvider):
    """
    No-operation persistence provider.

    This provider logs persistence operations but doesn't actually persist data.
    Useful for testing or when persistence is not required.
    """

    # Abstract method implementations
    async def save_saga_state(
        self, correlation_id: str, context: SagaContext, state: Dict[str, Any]
    ) -> None:
        """Save SAGA state - NoOp implementation."""
        logger.debug(f"NoOp save_saga_state: {correlation_id}")

    async def load_saga_state(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Load SAGA state - NoOp implementation."""
        logger.debug(f"NoOp load_saga_state: {correlation_id}")
        return None

    async def delete_saga_state(self, correlation_id: str) -> None:
        """Delete SAGA state - NoOp implementation."""
        logger.debug(f"NoOp delete_saga_state: {correlation_id}")

    async def list_active_sagas(self) -> List[str]:
        """List active SAGAs - NoOp implementation."""
        logger.debug("NoOp list_active_sagas")
        return []

    # Additional convenience methods for Java bridge integration
    async def persist_saga(self, saga_id: str, saga_context: Dict[str, Any]) -> bool:
        """Log persistence but don't actually persist."""
        logger.debug(f"NoOp persist saga: {saga_id}")
        return True

    async def retrieve_saga(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """Log retrieval but return None."""
        logger.debug(f"NoOp retrieve saga: {saga_id}")
        return None

    async def update_step_status(
        self, saga_id: str, step_id: str, status: str, result: Any = None
    ) -> bool:
        """Log status update but don't actually persist."""
        logger.debug(f"NoOp update step status: {saga_id}.{step_id} -> {status}")
        return True

    async def cleanup_completed_saga(self, saga_id: str) -> bool:
        """Log cleanup but don't actually clean up."""
        logger.debug(f"NoOp cleanup saga: {saga_id}")
        return True

    def get_provider_config(self) -> Dict[str, Any]:
        """Return configuration for no-op provider."""
        return {"type": "noop", "enabled": False}


class RedisSagaPersistenceProvider(SagaPersistenceProvider):
    """
    Redis-based SAGA persistence provider.

    Python defines the Redis configuration, Java executes the persistence operations.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        database: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "saga:",
        ttl_seconds: int = 86400,
        **redis_config,
    ):
        """
        Initialize Redis persistence configuration.

        Args:
            host: Redis host
            port: Redis port
            database: Redis database number
            password: Redis password (optional)
            key_prefix: Prefix for all Redis keys
            ttl_seconds: TTL for saga data
            **redis_config: Additional Redis configuration
        """
        self.host = host
        self.port = port
        self.database = database
        self.password = password
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds
        self.redis_config = redis_config

    # Abstract method implementations
    async def save_saga_state(
        self, correlation_id: str, context: SagaContext, state: Dict[str, Any]
    ) -> None:
        """Save SAGA state to Redis."""
        key = f"{self.key_prefix}{correlation_id}:state"
        logger.info(f"Saving SAGA state to Redis key: {key}")
        # Java engine will handle the actual Redis operations

    async def load_saga_state(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Load SAGA state from Redis."""
        key = f"{self.key_prefix}{correlation_id}:state"
        logger.info(f"Loading SAGA state from Redis key: {key}")
        # Java engine will handle the actual Redis operations
        return None  # Placeholder - Java will return the actual data

    async def delete_saga_state(self, correlation_id: str) -> None:
        """Delete SAGA state from Redis."""
        key = f"{self.key_prefix}{correlation_id}:state"
        logger.info(f"Deleting SAGA state from Redis key: {key}")
        # Java engine will handle the actual Redis operations

    async def list_active_sagas(self) -> List[str]:
        """List active SAGAs from Redis."""
        pattern = f"{self.key_prefix}*:state"
        logger.info(f"Listing active SAGAs from Redis pattern: {pattern}")
        # Java engine will handle the actual Redis operations
        return []  # Placeholder - Java will return the actual data

    # Additional convenience methods for Java bridge integration
    async def persist_saga(self, saga_id: str, saga_context: Dict[str, Any]) -> bool:
        """
        Define Redis persistence logic.

        The actual Redis operations are handled by Java.
        """
        key = f"{self.key_prefix}{saga_id}"
        logger.info(f"Persisting saga to Redis key: {key}")

        # Java engine will handle the actual Redis persistence
        # based on the configuration from get_provider_config()
        return True

    async def retrieve_saga(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """
        Define Redis retrieval logic.

        The actual Redis operations are handled by Java.
        """
        key = f"{self.key_prefix}{saga_id}"
        logger.info(f"Retrieving saga from Redis key: {key}")

        # Java engine will handle the actual Redis retrieval
        return None  # Placeholder - Java will return the actual data

    async def update_step_status(
        self, saga_id: str, step_id: str, status: str, result: Any = None
    ) -> bool:
        """
        Define Redis step status update logic.

        The actual Redis operations are handled by Java.
        """
        key = f"{self.key_prefix}{saga_id}:steps:{step_id}"
        logger.info(f"Updating step status in Redis key: {key} -> {status}")

        # Java engine will handle the actual Redis update
        return True

    async def cleanup_completed_saga(self, saga_id: str) -> bool:
        """
        Define Redis cleanup logic.

        The actual Redis operations are handled by Java.
        """
        pattern = f"{self.key_prefix}{saga_id}*"
        logger.info(f"Cleaning up saga from Redis pattern: {pattern}")

        # Java engine will handle the actual Redis cleanup
        return True

    def get_provider_config(self) -> Dict[str, Any]:
        """Get Redis provider configuration for Java engine."""
        config = {
            "type": "redis",
            "enabled": True,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "key_prefix": self.key_prefix,
            "ttl_seconds": self.ttl_seconds,
            "properties": self.redis_config,
        }

        if self.password:
            config["password"] = self.password

        return config


class DatabaseSagaPersistenceProvider(SagaPersistenceProvider):
    """
    Database-based SAGA persistence provider.

    Python defines the database configuration, Java executes the persistence operations.
    """

    def __init__(
        self,
        connection_url: str,
        table_prefix: str = "saga_",
        schema: Optional[str] = None,
        **db_config,
    ):
        """
        Initialize database persistence configuration.

        Args:
            connection_url: Database connection URL
            table_prefix: Prefix for all database tables
            schema: Database schema (optional)
            **db_config: Additional database configuration
        """
        self.connection_url = connection_url
        self.table_prefix = table_prefix
        self.schema = schema
        self.db_config = db_config

    # Abstract method implementations
    async def save_saga_state(
        self, correlation_id: str, context: SagaContext, state: Dict[str, Any]
    ) -> None:
        """Save SAGA state to database."""
        table_name = f"{self.table_prefix}state"
        if self.schema:
            table_name = f"{self.schema}.{table_name}"

        logger.info(f"Saving SAGA state to database table: {table_name}")
        # Java engine will handle the actual database operations

    async def load_saga_state(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Load SAGA state from database."""
        table_name = f"{self.table_prefix}state"
        if self.schema:
            table_name = f"{self.schema}.{table_name}"

        logger.info(f"Loading SAGA state from database table: {table_name}")
        # Java engine will handle the actual database operations
        return None  # Placeholder - Java will return the actual data

    async def delete_saga_state(self, correlation_id: str) -> None:
        """Delete SAGA state from database."""
        table_name = f"{self.table_prefix}state"
        if self.schema:
            table_name = f"{self.schema}.{table_name}"

        logger.info(f"Deleting SAGA state from database table: {table_name}")
        # Java engine will handle the actual database operations

    async def list_active_sagas(self) -> List[str]:
        """List active SAGAs from database."""
        table_name = f"{self.table_prefix}state"
        if self.schema:
            table_name = f"{self.schema}.{table_name}"

        logger.info(f"Listing active SAGAs from database table: {table_name}")
        # Java engine will handle the actual database operations
        return []  # Placeholder - Java will return the actual data

    # Additional convenience methods for Java bridge integration
    async def persist_saga(self, saga_id: str, saga_context: Dict[str, Any]) -> bool:
        """
        Define database persistence logic.

        The actual database operations are handled by Java.
        """
        table_name = f"{self.table_prefix}executions"
        if self.schema:
            table_name = f"{self.schema}.{table_name}"

        logger.info(f"Persisting saga to database table: {table_name}")

        # Java engine will handle the actual database persistence
        return True

    async def retrieve_saga(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """
        Define database retrieval logic.

        The actual database operations are handled by Java.
        """
        table_name = f"{self.table_prefix}executions"
        if self.schema:
            table_name = f"{self.schema}.{table_name}"

        logger.info(f"Retrieving saga from database table: {table_name}")

        # Java engine will handle the actual database retrieval
        return None  # Placeholder - Java will return the actual data

    async def update_step_status(
        self, saga_id: str, step_id: str, status: str, result: Any = None
    ) -> bool:
        """
        Define database step status update logic.

        The actual database operations are handled by Java.
        """
        table_name = f"{self.table_prefix}steps"
        if self.schema:
            table_name = f"{self.schema}.{table_name}"

        logger.info(f"Updating step status in database table: {table_name}")

        # Java engine will handle the actual database update
        return True

    async def cleanup_completed_saga(self, saga_id: str) -> bool:
        """
        Define database cleanup logic.

        The actual database operations are handled by Java.
        """
        logger.info(f"Cleaning up completed saga from database: {saga_id}")

        # Java engine will handle the actual database cleanup
        return True

    def get_provider_config(self) -> Dict[str, Any]:
        """Get database provider configuration for Java engine."""
        config = {
            "type": "database",
            "enabled": True,
            "connection_url": self.connection_url,
            "table_prefix": self.table_prefix,
            "properties": self.db_config,
        }

        if self.schema:
            config["schema"] = self.schema

        return config


class InMemorySagaPersistence(SagaPersistenceProvider):
    """In-memory SAGA persistence for testing and development."""

    def __init__(self):
        self._state_store: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger(__name__)

    async def save_saga_state(
        self, correlation_id: str, context: SagaContext, state: Dict[str, Any]
    ) -> None:
        """Save SAGA state."""
        saga_data = {
            "context": context.to_dict(),
            "state": state,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._state_store[correlation_id] = saga_data
        self._logger.debug(f"Saved SAGA state for {correlation_id}")

    async def load_saga_state(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Load SAGA state."""
        return self._state_store.get(correlation_id)

    async def delete_saga_state(self, correlation_id: str) -> None:
        """Delete SAGA state."""
        if correlation_id in self._state_store:
            del self._state_store[correlation_id]
            self._logger.debug(f"Deleted SAGA state for {correlation_id}")

    async def list_active_sagas(self) -> List[str]:
        """List active SAGA correlation IDs."""
        return list(self._state_store.keys())

    def clear_all(self) -> None:
        """Clear all state (for testing)."""
        self._state_store.clear()


class RedisSagaPersistence(SagaPersistenceProvider):
    """Redis-based SAGA persistence."""

    def __init__(self, redis_url: str = "redis://localhost:6379", key_prefix: str = "saga:"):
        import redis.asyncio as redis

        self._redis = redis.from_url(redis_url)
        self._key_prefix = key_prefix
        self._logger = logging.getLogger(__name__)

    def _make_key(self, correlation_id: str) -> str:
        """Create Redis key for correlation ID."""
        return f"{self._key_prefix}{correlation_id}"

    async def save_saga_state(
        self, correlation_id: str, context: SagaContext, state: Dict[str, Any]
    ) -> None:
        """Save SAGA state."""
        saga_data = {
            "context": context.to_dict(),
            "state": state,
            "updated_at": datetime.utcnow().isoformat(),
        }
        key = self._make_key(correlation_id)
        await self._redis.set(key, json.dumps(saga_data))
        self._logger.debug(f"Saved SAGA state to Redis for {correlation_id}")

    async def load_saga_state(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Load SAGA state."""
        key = self._make_key(correlation_id)
        data = await self._redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def delete_saga_state(self, correlation_id: str) -> None:
        """Delete SAGA state."""
        key = self._make_key(correlation_id)
        await self._redis.delete(key)
        self._logger.debug(f"Deleted SAGA state from Redis for {correlation_id}")

    async def list_active_sagas(self) -> List[str]:
        """List active SAGA correlation IDs."""
        pattern = f"{self._key_prefix}*"
        keys = await self._redis.keys(pattern)
        return [key.decode("utf-8").replace(self._key_prefix, "") for key in keys]

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.close()


def create_saga_persistence(provider: str = "memory", **kwargs) -> SagaPersistenceProvider:
    """Factory function to create SAGA persistence providers."""
    if provider == "memory":
        return InMemorySagaPersistence()
    elif provider == "redis":
        return RedisSagaPersistence(
            kwargs.get("connection_string", "redis://localhost:6379"),
            kwargs.get("key_prefix", "saga:"),
        )
    else:
        raise ValueError(f"Unknown SAGA persistence provider: {provider}")
