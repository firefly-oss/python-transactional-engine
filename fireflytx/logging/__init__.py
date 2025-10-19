"""
Logging utilities and configuration for FireflyTX.

Provides unified JSON logging with proper prefixes for Python and Java components,
including centralized configuration and log management.
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

from .java_log_bridge import JavaLogBridge, JavaLogEntry, JavaLogLevel, get_java_log_bridge
from .json_formatter import (
    FireflyTXJSONFormatter,
    JavaLogFormatter,
    PythonLogFormatter,
    configure_json_logging,
    create_json_handler,
)
from .manager import (
    FireflyTXLoggingManager,
    get_fireflytx_logger,
    get_logging_manager,
    setup_fireflytx_logging,
    shutdown_fireflytx_logging,
)

# Legacy imports for backwards compatibility
try:
    from .log_viewer import LogFilter, LogViewer

    _LEGACY_AVAILABLE = True
except ImportError:
    _LEGACY_AVAILABLE = False

__all__ = [
    "JavaLogBridge",
    "JavaLogEntry",
    "JavaLogLevel",
    "get_java_log_bridge",
    "FireflyTXJSONFormatter",
    "PythonLogFormatter",
    "JavaLogFormatter",
    "create_json_handler",
    "configure_json_logging",
    "FireflyTXLoggingManager",
    "get_logging_manager",
    "setup_fireflytx_logging",
    "get_fireflytx_logger",
    "shutdown_fireflytx_logging",
]

# Add legacy components if available
if _LEGACY_AVAILABLE:
    __all__.extend(["LogViewer", "LogFilter"])
