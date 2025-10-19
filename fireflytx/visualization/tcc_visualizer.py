"""
TCC topology visualizer for analyzing Try-Confirm-Cancel patterns.

Provides tools for visualizing TCC participant interactions, phase flows,
and transaction coordination patterns.
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
from typing import Dict, List, Type

from .graph_renderer import GraphEdge, GraphNode, GraphRenderer, OutputFormat


@dataclass
class TccParticipantInfo:
    """Information about a TCC participant."""

    participant_id: str
    participant_name: str
    order: int
    try_method: str
    confirm_method: str
    cancel_method: str
    try_timeout_ms: int
    confirm_timeout_ms: int
    cancel_timeout_ms: int
    try_retry: int
    confirm_retry: int
    cancel_retry: int


@dataclass
class TccTopologyGraph:
    """Represents the complete topology of a TCC transaction."""

    tcc_name: str
    participants: Dict[str, TccParticipantInfo]
    execution_order: List[str]  # Participants ordered by execution order

    def get_ordered_participants(self) -> List[TccParticipantInfo]:
        """Get participants ordered by execution order."""
        return sorted(self.participants.values(), key=lambda p: p.order)

    def get_phase_flow(self, phase: str) -> List[str]:
        """Get the flow of participants for a specific phase."""
        ordered = self.get_ordered_participants()
        if phase == "cancel":
            # Cancel phase typically runs in reverse order
            return [p.participant_id for p in reversed(ordered)]
        else:
            # Try and Confirm phases run in forward order
            return [p.participant_id for p in ordered]


class TccVisualizer:
    """
    Visualizes TCC (Try-Confirm-Cancel) transaction topologies.

    Analyzes TCC classes decorated with @tcc and their participants to create
    visual representations of the transaction coordination flow.
    """

    def __init__(self):
        self.renderer = GraphRenderer()

    def analyze_tcc_class(self, tcc_class: Type) -> TccTopologyGraph:
        """
        Analyze a TCC class and extract its topology.

        Args:
            tcc_class: Class decorated with @tcc

        Returns:
            TccTopologyGraph representing the TCC structure
        """
        if not hasattr(tcc_class, "_tcc_config"):
            raise ValueError(
                f"Class {tcc_class.__name__} is not a valid TCC (missing @tcc decorator)"
            )

        tcc_config = tcc_class._tcc_config
        participants = {}

        # Extract participant information
        for participant_id, participant_config in tcc_config.participants.items():
            participants[participant_id] = TccParticipantInfo(
                participant_id=participant_id,
                participant_name=participant_id,
                order=participant_config.order,
                try_method=participant_config.try_method or "try_method",
                confirm_method=participant_config.confirm_method or "confirm_method",
                cancel_method=participant_config.cancel_method or "cancel_method",
                try_timeout_ms=getattr(participant_config, "try_timeout_ms", 10000),
                confirm_timeout_ms=getattr(participant_config, "confirm_timeout_ms", 5000),
                cancel_timeout_ms=getattr(participant_config, "cancel_timeout_ms", 10000),
                try_retry=getattr(participant_config, "try_retry", 3),
                confirm_retry=getattr(participant_config, "confirm_retry", 5),
                cancel_retry=getattr(participant_config, "cancel_retry", 10),
            )

        # Calculate execution order
        execution_order = sorted(participants.keys(), key=lambda p: participants[p].order)

        return TccTopologyGraph(
            tcc_name=tcc_config.name, participants=participants, execution_order=execution_order
        )

    def visualize_tcc(self, tcc_class: Type, format: OutputFormat = OutputFormat.ASCII) -> str:
        """
        Create a visual representation of a TCC transaction.

        Args:
            tcc_class: Class decorated with @tcc
            format: Output format for visualization

        Returns:
            String representation of the TCC topology
        """
        topology = self.analyze_tcc_class(tcc_class)
        return self.render_topology(topology, format)

    def render_topology(
        self, topology: TccTopologyGraph, format: OutputFormat = OutputFormat.ASCII
    ) -> str:
        """
        Render a TCC topology in the specified format.

        Args:
            topology: TCC topology to render
            format: Output format

        Returns:
            Rendered topology as string
        """
        self.renderer.clear()

        # Add participant nodes for each phase
        for participant_id, participant_info in topology.participants.items():
            # Try phase node
            try_node = GraphNode(
                id=f"{participant_id}_try",
                label=f"TRY\\n{participant_info.try_method}\\n({participant_info.participant_name})",
                node_type="phase",
                properties={
                    "participant": participant_id,
                    "phase": "try",
                    "timeout_ms": participant_info.try_timeout_ms,
                    "retry": participant_info.try_retry,
                    "order": participant_info.order,
                },
            )
            self.renderer.add_node(try_node)

            # Confirm phase node
            confirm_node = GraphNode(
                id=f"{participant_id}_confirm",
                label=f"CONFIRM\\n{participant_info.confirm_method}\\n({participant_info.participant_name})",
                node_type="phase",
                properties={
                    "participant": participant_id,
                    "phase": "confirm",
                    "timeout_ms": participant_info.confirm_timeout_ms,
                    "retry": participant_info.confirm_retry,
                    "order": participant_info.order,
                },
            )
            self.renderer.add_node(confirm_node)

            # Cancel phase node
            cancel_node = GraphNode(
                id=f"{participant_id}_cancel",
                label=f"CANCEL\\n{participant_info.cancel_method}\\n({participant_info.participant_name})",
                node_type="phase",
                properties={
                    "participant": participant_id,
                    "phase": "cancel",
                    "timeout_ms": participant_info.cancel_timeout_ms,
                    "retry": participant_info.cancel_retry,
                    "order": participant_info.order,
                },
            )
            self.renderer.add_node(cancel_node)

        # Add participant summary nodes
        for participant_id, participant_info in topology.participants.items():
            participant_node = GraphNode(
                id=participant_id,
                label=f"{participant_info.participant_name}\\n(Order: {participant_info.order})",
                node_type="participant",
                properties={
                    "order": participant_info.order,
                    "phases": ["try", "confirm", "cancel"],
                },
            )
            self.renderer.add_node(participant_node)

        # Add phase flow edges (try -> confirm, try -> cancel)
        for participant_id in topology.participants:
            # Try to Confirm flow
            confirm_edge = GraphEdge(
                from_node=f"{participant_id}_try",
                to_node=f"{participant_id}_confirm",
                edge_type="flow",
                properties={"phase_transition": "try_to_confirm"},
            )
            self.renderer.add_edge(confirm_edge)

            # Try to Cancel flow (on failure)
            cancel_edge = GraphEdge(
                from_node=f"{participant_id}_try",
                to_node=f"{participant_id}_cancel",
                edge_type="compensation",
                properties={"phase_transition": "try_to_cancel"},
            )
            self.renderer.add_edge(cancel_edge)

        # Add execution order edges for try phase
        ordered_participants = topology.get_ordered_participants()
        for i in range(len(ordered_participants) - 1):
            current = ordered_participants[i]
            next_participant = ordered_participants[i + 1]

            edge = GraphEdge(
                from_node=f"{current.participant_id}_try",
                to_node=f"{next_participant.participant_id}_try",
                edge_type="dependency",
                properties={"execution_order": True},
            )
            self.renderer.add_edge(edge)

        return self.renderer.render(format)

    def get_execution_summary(self, topology: TccTopologyGraph) -> str:
        """Get a text summary of TCC execution characteristics."""
        lines = []
        lines.append(f"TCC Transaction: {topology.tcc_name}")
        lines.append(f"Total Participants: {len(topology.participants)}")

        ordered = topology.get_ordered_participants()
        lines.append(f"Execution Order: {' -> '.join([p.participant_name for p in ordered])}")

        # Calculate total timeouts
        total_try_timeout = sum(p.try_timeout_ms for p in ordered)
        total_confirm_timeout = sum(p.confirm_timeout_ms for p in ordered)
        total_cancel_timeout = sum(p.cancel_timeout_ms for p in ordered)

        lines.append(f"Total Try Timeout: {total_try_timeout}ms")
        lines.append(f"Total Confirm Timeout: {total_confirm_timeout}ms")
        lines.append(f"Total Cancel Timeout: {total_cancel_timeout}ms")

        # Calculate retry characteristics
        max_try_retry = max(p.try_retry for p in ordered) if ordered else 0
        max_confirm_retry = max(p.confirm_retry for p in ordered) if ordered else 0
        max_cancel_retry = max(p.cancel_retry for p in ordered) if ordered else 0

        lines.append(
            f"Max Retry Attempts - Try: {max_try_retry}, Confirm: {max_confirm_retry}, Cancel: {max_cancel_retry}"
        )

        return "\n".join(lines)

    def validate_topology(self, topology: TccTopologyGraph) -> List[str]:
        """Validate TCC topology and return any issues found."""
        issues = []

        # Check for duplicate orders
        orders = [p.order for p in topology.participants.values()]
        if len(set(orders)) != len(orders):
            issues.append("Duplicate participant orders detected")

        # Check for missing methods
        for participant_id, participant_info in topology.participants.items():
            if not participant_info.try_method:
                issues.append(f"Participant '{participant_id}' missing try method")
            if not participant_info.confirm_method:
                issues.append(f"Participant '{participant_id}' missing confirm method")
            if not participant_info.cancel_method:
                issues.append(f"Participant '{participant_id}' missing cancel method")

        # Check timeout configurations
        for participant_id, participant_info in topology.participants.items():
            if participant_info.try_timeout_ms <= 0:
                issues.append(f"Participant '{participant_id}' has invalid try timeout")
            if participant_info.confirm_timeout_ms <= 0:
                issues.append(f"Participant '{participant_id}' has invalid confirm timeout")
            if participant_info.cancel_timeout_ms <= 0:
                issues.append(f"Participant '{participant_id}' has invalid cancel timeout")

        return issues

    def get_phase_diagram(self, topology: TccTopologyGraph) -> str:
        """Generate a phase transition diagram showing TCC flow."""
        lines = []
        lines.append("TCC Phase Flow Diagram")
        lines.append("=" * 40)
        lines.append("")

        ordered = topology.get_ordered_participants()

        # Show the happy path (Try -> Confirm)
        lines.append("🎯 Happy Path (All participants succeed):")
        lines.append("  TRY Phase:")
        for i, participant in enumerate(ordered):
            arrow = "  └─>" if i == len(ordered) - 1 else "  ├─>"
            lines.append(f"{arrow} {participant.participant_name}.{participant.try_method}()")

        lines.append("\n  CONFIRM Phase:")
        for i, participant in enumerate(ordered):
            arrow = "  └─>" if i == len(ordered) - 1 else "  ├─>"
            lines.append(f"{arrow} {participant.participant_name}.{participant.confirm_method}()")

        # Show the failure path (Try -> Cancel)
        lines.append("\n🚨 Failure Path (Any participant fails):")
        lines.append("  TRY Phase (until failure):")
        lines.append("  ├─> [Some participants succeed]")
        lines.append("  └─> [One participant fails]")

        lines.append("\n  CANCEL Phase (reverse order):")
        for i, participant in enumerate(reversed(ordered)):
            arrow = "  └─>" if i == len(ordered) - 1 else "  ├─>"
            lines.append(f"{arrow} {participant.participant_name}.{participant.cancel_method}()")

        return "\n".join(lines)
