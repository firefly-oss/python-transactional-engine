"""
FireflyTX Interactive Shell

A sophisticated CLI IDE for FireflyTX development and debugging.
Provides an enhanced interactive environment with:
- Advanced UI with syntax highlighting and line numbers
- Interactive menus and command system
- Process management and monitoring
- Code visualization and inspection tools
- Real-time log viewing
- Developer utilities

Usage:
    python -m fireflytx.shell
    fireflytx-shell  # If installed

Copyright 2025 Firefly Software Solutions Inc
Licensed under the Apache License, Version 2.0
"""

from .core.shell import FireflyTXShell
from .core.session import ShellSession

__all__ = ["FireflyTXShell", "ShellSession"]

