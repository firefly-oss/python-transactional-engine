"""
Test suite for FireflyTX shell examples.

Validates that all shell examples can be loaded and executed correctly.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock

from fireflytx.shell.commands.examples import ExamplesLibrary
from fireflytx.shell.core.shell import FireflyTXShell
from fireflytx.shell.ui.formatter import ShellFormatter
from fireflytx.engine.saga_engine import SagaEngine
from fireflytx.engine.tcc_engine import TccEngine


class TestShellExamples:
    """Test shell examples functionality."""

    @pytest.fixture
    def mock_shell(self):
        """Create a mock shell for testing."""
        shell = Mock(spec=FireflyTXShell)

        # Create formatter with console attribute
        formatter = ShellFormatter(use_rich=True)
        # Add a mock console if rich is not available
        if not hasattr(formatter, 'console'):
            formatter.console = Mock()
        shell.formatter = formatter

        shell.session = Mock()
        shell.session.saga_engine = None
        shell.session.tcc_engine = None

        # Create a mock namespace for exec
        shell.context = Mock()
        shell.context.get_namespace = Mock(return_value={})

        return shell

    @pytest.fixture
    def examples_lib(self, mock_shell):
        """Create ExamplesLibrary instance."""
        return ExamplesLibrary(mock_shell)

    def test_show_all_examples(self, examples_lib, capsys):
        """Test that show_all_examples displays all 12 examples."""
        examples_lib.show_all_examples()
        
        # Verify output contains all examples
        captured = capsys.readouterr()
        output = captured.out
        
        # Check for example numbers
        for i in range(1, 13):
            assert str(i) in output or f"Example {i}" in str(examples_lib.show_all_examples)

    def test_show_example_valid(self, examples_lib):
        """Test showing valid examples."""
        # Test each example number
        for i in range(1, 13):
            try:
                examples_lib.show_example(i)
                # If no exception, test passed
                assert True
            except Exception as e:
                pytest.fail(f"Example {i} failed to display: {e}")

    def test_show_example_invalid(self, examples_lib):
        """Test showing invalid example number."""
        # Should handle gracefully
        examples_lib.show_example(999)
        # No exception should be raised

    def test_load_example_basic_saga(self, examples_lib, mock_shell):
        """Test loading example 1: Basic SAGA."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(1)
        
        # Verify PaymentSaga class was loaded
        assert 'PaymentSaga' in namespace
        assert hasattr(namespace['PaymentSaga'], 'validate_payment')
        assert hasattr(namespace['PaymentSaga'], 'charge_card')
        assert hasattr(namespace['PaymentSaga'], 'confirm_order')

    def test_load_example_saga_compensation(self, examples_lib, mock_shell):
        """Test loading example 2: SAGA with Compensation."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(2)
        
        # Verify OrderSaga class was loaded
        assert 'OrderSaga' in namespace
        assert hasattr(namespace['OrderSaga'], 'reserve_inventory')
        assert hasattr(namespace['OrderSaga'], 'release_inventory')
        assert hasattr(namespace['OrderSaga'], 'charge_payment')
        assert hasattr(namespace['OrderSaga'], 'refund_payment')

    def test_load_example_context_variables(self, examples_lib, mock_shell):
        """Test loading example 3: SAGA with Context Variables."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(3)
        
        # Verify ContextSaga class was loaded
        assert 'ContextSaga' in namespace
        assert hasattr(namespace['ContextSaga'], 'create_user')
        assert hasattr(namespace['ContextSaga'], 'create_wallet')
        assert hasattr(namespace['ContextSaga'], 'fund_wallet')

    def test_load_example_dependencies(self, examples_lib, mock_shell):
        """Test loading example 4: SAGA with Dependencies."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(4)
        
        # Verify ComplexOrderSaga class was loaded
        assert 'ComplexOrderSaga' in namespace
        assert hasattr(namespace['ComplexOrderSaga'], 'validate_order')
        assert hasattr(namespace['ComplexOrderSaga'], 'check_inventory')
        assert hasattr(namespace['ComplexOrderSaga'], 'check_credit')
        assert hasattr(namespace['ComplexOrderSaga'], 'calculate_shipping')
        assert hasattr(namespace['ComplexOrderSaga'], 'finalize_order')

    def test_load_example_basic_tcc(self, examples_lib, mock_shell):
        """Test loading example 5: Basic TCC."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(5)
        
        # Verify MoneyTransferTcc class was loaded
        assert 'MoneyTransferTcc' in namespace
        assert hasattr(namespace['MoneyTransferTcc'], 'AccountA')
        assert hasattr(namespace['MoneyTransferTcc'], 'AccountB')

    def test_load_example_tcc_multi_participant(self, examples_lib, mock_shell):
        """Test loading example 6: TCC Multi-Participant."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(6)
        
        # Verify DistributedTcc class was loaded
        assert 'DistributedTcc' in namespace
        assert hasattr(namespace['DistributedTcc'], 'InventoryService')
        assert hasattr(namespace['DistributedTcc'], 'PaymentService')
        assert hasattr(namespace['DistributedTcc'], 'ShippingService')

    def test_load_example_context_advanced(self, examples_lib, mock_shell):
        """Test loading example 7: Advanced Context Variables."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(7)
        
        # Verify AdvancedContextSaga class was loaded
        assert 'AdvancedContextSaga' in namespace
        assert hasattr(namespace['AdvancedContextSaga'], 'initialize_session')
        assert hasattr(namespace['AdvancedContextSaga'], 'calculate_price')
        assert hasattr(namespace['AdvancedContextSaga'], 'apply_limits')

    def test_load_example_error_handling(self, examples_lib, mock_shell):
        """Test loading example 8: Error Handling & Retry."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(8)
        
        # Verify RobustSaga class was loaded
        assert 'RobustSaga' in namespace
        assert hasattr(namespace['RobustSaga'], 'validate_with_retry')
        assert hasattr(namespace['RobustSaga'], 'process_with_timeout')
        assert hasattr(namespace['RobustSaga'], 'rollback_process')
        assert hasattr(namespace['RobustSaga'], 'finalize_critical')

    def test_load_example_parallel_execution(self, examples_lib, mock_shell):
        """Test loading example 9: Parallel Execution."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(9)
        
        # Verify ParallelSaga class was loaded
        assert 'ParallelSaga' in namespace
        assert hasattr(namespace['ParallelSaga'], 'initialize_batch')
        assert hasattr(namespace['ParallelSaga'], 'process_item_1')
        assert hasattr(namespace['ParallelSaga'], 'process_item_2')
        assert hasattr(namespace['ParallelSaga'], 'aggregate_results')

    def test_load_example_event_publishing(self, examples_lib, mock_shell):
        """Test loading example 10: Event Publishing (should fail gracefully)."""
        examples_lib.load_example(10)
        # Should not raise exception, just show message

    def test_load_example_persistence(self, examples_lib, mock_shell):
        """Test loading example 11: Persistence (should fail gracefully)."""
        examples_lib.load_example(11)
        # Should not raise exception, just show message

    def test_load_example_benchmarking(self, examples_lib, mock_shell):
        """Test loading example 12: Benchmarking."""
        namespace = {}
        mock_shell.context.get_namespace.return_value = namespace
        
        examples_lib.load_example(12)
        # Benchmarking example just shows usage, doesn't load classes

    def test_load_example_invalid(self, examples_lib, mock_shell):
        """Test loading invalid example number."""
        examples_lib.load_example(999)
        # Should handle gracefully without exception

    @pytest.mark.asyncio
    async def test_quick_start_without_engines(self, examples_lib, mock_shell):
        """Test quick_start when engines are not initialized."""
        mock_shell.session.saga_engine = None
        
        await examples_lib.quick_start()
        # Should show warning about engines not initialized

    @pytest.mark.asyncio
    async def test_quick_start_with_engines(self, examples_lib, mock_shell):
        """Test quick_start when engines are initialized."""
        mock_shell.session.saga_engine = Mock(spec=SagaEngine)
        mock_shell.session.tcc_engine = Mock(spec=TccEngine)
        
        await examples_lib.quick_start()
        # Should complete successfully

    def test_get_basic_saga_code(self, examples_lib):
        """Test that basic SAGA code is valid Python."""
        code = examples_lib._get_basic_saga_code()
        
        # Verify code contains expected elements
        assert 'PaymentSaga' in code
        assert '@saga' in code
        assert '@saga_step' in code
        assert 'validate_payment' in code
        assert 'charge_card' in code
        assert 'confirm_order' in code
        
        # Verify code can be compiled
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Basic SAGA code has syntax error: {e}")

    def test_get_saga_compensation_code(self, examples_lib):
        """Test that SAGA compensation code is valid Python."""
        code = examples_lib._get_saga_compensation_code()
        
        assert 'OrderSaga' in code
        assert '@compensation_step' in code
        assert 'reserve_inventory' in code
        assert 'release_inventory' in code
        
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"SAGA compensation code has syntax error: {e}")

    def test_get_basic_tcc_code(self, examples_lib):
        """Test that basic TCC code is valid Python."""
        code = examples_lib._get_basic_tcc_code()
        
        assert 'MoneyTransferTcc' in code
        assert '@tcc' in code
        assert '@tcc_participant' in code
        assert '@try_method' in code
        assert '@confirm_method' in code
        assert '@cancel_method' in code
        
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Basic TCC code has syntax error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

