"""
Status bar for FireflyTX shell.

Displays real-time status information at the bottom of the terminal.
"""

import time
from typing import Optional

try:
    from rich.console import Console
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class StatusBar:
    """Status bar for the shell."""
    
    def __init__(self, session, use_rich: bool = True):
        """
        Initialize status bar.
        
        Args:
            session: ShellSession instance
            use_rich: Whether to use rich formatting
        """
        self.session = session
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()
    
    def render(self) -> str:
        """
        Render the status bar.
        
        Returns:
            Status bar text
        """
        parts = []
        
        # Session info
        uptime_mins = int(self.session.uptime / 60)
        parts.append(f"⏱ {uptime_mins}m")
        
        # Engine status
        if self.session.is_initialized:
            parts.append("🟢 Engines")
        else:
            parts.append("🔴 Engines")
        
        # Bridge status
        if self.session.has_current_bridge:
            pid = self.session.current_bridge_pid
            parts.append(f"🔗 Bridge:{pid}")
        elif self.session.has_connected_bridge:
            pid = self.session.connected_bridge_pid
            parts.append(f"🔗 Connected:{pid}")
        
        # Execution count
        parts.append(f"📝 {self.session.execution_count}")
        
        return " | ".join(parts)
    
    def display(self):
        """Display the status bar."""
        status_text = self.render()
        
        if self.use_rich:
            text = Text(status_text, style="dim cyan")
            self.console.print(text)
        else:
            print(f"[{status_text}]")

