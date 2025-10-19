"""
Main FireflyTX shell implementation.

Provides an enhanced interactive shell with CLI IDE features.
"""

import asyncio
import atexit
import code
import os
import readline
import sys
from pathlib import Path
from typing import Optional

from fireflytx import __version__

from ..commands import (
    CommandRegistry,
    CommandCategory,
    EngineCommands,
    ProcessCommands,
    DevCommands,
    ExamplesLibrary,
)
from ..commands.util_commands import UtilCommands
from ..ui import (
    show_banner,
    StatusBar,
    Menu,
    FireflyPrompt,
    ShellFormatter,
)
from ..utils import HelpSystem, LogViewer
from .session import ShellSession
from .context import ShellContext


class FireflyTXShell:
    """Enhanced FireflyTX interactive shell."""
    
    def __init__(self):
        """Initialize the shell."""
        # Core components
        self.session = ShellSession()
        self.command_registry = CommandRegistry()

        # Create context early (will be populated with commands later)
        self.context = ShellContext(self.session, self.command_registry)

        # UI components
        self.formatter = ShellFormatter(use_rich=True)
        self.status_bar = StatusBar(self.session, use_rich=True)
        self.prompt = FireflyPrompt(self.session)

        # Command modules (they need context)
        self.engine_commands = EngineCommands(self)
        self.process_commands = ProcessCommands(self)
        self.dev_commands = DevCommands(self)
        self.util_commands = UtilCommands(self)
        self.examples = ExamplesLibrary(self)

        # Utility modules
        self.help_system = HelpSystem(self.command_registry, self.formatter)
        self.log_viewer = LogViewer(self.session, self.formatter)

        # Register all commands
        self._register_commands()

        # Update context with registered commands
        self.context._setup_namespace()

        # Setup history
        self._setup_history()

        # IPython support
        self._ipython_available = False
        try:
            import IPython
            self._ipython_available = True
        except ImportError:
            pass

        # Register cleanup on exit
        atexit.register(self._cleanup_on_exit)
    
    def _register_commands(self):
        """Register all shell commands."""
        # Engine commands
        self.command_registry.register(
            "init_engines",
            self.engine_commands.init_engines,
            CommandCategory.ENGINE,
            "Initialize SAGA and TCC engines",
            "await init_engines()",
            aliases=["init"],
            is_async=True,
        )
        
        self.command_registry.register(
            "shutdown_engines",
            self.engine_commands.shutdown_engines,
            CommandCategory.ENGINE,
            "Shutdown all engines",
            "await shutdown_engines()",
            aliases=["shutdown"],
            is_async=True,
        )
        
        self.command_registry.register(
            "reset",
            self.engine_commands.reset_engines,
            CommandCategory.ENGINE,
            "Reset engines (shutdown + reinit)",
            "await reset()",
            is_async=True,
        )
        
        self.command_registry.register(
            "status",
            self.engine_commands.show_status,
            CommandCategory.ENGINE,
            "Show current engine status",
            "status()",
        )
        
        self.command_registry.register(
            "config",
            self.engine_commands.show_config,
            CommandCategory.ENGINE,
            "Show engine configuration",
            "config()",
        )
        
        # Process commands
        self.command_registry.register(
            "list_bridges",
            self.process_commands.list_java_bridges,
            CommandCategory.PROCESS,
            "List all running Java bridge processes",
            "list_bridges()",
            aliases=["bridges"],
        )
        
        self.command_registry.register(
            "connect_bridge",
            self.process_commands.connect_to_bridge,
            CommandCategory.PROCESS,
            "Connect to an existing bridge",
            "connect_bridge(pid)",
            aliases=["connect"],
        )
        
        self.command_registry.register(
            "java_info",
            self.process_commands.show_java_info,
            CommandCategory.PROCESS,
            "Show Java subprocess information",
            "java_info() or java_info(pid)",
            aliases=["jinfo"],
        )

        self.command_registry.register(
            "kill_bridge",
            self.process_commands.kill_bridge,
            CommandCategory.PROCESS,
            "Kill a specific Java bridge process",
            "kill_bridge(pid) or kill_bridge(pid, force=True)",
            aliases=["kill"],
        )

        self.command_registry.register(
            "kill_all_bridges",
            self.process_commands.kill_all_bridges,
            CommandCategory.PROCESS,
            "Kill all Java bridge processes",
            "kill_all_bridges() or kill_all_bridges(force=True)",
            aliases=["killall"],
        )

        # Utility commands
        self.command_registry.register(
            "help",
            self.show_help,
            CommandCategory.UTILITY,
            "Show help information",
            "help()",
            aliases=["h", "?"],
        )

        self.command_registry.register(
            "examples",
            self.show_examples,
            CommandCategory.UTILITY,
            "Show code examples",
            "examples()",
            aliases=["ex"],
        )

        self.command_registry.register(
            "menu",
            self.show_menu,
            CommandCategory.UTILITY,
            "Show interactive menu",
            "menu()",
            aliases=["m"],
        )

        self.command_registry.register(
            "clear",
            self.clear_screen,
            CommandCategory.UTILITY,
            "Clear screen and show banner",
            "clear()",
            aliases=["cls"],
        )

        self.command_registry.register(
            "view_file",
            self.util_commands.view_file,
            CommandCategory.UTILITY,
            "View a file with syntax highlighting",
            "view_file('path/to/file.py')",
            aliases=["view", "cat"],
        )

        self.command_registry.register(
            "view_code",
            self.util_commands.view_code,
            CommandCategory.UTILITY,
            "View code with syntax highlighting",
            "view_code('print(hello)', 'python')",
        )



        self.command_registry.register(
            "pwd",
            self.util_commands.pwd,
            CommandCategory.UTILITY,
            "Print working directory",
            "pwd()",
        )

        self.command_registry.register(
            "ls",
            self.util_commands.ls,
            CommandCategory.UTILITY,
            "List directory contents",
            "ls('path')",
            aliases=["dir"],
        )

        # Developer commands
        self.command_registry.register(
            "inspect_saga",
            self.dev_commands.inspect_saga,
            CommandCategory.DEVELOPER,
            "Inspect a SAGA class structure",
            "inspect_saga(MySaga)",
            aliases=["inspect"],
        )

        self.command_registry.register(
            "inspect_tcc",
            self.dev_commands.inspect_tcc,
            CommandCategory.DEVELOPER,
            "Inspect a TCC class structure",
            "inspect_tcc(MyTcc)",
        )

        self.command_registry.register(
            "visualize",
            self.dev_commands.visualize,
            CommandCategory.DEVELOPER,
            "Visualize a SAGA or TCC workflow",
            "visualize(MySaga, 'ascii')",
            aliases=["viz"],
        )

        self.command_registry.register(
            "visualize_saga",
            self.dev_commands.visualize_saga,
            CommandCategory.DEVELOPER,
            "Visualize a SAGA workflow",
            "visualize_saga(MySaga, 'mermaid')",
        )

        self.command_registry.register(
            "visualize_tcc",
            self.dev_commands.visualize_tcc,
            CommandCategory.DEVELOPER,
            "Visualize a TCC workflow",
            "visualize_tcc(MyTcc, 'dot')",
        )

        self.command_registry.register(
            "benchmark",
            self.dev_commands.benchmark,
            CommandCategory.DEVELOPER,
            "Benchmark workflow execution",
            "await benchmark(MySaga, inputs, iterations=100)",
            is_async=True,
        )

        self.command_registry.register(
            "logs",
            self.dev_commands.show_logs,
            CommandCategory.DEVELOPER,
            "Show Java bridge logs",
            "logs(lines=50, follow=False, stream='both')",
        )

        # Examples commands
        self.command_registry.register(
            "example",
            self.examples.show_example,
            CommandCategory.UTILITY,
            "Show a specific example",
            "example(1)",
        )

        self.command_registry.register(
            "load_example",
            self.examples.load_example,
            CommandCategory.UTILITY,
            "Load an example into the shell namespace",
            "load_example(1)",
        )

        self.command_registry.register(
            "quick_start",
            self.examples.quick_start,
            CommandCategory.UTILITY,
            "Interactive quick start tutorial",
            "await quick_start()",
            is_async=True,
        )



    def _setup_history(self):
        """Setup command history."""
        history_file = Path.home() / ".fireflytx_history"
        
        try:
            if history_file.exists():
                readline.read_history_file(str(history_file))
            
            # Set history length
            readline.set_history_length(1000)
            
            # Save history on exit
            import atexit
            atexit.register(readline.write_history_file, str(history_file))
        except Exception:
            pass  # History not critical
    
    def show_help(self, topic: str = None):
        """
        Show help information.

        Args:
            topic: Optional topic to show help for (e.g., 'saga', 'tcc', 'config')
        """
        # Use the new HelpSystem for comprehensive help
        self.help_system.show_help(topic)
    
    def show_examples(self):
        """Show code examples."""
        self.examples.show_all_examples()
    
    def show_menu(self):
        """Show interactive menu."""
        from ..ui.menu import create_main_menu
        
        menu = create_main_menu(self)
        
        while True:
            selected = menu.show()
            
            if selected is None:
                break
            
            try:
                if selected.is_async:
                    # Run async action
                    if self._ipython_available:
                        # IPython handles top-level await
                        import IPython
                        IPython.get_ipython().run_cell(f"await {selected.action.__name__}()")
                    else:
                        asyncio.run(selected.action())
                else:
                    # Run sync action
                    selected.action()
            except Exception as e:
                self.formatter.print_error(f"Error executing {selected.label}: {e}")
                import traceback
                traceback.print_exc()
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name != 'nt' else 'cls')
        show_banner(__version__, use_rich=True)


    
    def run(self):
        """Run the interactive shell."""
        # Show banner first
        self._print_banner()

        # Start shell
        if self._ipython_available:
            self._run_ipython()
        else:
            self._run_standard()
    
    def _run_ipython(self):
        """Run with IPython."""
        from IPython.terminal.embed import InteractiveShellEmbed
        from traitlets.config.loader import Config

        # Create custom config
        config = Config()
        config.TerminalInteractiveShell.show_repl_greeting = False
        config.TerminalInteractiveShell.term_title = False
        config.TerminalInteractiveShell.term_title_format = "FireflyTX Shell"
        config.TerminalInteractiveShell.prompts_class = self._create_ipython_prompts()
        config.TerminalInteractiveShell.enable_tip = False

        # Create IPython shell
        ipshell = InteractiveShellEmbed(
            user_ns=self.context.get_namespace(),
            banner1="",  # We already showed the banner
            banner2="",  # No tips
            config=config,
        )

        # Auto-initialize engines on startup
        self._auto_init_engines(ipshell)

        # Start shell
        ipshell()
    
    def _auto_init_engines(self, ipshell):
        """Automatically initialize engines on startup."""
        try:
            # Run init_engines() asynchronously
            ipshell.run_cell("await init_engines()", silent=False)
        except Exception as e:
            # If auto-init fails, just print a warning and continue
            self.formatter.print_warning(f"Auto-initialization failed: {e}")
            self.formatter.print_info("You can manually initialize engines with: await init_engines()")

    def _run_standard(self):
        """Run with standard Python console."""
        console = code.InteractiveConsole(self.context.get_namespace())
        console.interact(banner="", exitmsg="")

    def _print_banner(self):
        """Print the FireflyTX banner."""
        from fireflytx.shell.ui.banner import show_banner

        # Print ASCII art banner with integrated welcome message
        show_banner(version="2025-08", use_rich=True)
    
    def _create_ipython_prompts(self):
        """Create custom IPython prompts."""
        from IPython.terminal.prompts import Prompts, Token
        
        shell_prompt = self.prompt
        
        class FireflyPrompts(Prompts):
            def in_prompt_tokens(self, cli=None):
                return [
                    (Token.Prompt, shell_prompt.get_prompt()),
                ]
            
            def continuation_prompt_tokens(self, cli=None, width=None):
                return [
                    (Token.Prompt, shell_prompt.get_continuation_prompt()),
                ]
            
            def out_prompt_tokens(self):
                return [
                    (Token.OutPrompt, "Out>>> "),
                ]
        
        return FireflyPrompts

    def _cleanup_on_exit(self):
        """Cleanup resources when shell exits."""
        try:
            # Print cleanup message
            print("\n🧹 Cleaning up FireflyTX resources...")

            # Only cleanup if engines were initialized
            if self.session.is_initialized:  # This is a property, not a method
                # Shutdown engines synchronously (atexit doesn't support async)
                if self.session.saga_engine:
                    try:
                        print("  ⏹️  Shutting down SAGA engine...")
                        # Try to shutdown gracefully with a new event loop
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(self.session.saga_engine.shutdown())
                            loop.close()
                            print("  ✅ SAGA engine shutdown")
                        except Exception as loop_error:
                            # If async shutdown fails, try to cleanup what we can
                            print(f"  ⚠️  Warning: Async shutdown failed, attempting manual cleanup: {loop_error}")
                            # Manually cleanup callback handlers and bridge
                            if hasattr(self.session.saga_engine, '_callback_handlers'):
                                for handler in self.session.saga_engine._callback_handlers.values():
                                    if hasattr(handler, "stop"):
                                        handler.stop()
                                self.session.saga_engine._callback_handlers.clear()
                            print("  ✅ SAGA engine cleanup completed")
                    except Exception as e:
                        print(f"  ⚠️  Warning: SAGA engine shutdown failed: {e}")

                if self.session.tcc_engine:
                    try:
                        print("  ⏹️  Shutting down TCC engine...")
                        # TccEngine uses stop() not shutdown()
                        self.session.tcc_engine.stop()
                        print("  ✅ TCC engine shutdown")
                    except Exception as e:
                        print(f"  ⚠️  Warning: TCC engine shutdown failed: {e}")

                # Shutdown Java bridge
                if self.session.java_bridge:
                    try:
                        print("  ⏹️  Shutting down Java bridge...")
                        # Use shutdown() method which calls shutdown_jvm()
                        if hasattr(self.session.java_bridge, 'shutdown'):
                            self.session.java_bridge.shutdown()
                        elif hasattr(self.session.java_bridge, 'shutdown_jvm'):
                            self.session.java_bridge.shutdown_jvm()
                        elif hasattr(self.session.java_bridge, 'close'):
                            self.session.java_bridge.close()
                        print("  ✅ Java bridge terminated")
                    except Exception as e:
                        print(f"  ⚠️  Warning: Java bridge shutdown failed: {e}")

            print("✨ Cleanup complete. Goodbye!")
        except Exception as e:
            # Print error but don't raise
            print(f"⚠️  Warning: Cleanup encountered errors: {e}")

