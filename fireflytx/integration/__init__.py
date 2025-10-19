"""
Integration layer for Python-Java communication.

This module contains all components responsible for bridging Python and Java:
- Java subprocess management
- Callback handlers for Java->Python method invocation
- Type conversion between Python and Java
- JAR building and management

Architecture:
    Python Application
         │
         ├─> JavaSubprocessBridge ──> Java Process (lib-transactional-engine)
         │                                    │
         │                                    │ HTTP Callbacks
         │                                    ▼
         └─────────────────────> PythonCallbackHandler
                                        │
                                        ├─> CallbackRegistry
                                        └─> TypeConverter

Public API:
    - JavaSubprocessBridge: Main bridge for Python-Java communication
    - PythonCallbackHandler: HTTP server for Java callbacks
    - CallbackRegistry: Registry for Python methods callable from Java
    - TypeConverter: Convert between Python and Java types
    - get_jar_path: Get or build the Java subprocess bridge JAR
"""

from .bridge import JavaSubprocessBridge, get_java_bridge
from .callbacks import CallbackRegistry, PythonCallbackHandler
from .jar_builder import JarBuilder, check_build_environment, get_jar_path
from .tcc_callbacks import TccCallbackHandler
from .type_conversion import TypeConverter

__all__ = [
    # Core bridge
    "JavaSubprocessBridge",
    "get_java_bridge",
    # Callback handlers
    "PythonCallbackHandler",
    "TccCallbackHandler",
    "CallbackRegistry",
    # Type conversion
    "TypeConverter",
    # JAR management
    "JarBuilder",
    "check_build_environment",
    "get_jar_path",
]

