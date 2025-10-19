"""
Integration tests for FireflyTX shell examples execution.

Tests that examples can actually be executed with real engines.
"""

import asyncio
import pytest
import pytest_asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fireflytx.engine.saga_engine import SagaEngine
from fireflytx.engine.tcc_engine import TccEngine
from fireflytx.shell.commands.examples import ExamplesLibrary
from fireflytx.shell.ui.formatter import ShellFormatter
from unittest.mock import Mock


class TestShellExamplesExecution:
    """Integration tests for executing shell examples with real engines."""

    @pytest_asyncio.fixture
    async def engines(self):
        """Create real engines for testing."""
        saga_engine = SagaEngine()
        tcc_engine = TccEngine()

        # Initialize engines
        await saga_engine.initialize()
        tcc_engine.start()

        yield saga_engine, tcc_engine

        # Cleanup
        await saga_engine.shutdown()
        tcc_engine.stop()

    @pytest.fixture
    def examples_lib(self):
        """Create ExamplesLibrary with mock shell."""
        shell = Mock()
        shell.formatter = ShellFormatter(use_rich=True)
        if not hasattr(shell.formatter, 'console'):
            shell.formatter.console = Mock()
        shell.session = Mock()
        shell.context = Mock()
        shell.context.get_namespace = Mock(return_value={})

        return ExamplesLibrary(shell)

    @pytest.mark.asyncio
    async def test_execute_basic_saga(self, engines, examples_lib, capsys):
        """Test executing example 1: Basic SAGA.

        Verifies:
        1. All steps execute successfully
        2. No compensation is triggered
        3. Business logic completes correctly
        """
        saga_engine, _ = engines

        # Load the example
        namespace = {}
        examples_lib.shell.context.get_namespace.return_value = namespace
        examples_lib.load_example(1)

        # Get the PaymentSaga class
        PaymentSaga = namespace.get('PaymentSaga')
        assert PaymentSaga is not None, "PaymentSaga not loaded"

        # Execute the SAGA
        result = await saga_engine.execute(PaymentSaga, {
            'order_id': 'ORD-TEST-001',
            'amount': 99.99
        })

        # Verify execution
        assert result is not None
        assert result.is_success, f"SAGA should succeed but got: {result}"

        # Capture output to verify business logic
        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Verify no compensation was triggered (successful execution)
        assert "compensation" not in output.lower() and "rollback" not in output.lower(), \
            "Compensation should not be triggered for successful SAGA"

    @pytest.mark.asyncio
    async def test_execute_saga_compensation(self, engines, examples_lib, capsys):
        """Test executing example 2: SAGA with Compensation.

        Verifies:
        1. reserve_inventory step executes successfully
        2. charge_payment step fails after retries
        3. release_inventory compensation is executed
        4. Compensation receives correct reservation_id from step result
        """
        saga_engine, _ = engines

        # Load the example
        namespace = {}
        examples_lib.shell.context.get_namespace.return_value = namespace
        examples_lib.load_example(2)

        # Get the OrderSaga class
        OrderSaga = namespace.get('OrderSaga')
        assert OrderSaga is not None, "OrderSaga not loaded"

        # Execute the SAGA (should fail and compensate)
        try:
            result = await saga_engine.execute(OrderSaga, {
                'order_id': 'ORD-TEST-002',
                'quantity': 5,
                'amount': 100.00
            })
            # The saga is designed to fail, so we expect compensation
            # Result status should indicate failure or compensation
            assert result is not None
        except Exception as e:
            # Expected to fail due to payment decline
            assert "Payment declined" in str(e) or "card expired" in str(e)

        # Capture output to verify business logic
        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Verify business behavior:
        # 1. Inventory was reserved
        assert "📦 Reserving 5 items" in output, "Inventory reservation not executed"
        assert "✅ Reserved: RES-ORD-TEST-002" in output, "Reservation ID not generated"

        # 2. Payment was attempted (with retries - should see 4 attempts: initial + 3 retries)
        payment_attempts = output.count("💳 Charging $100.0")
        assert payment_attempts == 4, f"Expected 4 payment attempts (1 + 3 retries), got {payment_attempts}"

        # 3. Compensation was executed with correct reservation_id
        assert "🔄 Releasing reservation RES-ORD-TEST-002" in output, \
            "Compensation not executed or received wrong reservation_id"

        # 4. Verify compensation received the step result, not 'unknown'
        assert "🔄 Releasing reservation unknown" not in output, \
            "Compensation received 'unknown' instead of actual reservation_id"

    @pytest.mark.asyncio
    async def test_execute_context_saga(self, engines, examples_lib):
        """Test executing example 3: SAGA with Context Variables."""
        saga_engine, _ = engines
        
        # Load the example
        namespace = {}
        examples_lib.shell.context.get_namespace.return_value = namespace
        examples_lib.load_example(3)
        
        # Get the ContextSaga class
        ContextSaga = namespace.get('ContextSaga')
        assert ContextSaga is not None, "ContextSaga not loaded"
        
        # Execute the SAGA
        result = await saga_engine.execute(ContextSaga, {
            'user_id': 'U123',
            'amount': 50.00
        })
        
        # Verify execution
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_dependencies_saga(self, engines, examples_lib):
        """Test executing example 4: SAGA with Dependencies."""
        saga_engine, _ = engines
        
        # Load the example
        namespace = {}
        examples_lib.shell.context.get_namespace.return_value = namespace
        examples_lib.load_example(4)
        
        # Get the ComplexOrderSaga class
        ComplexOrderSaga = namespace.get('ComplexOrderSaga')
        assert ComplexOrderSaga is not None, "ComplexOrderSaga not loaded"
        
        # Execute the SAGA
        result = await saga_engine.execute(ComplexOrderSaga, {
            'order_id': 'ORD-TEST-004'
        })
        
        # Verify execution
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_basic_tcc(self, engines, examples_lib, capsys):
        """Test executing example 5: Basic TCC.

        Verifies:
        1. TRY phase reserves resources
        2. CONFIRM phase commits the transaction
        3. Business logic executes correctly
        """
        _, tcc_engine = engines

        # Load the example
        namespace = {}
        examples_lib.shell.context.get_namespace.return_value = namespace
        examples_lib.load_example(5)

        # Get the MoneyTransferTcc class
        MoneyTransferTcc = namespace.get('MoneyTransferTcc')
        assert MoneyTransferTcc is not None, "MoneyTransferTcc not loaded"

        # Execute the TCC
        result = await tcc_engine.execute(MoneyTransferTcc, {
            'amount': 100.00
        })

        # Verify execution
        assert result is not None

        # Capture output to verify business logic
        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Verify TCC phases executed:
        # 1. TRY phase - resources reserved
        assert "TRY" in output or "try" in output.lower(), "TRY phase not executed"

        # 2. CONFIRM phase - transaction committed
        assert "CONFIRM" in output or "confirm" in output.lower(), "CONFIRM phase not executed"

    @pytest.mark.asyncio
    async def test_execute_tcc_multi_participant(self, engines, examples_lib):
        """Test executing example 6: TCC Multi-Participant."""
        _, tcc_engine = engines
        
        # Load the example
        namespace = {}
        examples_lib.shell.context.get_namespace.return_value = namespace
        examples_lib.load_example(6)
        
        # Get the DistributedTcc class
        DistributedTcc = namespace.get('DistributedTcc')
        assert DistributedTcc is not None, "DistributedTcc not loaded"
        
        # Execute the TCC
        result = await tcc_engine.execute(DistributedTcc, {
            'order_id': 'ORD-TEST-006',
            'amount': 250.00
        })
        
        # Verify execution
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_context_advanced(self, engines, examples_lib):
        """Test executing example 7: Advanced Context Variables."""
        saga_engine, _ = engines
        
        # Load the example
        namespace = {}
        examples_lib.shell.context.get_namespace.return_value = namespace
        examples_lib.load_example(7)
        
        # Get the AdvancedContextSaga class
        AdvancedContextSaga = namespace.get('AdvancedContextSaga')
        assert AdvancedContextSaga is not None, "AdvancedContextSaga not loaded"
        
        # Execute the SAGA
        result = await saga_engine.execute(AdvancedContextSaga, {
            'session_id': 'S123'
        })
        
        # Verify execution
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, engines, examples_lib):
        """Test executing example 8: Error Handling & Retry."""
        saga_engine, _ = engines
        
        # Load the example
        namespace = {}
        examples_lib.shell.context.get_namespace.return_value = namespace
        examples_lib.load_example(8)
        
        # Get the RobustSaga class
        RobustSaga = namespace.get('RobustSaga')
        assert RobustSaga is not None, "RobustSaga not loaded"
        
        # Execute the SAGA (may retry multiple times)
        result = await saga_engine.execute(RobustSaga, {
            'order_id': 'ORD-TEST-008'
        })
        
        # Verify execution (should eventually succeed with retries)
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_parallel_execution(self, engines, examples_lib):
        """Test executing example 9: Parallel Execution."""
        saga_engine, _ = engines
        
        # Load the example
        namespace = {}
        examples_lib.shell.context.get_namespace.return_value = namespace
        examples_lib.load_example(9)
        
        # Get the ParallelSaga class
        ParallelSaga = namespace.get('ParallelSaga')
        assert ParallelSaga is not None, "ParallelSaga not loaded"
        
        # Execute the SAGA
        result = await saga_engine.execute(ParallelSaga, {
            'batch_id': 'B001'
        })
        
        # Verify execution
        assert result is not None

    @pytest.mark.asyncio
    async def test_tcc_cancel_behavior(self, engines):
        """Test TCC CANCEL phase is executed when TRY phase fails.

        Verifies:
        1. First participant TRY succeeds
        2. Second participant TRY fails
        3. TCC transaction fails (does not succeed)
        4. CANCEL is triggered (verified by TCC failure)

        Note: We cannot easily verify CANCEL execution details because output
        from TCC callbacks happens in Java subprocess. The test verifies that
        the TCC fails as expected, which implicitly tests CANCEL behavior.
        """
        _, tcc_engine = engines

        # Create a TCC that will fail in the second participant
        from fireflytx import tcc, tcc_participant, try_method, confirm_method, cancel_method

        # Track execution for verification
        execution_log = []

        @tcc("test-cancel-tcc")
        class CancelTestTcc:
            """TCC designed to test CANCEL behavior."""

            @tcc_participant("participant-1", order=1)
            class Participant1:
                @try_method
                async def try_action(self, data: dict):
                    execution_log.append("P1_TRY")
                    return {"reserved": True, "reservation_id": "RES-001"}

                @confirm_method
                async def confirm_action(self, data: dict, try_result: dict):
                    execution_log.append(f"P1_CONFIRM_{try_result.get('reservation_id')}")
                    return {"confirmed": True}

                @cancel_method
                async def cancel_action(self, data: dict, try_result: dict):
                    res_id = try_result.get('reservation_id', 'unknown')
                    execution_log.append(f"P1_CANCEL_{res_id}")
                    return {"cancelled": True}

            @tcc_participant("participant-2", order=2)
            class Participant2:
                @try_method
                async def try_action(self, data: dict):
                    execution_log.append("P2_TRY_FAIL")
                    raise Exception("Participant 2 TRY failed - triggering CANCEL")

                @confirm_method
                async def confirm_action(self, data: dict, try_result: dict):
                    execution_log.append("P2_CONFIRM")
                    return {"confirmed": True}

                @cancel_method
                async def cancel_action(self, data: dict, try_result: dict):
                    execution_log.append("P2_CANCEL")
                    return {"cancelled": True}

        # Execute the TCC (should fail and trigger CANCEL)
        try:
            result = await tcc_engine.execute(CancelTestTcc, {'test': 'cancel'})
            # Should fail
            assert False, "TCC should have failed but succeeded"
        except Exception as e:
            # Expected to fail
            assert "failed" in str(e).lower(), f"Expected failure message, got: {e}"

        # Verify execution order:
        # 1. Participant 1 TRY should have executed
        assert "P1_TRY" in execution_log, f"Participant 1 TRY not executed. Log: {execution_log}"

        # 2. Participant 2 TRY should have failed
        assert "P2_TRY_FAIL" in execution_log, f"Participant 2 TRY not executed. Log: {execution_log}"

        # 3. Participant 1 CANCEL should have been called with correct reservation_id
        assert "P1_CANCEL_RES-001" in execution_log, \
            f"Participant 1 CANCEL not executed or received wrong reservation_id. Log: {execution_log}"

        # 4. Verify CANCEL received the try_result, not 'unknown'
        assert "P1_CANCEL_unknown" not in execution_log, \
            f"CANCEL received 'unknown' instead of actual reservation_id. Log: {execution_log}"

        # 5. CONFIRM should NOT be called since TRY failed
        assert "P1_CONFIRM" not in execution_log and "P2_CONFIRM" not in execution_log, \
            f"CONFIRM should not be called when TRY fails. Log: {execution_log}"

    def test_all_loadable_examples_have_execution_tests(self, examples_lib):
        """Verify all loadable examples have execution tests."""
        loadable_examples = [1, 2, 3, 4, 5, 6, 7, 8, 9]

        # Get all test methods
        test_methods = [
            method for method in dir(self)
            if method.startswith('test_execute_')
        ]

        # Should have at least one test per loadable example
        assert len(test_methods) >= len(loadable_examples), \
            f"Missing execution tests. Have {len(test_methods)}, need {len(loadable_examples)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

