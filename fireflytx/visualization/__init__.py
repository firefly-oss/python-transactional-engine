"""
Visualization module for SAGA and TCC transaction topologies.

This module provides tools for visualizing transaction patterns including:
- SAGA step dependencies and compensation flows
- TCC participant interactions and phases
- Transaction execution flows and rollback paths
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

from .graph_renderer import GraphRenderer, OutputFormat
from .saga_visualizer import SagaTopologyGraph, SagaVisualizer
from .tcc_visualizer import TccTopologyGraph, TccVisualizer

__all__ = [
    "SagaVisualizer",
    "SagaTopologyGraph",
    "TccVisualizer",
    "TccTopologyGraph",
    "GraphRenderer",
    "OutputFormat",
]
