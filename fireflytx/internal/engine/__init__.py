"""
Internal engine implementations (Python side wrappers around the Java engine).

These modules are considered internal. Use fireflytx.api for the stable
public API.
"""
from typing import Any

# Re-export from legacy locations to keep runtime behavior intact
try:
    from ...engine.saga_engine import SagaEngine  # type: ignore
except Exception as _e:  # pragma: no cover
    SagaEngine = Any  # fallback typing placeholder

try:
    from ...engine.tcc_engine import TccEngine  # type: ignore
except Exception as _e:  # pragma: no cover
    TccEngine = Any  # fallback typing placeholder

__all__ = ["SagaEngine", "TccEngine"]
