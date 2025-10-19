"""
Shell session management.

Handles the state and lifecycle of a FireflyTX shell session.
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime

from fireflytx import SagaEngine, TccEngine
from fireflytx.integration import JavaSubprocessBridge


class ShellSession:
    """Manages the state of a FireflyTX shell session."""

    def __init__(self):
        """Initialize a new shell session."""
        self.start_time = datetime.now()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Engine instances
        self.saga_engine: Optional[SagaEngine] = None
        self.tcc_engine: Optional[TccEngine] = None
        self.java_bridge: Optional[JavaSubprocessBridge] = None
        
        # Session state
        self._engines_initialized = False
        self._connected_bridge_info: Optional[Dict[str, Any]] = None
        
        # History and command tracking
        self.command_history: List[str] = []
        self.execution_count = 0
        
        # Working directory
        self.working_dir = Path.cwd()
        
    @property
    def uptime(self) -> float:
        """Get session uptime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def command_count(self) -> int:
        """Get total command count."""
        return self.execution_count
    
    @property
    def is_initialized(self) -> bool:
        """Check if engines are initialized."""
        return self._engines_initialized
    
    @property
    def has_current_bridge(self) -> bool:
        """Check if there's a current bridge."""
        return self.java_bridge is not None
    
    @property
    def has_connected_bridge(self) -> bool:
        """Check if there's a connected bridge."""
        return self._connected_bridge_info is not None
    
    @property
    def current_bridge_pid(self) -> Optional[int]:
        """Get current bridge PID."""
        if self.java_bridge and self.java_bridge._java_process:
            return self.java_bridge._java_process.pid
        return None
    
    @property
    def connected_bridge_pid(self) -> Optional[int]:
        """Get connected bridge PID."""
        if self._connected_bridge_info:
            return self._connected_bridge_info.get('pid')
        return None
    
    def set_connected_bridge(self, bridge_info: Dict[str, Any]):
        """Set connected bridge information."""
        self._connected_bridge_info = bridge_info
    
    def clear_connected_bridge(self):
        """Clear connected bridge information."""
        self._connected_bridge_info = None
    
    def mark_initialized(self):
        """Mark engines as initialized."""
        self._engines_initialized = True
    
    def mark_uninitialized(self):
        """Mark engines as uninitialized."""
        self._engines_initialized = False
    
    def add_command(self, command: str):
        """Add a command to history."""
        self.command_history.append(command)
        self.execution_count += 1
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of session status."""
        return {
            'session_id': self.session_id,
            'uptime': self.uptime,
            'engines_initialized': self._engines_initialized,
            'saga_engine': self.saga_engine is not None,
            'tcc_engine': self.tcc_engine is not None,
            'java_bridge': self.java_bridge is not None,
            'current_bridge_pid': self.current_bridge_pid,
            'connected_bridge_pid': self.connected_bridge_pid,
            'execution_count': self.execution_count,
            'working_dir': str(self.working_dir),
        }

