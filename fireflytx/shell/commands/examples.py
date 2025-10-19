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
        self.formatter.print_header("📚 FireflyTX Examples Library - Battle-Tested Patterns")

        examples = [
            ("1", "Basic SAGA", "Simple payment processing SAGA"),
            ("2", "SAGA with Compensation", "Order processing with automatic rollback"),
            ("3", "SAGA with Context Variables", "Share data between steps using context"),
            ("4", "SAGA with Dependencies", "Complex workflow with parallel execution"),
            ("5", "Basic TCC", "Money transfer with Try-Confirm-Cancel"),
            ("6", "TCC Multi-Participant", "Distributed transaction across services"),
            ("7", "Context Variables Advanced", "Advanced context variable patterns"),
            ("8", "Error Handling & Retry", "Robust error handling with retries"),
            ("9", "Parallel Execution", "Concurrent step execution patterns"),
            ("10", "Event Publishing", "SAGA with event-driven architecture"),
            ("11", "Persistence & Recovery", "State persistence and recovery"),
            ("12", "Benchmarking", "Performance testing and optimization"),
        ]

        rows = [[num, name, desc] for num, name, desc in examples]
        self.formatter.print_table(
            "Available Examples",
            ["#", "Name", "Description"],
            rows
        )

        self.formatter.print_info("\n💡 Commands:")
        self.formatter.print_info("  • example(number)      - View example code and explanation")
        self.formatter.print_info("  • load_example(number) - Load example into shell for execution")
        self.formatter.print_info("\n📖 Example: example(1) or load_example(1)")
    
    def show_example(self, number: int):
        """
        Show a specific example.

        Args:
            number: Example number
        """
        examples = {
            1: self._example_basic_saga,
            2: self._example_saga_compensation,
            3: self._example_saga_context_variables,
            4: self._example_saga_dependencies,
            5: self._example_basic_tcc,
            6: self._example_tcc_multi_participant,
            7: self._example_context_advanced,
            8: self._example_error_handling,
            9: self._example_parallel_execution,
            10: self._example_event_publishing,
            11: self._example_persistence,
            12: self._example_benchmarking,
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
            3: self._get_saga_context_code(),
            4: self._get_saga_dependencies_code(),
            5: self._get_basic_tcc_code(),
            6: self._get_tcc_multi_participant_code(),
            7: self._get_context_advanced_code(),
            8: self._get_error_handling_code(),
            9: self._get_parallel_execution_code(),
            10: None,  # Event publishing - complex setup
            11: None,  # Persistence - requires external services
            12: self._get_benchmarking_code(),
        }

        code = example_codes.get(number)
        if code is None:
            self.formatter.print_error(f"Example {number} cannot be loaded (requires external setup)")
            self.formatter.print_info("Use example({number}) to view the code instead")
            return

        try:
            # Execute the code in the shell's namespace
            exec(code, self.shell.context.get_namespace())

            self.formatter.print_success(f"✓ Example {number} loaded successfully!")
            self.formatter.print_info("\n📦 The example classes are now available in your namespace.")
            self.formatter.print_info("💡 Quick start:")

            usage_hints = {
                1: ["await init_engines()", "result = await saga_engine.execute(PaymentSaga, {'order_id': 'ORD-001', 'amount': 99.99})"],
                2: ["await init_engines()", "result = await saga_engine.execute(OrderSaga, {'quantity': 5, 'amount': 100.00})"],
                3: ["await init_engines()", "result = await saga_engine.execute(ContextSaga, {'user_id': 'U123', 'amount': 50.00})"],
                4: ["await init_engines()", "result = await saga_engine.execute(ComplexOrderSaga, {'order_id': 'ORD-001'})"],
                5: ["await init_engines()", "result = await tcc_engine.execute(MoneyTransferTcc, {'amount': 100.00})"],
                6: ["await init_engines()", "result = await tcc_engine.execute(DistributedTcc, {'order_id': 'ORD-001', 'amount': 250.00})"],
                7: ["await init_engines()", "result = await saga_engine.execute(AdvancedContextSaga, {'session_id': 'S123'})"],
                8: ["await init_engines()", "result = await saga_engine.execute(RobustSaga, {'order_id': 'ORD-001'})"],
                9: ["await init_engines()", "result = await saga_engine.execute(ParallelSaga, {'batch_id': 'B001'})"],
                12: ["await benchmark(PaymentSaga, {'order_id': 'ORD-001', 'amount': 99.99}, iterations=100)"],
            }

            hints = usage_hints.get(number, [])
            for hint in hints:
                self.formatter.print_info(f"  {hint}")

        except Exception as e:
            self.formatter.print_error(f"Failed to load example: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_basic_saga_code(self):
        """Get basic SAGA example code."""
        return '''from fireflytx import saga, saga_step

@saga("payment-processing")
class PaymentSaga:
    """Simple payment processing SAGA - Battle-tested pattern."""

    @saga_step("validate", retry=3, timeout_ms=5000)
    async def validate_payment(self, data: dict):
        """Validate payment details with retry logic."""
        print(f"✅ Validating payment for order {data.get('order_id', 'unknown')}")

        # Simulate validation
        if not data.get('order_id'):
            raise ValueError("Order ID is required")
        if data.get('amount', 0) <= 0:
            raise ValueError("Amount must be positive")

        return {"status": "validated", "validated_at": "2025-10-19T12:00:00Z"}

    @saga_step("charge", depends_on=["validate"], retry=2, timeout_ms=10000)
    async def charge_card(self, data: dict):
        """Charge the credit card with automatic retry."""
        print(f"💳 Charging ${data.get('amount', 0)}")

        # Simulate payment processing
        import random
        if random.random() < 0.1:  # 10% simulated failure rate
            raise Exception("Payment gateway timeout - will retry")

        return {"transaction_id": f"txn_{data.get('order_id', 'unknown')}", "charged": True}

    @saga_step("confirm", depends_on=["charge"])
    async def confirm_order(self, data: dict):
        """Confirm the order after successful payment."""
        print(f"🎉 Order {data.get('order_id', 'unknown')} confirmed!")
        return {"confirmed": True, "confirmation_id": f"conf_{data.get('order_id', 'unknown')}"}
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
    """Order processing with automatic compensation on failure."""

    @saga_step("reserve-inventory", compensate="release_inventory", retry=3)
    async def reserve_inventory(self, data: dict):
        """Reserve inventory with automatic rollback."""
        print(f"📦 Reserving {data.get('quantity', 0)} items")

        # Simulate inventory check
        if data.get('quantity', 0) > 100:
            raise Exception("Insufficient inventory")

        reservation_id = f"RES-{data.get('order_id', 'unknown')}"
        print(f"✅ Reserved: {reservation_id}")
        return {"reserved": True, "reservation_id": reservation_id}

    @compensation_step("reserve-inventory")
    async def release_inventory(self, result: dict):
        """Release reserved inventory (automatic rollback)."""
        # The result parameter contains the output from reserve_inventory step
        reservation_id = result.get('reservation_id', 'unknown')
        print(f"🔄 Releasing reservation {reservation_id}")
        return {"released": True}

    @saga_step("charge-payment", depends_on=["reserve-inventory"], compensate="refund_payment")
    async def charge_payment(self, data: dict):
        """Charge payment - will fail to demonstrate compensation."""
        print(f"💳 Charging ${data.get('amount', 0)}")

        # Simulate payment failure to trigger compensation
        raise Exception("Payment declined - card expired!")

    @compensation_step("charge-payment")
    async def refund_payment(self, result: dict):
        """Refund payment (compensation - won't be called since charge fails)."""
        print("🔄 Refunding payment")
        return {"refunded": True}
'''

    def _example_saga_compensation(self):
        """Show SAGA with compensation example."""
        self.formatter.print_header("📖 Example 2: SAGA with Compensation")

        code = self._get_saga_compensation_code() + '''
# When charge_payment fails, release_inventory will be called automatically
# This demonstrates the automatic rollback mechanism
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]SAGA with Compensation[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Use compensate='method_name' in @saga_step\n"
            "  • Compensations run in REVERSE order on failure\n"
            "  • Each compensation receives the step's result\n"
            "  • Automatic rollback ensures data consistency\n"
            "  • Failed steps don't trigger their own compensation\n\n"
            "💾 To load this example: load_example(2)",
            title="Tips",
            style="yellow"
        )

    def _get_saga_context_code(self):
        """Get SAGA with context variables example code."""
        return '''from fireflytx import saga, saga_step, SagaContext

@saga("context-demo")
class ContextSaga:
    """Demonstrate context variable sharing between steps."""

    @saga_step("create-user")
    async def create_user(self, data: dict, context: SagaContext):
        """Create user and store ID in context."""
        user_id = f"USER-{data.get('user_id', 'unknown')}"
        print(f"👤 Creating user: {user_id}")

        # Store in context for other steps
        context.set_variable("user_id", user_id)
        context.set_variable("created_at", "2025-10-19T12:00:00Z")

        return {"user_id": user_id, "status": "created"}

    @saga_step("create-wallet", depends_on=["create-user"])
    async def create_wallet(self, data: dict, context: SagaContext):
        """Create wallet using user_id from context."""
        # Retrieve from context
        user_id = context.get_variable("user_id")
        print(f"💰 Creating wallet for user: {user_id}")

        wallet_id = f"WALLET-{user_id}"
        context.set_variable("wallet_id", wallet_id)

        return {"wallet_id": wallet_id, "balance": 0.0}

    @saga_step("fund-wallet", depends_on=["create-wallet"])
    async def fund_wallet(self, data: dict, context: SagaContext):
        """Fund wallet using IDs from context."""
        user_id = context.get_variable("user_id")
        wallet_id = context.get_variable("wallet_id")
        amount = data.get('amount', 0)

        print(f"💵 Funding wallet {wallet_id} with ${amount}")

        return {"funded": True, "new_balance": amount}
'''

    def _example_saga_context_variables(self):
        """Show SAGA with context variables example."""
        self.formatter.print_header("📖 Example 3: SAGA with Context Variables")

        code = self._get_saga_context_code() + '''
# Context variables allow steps to share data
# Use context.set_variable() and context.get_variable()
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Context Variables[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Add 'context: SagaContext' parameter to steps\n"
            "  • Use context.set_variable(key, value) to store\n"
            "  • Use context.get_variable(key) to retrieve\n"
            "  • Context flows through all dependent steps\n"
            "  • Perfect for passing IDs, tokens, etc.\n\n"
            "💾 To load this example: load_example(3)",
            title="Tips",
            style="yellow"
        )
    
    def _get_saga_dependencies_code(self):
        """Get SAGA with complex dependencies example code."""
        return '''from fireflytx import saga, saga_step, SagaContext

@saga("complex-order", layer_concurrency=3)
class ComplexOrderSaga:
    """Complex order processing with parallel execution."""

    @saga_step("validate-order")
    async def validate_order(self, data: dict, context: SagaContext):
        """Validate order - runs first."""
        print(f"✅ Validating order {data.get('order_id', 'unknown')}")
        context.set_variable("order_validated", True)
        return {"validated": True}

    # These three steps run in PARALLEL after validation
    @saga_step("check-inventory", depends_on=["validate-order"])
    async def check_inventory(self, data: dict):
        """Check inventory - runs in parallel with credit check."""
        print("📦 Checking inventory...")
        return {"available": True, "warehouse": "WH-001"}

    @saga_step("check-credit", depends_on=["validate-order"])
    async def check_credit(self, data: dict):
        """Check credit - runs in parallel with inventory check."""
        print("💳 Checking credit...")
        return {"approved": True, "limit": 5000.0}

    @saga_step("calculate-shipping", depends_on=["validate-order"])
    async def calculate_shipping(self, data: dict):
        """Calculate shipping - runs in parallel."""
        print("🚚 Calculating shipping...")
        return {"cost": 15.99, "carrier": "FastShip"}

    # This step waits for ALL parallel steps to complete
    @saga_step("finalize-order", depends_on=["check-inventory", "check-credit", "calculate-shipping"])
    async def finalize_order(self, data: dict, context: SagaContext):
        """Finalize order after all checks pass."""
        print("🎉 Finalizing order...")
        return {"status": "completed", "order_id": data.get('order_id', 'unknown')}
'''

    def _example_saga_dependencies(self):
        """Show SAGA with dependencies example."""
        self.formatter.print_header("📖 Example 4: SAGA with Dependencies & Parallel Execution")

        code = self._get_saga_dependencies_code() + '''
# Steps with same dependencies run in PARALLEL
# layer_concurrency controls max parallel steps per layer
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Complex Dependencies[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Use depends_on to control execution order\n"
            "  • Steps with same dependencies run in PARALLEL\n"
            "  • layer_concurrency limits parallel execution\n"
            "  • Perfect for optimizing workflow performance\n"
            "  • Automatic dependency resolution\n\n"
            "💾 To load this example: load_example(4)",
            title="Tips",
            style="yellow"
        )

    def _get_basic_tcc_code(self):
        """Get basic TCC example code."""
        return '''from pydantic import BaseModel
from fireflytx import tcc, tcc_participant, try_method, confirm_method, cancel_method

# Define Pydantic models for type safety
class TransferRequest(BaseModel):
    """Transfer request data."""
    amount: float
    from_account: str = "Account-A"
    to_account: str = "Account-B"

class ReservationResult(BaseModel):
    """Reservation result from TRY phase."""
    reserved: bool
    reservation_id: str
    amount: float = 0.0

class ConfirmResult(BaseModel):
    """Result from CONFIRM phase."""
    confirmed: bool
    new_balance: float

@tcc("transfer-money")
class MoneyTransferTcc:
    """Money transfer using TCC pattern with Pydantic models - Battle-tested."""

    @tcc_participant("account-a", order=1)
    class AccountA:
        """Source account participant."""

        @try_method
        async def try_debit(self, data: TransferRequest) -> ReservationResult:
            """Try to reserve funds from account A."""
            print(f"🔒 TRY: Reserving ${data.amount} from {data.from_account}")

            # Simulate balance check
            if data.amount > 1000:
                raise Exception("Insufficient funds")

            return ReservationResult(
                reserved=True,
                reservation_id="RES-A-001",
                amount=data.amount
            )

        @confirm_method
        async def confirm_debit(self, data: TransferRequest, try_result: ReservationResult) -> ConfirmResult:
            """Confirm the debit - commit the transaction."""
            print(f"✅ CONFIRM: Debiting {data.from_account} (reservation: {try_result.reservation_id})")
            return ConfirmResult(confirmed=True, new_balance=500.0)

        @cancel_method
        async def cancel_debit(self, data: TransferRequest, try_result: ReservationResult):
            """Cancel the debit - release the reservation."""
            print(f"🔄 CANCEL: Releasing reservation {try_result.reservation_id}")
            return {"cancelled": True}

    @tcc_participant("account-b", order=2)
    class AccountB:
        """Destination account participant."""

        @try_method
        async def try_credit(self, data: TransferRequest) -> ReservationResult:
            """Try to prepare credit to account B."""
            print(f"🔒 TRY: Preparing to credit ${data.amount} to {data.to_account}")
            return ReservationResult(
                reserved=True,
                reservation_id="RES-B-001",
                amount=data.amount
            )

        @confirm_method
        async def confirm_credit(self, data: TransferRequest, try_result: ReservationResult) -> ConfirmResult:
            """Confirm the credit - commit the transaction."""
            print(f"✅ CONFIRM: Crediting {data.to_account}")
            return ConfirmResult(confirmed=True, new_balance=1500.0)

        @cancel_method
        async def cancel_credit(self, data: TransferRequest, try_result: ReservationResult):
            """Cancel the credit - rollback."""
            print(f"🔄 CANCEL: Cancelling credit preparation")
            return {"cancelled": True}
'''

    def _example_basic_tcc(self):
        """Show basic TCC example."""
        self.formatter.print_header("📖 Example 5: Basic TCC")

        code = self._get_basic_tcc_code() + '''
# TCC ensures ACID properties across distributed services
# Try -> Confirm (success) or Cancel (failure)
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Basic TCC Example[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • TCC has three phases: Try, Confirm, Cancel\n"
            "  • Try phase reserves resources (locks)\n"
            "  • Confirm phase commits all changes\n"
            "  • Cancel phase releases all reservations\n"
            "  • Strong consistency guarantee\n"
            "  • Use 'order' to control participant execution\n\n"
            "💾 To load this example: load_example(5)",
            title="Tips",
            style="yellow"
        )

    def _get_tcc_multi_participant_code(self):
        """Get TCC with multiple participants example code."""
        return '''from pydantic import BaseModel
from fireflytx import tcc, tcc_participant, try_method, confirm_method, cancel_method

# Define Pydantic models
class OrderRequest(BaseModel):
    """Order request data."""
    order_id: str
    customer_id: str
    amount: float
    items: list = []

class InventoryReservation(BaseModel):
    """Inventory reservation result."""
    reserved: bool
    reservation_id: str

class PaymentAuthorization(BaseModel):
    """Payment authorization result."""
    authorized: bool
    auth_code: str

class ShippingSchedule(BaseModel):
    """Shipping schedule result."""
    scheduled: bool
    tracking: str

@tcc("distributed-order")
class DistributedTcc:
    """Distributed order processing with Pydantic models across multiple services."""

    @tcc_participant("inventory-service", order=1)
    class InventoryService:
        """Inventory management service."""

        @try_method
        async def try_reserve(self, data: OrderRequest) -> InventoryReservation:
            """Try to reserve inventory."""
            print(f"📦 [Inventory] TRY: Reserving items for {data.order_id}")
            reservation_id = f"INV-{data.order_id}"
            return InventoryReservation(reserved=True, reservation_id=reservation_id)

        @confirm_method
        async def confirm_reserve(self, data: OrderRequest, try_result: InventoryReservation):
            """Confirm inventory reservation."""
            print(f"✅ [Inventory] CONFIRM: Committing reservation {try_result.reservation_id}")
            return {"committed": True}

        @cancel_method
        async def cancel_reserve(self, data: OrderRequest, try_result: InventoryReservation):
            """Cancel inventory reservation."""
            print(f"🔄 [Inventory] CANCEL: Releasing {try_result.reservation_id}")
            return {"released": True}

    @tcc_participant("payment-service", order=2)
    class PaymentService:
        """Payment processing service."""

        @try_method
        async def try_charge(self, data: OrderRequest) -> PaymentAuthorization:
            """Try to authorize payment."""
            print(f"💳 [Payment] TRY: Authorizing ${data.amount}")
            auth_code = f"AUTH-{data.order_id}"
            return PaymentAuthorization(authorized=True, auth_code=auth_code)

        @confirm_method
        async def confirm_charge(self, data: OrderRequest, try_result: PaymentAuthorization):
            """Confirm payment charge."""
            print(f"✅ [Payment] CONFIRM: Capturing payment {try_result.auth_code}")
            return {"captured": True}

        @cancel_method
        async def cancel_charge(self, data: OrderRequest, try_result: PaymentAuthorization):
            """Cancel payment authorization."""
            print(f"🔄 [Payment] CANCEL: Voiding auth {try_result.auth_code}")
            return {"voided": True}

    @tcc_participant("shipping-service", order=3)
    class ShippingService:
        """Shipping service."""

        @try_method
        async def try_schedule(self, data: OrderRequest) -> ShippingSchedule:
            """Try to schedule shipping."""
            print(f"🚚 [Shipping] TRY: Scheduling shipment for {data.order_id}")
            return ShippingSchedule(scheduled=True, tracking="TRK-001")

        @confirm_method
        async def confirm_schedule(self, data: OrderRequest, try_result: ShippingSchedule):
            """Confirm shipping schedule."""
            print(f"✅ [Shipping] CONFIRM: Creating label {try_result.tracking}")
            return {"label_created": True}

        @cancel_method
        async def cancel_schedule(self, data: OrderRequest, try_result: ShippingSchedule):
            """Cancel shipping schedule."""
            print(f"🔄 [Shipping] CANCEL: Cancelling shipment {try_result.tracking}")
            return {"cancelled": True}
'''

    def _example_tcc_multi_participant(self):
        """Show TCC with multiple participants."""
        self.formatter.print_header("📖 Example 6: TCC with Multiple Participants")

        code = self._get_tcc_multi_participant_code() + '''
# Multi-participant TCC coordinates across distributed services
# All participants must succeed in Try phase before Confirm
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Multi-Participant TCC[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Multiple participants = multiple services\n"
            "  • All Try methods must succeed\n"
            "  • If any Try fails, all Cancel methods run\n"
            "  • If all Try succeed, all Confirm methods run\n"
            "  • Use TccContext to share data between participants\n"
            "  • Perfect for distributed transactions\n\n"
            "💾 To load this example: load_example(6)",
            title="Tips",
            style="yellow"
        )
    
    def _get_context_advanced_code(self):
        """Get advanced context variables example code."""
        return '''from fireflytx import saga, saga_step, SagaContext

@saga("advanced-context")
class AdvancedContextSaga:
    """Advanced context variable patterns."""

    @saga_step("initialize")
    async def initialize_session(self, data: dict, context: SagaContext):
        """Initialize session with multiple context variables."""
        session_id = data.get('session_id', 'unknown')
        print(f"🔧 Initializing session: {session_id}")

        # Store multiple variables
        context.set_variable("session_id", session_id)
        context.set_variable("user_tier", "premium")
        context.set_variable("discount_rate", 0.15)
        context.set_variable("max_items", 10)

        # Also use headers for metadata
        context.put_header("trace_id", f"trace-{session_id}")
        context.put_header("region", "us-west-2")

        return {"initialized": True}

    @saga_step("calculate-price", depends_on=["initialize"])
    async def calculate_price(self, data: dict, context: SagaContext):
        """Calculate price using context variables."""
        discount_rate = context.get_variable("discount_rate")
        user_tier = context.get_variable("user_tier")

        base_price = 100.0
        final_price = base_price * (1 - discount_rate)

        print(f"💰 Price calculation: ${base_price} -> ${final_price} ({user_tier} tier)")

        context.set_variable("final_price", final_price)
        return {"price": final_price}

    @saga_step("apply-limits", depends_on=["calculate-price"])
    async def apply_limits(self, data: dict, context: SagaContext):
        """Apply limits based on context."""
        max_items = context.get_variable("max_items")
        final_price = context.get_variable("final_price")
        trace_id = context.get_header("trace_id")

        print(f"🎯 Applying limits: max {max_items} items (trace: {trace_id})")
        print(f"   Final price: ${final_price}")

        return {"limits_applied": True}
'''

    def _example_context_advanced(self):
        """Show advanced context variables example."""
        self.formatter.print_header("📖 Example 7: Advanced Context Variables")

        code = self._get_context_advanced_code() + '''
# Advanced patterns: multiple variables, headers, complex data flow
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Advanced Context[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Store multiple related variables\n"
            "  • Use headers for metadata (trace IDs, regions)\n"
            "  • Variables persist across all steps\n"
            "  • Perfect for complex business logic\n"
            "  • Type-safe with proper hints\n\n"
            "💾 To load this example: load_example(7)",
            title="Tips",
            style="yellow"
        )

    def _get_error_handling_code(self):
        """Get error handling and retry example code."""
        return '''from fireflytx import saga, saga_step, compensation_step

@saga("robust-processing")
class RobustSaga:
    """Demonstrate robust error handling and retry patterns."""

    @saga_step("validate", retry=5, timeout_ms=3000, backoff_ms=1000)
    async def validate_with_retry(self, data: dict):
        """Validate with automatic retry on failure."""
        print(f"🔍 Validating (will retry up to 5 times)...")

        # Simulate transient failures
        import random
        if random.random() < 0.6:  # 60% failure rate
            raise Exception("Transient validation error - will retry")

        print("✅ Validation succeeded!")
        return {"validated": True}

    @saga_step("process", depends_on=["validate"], retry=3, timeout_ms=10000,
               compensate="rollback_process")
    async def process_with_timeout(self, data: dict):
        """Process with timeout and compensation."""
        print(f"⚙️ Processing (timeout: 10s, retry: 3)...")

        # Simulate processing
        import asyncio
        await asyncio.sleep(0.1)

        return {"processed": True, "process_id": "PROC-001"}

    @compensation_step("process")
    async def rollback_process(self, result: dict):
        """Rollback processing on failure."""
        process_id = result.get('process_id', 'unknown')
        print(f"🔄 Rolling back process: {process_id}")
        return {"rolled_back": True}

    @saga_step("finalize", depends_on=["process"], retry=2,
               compensation_critical=True)
    async def finalize_critical(self, data: dict):
        """Critical finalization step."""
        print(f"🎯 Finalizing (critical step)...")
        return {"finalized": True}
'''

    def _example_error_handling(self):
        """Show error handling example."""
        self.formatter.print_header("📖 Example 8: Error Handling & Retry")

        code = self._get_error_handling_code() + '''
# Robust error handling with retry, timeout, and compensation
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Error Handling[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Use retry parameter for automatic retries\n"
            "  • Set timeout_ms to prevent hanging\n"
            "  • backoff_ms adds delay between retries\n"
            "  • compensation_critical ensures rollback\n"
            "  • Perfect for unreliable external services\n\n"
            "💾 To load this example: load_example(8)",
            title="Tips",
            style="yellow"
        )

    def _get_parallel_execution_code(self):
        """Get parallel execution example code."""
        return '''from fireflytx import saga, saga_step, SagaContext

@saga("parallel-batch", layer_concurrency=5)
class ParallelSaga:
    """Demonstrate parallel execution for performance."""

    @saga_step("init-batch")
    async def initialize_batch(self, data: dict, context: SagaContext):
        """Initialize batch processing."""
        batch_id = data.get('batch_id', 'unknown')
        print(f"📋 Initializing batch: {batch_id}")
        context.set_variable("batch_id", batch_id)
        return {"initialized": True}

    # These 5 steps run in PARALLEL (layer_concurrency=5)
    @saga_step("process-1", depends_on=["init-batch"])
    async def process_item_1(self, data: dict):
        """Process item 1 in parallel."""
        print("⚡ Processing item 1...")
        return {"item": 1, "status": "done"}

    @saga_step("process-2", depends_on=["init-batch"])
    async def process_item_2(self, data: dict):
        """Process item 2 in parallel."""
        print("⚡ Processing item 2...")
        return {"item": 2, "status": "done"}

    @saga_step("process-3", depends_on=["init-batch"])
    async def process_item_3(self, data: dict):
        """Process item 3 in parallel."""
        print("⚡ Processing item 3...")
        return {"item": 3, "status": "done"}

    @saga_step("process-4", depends_on=["init-batch"])
    async def process_item_4(self, data: dict):
        """Process item 4 in parallel."""
        print("⚡ Processing item 4...")
        return {"item": 4, "status": "done"}

    @saga_step("process-5", depends_on=["init-batch"])
    async def process_item_5(self, data: dict):
        """Process item 5 in parallel."""
        print("⚡ Processing item 5...")
        return {"item": 5, "status": "done"}

    # This step waits for ALL parallel steps
    @saga_step("aggregate", depends_on=["process-1", "process-2", "process-3",
                                         "process-4", "process-5"])
    async def aggregate_results(self, data: dict, context: SagaContext):
        """Aggregate all parallel results."""
        batch_id = context.get_variable("batch_id")
        print(f"📊 Aggregating results for batch: {batch_id}")
        return {"total_processed": 5, "batch_complete": True}
'''

    def _example_parallel_execution(self):
        """Show parallel execution example."""
        self.formatter.print_header("📖 Example 9: Parallel Execution")

        code = self._get_parallel_execution_code() + '''
# Parallel execution dramatically improves performance
# Use layer_concurrency to control parallelism
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Parallel Execution[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Steps with same dependencies run in parallel\n"
            "  • layer_concurrency controls max parallelism\n"
            "  • Perfect for batch processing\n"
            "  • Dramatically improves throughput\n"
            "  • Automatic synchronization at join points\n\n"
            "💾 To load this example: load_example(9)",
            title="Tips",
            style="yellow"
        )

    def _example_event_publishing(self):
        """Show event publishing example."""
        self.formatter.print_header("📖 Example 10: Event Publishing")

        code = '''from fireflytx import saga, saga_step, SagaEngine
from fireflytx.events import KafkaStepEventPublisher

# Configure event publishing
event_publisher = KafkaStepEventPublisher(
    bootstrap_servers="localhost:9092",
    topic="saga-events"
)

engine = SagaEngine(event_publisher=event_publisher)

# Your SAGA will now publish events for:
# - Step started
# - Step completed
# - Step failed
# - Compensation triggered
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Event Publishing[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Publish events to Kafka, Redis, or custom\n"
            "  • Track SAGA execution in real-time\n"
            "  • Build event-driven architectures\n"
            "  • Integrate with monitoring systems\n"
            "  • Requires external Kafka/Redis setup\n\n"
            "📚 See documentation for full setup",
            title="Tips",
            style="yellow"
        )

    def _example_persistence(self):
        """Show persistence example."""
        self.formatter.print_header("📖 Example 11: Persistence & Recovery")

        code = '''from fireflytx import saga, saga_step, SagaEngine
from fireflytx.persistence import RedisPersistenceProvider

# Configure persistence
persistence = RedisPersistenceProvider(
    host="localhost",
    port=6379,
    db=0
)

engine = SagaEngine(
    persistence_provider=persistence,
    persistence_enabled=True
)

# SAGA state is now persisted:
# - Recover from crashes
# - Resume failed SAGAs
# - Audit trail
# - Debugging support
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Persistence[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Persist SAGA state to Redis or custom\n"
            "  • Automatic crash recovery\n"
            "  • Resume failed transactions\n"
            "  • Complete audit trail\n"
            "  • Requires external Redis setup\n\n"
            "📚 See documentation for full setup",
            title="Tips",
            style="yellow"
        )
    
    def _get_benchmarking_code(self):
        """Get benchmarking example code."""
        return '''# Benchmarking is built into the shell
# Use the benchmark() function to test performance

# Example usage:
# await benchmark(PaymentSaga, {"order_id": "ORD-001", "amount": 99.99}, iterations=100)
'''

    def _example_benchmarking(self):
        """Show benchmarking example."""
        self.formatter.print_header("📖 Example 12: Benchmarking & Performance Testing")

        code = '''# Benchmark your SAGA or TCC workflows
await benchmark(PaymentSaga, {
    "order_id": "ORD-001",
    "amount": 99.99
}, iterations=100)

# Output shows:
# ┌─────────────────────────────────────┐
# │ Benchmark Results                   │
# ├─────────────────────────────────────┤
# │ Total runs:        100              │
# │ Successful:        98               │
# │ Failed:            2                │
# │ Success rate:      98.0%            │
# │                                     │
# │ Avg time:          45.2ms           │
# │ Min time:          32.1ms           │
# │ Max time:          89.5ms           │
# │ Throughput:        22.1 ops/sec     │
# └─────────────────────────────────────┘

# Advanced benchmarking
await benchmark(
    ComplexOrderSaga,
    {"order_id": "ORD-001"},
    iterations=1000,
    warmup=10,  # Warmup runs
    concurrent=5  # Concurrent executions
)
'''

        syntax = Syntax(code, "python", theme="solarized-dark", line_numbers=True)
        panel = Panel(syntax, title="[bold cyan]Benchmarking[/bold cyan]", border_style="cyan")
        self.formatter.console.print(panel)

        self.formatter.print_panel(
            "💡 Key Points:\n"
            "  • Test performance under load\n"
            "  • Identify bottlenecks\n"
            "  • Measure throughput and latency\n"
            "  • Compare different implementations\n"
            "  • Built-in statistical analysis\n\n"
            "💾 To load this example: load_example(12)",
            title="Tips",
            style="yellow"
        )
    
    async def quick_start(self):
        """Interactive quick start tutorial."""
        self.formatter.print_header("🚀 FireflyTX Quick Start Tutorial")

        self.formatter.print_panel(
            "Welcome to FireflyTX - Battle-Tested Distributed Transactions!\n\n"
            "This tutorial will guide you through:\n"
            "  1. Initializing engines (SAGA & TCC)\n"
            "  2. Loading and running examples\n"
            "  3. Understanding key patterns\n"
            "  4. Testing and benchmarking\n\n"
            "Let's get started! 🔥",
            title="Welcome",
            style="cyan"
        )

        # Step 1: Initialize engines
        self.formatter.print_info("\n📍 Step 1: Initialize Engines")
        self.formatter.print_info("Run: await init_engines()")

        if not self.shell.session.saga_engine:
            self.formatter.print_warning("⚠️  Engines not initialized. Please run: await init_engines()")
            return

        self.formatter.print_success("✅ Engines initialized!")

        # Step 2: Show available examples
        self.formatter.print_info("\n📍 Step 2: Explore Examples")
        self.formatter.print_info("We have 12 battle-tested examples covering:")
        self.formatter.print_info("  • Basic SAGA patterns (examples 1-4)")
        self.formatter.print_info("  • TCC patterns (examples 5-6)")
        self.formatter.print_info("  • Advanced patterns (examples 7-9)")
        self.formatter.print_info("  • Integration patterns (examples 10-11)")
        self.formatter.print_info("  • Performance testing (example 12)")

        # Step 3: Quick example
        self.formatter.print_info("\n📍 Step 3: Try Your First SAGA")
        self.formatter.print_info("Load example 1:")
        self.formatter.print_info("  load_example(1)")
        self.formatter.print_info("\nThen execute it:")
        self.formatter.print_info("  result = await saga_engine.execute(PaymentSaga, {'order_id': 'ORD-001', 'amount': 99.99})")

        # Step 4: Next steps
        self.formatter.print_panel(
            "🎯 Next Steps:\n\n"
            "📚 View all examples:\n"
            "  • examples() - List all available examples\n"
            "  • example(N) - View example N with explanation\n"
            "  • load_example(N) - Load example N for execution\n\n"
            "🔍 Explore patterns:\n"
            "  • example(2) - Compensation & rollback\n"
            "  • example(3) - Context variables\n"
            "  • example(5) - TCC pattern\n"
            "  • example(8) - Error handling & retry\n\n"
            "⚡ Test performance:\n"
            "  • example(12) - Benchmarking\n"
            "  • await benchmark(YourSaga, inputs, iterations=100)\n\n"
            "💡 Get help:\n"
            "  • help() - Show all commands\n"
            "  • inspect_saga(YourSaga) - Inspect structure\n\n"
            "Happy coding! 🔥",
            title="Congratulations!",
            style="green"
        )

