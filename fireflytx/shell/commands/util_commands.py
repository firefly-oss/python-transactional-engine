"""
Utility commands for FireflyTX shell.

Provides helper functions and utilities.
"""

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from rich.syntax import Syntax
from rich.panel import Panel

if TYPE_CHECKING:
    from ..core.shell import FireflyTXShell


class UtilCommands:
    """Utility commands."""

    def __init__(self, shell: "FireflyTXShell"):
        """
        Initialize utility commands.

        Args:
            shell: FireflyTXShell instance
        """
        self.shell = shell
        self.formatter = shell.formatter
        self.session = shell.session

    def run_async(self, coro):
        """
        Helper to run async code in the shell.

        Args:
            coro: Coroutine to run

        Usage:
            run(init_engines())
            run(saga_engine.execute(MySaga, {}))
        """
        return asyncio.run(coro)

    def view_file(
        self,
        filepath: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ):
        """
        View a file with syntax highlighting.

        Args:
            filepath: Path to file
            start_line: Optional starting line number
            end_line: Optional ending line number

        Usage:
            view_file("fireflytx/engine.py")
            view_file("fireflytx/engine.py", 10, 50)
        """
        try:
            path = Path(filepath)
            if not path.exists():
                self.formatter.print_error(f"File not found: {filepath}")
                return

            # Read file content
            with open(path, 'r') as f:
                lines = f.readlines()

            # Apply line range if specified
            if start_line is not None or end_line is not None:
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                lines = lines[start:end]

            code = ''.join(lines)

            # Detect language from file extension
            ext_to_lang = {
                '.py': 'python',
                '.js': 'javascript',
                '.java': 'java',
                '.json': 'json',
                '.yaml': 'yaml',
                '.yml': 'yaml',
                '.md': 'markdown',
                '.sh': 'bash',
            }
            language = ext_to_lang.get(path.suffix, 'text')

            # Create syntax highlighted panel
            syntax = Syntax(code, language, theme="solarized-dark", line_numbers=True)
            panel = Panel(syntax, title=f"[bold cyan]{filepath}[/bold cyan]", border_style="cyan")
            self.formatter.console.print(panel)

        except Exception as e:
            self.formatter.print_error(f"Failed to view file: {e}")

    def view_code(self, code: str, language: str = "python", title: str = "Code"):
        """
        View code with syntax highlighting.

        Args:
            code: Code to display
            language: Programming language (default: python)
            title: Panel title

        Usage:
            view_code("print('hello')")
            view_code('{"key": "value"}', "json", "Config")
        """
        try:
            syntax = Syntax(code, language, theme="solarized-dark", line_numbers=True)
            panel = Panel(syntax, title=f"[bold cyan]{title}[/bold cyan]", border_style="cyan")
            self.formatter.console.print(panel)
        except Exception as e:
            self.formatter.print_error(f"Failed to view code: {e}")



    def clear_screen(self):
        """
        Clear the terminal screen.

        Usage:
            clear()
        """
        os.system('clear' if os.name != 'nt' else 'cls')
        self.formatter.console.clear()

    def pwd(self):
        """
        Print current working directory.

        Usage:
            pwd()
        """
        cwd = os.getcwd()
        self.formatter.print_info(f"Current directory: {cwd}")
        return cwd

    def ls(self, path: str = "."):
        """
        List files in a directory.

        Args:
            path: Directory path (default: current directory)

        Usage:
            ls()
            ls("fireflytx")
        """
        try:
            p = Path(path)
            if not p.exists():
                self.formatter.print_error(f"Path not found: {path}")
                return

            if p.is_file():
                self.formatter.print_info(f"File: {path}")
                return

            items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))

            self.formatter.print_info(f"Contents of {path}:")
            for item in items:
                icon = "📁" if item.is_dir() else "📄"
                self.formatter.console.print(f"  {icon} {item.name}")

        except Exception as e:
            self.formatter.print_error(f"Failed to list directory: {e}")

