"""
Help system for FireflyTX shell.

Provides comprehensive help and documentation.
"""


class HelpSystem:
    """Help system for the shell."""
    
    def __init__(self, command_registry, formatter):
        """
        Initialize help system.
        
        Args:
            command_registry: CommandRegistry instance
            formatter: ShellFormatter instance
        """
        self.command_registry = command_registry
        self.formatter = formatter
    
    def show_help(self, topic: str = None):
        """
        Show help information.

        Args:
            topic: Optional topic to show help for
        """
        if topic:
            self._show_topic_help(topic)
        else:
            self._show_general_help()

    def _show_general_help(self):
        """Show general help information."""
        self.formatter.print_header("🔥 FireflyTX Interactive Shell - Help")

        # Overview
        print()
        self.formatter.console.print("[bold yellow]Overview[/bold yellow]")
        self.formatter.console.print(
            "FireflyTX is a distributed transaction framework for Python that implements "
            "SAGA and TCC patterns using Java lib-transactional-engine for orchestration."
        )
        print()

        # Quick Start
        self.formatter.console.print("[bold yellow]Quick Start[/bold yellow]")
        self.formatter.print_code("""
# Initialize engines
await init_engines()

# Check status
status()

# List available commands
commands()

# Get help on a specific topic
help('saga')
help('tcc')
help('config')
""")

        # Available Topics
        print()
        self.formatter.console.print("[bold yellow]Available Help Topics[/bold yellow]")
        topics = {
            "saga": "SAGA pattern and execution",
            "tcc": "TCC (Try-Confirm-Cancel) pattern",
            "config": "Engine configuration",
            "commands": "Available shell commands",
            "examples": "Code examples and tutorials",
            "debugging": "Debugging and troubleshooting",
        }

        for topic_name, description in topics.items():
            self.formatter.console.print(f"  • [cyan]{topic_name:12}[/cyan] - {description}")

        print()
        self.formatter.console.print("💡 Use [bold green]help('<topic>')[/bold green] to get detailed information on a topic")

    def _show_topic_help(self, topic: str):
        """Show help for a specific topic."""
        topic = topic.lower()

        if topic == "saga":
            self._show_saga_help()
        elif topic == "tcc":
            self._show_tcc_help()
        elif topic == "config":
            self._show_config_help()
        elif topic == "commands":
            self._show_commands_help()
        elif topic == "examples":
            self._show_examples_help()
        elif topic == "debugging":
            self._show_debugging_help()
        else:
            self.formatter.print_error(f"Unknown help topic: {topic}")
            self.formatter.print_info("Use help() to see available topics")

    def _show_saga_help(self):
        """Show SAGA pattern help."""
        self.formatter.print_header("📖 SAGA Pattern Help")

        print()
        self.formatter.console.print("[bold yellow]What is SAGA?[/bold yellow]")
        self.formatter.console.print(
            "SAGA is a pattern for managing distributed transactions across multiple services. "
            "It breaks a transaction into a sequence of local transactions, each with a "
            "compensation action to undo its effects if needed."
        )
        print()

        self.formatter.console.print("[bold yellow]Basic Example[/bold yellow]")
        self.formatter.print_code("""
from fireflytx import saga, saga_step, compensation_step

@saga("order-processing")
class OrderProcessingSaga:
    @saga_step("reserve-payment")
    async def reserve_payment(self, ctx, order_data):
        payment_id = await payment_service.reserve(order_data)
        ctx.set_data("payment_id", payment_id)
        return {"payment_id": payment_id}

    @compensation_step("reserve-payment")
    async def cancel_payment(self, ctx, order_data):
        payment_id = ctx.get_data("payment_id")
        await payment_service.cancel(payment_id)

    @saga_step("reserve-inventory", depends_on="reserve-payment")
    async def reserve_inventory(self, ctx, order_data):
        return await inventory_service.reserve(order_data)

# Execute the SAGA
engine = SagaEngine()
await engine.initialize()
result = await engine.execute(OrderProcessingSaga, order_data)
""")

        print()
        self.formatter.console.print("[bold yellow]Key Concepts[/bold yellow]")
        self.formatter.console.print("  • @saga decorator defines a SAGA transaction")
        self.formatter.console.print("  • @saga_step defines a step in the SAGA")
        self.formatter.console.print("  • @compensation_step defines rollback logic")
        self.formatter.console.print("  • depends_on creates step dependencies")
        self.formatter.console.print("  • Context shares data between steps")

    def _show_tcc_help(self):
        """Show TCC pattern help."""
        self.formatter.print_header("📖 TCC Pattern Help")

        print()
        self.formatter.console.print("[bold yellow]What is TCC?[/bold yellow]")
        self.formatter.console.print(
            "TCC (Try-Confirm-Cancel) is a two-phase commit pattern for distributed transactions. "
            "It consists of three phases: Try (reserve resources), Confirm (commit), and Cancel (rollback)."
        )
        print()

        self.formatter.console.print("[bold yellow]Basic Example[/bold yellow]")
        self.formatter.print_code("""
from fireflytx import tcc, tcc_participant

@tcc("money-transfer")
class MoneyTransferTcc:
    @tcc_participant("debit-account")
    async def debit_account(self, transfer_data):
        # Try: Reserve funds
        await account_service.reserve_debit(transfer_data)

    @tcc_participant("debit-account", phase="confirm")
    async def confirm_debit(self, transfer_data):
        # Confirm: Actually debit the account
        await account_service.confirm_debit(transfer_data)

    @tcc_participant("debit-account", phase="cancel")
    async def cancel_debit(self, transfer_data):
        # Cancel: Release the reservation
        await account_service.release_debit(transfer_data)

# Execute the TCC transaction
engine = TccEngine()
engine.start()
result = await engine.execute(MoneyTransferTcc, transfer_data)
""")

    def _show_config_help(self):
        """Show configuration help."""
        self.formatter.print_header("📖 Configuration Help")

        print()
        self.formatter.console.print("[bold yellow]Engine Configuration[/bold yellow]")
        self.formatter.print_code("""
from fireflytx import SagaEngine, EngineConfig, PersistenceConfig, JvmConfig

# Development configuration (default)
config = EngineConfig()

# Production configuration
config = EngineConfig(
    max_concurrent_executions=200,
    default_timeout_ms=60000,
    persistence=PersistenceConfig(
        type="redis",
        connection_string="redis://localhost:6379"
    ),
    jvm=JvmConfig(
        heap_size="2g",
        gc_algorithm="G1GC"
    )
)

engine = SagaEngine(config=config)
await engine.initialize()
""")

        print()
        self.formatter.console.print("[bold yellow]View Current Configuration[/bold yellow]")
        self.formatter.console.print("💡 Use the [bold green]config()[/bold green] command to view current engine configuration")

    def _show_commands_help(self):
        """Show available commands."""
        self.formatter.print_header("📖 Available Commands")

        # Get all commands from registry
        if self.command_registry:
            from ..commands.registry import CommandCategory

            for category in CommandCategory:
                commands = self.command_registry.get_commands_by_category(category)
                if not commands:
                    continue

                print()
                self.formatter.console.print(f"[bold yellow]{category.value.upper()}[/bold yellow]")
                for cmd in commands:
                    self.formatter.console.print(f"  • [cyan]{cmd.name:20}[/cyan] - {cmd.description}")
        else:
            self.formatter.console.print("💡 Use [bold green]commands()[/bold green] to see all available commands")

    def _show_examples_help(self):
        """Show examples help."""
        self.formatter.print_header("📖 Examples")
        self.formatter.console.print("💡 Use [bold green]examples()[/bold green] command to see code examples and tutorials")

    def _show_debugging_help(self):
        """Show debugging help."""
        self.formatter.print_header("📖 Debugging & Troubleshooting")

        print()
        self.formatter.console.print("[bold yellow]Common Commands[/bold yellow]")
        self.formatter.console.print("  • [cyan]status()[/cyan] - Check engine status")
        self.formatter.console.print("  • [cyan]config()[/cyan] - View configuration")
        self.formatter.console.print("  • [cyan]history()[/cyan] - View command history")
        self.formatter.console.print("  • [cyan]clear()[/cyan] - Clear the screen")

        print()
        self.formatter.console.print("[bold yellow]Troubleshooting[/bold yellow]")
        self.formatter.console.print("  • If engines fail to initialize, check Java installation")
        self.formatter.console.print("  • Use [bold green]await init_engines()[/bold green] to reinitialize")
        self.formatter.console.print("  • Check logs for detailed error messages")

