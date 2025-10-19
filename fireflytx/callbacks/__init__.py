"""
Callbacks and HTTP handlers for Python methods invoked by the Java engine.

DEPRECATED: This module is deprecated. Import from fireflytx.integration instead.

Public re-exports for backwards compatibility.
"""
import warnings

from ..integration import CallbackRegistry, PythonCallbackHandler

warnings.warn(
    "fireflytx.callbacks is deprecated. Import from fireflytx.integration instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["PythonCallbackHandler", "CallbackRegistry"]
