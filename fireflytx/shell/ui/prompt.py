"""
Custom prompt for FireflyTX shell.

Provides an enhanced prompt with status indicators.
"""

from typing import Optional


class FireflyPrompt:
    """Custom prompt for the shell."""
    
    def __init__(self, session):
        """
        Initialize prompt.
        
        Args:
            session: ShellSession instance
        """
        self.session = session
    
    def get_prompt(self, continuation: bool = False) -> str:
        """
        Get the prompt string.

        Args:
            continuation: Whether this is a continuation prompt

        Returns:
            Prompt string
        """
        if continuation:
            return "       .. "

        # Build status indicators
        indicators = []

        # Engine status
        if self.session.is_initialized:
            indicators.append("✓")
        else:
            indicators.append("○")

        # Bridge status
        if self.session.has_current_bridge:
            indicators.append("🔗")
        elif self.session.has_connected_bridge:
            indicators.append("⚡")

        # Build prompt
        if indicators:
            status = "".join(indicators)
            return f"fireflytx[{status}]>> "
        else:
            return "fireflytx>> "
    
    def get_continuation_prompt(self) -> str:
        """Get the continuation prompt."""
        return self.get_prompt(continuation=True)

