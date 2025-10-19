"""
TccInputs - Input management for TCC participants.

This module provides the Python equivalent of the Java TccInputs,
managing inputs for TCC participant execution.
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

from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from fireflytx.core.tcc_context import TccContext


@dataclass
class TccInputs:
    """
    Manages inputs for TCC participants.

    This class provides a Python interface to the Java TccInputs,
    allowing flexible input specification for TCC transactions.
    """

    participant_inputs: Dict[str, Any] = field(default_factory=dict)
    global_timeout: Optional[timedelta] = None
    context: Optional["TccContext"] = None

    @classmethod
    def empty(cls) -> "TccInputs":
        """Create empty TCC inputs."""
        return cls()

    @classmethod
    def of(cls, participant_id: str, input_value: Any) -> "TccInputs":
        """Create TCC inputs with a single participant."""
        return cls(participant_inputs={participant_id: input_value})

    @classmethod
    def builder(cls) -> "TccInputsBuilder":
        """Create a builder for TCC inputs."""
        return TccInputsBuilder()

    def add_participant_input(self, participant_id: str, input_value: Any) -> "TccInputs":
        """Add input for a participant."""
        new_inputs = self.participant_inputs.copy()
        new_inputs[participant_id] = input_value
        return TccInputs(
            participant_inputs=new_inputs, global_timeout=self.global_timeout, context=self.context
        )

    def get_participant_input(self, participant_id: str) -> Any:
        """Get input for a participant."""
        return self.participant_inputs.get(participant_id)

    def has_participant_input(self, participant_id: str) -> bool:
        """Check if participant has input."""
        return participant_id in self.participant_inputs

    def set_global_timeout(self, timeout: timedelta) -> "TccInputs":
        """Set global timeout for all participants."""
        return TccInputs(
            participant_inputs=self.participant_inputs.copy(),
            global_timeout=timeout,
            context=self.context,
        )

    def set_context(self, context: "TccContext") -> "TccInputs":
        """Set TCC context."""
        return TccInputs(
            participant_inputs=self.participant_inputs.copy(),
            global_timeout=self.global_timeout,
            context=context,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "participant_inputs": self.participant_inputs,
            "global_timeout": self.global_timeout.total_seconds() if self.global_timeout else None,
            "context": self.context.to_dict() if self.context else None,
        }

    # Java object creation handled by subprocess bridge in engine classes


class TccInputsBuilder:
    """Builder for TccInputs."""

    def __init__(self):
        self._participant_inputs = {}
        self._global_timeout = None
        self._context = None

    def for_participant(self, participant_id: str, input_value: Any) -> "TccInputsBuilder":
        """Add input for a participant."""
        self._participant_inputs[participant_id] = input_value
        return self

    def with_global_timeout(self, timeout: timedelta) -> "TccInputsBuilder":
        """Set global timeout."""
        self._global_timeout = timeout
        return self

    def with_context(self, context: "TccContext") -> "TccInputsBuilder":
        """Set TCC context."""
        self._context = context
        return self

    def build(self) -> TccInputs:
        """Build the TccInputs object."""
        return TccInputs(
            participant_inputs=self._participant_inputs.copy(),
            global_timeout=self._global_timeout,
            context=self._context,
        )
