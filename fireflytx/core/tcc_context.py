"""
TccContext - Runtime context for TCC execution.

This module provides the Python equivalent of the Java TccContext,
maintaining state and metadata during TCC transaction execution.
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
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .saga_context import SagaContext


class TccPhase(Enum):
    """TCC execution phases."""

    TRY = "TRY"
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"


class TccParticipantStatus(Enum):
    """TCC participant status."""

    INITIALIZED = "INITIALIZED"
    TRY_SUCCEEDED = "TRY_SUCCEEDED"
    TRY_FAILED = "TRY_FAILED"
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"
    CONFIRM_FAILED = "CONFIRM_FAILED"
    CANCEL_FAILED = "CANCEL_FAILED"


@dataclass
class TccContext:
    """
    Runtime context for TCC execution.

    This class wraps a SagaContext and adds TCC-specific functionality
    for managing participant states and phases.
    """

    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tcc_name: Optional[str] = None
    current_phase: TccPhase = TccPhase.TRY
    participant_try_results: Dict[str, Any] = field(default_factory=dict)
    participant_statuses: Dict[str, TccParticipantStatus] = field(default_factory=dict)
    _saga_context: Optional["SagaContext"] = field(default=None, init=False)

    def __post_init__(self):
        """Initialize the underlying SagaContext."""
        if not self._saga_context:
            from .saga_context import SagaContext

            self._saga_context = SagaContext(
                correlation_id=self.correlation_id, saga_name=self.tcc_name
            )

    @classmethod
    def from_saga_context(cls, saga_context: "SagaContext") -> "TccContext":
        """Create TccContext from SagaContext."""
        context = cls(correlation_id=saga_context.correlation_id, tcc_name=saga_context.saga_name)
        context._saga_context = saga_context
        return context

    def get_current_phase(self) -> TccPhase:
        """Get current TCC phase."""
        return self.current_phase

    def set_current_phase(self, phase: TccPhase) -> None:
        """Set current TCC phase."""
        self.current_phase = phase

    def set_tcc_name(self, tcc_name: str) -> None:
        """Set TCC transaction name."""
        self.tcc_name = tcc_name
        if self._saga_context:
            self._saga_context.saga_name = tcc_name

    def set_participant_try_result(self, participant_id: str, result: Any) -> None:
        """Set the try result for a participant."""
        self.participant_try_results[participant_id] = result

    def get_participant_try_result(
        self, participant_id: str, result_type: type = None
    ) -> Optional[Any]:
        """Get the try result for a participant."""
        result = self.participant_try_results.get(participant_id)
        if result is not None and result_type is not None:
            # Simple type checking - in a full implementation this would be more sophisticated
            if isinstance(result, result_type):
                return result
            else:
                # Try to convert if possible
                try:
                    return result_type(result)
                except (ValueError, TypeError):
                    return None
        return result

    def get_all_try_results(self) -> Dict[str, Any]:
        """Get all try results."""
        return self.participant_try_results.copy()

    def set_participant_status(self, participant_id: str, status: TccParticipantStatus) -> None:
        """Set participant status."""
        self.participant_statuses[participant_id] = status

    def get_participant_status(self, participant_id: str) -> TccParticipantStatus:
        """Get participant status."""
        return self.participant_statuses.get(participant_id, TccParticipantStatus.INITIALIZED)

    # Delegate to underlying SagaContext
    def put_header(self, key: str, value: str) -> None:
        """Add a header value."""
        if self._saga_context:
            self._saga_context.put_header(key, value)

    def get_header(self, key: str) -> Optional[str]:
        """Get a header value."""
        if self._saga_context:
            return self._saga_context.get_header(key)
        return None

    def set_variable(self, key: str, value: Any) -> None:
        """Set a context variable."""
        if self._saga_context:
            self._saga_context.set_variable(key, value)

    def get_variable(self, key: str, result_type: type = None) -> Any:
        """Get a context variable."""
        if self._saga_context:
            if result_type:
                return self._saga_context.get_variable(key, None)
            else:
                return self._saga_context.get_variable(key)
        return None

    def set_data(self, key: str, value: Any) -> None:
        """Set context data (alias for set_variable)."""
        self.set_variable(key, value)

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get context data (alias for get_variable)."""
        return self.get_variable(key) or default

    def started_at(self) -> datetime:
        """Get start time."""
        if self._saga_context:
            return self._saga_context.started_at
        return datetime.now()

    def headers(self) -> Dict[str, str]:
        """Get all headers."""
        if self._saga_context:
            return self._saga_context.headers.copy()
        return {}

    def variables(self) -> Dict[str, Any]:
        """Get all variables."""
        if self._saga_context:
            return self._saga_context.variables.copy()
        return {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            "correlation_id": self.correlation_id,
            "tcc_name": self.tcc_name,
            "current_phase": self.current_phase.value,
            "participant_try_results": self.participant_try_results,
            "participant_statuses": {k: v.value for k, v in self.participant_statuses.items()},
        }

        if self._saga_context:
            data["saga_context"] = self._saga_context.to_dict()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TccContext":
        """Create from dictionary."""
        context = cls(
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            tcc_name=data.get("tcc_name"),
            current_phase=TccPhase(data.get("current_phase", "TRY")),
            participant_try_results=data.get("participant_try_results", {}),
            participant_statuses={
                k: TccParticipantStatus(v) for k, v in data.get("participant_statuses", {}).items()
            },
        )

        # Restore saga context if present
        saga_context_data = data.get("saga_context")
        if saga_context_data:
            from .saga_context import SagaContext

            context._saga_context = SagaContext.from_dict(saga_context_data)

        return context

    # Java object creation handled by subprocess bridge in engine classes
