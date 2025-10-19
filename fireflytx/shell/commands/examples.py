"""
Examples library for FireflyTX shell.

Provides code examples and interactive tutorials.
"""

from typing import TYPE_CHECKING
from rich.syntax import Syntax
from rich.panel import Panel
from rich.columns import Columns

if TYPE_CHECKING:
    from ..core.shell import FireflyTXShell


class ExamplesLibrary:
    """Examples and tutorials for FireflyTX."""
    
    def __init__(self, shell: "FireflyTXShell"):
        """
        Initialize examples library.
        
        Args:
            shell: FireflyTXShell instance
        """
        self.shell = shell
        self.formatter = shell.formatter
    
    def show_all_examples(self):
        """Show all available examples."""
        self.formatter.print_header("📚 FireflyTX Examples Library")
        
        examples = [
            ("1", "Basic SAGA", "Simple SAGA pattern example"),
            ("2", "SAGA with Compensation", "SAGA with compensation steps"),
            ("3", "Basic TCC", "Simple TCC pattern example"),
            ("4", "TCC with Multiple Participants", "TCC with multiple participants"),
            ("5", "Event Publishing", "SAGA with event publishing"),
            ("6", "Persistence", "SAGA with persistence"),
            ("7", "Visualization", "Visualizing workflows"),
            ("8", "Benchmarking", "Performance testing"),
        ]
        
        rows = [[num, name, desc] for num, name, desc in examples]
        self.formatter.print_table(
            "Available Examples",
            ["#", "Name", "Description"],
            rows
        )
        
        self.formatter.print_info("\nUse example(number) to view a specific example")
        self.formatter.print_info("Example: example(1)")
    
    def show_example(self, number: int):
        """
        Show a specific example.

        Args:
            number: Example number
        """
        examples = {
            1: self._example_basic_saga,
            2: self._example_saga_compensation,
            3: self._example_basic_tcc,
            4: self._example_tcc_multi_participant,
            5: self._example_event_publishing,
            6: self._example_persistence,
            7: self._example_visualization,
            8: self._example_benchmarking,
        }

        example_func = examples.get(number)
        if example_func:
            example_func()
        else:
            self.formatter.print_error(f"Example {number} not found")
            self.show_all_examples()

    def load_example(self, number: int):
        """
        Load an example into the shell namespace for execution.

        Args:
            number: Example number
        """
        example_codes = {
            1: self._get_basic_saga_code(),
            2: self._get_saga_compensation_code(),
            3: self._get_basic_tcc_code(),
            4: None,  # Not implemented yet
            5: None,  # Not implemented yet
            6: None,  # Not implemented yet
            7: self._get_visualization_code(),
            8: self._get_benchmarking_code(),
        }

        code = example_codes.get(number)
        if code is None:
            self.formatter.print_error(f"Example {number} cannot be loaded or is not implemented yet")
            return

        try:
            # Execute the code in the shell's namespace
            exec(code, self.shell.context.get_namespace())

            self.formatter.print_success(f"✓ Example {number} loaded successfully!")
            self.formatter.print_info("\nThe example classes are now available in your namespace.")
            self.formatter.print_info("You can now use them directly. For example:")

            if number == 1:
                self.formatter.print_info("  await init_engines()")
                self.formatter.print_info("  result = await saga_engine.execute(PaymentSaga, {'order_id': 'ORD-001', 'amount': 99.99})")
            elif number == 2:
                self.formatter.print_info("  await init_engines()")
                self.formatter.print_info("  result = await saga_engine.execute(OrderSaga, {'quantity': 5, 'amount': 100.00})")
            elif number == 3:
                self.formatter.print_info("  await init_engines()")
                self.formatter.print_info("  result = await tcc_engine.execute(MoneyTransferTcc, {'amount': 100.00})")

        except Exception as e:
            self.formatter.print_error(f"Failed to load example: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_basic_saga_code(self):
        """Get basic SAGA example code."""
        return '''from fireflytx import saga, saga_step

@saga("payment-processing")
class PaymentSaga:
    """Simple payment processing SAGA."""

    @saga_step("validate")
    async def validate_payment(self, inputs):
        """Validate payment details."""
        print(f"Validating payment for order {inputs['order_id']}")
        return {"status": "validated"}

    @saga_step("charge")
    async def charge_card(self, inputs):
        """Charge the credit card."""
        print(f"Charging ${inputs['amount']}")
        return {"transaction_id": "txn_123"}

    @saga_step("confirm")
    async def confirm_order(self, inputs):
        """Confirm the order."""
        print("Order confirmed!")
        return {"confirmed": True}
'''

    def _example_basic_saga(self):
        """Show basic SAGA example."""
        self.formatter.print_header("📖 Example 1: Basic SAGA")

        code = self._get_basic_saga_code() + '''
# Usage:
# await init_engines()
# result = await saga_engine.execute(PaymentSaga, {
#     "order_id": "ORD-001",
#     "amount": 99.99
# })
# print(result)
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Basic SAGA Example[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Use @saga decorator to define a SAGA\n"
            "  • Use @saga_step to define steps\n"
            "  • Steps execute in order\n"
            "  • Each step receives inputs and returns results\n\n"
            "💾 To load this example: load_example(1)",
            title="Tips",
            style="yellow"
        )
    
    def _get_saga_compensation_code(self):
        """Get SAGA with compensation example code."""
        return '''from fireflytx import saga, saga_step, compensation_step

@saga("order-processing")
class OrderSaga:
    """Order processing with compensation."""

    @saga_step("reserve-inventory")
    async def reserve_inventory(self, inputs):
        """Reserve inventory."""
        print(f"Reserving {inputs['quantity']} items")
        return {"reserved": True, "reservation_id": "RES-001"}

    @compensation_step("reserve-inventory")
    async def release_inventory(self, inputs, step_result):
        """Release reserved inventory (compensation)."""
        print(f"Releasing reservation {step_result['reservation_id']}")
        return {"released": True}

    @saga_step("charge-payment")
    async def charge_payment(self, inputs):
        """Charge payment."""
        print(f"Charging ${inputs['amount']}")
        # Simulate failure
        raise Exception("Payment declined!")

    @compensation_step("charge-payment")
    async def refund_payment(self, inputs, step_result):
        """Refund payment (compensation)."""
        print("Refunding payment")
        return {"refunded": True}
'''

    def _example_saga_compensation(self):
        """Show SAGA with compensation example."""
        self.formatter.print_header("📖 Example 2: SAGA with Compensation")

        code = self._get_saga_compensation_code() + '''
# When charge_payment fails, release_inventory will be called automatically
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]SAGA with Compensation[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Use @compensation_step to define compensations\n"
            "  • Compensations run in reverse order on failure\n"
            "  • Each compensation receives step results\n"
            "  • Automatic rollback on errors\n\n"
            "💾 To load this example: load_example(2)",
            title="Tips",
            style="yellow"
        )
    
    def _get_basic_tcc_code(self):
        """Get basic TCC example code."""
        return '''from fireflytx import tcc, tcc_participant, try_method, confirm_method, cancel_method

@tcc("transfer-money")
class MoneyTransferTcc:
    """Money transfer using TCC pattern."""

    @tcc_participant("account-a")
    class AccountA:
        """First account participant."""

        @try_method
        async def try_debit(self, inputs):
            """Try to debit account A."""
            print(f"Trying to debit ${inputs['amount']} from Account A")
            return {"reserved": True}

        @confirm_method
        async def confirm_debit(self, inputs, try_result):
            """Confirm the debit."""
            print("Confirming debit from Account A")
            return {"debited": True}

        @cancel_method
        async def cancel_debit(self, inputs, try_result):
            """Cancel the debit."""
            print("Cancelling debit from Account A")
            return {"cancelled": True}
'''

    def _example_basic_tcc(self):
        """Show basic TCC example."""
        self.formatter.print_header("📖 Example 3: Basic TCC")

        code = self._get_basic_tcc_code() + '''
# Usage:
# await init_engines()
# result = await tcc_engine.execute(MoneyTransferTcc, {"amount": 100.00})
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Basic TCC Example[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • TCC has three phases: Try, Confirm, Cancel\n"
            "  • Try phase reserves resources\n"
            "  • Confirm phase commits changes\n"
            "  • Cancel phase releases reservations\n"
            "  • Strong consistency guarantee\n\n"
            "💾 To load this example: load_example(3)",
            title="Tips",
            style="yellow"
        )
    
    def _example_tcc_multi_participant(self):
        """Show TCC with multiple participants."""
        self.formatter.print_header("📖 Example 4: TCC with Multiple Participants")
        self.formatter.print_info("See documentation for multi-participant TCC examples")
    
    def _example_event_publishing(self):
        """Show event publishing example."""
        self.formatter.print_header("📖 Example 5: Event Publishing")
        self.formatter.print_info("See documentation for event publishing examples")
    
    def _example_persistence(self):
        """Show persistence example."""
        self.formatter.print_header("📖 Example 6: Persistence")
        self.formatter.print_info("See documentation for persistence examples")
    
    def _get_visualization_code(self):
        """Get visualization example code."""
        return '''# Visualization helper functions are already available in the shell
# Use: inspect_saga(PaymentSaga), visualize(PaymentSaga, "ascii"), etc.
'''

    def _get_benchmarking_code(self):
        """Get benchmarking example code."""
        return '''# Benchmarking helper function is already available in the shell
# Use: await benchmark(PaymentSaga, inputs, iterations=100)
'''

    def _example_visualization(self):
        """Show visualization example."""
        self.formatter.print_header("📖 Example 7: Visualization")

        code = '''# Visualize a SAGA or TCC workflow
from fireflytx.visualization import SagaVisualizer, OutputFormat

# ASCII visualization
visualizer = SagaVisualizer(PaymentSaga)
print(visualizer.visualize(OutputFormat.ASCII))

# Mermaid diagram
mermaid = visualizer.visualize(OutputFormat.MERMAID)
print(mermaid)

# Or use shell commands:
# inspect_saga(PaymentSaga)
# visualize(PaymentSaga, "ascii")
# visualize(PaymentSaga, "mermaid")
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Visualization Example[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

    def _example_benchmarking(self):
        """Show benchmarking example."""
        self.formatter.print_header("📖 Example 8: Benchmarking")

        code = '''# Benchmark a workflow
await benchmark(PaymentSaga, {
    "order_id": "ORD-001",
    "amount": 99.99
}, iterations=100)

# This will run the workflow 100 times and show:
# - Average execution time
# - Min/max times
# - Throughput (ops/sec)
# - Success/failure counts
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Benchmarking Example[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)
    
    async def quick_start(self):
        """Interactive quick start tutorial."""
        self.formatter.print_header("🚀 FireflyTX Quick Start Tutorial")
        
        self.formatter.print_panel(
            "Welcome to FireflyTX! This tutorial will guide you through:\n"
            "  1. Initializing engines\n"
            "  2. Creating a simple SAGA\n"
            "  3. Executing the SAGA\n"
            "  4. Visualizing the workflow\n\n"
            "Let's get started!",
            title="Welcome",
            style="cyan"
        )
        
        # Step 1: Initialize engines
        self.formatter.print_info("\n📍 Step 1: Initialize Engines")
        self.formatter.print_info("Run: await init_engines()")
        
        if not self.shell.session.saga_engine:
            self.formatter.print_warning("Engines not initialized. Please run: await init_engines()")
            return
        
        self.formatter.print_success("✓ Engines initialized!")
        
        # Step 2: Show example SAGA
        self.formatter.print_info("\n📍 Step 2: Example SAGA")
        self._example_basic_saga()
        
        # Step 3: Execution
        self.formatter.print_info("\n📍 Step 3: Execute the SAGA")
        self.formatter.print_info("Copy the example code above and execute it!")
        
        # Step 4: Next steps
        self.formatter.print_panel(
            "🎉 Next Steps:\n"
            "  • Try example(2) for compensation patterns\n"
            "  • Try example(3) for TCC patterns\n"
            "  • Use inspect_saga(YourSaga) to inspect structure\n"
            "  • Use visualize(YourSaga) to see diagrams\n"
            "  • Use help() to see all commands\n\n"
            "Happy coding! 🔥",
            title="Congratulations!",
            style="green"
        )

