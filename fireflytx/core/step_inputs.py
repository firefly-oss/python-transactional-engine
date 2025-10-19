"""
StepInputs - Input management for SAGA steps.

This module provides the Python equivalent of the Java StepInputs,
managing inputs for SAGA step execution.
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
from typing import Any, Callable, Dict


@dataclass
class StepInputs:
    """
    Manages inputs for SAGA steps.

    This class provides a Python interface to the Java StepInputs,
    allowing flexible input specification and materialization.
    """

    inputs: Dict[str, Any] = field(default_factory=dict)
    resolvers: Dict[str, Callable] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> "StepInputs":
        """Create empty step inputs."""
        return cls()

    @classmethod
    def of(cls, step_id: str, input_value: Any) -> "StepInputs":
        """Create step inputs with a single step."""
        return cls(inputs={step_id: input_value})

    @classmethod
    def of_dict(cls, inputs: Dict[str, Any]) -> "StepInputs":
        """Create step inputs from a dictionary."""
        return cls(inputs=inputs.copy())

    @classmethod
    def builder(cls) -> "StepInputsBuilder":
        """Create a builder for step inputs."""
        return StepInputsBuilder()

    def add_input(self, step_id: str, input_value: Any) -> "StepInputs":
        """Add an input for a step."""
        new_inputs = self.inputs.copy()
        new_inputs[step_id] = input_value
        return StepInputs(inputs=new_inputs, resolvers=self.resolvers.copy())

    def add_resolver(self, step_id: str, resolver: Callable) -> "StepInputs":
        """Add a resolver function for a step."""
        new_resolvers = self.resolvers.copy()
        new_resolvers[step_id] = resolver
        return StepInputs(inputs=self.inputs.copy(), resolvers=new_resolvers)

    def get_input(self, step_id: str) -> Any:
        """Get input for a step."""
        if step_id in self.inputs:
            return self.inputs[step_id]
        elif step_id in self.resolvers:
            # Resolver will be called during materialization
            return self.resolvers[step_id]
        return None

    def raw_value(self, step_id: str) -> Any:
        """Get raw value without resolver evaluation."""
        return self.inputs.get(step_id)

    def has_input(self, step_id: str) -> bool:
        """Check if step has input or resolver."""
        return step_id in self.inputs or step_id in self.resolvers

    def materialize_all(self, context) -> Dict[str, Any]:
        """Materialize all inputs and resolvers."""

        materialized = {}

        # Add direct inputs
        materialized.update(self.inputs)

        # Evaluate resolvers
        for step_id, resolver in self.resolvers.items():
            try:
                materialized[step_id] = resolver(context)
            except Exception as e:
                # Log error but continue
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to resolve input for step {step_id}: {e}")
                materialized[step_id] = None

        return materialized

    def materialized_view(self, context) -> Dict[str, Any]:
        """Get materialized view of inputs."""
        return self.materialize_all(context)

    # Java object creation handled by subprocess bridge in engine classes


class StepInputsBuilder:
    """Builder for StepInputs."""

    def __init__(self):
        self._inputs = {}
        self._resolvers = {}

    def for_step_id(self, step_id: str, input_value: Any) -> "StepInputsBuilder":
        """Add input for a step ID."""
        self._inputs[step_id] = input_value
        return self

    def for_step(self, method_ref: Callable, input_value: Any) -> "StepInputsBuilder":
        """Add input for a step using method reference."""
        # Extract step ID from method reference
        step_id = getattr(method_ref, "_saga_step_config", {}).get("step_id")
        if not step_id:
            step_id = method_ref.__name__

        self._inputs[step_id] = input_value
        return self

    def for_step_id_resolver(self, step_id: str, resolver: Callable) -> "StepInputsBuilder":
        """Add resolver function for a step."""
        self._resolvers[step_id] = resolver
        return self

    def build(self) -> StepInputs:
        """Build the StepInputs object."""
        return StepInputs(inputs=self._inputs.copy(), resolvers=self._resolvers.copy())
