"""
TCC persistence provider for state management.
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

from ..core.tcc_context import TccContext


class TccPersistenceProvider(ABC):
    """Abstract base class for TCC persistence."""

    @abstractmethod
    async def save_tcc_state(
        self, transaction_id: str, context: TccContext, state: Dict[str, Any]
    ) -> None:
        """Save TCC state."""
        pass

    @abstractmethod
    async def load_tcc_state(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Load TCC state."""
        pass

    @abstractmethod
    async def delete_tcc_state(self, transaction_id: str) -> None:
        """Delete TCC state."""
        pass

    @abstractmethod
    async def list_active_transactions(self) -> List[str]:
        """List active TCC transaction IDs."""
        pass


class InMemoryTccPersistence(TccPersistenceProvider):
    """In-memory TCC persistence for testing and development."""

    def __init__(self):
        self._state_store: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger(__name__)

    async def save_tcc_state(
        self, transaction_id: str, context: TccContext, state: Dict[str, Any]
    ) -> None:
        """Save TCC state."""
        tcc_data = {
            "context": context.to_dict(),
            "state": state,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._state_store[transaction_id] = tcc_data
        self._logger.debug(f"Saved TCC state for {transaction_id}")

    async def load_tcc_state(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Load TCC state."""
        return self._state_store.get(transaction_id)

    async def delete_tcc_state(self, transaction_id: str) -> None:
        """Delete TCC state."""
        if transaction_id in self._state_store:
            del self._state_store[transaction_id]
            self._logger.debug(f"Deleted TCC state for {transaction_id}")

    async def list_active_transactions(self) -> List[str]:
        """List active TCC transaction IDs."""
        return list(self._state_store.keys())

    def clear_all(self) -> None:
        """Clear all state (for testing)."""
        self._state_store.clear()


class RedisTccPersistence(TccPersistenceProvider):
    """Redis-based TCC persistence."""

    def __init__(self, redis_url: str = "redis://localhost:6379", key_prefix: str = "tcc:"):
        import redis.asyncio as redis

        self._redis = redis.from_url(redis_url)
        self._key_prefix = key_prefix
        self._logger = logging.getLogger(__name__)

    def _make_key(self, transaction_id: str) -> str:
        """Create Redis key for transaction ID."""
        return f"{self._key_prefix}{transaction_id}"

    async def save_tcc_state(
        self, transaction_id: str, context: TccContext, state: Dict[str, Any]
    ) -> None:
        """Save TCC state."""
        tcc_data = {
            "context": context.to_dict(),
            "state": state,
            "updated_at": datetime.utcnow().isoformat(),
        }
        key = self._make_key(transaction_id)
        await self._redis.set(key, json.dumps(tcc_data))
        self._logger.debug(f"Saved TCC state to Redis for {transaction_id}")

    async def load_tcc_state(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Load TCC state."""
        key = self._make_key(transaction_id)
        data = await self._redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def delete_tcc_state(self, transaction_id: str) -> None:
        """Delete TCC state."""
        key = self._make_key(transaction_id)
        await self._redis.delete(key)
        self._logger.debug(f"Deleted TCC state from Redis for {transaction_id}")

    async def list_active_transactions(self) -> List[str]:
        """List active TCC transaction IDs."""
        pattern = f"{self._key_prefix}*"
        keys = await self._redis.keys(pattern)
        return [key.decode("utf-8").replace(self._key_prefix, "") for key in keys]

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.close()


def create_tcc_persistence(provider: str = "memory", **kwargs) -> TccPersistenceProvider:
    """Factory function to create TCC persistence providers."""
    if provider == "memory":
        return InMemoryTccPersistence()
    elif provider == "redis":
        return RedisTccPersistence(
            kwargs.get("connection_string", "redis://localhost:6379"),
            kwargs.get("key_prefix", "tcc:"),
        )
    else:
        raise ValueError(f"Unknown TCC persistence provider: {provider}")
