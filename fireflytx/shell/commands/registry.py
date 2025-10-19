"""
Command registry for the FireflyTX shell.

Provides a centralized system for registering and discovering commands.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CommandCategory(Enum):
    """Command categories for organization."""
    ENGINE = "engine"
    PROCESS = "process"
    DEVELOPER = "developer"
    VISUALIZATION = "visualization"
    UTILITY = "utility"
    SYSTEM = "system"


@dataclass
class Command:
    """Represents a shell command."""
    name: str
    func: Callable
    category: CommandCategory
    description: str
    usage: str
    aliases: List[str] = None
    is_async: bool = False
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class CommandRegistry:
    """Registry for shell commands."""
    
    def __init__(self):
        """Initialize the command registry."""
        self._commands: Dict[str, Command] = {}
        self._aliases: Dict[str, str] = {}  # alias -> command_name
        self._categories: Dict[CommandCategory, List[str]] = {
            cat: [] for cat in CommandCategory
        }
    
    def register(
        self,
        name: str,
        func: Callable,
        category: CommandCategory,
        description: str,
        usage: str,
        aliases: Optional[List[str]] = None,
        is_async: bool = False,
    ):
        """
        Register a command.
        
        Args:
            name: Command name
            func: Command function
            category: Command category
            description: Short description
            usage: Usage example
            aliases: List of aliases
            is_async: Whether the command is async
        """
        cmd = Command(
            name=name,
            func=func,
            category=category,
            description=description,
            usage=usage,
            aliases=aliases or [],
            is_async=is_async,
        )
        
        self._commands[name] = cmd
        self._categories[category].append(name)
        
        # Register aliases
        for alias in cmd.aliases:
            self._aliases[alias] = name
    
    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name or alias."""
        # Check if it's an alias
        if name in self._aliases:
            name = self._aliases[name]
        
        return self._commands.get(name)
    
    def get_all_commands(self) -> Dict[str, Callable]:
        """Get all command functions as a dict."""
        return {name: cmd.func for name, cmd in self._commands.items()}
    
    def get_commands_by_category(self, category: CommandCategory) -> List[Command]:
        """Get all commands in a category."""
        return [self._commands[name] for name in self._categories[category]]
    
    def list_commands(self, category: Optional[CommandCategory] = None) -> List[Command]:
        """
        List all commands, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of commands
        """
        if category:
            return self.get_commands_by_category(category)
        return list(self._commands.values())
    
    def search_commands(self, query: str) -> List[Command]:
        """
        Search for commands by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching commands
        """
        query = query.lower()
        results = []
        
        for cmd in self._commands.values():
            if (query in cmd.name.lower() or 
                query in cmd.description.lower() or
                any(query in alias.lower() for alias in cmd.aliases)):
                results.append(cmd)
        
        return results

