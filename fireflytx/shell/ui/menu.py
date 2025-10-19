"""
Interactive menu system for FireflyTX shell.

Provides a user-friendly menu interface for common operations.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


@dataclass
class MenuItem:
    """Represents a menu item."""
    key: str
    label: str
    description: str
    action: Callable
    is_async: bool = False


class Menu:
    """Interactive menu system."""
    
    def __init__(self, title: str, items: List[MenuItem], use_rich: bool = True):
        """
        Initialize menu.
        
        Args:
            title: Menu title
            items: List of menu items
            use_rich: Whether to use rich formatting
        """
        self.title = title
        self.items = items
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()
    
    def show(self) -> Optional[MenuItem]:
        """
        Display the menu and get user selection.
        
        Returns:
            Selected menu item or None if cancelled
        """
        while True:
            self._display_menu()
            choice = self._get_choice()
            
            if choice is None:
                return None
            
            # Find matching item
            for item in self.items:
                if item.key.lower() == choice.lower():
                    return item
            
            # Invalid choice
            if self.use_rich:
                self.console.print(f"❌ Invalid choice: {choice}", style="red")
            else:
                print(f"❌ Invalid choice: {choice}")
    
    def _display_menu(self):
        """Display the menu."""
        if self.use_rich:
            self._display_rich_menu()
        else:
            self._display_plain_menu()
    
    def _display_rich_menu(self):
        """Display menu using rich."""
        self.console.print()
        self.console.print(f"[bold cyan]{self.title}[/bold cyan]")
        self.console.print()
        
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="blue",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        
        table.add_column("Key", style="yellow", width=8)
        table.add_column("Action", style="green")
        table.add_column("Description", style="dim")
        
        for item in self.items:
            table.add_row(
                f"[{item.key}]",
                item.label,
                item.description,
            )
        
        # Add quit option
        table.add_row("[q]", "Quit", "Return to shell", style="dim")
        
        self.console.print(table)
        self.console.print()
    
    def _display_plain_menu(self):
        """Display menu using plain text."""
        print()
        print("=" * 70)
        print(self.title)
        print("=" * 70)
        print()
        
        for item in self.items:
            print(f"  [{item.key}] {item.label}")
            print(f"      {item.description}")
            print()
        
        print(f"  [q] Quit - Return to shell")
        print()
        print("=" * 70)
    
    def _get_choice(self) -> Optional[str]:
        """
        Get user's menu choice.
        
        Returns:
            User's choice or None if quit
        """
        if self.use_rich:
            choice = Prompt.ask(
                "[bold cyan]Select an option[/bold cyan]",
                default="q",
            )
        else:
            choice = input("Select an option [q]: ").strip() or "q"
        
        if choice.lower() == 'q':
            return None
        
        return choice


def create_main_menu(shell) -> Menu:
    """
    Create the main menu for the shell.

    Args:
        shell: FireflyTXShell instance

    Returns:
        Menu instance
    """
    items = [
        MenuItem(
            key="1",
            label="Initialize Engines",
            description="Start SAGA and TCC engines",
            action=shell.engine_commands.init_engines,
            is_async=True,
        ),
        MenuItem(
            key="2",
            label="Show Status",
            description="Display current engine status",
            action=shell.engine_commands.show_status,
        ),
        MenuItem(
            key="3",
            label="List Bridges",
            description="Show all running Java bridge processes",
            action=shell.process_commands.list_java_bridges,
        ),
        MenuItem(
            key="4",
            label="Java Info",
            description="Show Java subprocess information",
            action=shell.process_commands.show_java_info,
        ),
        MenuItem(
            key="5",
            label="Examples",
            description="Show code examples",
            action=shell.show_examples,
        ),
        MenuItem(
            key="6",
            label="Help",
            description="Show help information",
            action=shell.show_help,
        ),
        MenuItem(
            key="7",
            label="Shutdown Engines",
            description="Shutdown all engines",
            action=shell.engine_commands.shutdown_engines,
            is_async=True,
        ),
    ]

    return Menu("🔥 FireflyTX Main Menu", items)

