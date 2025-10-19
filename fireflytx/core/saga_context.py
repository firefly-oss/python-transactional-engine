"""
SagaContext - Runtime context for saga execution.

This module provides the Python equivalent of the Java SagaContext,
maintaining state and metadata during saga execution.
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

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Set


@dataclass
class SagaContext:
    """
    Runtime context for saga execution.

    This class maintains state, variables, headers, and step results
    during saga execution, providing a Python interface to the Java SagaContext.
    """

    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    saga_name: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    headers: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)
    step_statuses: Dict[str, str] = field(default_factory=dict)
    step_attempts: Dict[str, int] = field(default_factory=dict)
    idempotency_keys: Set[str] = field(default_factory=set)

    def put_header(self, key: str, value: str) -> None:
        """Add a header value."""
        self.headers[key] = value

    def get_header(self, key: str) -> Optional[str]:
        """Get a header value."""
        return self.headers.get(key)

    def set_variable(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.variables.get(key, default)

    def set_step_result(self, step_id: str, result: Any) -> None:
        """Set the result of a step."""
        self.step_results[step_id] = result

    def get_step_result(self, step_id: str) -> Any:
        """Get the result of a step."""
        return self.step_results.get(step_id)

    def set_step_status(self, step_id: str, status: str) -> None:
        """Set the status of a step."""
        self.step_statuses[step_id] = status

    def get_step_status(self, step_id: str) -> Optional[str]:
        """Get the status of a step."""
        return self.step_statuses.get(step_id)

    def increment_attempts(self, step_id: str) -> int:
        """Increment and return the attempt count for a step."""
        current = self.step_attempts.get(step_id, 0)
        self.step_attempts[step_id] = current + 1
        return self.step_attempts[step_id]

    def get_attempts(self, step_id: str) -> int:
        """Get the attempt count for a step."""
        return self.step_attempts.get(step_id, 0)

    def add_idempotency_key(self, key: str) -> None:
        """Add an idempotency key."""
        self.idempotency_keys.add(key)

    def has_idempotency_key(self, key: str) -> bool:
        """Check if an idempotency key exists."""
        return key in self.idempotency_keys

    def set_data(self, key: str, value: Any) -> None:
        """Set context data (alias for set_variable)."""
        self.set_variable(key, value)

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get context data (alias for get_variable)."""
        return self.get_variable(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "correlation_id": self.correlation_id,
            "saga_name": self.saga_name,
            "started_at": self.started_at.isoformat(),
            "headers": self.headers,
            "variables": self.variables,
            "step_results": self.step_results,
            "step_statuses": self.step_statuses,
            "step_attempts": self.step_attempts,
            "idempotency_keys": list(self.idempotency_keys),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SagaContext":
        """Create from dictionary."""
        context = cls(
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            saga_name=data.get("saga_name"),
            started_at=datetime.fromisoformat(data.get("started_at", datetime.now().isoformat())),
            headers=data.get("headers", {}),
            variables=data.get("variables", {}),
            step_results=data.get("step_results", {}),
            step_statuses=data.get("step_statuses", {}),
            step_attempts=data.get("step_attempts", {}),
            idempotency_keys=set(data.get("idempotency_keys", [])),
        )
        return context

    # Java object creation handled by subprocess bridge in engine classes
