"""
Output formatting utilities for FireflyTX shell.

Provides beautiful, consistent formatting for shell output.
"""

from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.tree import Tree
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

class ShellFormatter:
    """Formatter for shell output."""

    def __init__(self, use_rich: bool = True):
        """
        Initialize formatter.

        Args:
            use_rich: Whether to use rich formatting
        """
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()
    
    def print_success(self, message: str):
        """Print a success message."""
        if self.use_rich:
            self.console.print(f"✅ {message}", style="green")
        else:
            print(f"✅ {message}")
    
    def print_error(self, message: str):
        """Print an error message."""
        if self.use_rich:
            self.console.print(f"❌ {message}", style="red bold")
        else:
            print(f"❌ {message}")
    
    def print_warning(self, message: str):
        """Print a warning message."""
        if self.use_rich:
            self.console.print(f"⚠️  {message}", style="yellow")
        else:
            print(f"⚠️  {message}")
    
    def print_info(self, message: str):
        """Print an info message."""
        if self.use_rich:
            self.console.print(f"💡 {message}", style="blue")
        else:
            print(f"💡 {message}")
    
    def print_header(self, title: str, subtitle: Optional[str] = None):
        """Print a section header."""
        if self.use_rich:
            text = Text(title, style="bold cyan")
            if subtitle:
                text.append(f"\n{subtitle}", style="dim")
            self.console.print(Panel(text, border_style="cyan"))
        else:
            print("\n" + "=" * 70)
            print(title)
            if subtitle:
                print(subtitle)
            print("=" * 70)
    
    def print_table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[Any]],
        show_lines: bool = False,
    ):
        """
        Print a formatted table.
        
        Args:
            title: Table title
            headers: Column headers
            rows: Table rows
            show_lines: Whether to show row lines
        """
        if self.use_rich:
            table = Table(
                title=title,
                show_header=True,
                header_style="bold cyan",
                border_style="blue",
                show_lines=show_lines,
                box=box.ROUNDED,
            )
            
            for header in headers:
                table.add_column(header)
            
            for row in rows:
                table.add_row(*[str(cell) for cell in row])
            
            self.console.print(table)
        else:
            # Fallback to plain text table
            print(f"\n{title}")
            print("=" * 70)
            
            # Print headers
            header_line = " | ".join(str(h).ljust(15) for h in headers)
            print(header_line)
            print("-" * 70)
            
            # Print rows
            for row in rows:
                row_line = " | ".join(str(cell).ljust(15) for cell in row)
                print(row_line)
            
            print("=" * 70)
    
    def print_code(
        self,
        code: str,
        language: str = "python",
        line_numbers: bool = True,
        theme: str = "monokai",
    ):
        """
        Print syntax-highlighted code.
        
        Args:
            code: Code to display
            language: Programming language
            line_numbers: Whether to show line numbers
            theme: Syntax highlighting theme
        """
        if self.use_rich:
            syntax = Syntax(
                code,
                language,
                theme=theme,
                line_numbers=line_numbers,
                word_wrap=False,
            )
            self.console.print(syntax)
        else:
            # Fallback to plain text with line numbers
            if line_numbers:
                lines = code.split('\n')
                for i, line in enumerate(lines, 1):
                    print(f"{i:4d} | {line}")
            else:
                print(code)
    
    def print_tree(self, title: str, data: Dict[str, Any]):
        """
        Print a tree structure.
        
        Args:
            title: Tree title
            data: Nested dictionary to display as tree
        """
        if self.use_rich:
            tree = Tree(f"[bold cyan]{title}[/bold cyan]")
            self._build_tree(tree, data)
            self.console.print(tree)
        else:
            # Fallback to indented text
            print(f"\n{title}")
            print("=" * 70)
            self._print_dict_tree(data, indent=0)
    
    def _build_tree(self, tree: "Tree", data: Any, key: Optional[str] = None):
        """Recursively build a rich tree."""
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    branch = tree.add(f"[yellow]{k}[/yellow]")
                    self._build_tree(branch, v)
                else:
                    tree.add(f"[yellow]{k}[/yellow]: [green]{v}[/green]")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    branch = tree.add(f"[yellow][{i}][/yellow]")
                    self._build_tree(branch, item)
                else:
                    tree.add(f"[yellow][{i}][/yellow]: [green]{item}[/green]")
        else:
            if key:
                tree.add(f"[green]{data}[/green]")
    
    def _print_dict_tree(self, data: Any, indent: int = 0):
        """Print a dictionary as an indented tree (fallback)."""
        prefix = "  " * indent
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    print(f"{prefix}{k}:")
                    self._print_dict_tree(v, indent + 1)
                else:
                    print(f"{prefix}{k}: {v}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    print(f"{prefix}[{i}]:")
                    self._print_dict_tree(item, indent + 1)
                else:
                    print(f"{prefix}[{i}]: {item}")
        else:
            print(f"{prefix}{data}")
    
    def print_panel(self, content: str, title: Optional[str] = None, style: str = "blue"):
        """
        Print content in a panel.
        
        Args:
            content: Content to display
            title: Optional panel title
            style: Border style
        """
        if self.use_rich:
            panel = Panel(content, title=title, border_style=style)
            self.console.print(panel)
        else:
            print("\n" + "=" * 70)
            if title:
                print(title)
                print("-" * 70)
            print(content)
            print("=" * 70)

