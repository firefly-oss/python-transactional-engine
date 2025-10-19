"""
SAGA topology visualizer for analyzing transaction patterns.

Provides tools for visualizing SAGA step dependencies, compensation flows,
and execution paths.
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

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Type

from .graph_renderer import GraphEdge, GraphNode, GraphRenderer, OutputFormat


@dataclass
class SagaStepInfo:
    """Information about a SAGA step."""

    step_id: str
    method_name: str
    depends_on: List[str]
    compensate: Optional[str]
    retry: int
    timeout_ms: int
    compensation_critical: bool
    compensation_retry: int
    compensation_timeout_ms: int


@dataclass
class SagaTopologyGraph:
    """Represents the complete topology of a SAGA."""

    saga_name: str
    steps: Dict[str, SagaStepInfo]
    compensation_methods: Dict[str, str]  # step_id -> compensation_method_name
    execution_layers: List[List[str]]  # Steps grouped by execution layer

    def get_root_steps(self) -> List[str]:
        """Get steps that have no dependencies (root nodes)."""
        all_dependencies = set()
        for step in self.steps.values():
            all_dependencies.update(step.depends_on)

        return [step_id for step_id in self.steps.keys() if step_id not in all_dependencies]

    def get_leaf_steps(self) -> List[str]:
        """Get steps that no other steps depend on (leaf nodes)."""
        has_dependents = set()
        for step in self.steps.values():
            has_dependents.update(step.depends_on)

        return [step_id for step_id in self.steps.keys() if step_id not in has_dependents]

    def get_compensation_chain(self) -> List[str]:
        """Get the compensation chain in reverse execution order."""
        # This is a simplified implementation - in practice, you'd use the topology
        # to determine the correct compensation order
        return list(reversed(list(self.steps.keys())))


class SagaVisualizer:
    """
    Visualizes SAGA transaction topologies.

    Analyzes SAGA classes decorated with @saga and their steps to create
    visual representations of the transaction flow and compensation paths.
    """

    def __init__(self):
        self.renderer = GraphRenderer()

    def analyze_saga_class(self, saga_class: Type) -> SagaTopologyGraph:
        """
        Analyze a SAGA class and extract its topology.

        Args:
            saga_class: Class decorated with @saga

        Returns:
            SagaTopologyGraph representing the SAGA structure
        """
        if not hasattr(saga_class, "_saga_config"):
            raise ValueError(
                f"Class {saga_class.__name__} is not a valid SAGA (missing @saga decorator)"
            )

        saga_config = saga_class._saga_config
        steps = {}
        compensation_methods = {}

        # Extract step information
        for step_id, step_config in saga_config.steps.items():
            # Find the method name by looking for the step_id in the class methods
            method_name = step_id  # Default fallback
            for attr_name in dir(saga_class):
                attr = getattr(saga_class, attr_name)
                if hasattr(attr, "_saga_step_config") and attr._saga_step_config.step_id == step_id:
                    method_name = attr_name
                    break

            steps[step_id] = SagaStepInfo(
                step_id=step_id,
                method_name=method_name,
                depends_on=step_config.depends_on or [],
                compensate=step_config.compensate,
                retry=step_config.retry,
                timeout_ms=step_config.timeout_ms,
                compensation_critical=step_config.compensation_critical,
                compensation_retry=step_config.compensation_retry,
                compensation_timeout_ms=step_config.compensation_timeout_ms,
            )

        # Extract compensation methods
        compensation_methods = saga_config.compensation_methods

        # Calculate execution layers (steps that can run in parallel)
        execution_layers = self._calculate_execution_layers(steps)

        return SagaTopologyGraph(
            saga_name=saga_config.name,
            steps=steps,
            compensation_methods=compensation_methods,
            execution_layers=execution_layers,
        )

    def visualize_saga(self, saga_class: Type, format: OutputFormat = OutputFormat.ASCII) -> str:
        """
        Create a visual representation of a SAGA.

        Args:
            saga_class: Class decorated with @saga
            format: Output format for visualization

        Returns:
            String representation of the SAGA topology
        """
        topology = self.analyze_saga_class(saga_class)
        return self.render_topology(topology, format)

    def render_topology(
        self, topology: SagaTopologyGraph, format: OutputFormat = OutputFormat.ASCII
    ) -> str:
        """
        Render a SAGA topology in the specified format.

        Args:
            topology: SAGA topology to render
            format: Output format

        Returns:
            Rendered topology as string
        """
        self.renderer.clear()

        # Add step nodes
        for step_id, step_info in topology.steps.items():
            node = GraphNode(
                id=step_id,
                label=f"{step_info.method_name}\\n({step_id})",
                node_type="step",
                properties={
                    "retry": step_info.retry,
                    "timeout_ms": step_info.timeout_ms,
                    "depends_on": step_info.depends_on,
                    "compensate": step_info.compensate or "None",
                },
            )
            self.renderer.add_node(node)

        # Add compensation nodes
        for step_id, comp_method in topology.compensation_methods.items():
            if comp_method and step_id in topology.steps:
                node = GraphNode(
                    id=f"{step_id}_compensation",
                    label=f"{comp_method}\\n(compensate {step_id})",
                    node_type="compensation",
                    properties={
                        "target_step": step_id,
                        "critical": topology.steps[step_id].compensation_critical,
                    },
                )
                self.renderer.add_node(node)

        # Add dependency edges
        for step_id, step_info in topology.steps.items():
            for dependency in step_info.depends_on:
                if dependency in topology.steps:
                    edge = GraphEdge(
                        from_node=dependency, to_node=step_id, edge_type="dependency", properties={}
                    )
                    self.renderer.add_edge(edge)

        # Add compensation edges
        for step_id, comp_method in topology.compensation_methods.items():
            if comp_method and step_id in topology.steps:
                edge = GraphEdge(
                    from_node=step_id,
                    to_node=f"{step_id}_compensation",
                    edge_type="compensation",
                    properties={},
                )
                self.renderer.add_edge(edge)

        return self.renderer.render(format)

    def _calculate_execution_layers(self, steps: Dict[str, SagaStepInfo]) -> List[List[str]]:
        """Calculate which steps can execute in parallel (same layer)."""
        layers = []
        remaining_steps = set(steps.keys())
        completed_steps = set()

        while remaining_steps:
            # Find steps that can execute now (all dependencies satisfied)
            current_layer = []
            for step_id in list(remaining_steps):
                step_info = steps[step_id]
                if all(dep in completed_steps for dep in step_info.depends_on):
                    current_layer.append(step_id)

            if not current_layer:
                # This shouldn't happen with a valid SAGA, but handle circular dependencies
                current_layer = list(remaining_steps)

            layers.append(current_layer)
            for step_id in current_layer:
                remaining_steps.remove(step_id)
                completed_steps.add(step_id)

        return layers

    def get_execution_summary(self, topology: SagaTopologyGraph) -> str:
        """Get a text summary of SAGA execution characteristics."""
        lines = []
        lines.append(f"SAGA: {topology.saga_name}")
        lines.append(f"Total Steps: {len(topology.steps)}")
        lines.append(f"Execution Layers: {len(topology.execution_layers)}")
        lines.append(f"Root Steps: {', '.join(topology.get_root_steps())}")
        lines.append(f"Leaf Steps: {', '.join(topology.get_leaf_steps())}")

        # Calculate max parallel execution
        max_parallel = (
            max(len(layer) for layer in topology.execution_layers)
            if topology.execution_layers
            else 0
        )
        lines.append(f"Max Parallel Steps: {max_parallel}")

        # Count compensations
        compensated_steps = len([s for s in topology.steps.values() if s.compensate])
        lines.append(f"Compensated Steps: {compensated_steps}/{len(topology.steps)}")

        return "\n".join(lines)

    def validate_topology(self, topology: SagaTopologyGraph) -> List[str]:
        """Validate SAGA topology and return any issues found."""
        issues = []

        # Check for circular dependencies
        def has_circular_dependency(step_id: str, path: Set[str]) -> bool:
            if step_id in path:
                return True

            if step_id not in topology.steps:
                return False

            path.add(step_id)
            for dep in topology.steps[step_id].depends_on:
                if has_circular_dependency(dep, path.copy()):
                    return True

            return False

        for step_id in topology.steps:
            if has_circular_dependency(step_id, set()):
                issues.append(f"Circular dependency detected involving step: {step_id}")

        # Check for missing dependencies
        for step_id, step_info in topology.steps.items():
            for dep in step_info.depends_on:
                if dep not in topology.steps:
                    issues.append(f"Step '{step_id}' depends on unknown step '{dep}'")

        # Check for missing compensation methods
        for step_id, step_info in topology.steps.items():
            if (
                step_info.compensate
                and step_info.compensate not in topology.compensation_methods.values()
            ):
                issues.append(
                    f"Step '{step_id}' references unknown compensation method '{step_info.compensate}'"
                )

        return issues
