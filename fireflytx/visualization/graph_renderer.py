"""
Graph renderer for topology visualization with multiple output formats.

Supports ASCII, DOT, Mermaid, and SVG output formats for transaction topologies.
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
from enum import Enum
from typing import Any, Dict, List, Optional, TextIO, Tuple


class OutputFormat(Enum):
    """Supported output formats for topology visualization."""

    ASCII = "ascii"
    DOT = "dot"
    MERMAID = "mermaid"
    SVG = "svg"
    JSON = "json"


@dataclass
class GraphNode:
    """Represents a node in the topology graph."""

    id: str
    label: str
    node_type: str  # 'step', 'compensation', 'participant', 'phase'
    properties: Dict[str, Any]
    x: Optional[int] = None
    y: Optional[int] = None


@dataclass
class GraphEdge:
    """Represents an edge in the topology graph."""

    from_node: str
    to_node: str
    edge_type: str  # 'dependency', 'compensation', 'flow'
    properties: Dict[str, Any]


class GraphRenderer:
    """
    Renders topology graphs in various formats.

    Supports ASCII art, DOT notation, Mermaid diagrams, and SVG output.
    """

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def clear(self) -> None:
        """Clear all nodes and edges."""
        self.nodes.clear()
        self.edges.clear()

    def render(self, format: OutputFormat, output: Optional[TextIO] = None) -> str:
        """
        Render the graph in the specified format.

        Args:
            format: Output format for rendering
            output: Optional output stream to write to

        Returns:
            Rendered graph as string
        """
        if format == OutputFormat.ASCII:
            result = self._render_ascii()
        elif format == OutputFormat.DOT:
            result = self._render_dot()
        elif format == OutputFormat.MERMAID:
            result = self._render_mermaid()
        elif format == OutputFormat.SVG:
            result = self._render_svg()
        elif format == OutputFormat.JSON:
            result = self._render_json()
        else:
            raise ValueError(f"Unsupported output format: {format}")

        if output:
            output.write(result)

        return result

    def _render_ascii(self) -> str:
        """Render graph as ASCII art."""
        if not self.nodes:
            return "Empty graph"

        lines = []
        lines.append("Transaction Topology")
        lines.append("=" * 50)

        # Group nodes by type
        steps = [n for n in self.nodes.values() if n.node_type == "step"]
        compensations = [n for n in self.nodes.values() if n.node_type == "compensation"]
        participants = [n for n in self.nodes.values() if n.node_type == "participant"]

        if steps:
            lines.append("\n📋 Steps:")
            for step in steps:
                retry = step.properties.get("retry", 0)
                timeout = step.properties.get("timeout_ms", "N/A")
                depends_on = step.properties.get("depends_on", [])
                compensate = step.properties.get("compensate", "None")

                lines.append(f"  ┌─ {step.label}")
                lines.append(f"  │  ID: {step.id}")
                lines.append(f"  │  Retry: {retry}")
                lines.append(f"  │  Timeout: {timeout}ms")
                lines.append(f"  │  Depends: {', '.join(depends_on) if depends_on else 'None'}")
                lines.append(f"  │  Compensate: {compensate}")
                lines.append("  └─")

        if compensations:
            lines.append("\n🔄 Compensations:")
            for comp in compensations:
                target = comp.properties.get("target_step", "N/A")
                critical = comp.properties.get("critical", False)
                lines.append(f"  ┌─ {comp.label}")
                lines.append(f"  │  Target: {target}")
                lines.append(f"  │  Critical: {'✓' if critical else '✗'}")
                lines.append("  └─")

        if participants:
            lines.append("\n👥 TCC Participants:")
            for participant in participants:
                order = participant.properties.get("order", 0)
                phases = participant.properties.get("phases", [])
                lines.append(f"  ┌─ {participant.label}")
                lines.append(f"  │  Order: {order}")
                lines.append(f"  │  Phases: {', '.join(phases)}")
                lines.append("  └─")

        # Show execution flow
        if self.edges:
            lines.append("\n🔗 Execution Flow:")
            for edge in self.edges:
                arrow = (
                    "──→"
                    if edge.edge_type == "flow"
                    else "╶╶→" if edge.edge_type == "dependency" else "⤴─→"
                )
                lines.append(f"  {edge.from_node} {arrow} {edge.to_node} ({edge.edge_type})")

        return "\n".join(lines)

    def _render_dot(self) -> str:
        """Render graph as DOT notation for Graphviz."""
        lines = []
        lines.append("digraph TransactionTopology {")
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=rounded];")

        # Define node styles
        lines.append("  // Node definitions")
        for node in self.nodes.values():
            color = self._get_dot_color(node.node_type)
            label = node.label.replace('"', '\\"')
            lines.append(f'  "{node.id}" [label="{label}", color="{color}"];')

        # Define edges
        lines.append("  // Edge definitions")
        for edge in self.edges:
            style = self._get_dot_edge_style(edge.edge_type)
            lines.append(f'  "{edge.from_node}" -> "{edge.to_node}" [style="{style}"];')

        lines.append("}")
        return "\n".join(lines)

    def _render_mermaid(self) -> str:
        """Render graph as Mermaid diagram."""
        lines = []
        lines.append("graph LR")

        # Define nodes
        for node in self.nodes.values():
            shape = self._get_mermaid_shape(node.node_type)
            label = node.label.replace('"', "'")
            lines.append(f"  {node.id}{shape[0]}{label}{shape[1]}")

        # Define edges
        for edge in self.edges:
            arrow = self._get_mermaid_arrow(edge.edge_type)
            lines.append(f"  {edge.from_node} {arrow} {edge.to_node}")

        return "\n".join(lines)

    def _render_svg(self) -> str:
        """Render graph as SVG (basic implementation)."""
        # This is a simplified SVG implementation
        # In production, you might want to use a proper graph layout library
        return """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
  <text x="10" y="30" font-family="Arial" font-size="16">Transaction Topology (SVG)</text>
  <text x="10" y="60" font-family="Arial" font-size="12">Use DOT format with Graphviz for full SVG support</text>
</svg>"""

    def _render_json(self) -> str:
        """Render graph as JSON."""
        import json

        graph_data = {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "type": node.node_type,
                    "properties": node.properties,
                    "position": {"x": node.x, "y": node.y} if node.x is not None else None,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "from": edge.from_node,
                    "to": edge.to_node,
                    "type": edge.edge_type,
                    "properties": edge.properties,
                }
                for edge in self.edges
            ],
        }

        return json.dumps(graph_data, indent=2)

    def _get_dot_color(self, node_type: str) -> str:
        """Get DOT color for node type."""
        colors = {
            "step": "lightblue",
            "compensation": "lightcoral",
            "participant": "lightgreen",
            "phase": "lightyellow",
        }
        return colors.get(node_type, "lightgray")

    def _get_dot_edge_style(self, edge_type: str) -> str:
        """Get DOT edge style for edge type."""
        styles = {"dependency": "solid", "compensation": "dashed", "flow": "bold"}
        return styles.get(edge_type, "solid")

    def _get_mermaid_shape(self, node_type: str) -> Tuple[str, str]:
        """Get Mermaid shape delimiters for node type."""
        shapes = {
            "step": ("[", "]"),
            "compensation": ("((", "))"),
            "participant": ("(", ")"),
            "phase": ("{", "}"),
        }
        return shapes.get(node_type, ("[", "]"))

    def _get_mermaid_arrow(self, edge_type: str) -> str:
        """Get Mermaid arrow style for edge type."""
        arrows = {"dependency": "-->", "compensation": "-.->", "flow": "==="}
        return arrows.get(edge_type, "-->")
