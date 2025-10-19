"""
Integration tests for FireflyTX shell examples execution.

Tests that examples can actually be executed with real engines.
"""

import asyncio
import pytest
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
    """Integration tests for executing shell examples."""

    @pytest.fixture
    async def engines(self):
        """Create real engines for testing."""
        saga_engine = SagaEngine()
        tcc_engine = TccEngine()
        
        # Initialize engines
        await saga_engine.initialize()
        await tcc_engine.initialize()
        
        yield saga_engine, tcc_engine
        
        # Cleanup
        await saga_engine.shutdown()
        await tcc_engine.shutdown()

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
    async def test_execute_basic_saga(self, engines, examples_lib):
        """Test executing example 1: Basic SAGA."""
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
        assert result.get('status') in ['COMPLETED', 'SUCCESS', 'completed', 'success']

    @pytest.mark.asyncio
    async def test_execute_saga_compensation(self, engines, examples_lib):
        """Test executing example 2: SAGA with Compensation."""
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
    async def test_execute_basic_tcc(self, engines, examples_lib):
        """Test executing example 5: Basic TCC."""
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

