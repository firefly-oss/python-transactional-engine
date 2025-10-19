"""
Banner display for FireflyTX shell.

Shows the welcome banner with system information.
"""

import sys
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def show_banner(version: str = "1.0.0", use_rich: bool = True):
    """
    Display the FireflyTX shell banner.

    Args:
        version: FireflyTX version
        use_rich: Whether to use rich formatting (if available)
    """
    # ASCII art banner
    ascii_banner = r"""
  _____.__                _____.__
_/ ____\__|______   _____/ ____\  | ___.__.
\   __\|  \_  __ \_/ __ \   __\|  |<   |  |
 |  |  |  ||  | \/\  ___/|  |  |  |_\___  |
 |__|  |__||__|    \___  >__|  |____/ ____|
                       \/           \/
:: fireflytx ::                  (v2025-08)
"""

    if RICH_AVAILABLE and use_rich:
        console = Console()

        # Print ASCII banner in cyan
        console.print(ascii_banner, style="cyan bold")

        # Print unified welcome message with pre-loaded info and quick start
        welcome = Text()
        welcome.append("🔥 Welcome to FireflyTX Interactive Shell\n\n", style="bold cyan")

        # Pre-loaded section
        welcome.append("Pre-loaded:\n", style="bold yellow")
        welcome.append("  Decorators:  ", style="dim")
        welcome.append("@saga, @saga_step, @compensation_step, @tcc, @tcc_participant\n", style="green")
        welcome.append("  Engines:     ", style="dim")
        welcome.append("SagaEngine, TccEngine, EngineConfig\n", style="green")
        welcome.append("  Visualizers: ", style="dim")
        welcome.append("SagaVisualizer, TccVisualizer, OutputFormat\n", style="green")
        welcome.append("  Utilities:   ", style="dim")
        welcome.append("asyncio, json, Path, pprint, datetime\n\n", style="green")

        # Quick start section
        welcome.append("Quick Start:\n", style="bold yellow")
        welcome.append("  • Type ", style="dim")
        welcome.append("help()", style="bold green")
        welcome.append(" for command reference\n", style="dim")
        welcome.append("  • Type ", style="dim")
        welcome.append("examples()", style="bold green")
        welcome.append(" for code examples\n", style="dim")
        welcome.append("  • Type ", style="dim")
        welcome.append("quick_start()", style="bold green")
        welcome.append(" for interactive tutorial\n", style="dim")
        welcome.append("  • Type ", style="dim")
        welcome.append("status()", style="bold green")
        welcome.append(" to view engine status\n\n", style="dim")

        # Tagline
        welcome.append("Python defines, Java executes.", style="dim italic cyan")

        panel = Panel(
            welcome,
            title="[bold cyan]Getting Started[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(panel)
        console.print()
    else:
        # Fallback to plain text
        print(ascii_banner)
        print("=" * 64)
        print("🔥 Welcome to FireflyTX Interactive Shell")
        print()
        print("Pre-loaded:")
        print("  Decorators:  @saga, @saga_step, @compensation_step, @tcc, @tcc_participant")
        print("  Engines:     SagaEngine, TccEngine, EngineConfig")
        print("  Visualizers: SagaVisualizer, TccVisualizer, OutputFormat")
        print("  Utilities:   asyncio, json, Path, pprint, datetime")
        print()
        print("Quick Start:")
        print("  • Type help() for command reference")
        print("  • Type examples() for code examples")
        print("  • Type quick_start() for interactive tutorial")
        print("  • Type status() to view engine status")
        print()
        print("Python defines, Java executes.")
        print("=" * 64)

