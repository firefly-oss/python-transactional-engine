#!/usr/bin/env python3
"""
Unit tests for SAGA and TCC decorators.
"""

"""
Copyright (c) 2025 Firefly Software Solutions Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import pytest
import asyncio
from typing import Any
from pydantic import BaseModel

from fireflytx.decorators.saga import (
    saga,
    saga_step,
    compensation_step,
    get_saga_config,
    get_step_config,
    is_saga_class,
    is_saga_step,
    is_compensation_step,
)
from fireflytx.decorators.tcc import (
    tcc,
    tcc_participant,
    try_method,
    confirm_method,
    cancel_method,
    get_tcc_config,
    get_participant_config,
    get_tcc_method_config,
    is_tcc_class,
    is_tcc_participant,
    is_try_method,
    is_confirm_method,
    is_cancel_method,
)


class SampleData(BaseModel):
    id: str
    value: float


class TestSagaDecorators:
    """Test SAGA decorators functionality."""

    def test_saga_decorator(self):
        """Test @saga decorator."""

        @saga("test-saga", layer_concurrency=3)
        class TestSaga:
            pass

        assert is_saga_class(TestSaga)
        assert TestSaga._saga_name == "test-saga"

        config = get_saga_config(TestSaga)
        assert config is not None
        assert config.name == "test-saga"
        assert config.layer_concurrency == 3

    def test_saga_step_decorator(self):
        """Test @saga_step decorator."""

        @saga_step("test-step", depends_on=["dep1", "dep2"], retry=5, timeout_ms=10000)
        async def test_step(self, data: SampleData) -> SampleData:
            return data

        assert is_saga_step(test_step)

        config = get_step_config(test_step)
        assert config is not None
        assert config.step_id == "test-step"
        assert config.depends_on == ["dep1", "dep2"]
        assert config.retry == 5
        assert config.timeout_ms == 10000

    def test_compensation_step_decorator(self):
        """Test @compensation_step decorator."""

        @compensation_step("test-step")
        async def compensate_test(self, data: SampleData) -> None:
            pass

        assert is_compensation_step(compensate_test)
        assert compensate_test._compensation_for_step == "test-step"

    def test_complete_saga_class(self):
        """Test complete SAGA class with multiple decorators."""

        @saga("order-processing")
        class OrderSaga:

            @saga_step("validate", retry=3)
            async def validate_order(self, order: SampleData) -> SampleData:
                return SampleData(id=f"validated-{order.id}", value=order.value)

            @saga_step("process", depends_on=["validate"], compensate="undo_process")
            async def process_order(self, order: SampleData) -> SampleData:
                return SampleData(id=f"processed-{order.id}", value=order.value * 2)

            @compensation_step("process")
            async def undo_process(self, result: SampleData) -> None:
                pass

        assert is_saga_class(OrderSaga)
        config = get_saga_config(OrderSaga)
        assert len(config.steps) == 2
        assert "validate" in config.steps
        assert "process" in config.steps
        assert config.compensation_methods["process"] == "undo_process"

    @pytest.mark.asyncio
    async def test_saga_step_execution(self):
        """Test SAGA step execution wrapper."""
        call_count = 0

        @saga_step("counter-step")
        async def increment_counter(self) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        # Test that the wrapper preserves functionality
        result = await increment_counter(None)
        assert result == 1
        assert call_count == 1


class TestTccDecorators:
    """Test TCC decorators functionality."""

    def test_tcc_decorator(self):
        """Test @tcc decorator."""

        @tcc("test-tcc", timeout_ms=60000)
        class TestTcc:
            pass

        assert is_tcc_class(TestTcc)
        assert TestTcc._tcc_name == "test-tcc"

        config = get_tcc_config(TestTcc)
        assert config is not None
        assert config.name == "test-tcc"
        assert config.timeout_ms == 60000

    def test_tcc_participant_decorator(self):
        """Test @tcc_participant decorator."""

        @tcc_participant("test-participant", order=2)
        class TestParticipant:
            pass

        assert is_tcc_participant(TestParticipant)

        config = get_participant_config(TestParticipant)
        assert config is not None
        assert config.participant_id == "test-participant"
        assert config.order == 2

    def test_tcc_method_decorators(self):
        """Test TCC method decorators."""

        @try_method(timeout_ms=5000, retry=2)
        async def try_reserve(self, data: SampleData) -> SampleData:
            return data

        @confirm_method(timeout_ms=3000)
        async def confirm_reserve(self, data: SampleData) -> None:
            pass

        @cancel_method(retry=5)
        async def cancel_reserve(self, data: SampleData) -> None:
            pass

        assert is_try_method(try_reserve)
        assert is_confirm_method(confirm_reserve)
        assert is_cancel_method(cancel_reserve)

        try_config = get_tcc_method_config(try_reserve)
        assert try_config.method_type == "try"
        assert try_config.timeout_ms == 5000
        assert try_config.retry == 2

        confirm_config = get_tcc_method_config(confirm_reserve)
        assert confirm_config.method_type == "confirm"
        assert confirm_config.timeout_ms == 3000

        cancel_config = get_tcc_method_config(cancel_reserve)
        assert cancel_config.method_type == "cancel"
        assert cancel_config.retry == 5

    def test_complete_tcc_class(self):
        """Test complete TCC class with participants and methods."""

        @tcc("payment-processing")
        class PaymentTcc:

            @tcc_participant("payment", order=1)
            class PaymentParticipant:

                @try_method
                async def reserve_payment(self, amount: float) -> str:
                    return f"reservation-{amount}"

                @confirm_method
                async def confirm_payment(self, reservation: str) -> None:
                    pass

                @cancel_method
                async def cancel_payment(self, reservation: str) -> None:
                    pass

            @tcc_participant("inventory", order=2)
            class InventoryParticipant:

                @try_method
                async def reserve_inventory(self, quantity: int) -> str:
                    return f"inv-{quantity}"

                @confirm_method
                async def confirm_inventory(self, reservation: str) -> None:
                    pass

                @cancel_method
                async def cancel_inventory(self, reservation: str) -> None:
                    pass

        assert is_tcc_class(PaymentTcc)
        config = get_tcc_config(PaymentTcc)
        assert len(config.participants) == 2
        assert "payment" in config.participants
        assert "inventory" in config.participants

        payment_config = config.participants["payment"]
        assert payment_config.order == 1
        assert payment_config.try_method == "reserve_payment"
        assert payment_config.confirm_method == "confirm_payment"
        assert payment_config.cancel_method == "cancel_payment"

    @pytest.mark.asyncio
    async def test_tcc_method_execution(self):
        """Test TCC method execution wrappers."""
        results = []

        @try_method
        async def try_operation(self, value: str) -> str:
            results.append(f"try-{value}")
            return f"result-{value}"

        @confirm_method
        async def confirm_operation(self, result: str) -> None:
            results.append(f"confirm-{result}")

        @cancel_method
        async def cancel_operation(self, result: str) -> None:
            results.append(f"cancel-{result}")

        # Test try method
        result = await try_operation(None, "test")
        assert result == "result-test"
        assert "try-test" in results

        # Test confirm method
        await confirm_operation(None, result)
        assert "confirm-result-test" in results

        # Test cancel method
        await cancel_operation(None, result)
        assert "cancel-result-test" in results


class TestDecoratorIntegration:
    """Test integration between decorators."""

    def test_non_decorated_classes(self):
        """Test that non-decorated classes return False for is_* checks."""

        class RegularClass:
            def regular_method(self):
                pass

        assert not is_saga_class(RegularClass)
        assert not is_tcc_class(RegularClass)
        assert not is_saga_step(RegularClass.regular_method)
        assert not is_try_method(RegularClass.regular_method)

    def test_mixed_decorators_error_handling(self):
        """Test that mixed decorators don't interfere."""

        @saga("test-saga")
        class SagaClass:

            @saga_step("step1")
            async def saga_method(self):
                pass

        @tcc("test-tcc")
        class TccClass:

            @tcc_participant("part1")
            class Participant:

                @try_method
                async def tcc_method(self):
                    pass

        # Verify they don't interfere
        assert is_saga_class(SagaClass)
        assert not is_tcc_class(SagaClass)
        assert is_tcc_class(TccClass)
        assert not is_saga_class(TccClass)

        assert is_saga_step(SagaClass.saga_method)
        assert not is_try_method(SagaClass.saga_method)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
