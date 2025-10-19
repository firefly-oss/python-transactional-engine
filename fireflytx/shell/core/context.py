"""
Shell context and namespace management.

Manages the Python namespace and pre-loaded objects for the shell.
"""

import asyncio
import json
import pprint
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fireflytx import (
    SagaEngine,
    TccEngine,
    __version__,
    saga,
    saga_step,
    compensation_step,
    tcc,
    tcc_participant,
)
from fireflytx.config.engine_config import EngineConfig
from fireflytx.integration import (
    JavaSubprocessBridge,
    PythonCallbackHandler,
    TccCallbackHandler,
    TypeConverter,
    JarBuilder,
    get_jar_path,
)
from fireflytx.visualization import SagaVisualizer, TccVisualizer, OutputFormat


class ShellContext:
    """Manages the shell namespace and context."""

    def __init__(self, session, command_registry):
        """
        Initialize shell context.
        
        Args:
            session: ShellSession instance
            command_registry: CommandRegistry instance
        """
        self.session = session
        self.command_registry = command_registry
        self.namespace: Dict[str, Any] = {}
        self._setup_namespace()
    
    def _setup_namespace(self):
        """Setup the shell namespace with pre-loaded objects."""
        # First, add all registered commands to namespace
        # This must be done first so they can override built-ins
        command_funcs = self.command_registry.get_all_commands()

        self.namespace = {
            # Version info
            "__version__": __version__,
            "version": __version__,

            # Core classes
            "SagaEngine": SagaEngine,
            "TccEngine": TccEngine,
            "EngineConfig": EngineConfig,

            # Decorators
            "saga": saga,
            "saga_step": saga_step,
            "compensation_step": compensation_step,
            "tcc": tcc,
            "tcc_participant": tcc_participant,

            # Integration components
            "JavaSubprocessBridge": JavaSubprocessBridge,
            "PythonCallbackHandler": PythonCallbackHandler,
            "TccCallbackHandler": TccCallbackHandler,
            "TypeConverter": TypeConverter,
            "JarBuilder": JarBuilder,
            "get_jar_path": get_jar_path,

            # Visualization components
            "SagaVisualizer": SagaVisualizer,
            "TccVisualizer": TccVisualizer,
            "OutputFormat": OutputFormat,

            # Standard library utilities
            "asyncio": asyncio,
            "Path": Path,
            "json": json,
            "pprint": pprint.pprint,
            "pp": pprint.pprint,  # Shorthand
            "Dict": Dict,
            "List": List,
            "Optional": Optional,
            "Any": Any,
            "dataclass": dataclass,
            "datetime": datetime,
            "timedelta": timedelta,

            # Session and context
            "session": self.session,
            "context": self,

            # Engine instances (will be set after init)
            "saga_engine": None,
            "tcc_engine": None,
            "java_bridge": None,
        }

        # Add all registered commands to namespace (override built-ins)
        self.namespace.update(command_funcs)
    
    def update_engines(self):
        """Update engine references in namespace."""
        self.namespace["saga_engine"] = self.session.saga_engine
        self.namespace["tcc_engine"] = self.session.tcc_engine
        self.namespace["java_bridge"] = self.session.java_bridge
    
    def get_namespace(self) -> Dict[str, Any]:
        """Get the current namespace."""
        return self.namespace
    
    def add_to_namespace(self, name: str, value: Any):
        """Add an object to the namespace."""
        self.namespace[name] = value
    
    def remove_from_namespace(self, name: str):
        """Remove an object from the namespace."""
        if name in self.namespace:
            del self.namespace[name]

