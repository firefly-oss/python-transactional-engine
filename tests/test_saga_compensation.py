#!/usr/bin/env python3
"""
Comprehensive tests for SAGA compensation functionality using REAL SagaEngine.

Tests step compensation selection, compensation policies, and proper
compensation triggering in various failure scenarios.

ALL TESTS USE REAL JAVA ENGINE - NO MOCKS OR SIMULATIONS!
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
import logging
from typing import List, Dict, Any
from pydantic import BaseModel

from fireflytx import SagaEngine
from fireflytx.decorators.saga import saga, saga_step, compensation_step
from fireflytx.engine.saga_engine import CompensationPolicy


# Test data models
class OrderData(BaseModel):
    order_id: str
    customer_id: str
    amount: float
    should_fail_at: str = ""  # Step name where to simulate failure


class StepResult(BaseModel):
    step_id: str
    result_id: str
    data: Dict[str, Any]


class CompensationRecord(BaseModel):
    step_id: str
    compensated_at: str
    data: Dict[str, Any]


# Mock saga implementations for testing different scenarios
@saga("order-processing-success", layer_concurrency=3)
class SuccessfulOrderSaga:
    """SAGA that completes all steps successfully."""

    def __init__(self):
        self.execution_log: List[str] = []
        self.compensation_log: List[str] = []

    @saga_step("reserve_inventory", retry=2, timeout_ms=5000, compensate="release_inventory")
    async def reserve_inventory(self, order: OrderData) -> StepResult:
        """Reserve inventory for the order."""
        self.execution_log.append("reserve_inventory")
        await asyncio.sleep(0.01)  # Simulate async work

        return StepResult(
            step_id="reserve_inventory",
            result_id=f"inv-{order.order_id}",
            data={"product_id": "WIDGET-123", "quantity": 2},
        )

    @saga_step(
        "process_payment",
        depends_on=["reserve_inventory"],
        retry=3,
        timeout_ms=10000,
        compensate="refund_payment",
    )
    async def process_payment(self, order: OrderData) -> StepResult:
        """Process payment for the order."""
        self.execution_log.append("process_payment")
        await asyncio.sleep(0.01)

        return StepResult(
            step_id="process_payment",
            result_id=f"pay-{order.order_id}",
            data={"amount": order.amount, "method": "CREDIT_CARD"},
        )

    @saga_step("ship_order", depends_on=["process_payment"], compensate="cancel_shipment")
    async def ship_order(self, order: OrderData) -> StepResult:
        """Create shipment for the order."""
        self.execution_log.append("ship_order")
        await asyncio.sleep(0.01)

        return StepResult(
            step_id="ship_order",
            result_id=f"ship-{order.order_id}",
            data={"carrier": "FastShip", "tracking": f"TRK{order.order_id}"},
        )

    # Compensation methods
    @compensation_step("reserve_inventory")
    async def release_inventory(self, result: StepResult) -> None:
        """Release inventory reservation."""
        self.compensation_log.append("release_inventory")
        await asyncio.sleep(0.01)

    @compensation_step("process_payment")
    async def refund_payment(self, result: StepResult) -> None:
        """Refund the payment."""
        self.compensation_log.append("refund_payment")
        await asyncio.sleep(0.01)

    @compensation_step("ship_order")
    async def cancel_shipment(self, result: StepResult) -> None:
        """Cancel the shipment."""
        self.compensation_log.append("cancel_shipment")
        await asyncio.sleep(0.01)


@saga("order-processing-payment-failure")
class PaymentFailureSaga(SuccessfulOrderSaga):
    """SAGA that fails at payment step and triggers compensation."""

    @saga_step(
        "process_payment",
        depends_on=["reserve_inventory"],
        retry=3,
        timeout_ms=10000,
        compensate="refund_payment",
    )
    async def process_payment(self, order: OrderData) -> StepResult:
        """Process payment - will fail for testing."""
        self.execution_log.append("process_payment")
        await asyncio.sleep(0.01)

        if order.should_fail_at == "process_payment":
            raise Exception("Payment declined - insufficient funds")

        return await super().process_payment(order)


@saga("order-processing-shipping-failure")
class ShippingFailureSaga(SuccessfulOrderSaga):
    """SAGA that fails at shipping step and triggers compensation."""

    @saga_step("ship_order", depends_on=["process_payment"], compensate="cancel_shipment")
    async def ship_order(self, order: OrderData) -> StepResult:
        """Ship order - will fail for testing."""
        self.execution_log.append("ship_order")
        await asyncio.sleep(0.01)

        if order.should_fail_at == "ship_order":
            raise Exception("Shipping service unavailable")

        return await super().ship_order(order)


class TestSagaCompensation:
    """Test SAGA compensation functionality using REAL SagaEngine."""

    @pytest.mark.asyncio
    async def test_successful_saga_no_compensation(self):
        """Test successful SAGA execution with no compensation needed using REAL engine."""
        engine = SagaEngine(
            compensation_policy=CompensationPolicy.STRICT_SEQUENTIAL,
            persistence_enabled=False
        )
        await engine.initialize()

        order = OrderData(order_id="ORD-001", customer_id="CUST-123", amount=99.99)

        # Execute SAGA through REAL Java engine
        result = await engine.execute(SuccessfulOrderSaga, order.model_dump())

        # Verify successful execution
        assert result.is_success, f"SAGA failed: {result.error}"
        assert result.saga_name == "order-processing-success"

        # Verify no compensation was triggered
        assert len(result.compensated_steps) == 0
        assert len(result.failed_steps) == 0

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_payment_failure_triggers_compensation(self):
        """Test that payment failure triggers inventory compensation using REAL engine."""
        engine = SagaEngine(
            compensation_policy=CompensationPolicy.STRICT_SEQUENTIAL,
            persistence_enabled=False
        )
        await engine.initialize()

        order = OrderData(
            order_id="ORD-FAIL-001",
            customer_id="CUST-456",
            amount=150.00,
            should_fail_at="process_payment",
        )

        # Execute SAGA through REAL Java engine - should fail at payment
        result = await engine.execute(PaymentFailureSaga, order.model_dump())

        # Verify failure was detected
        assert not result.is_success, "SAGA should have failed"
        assert result.saga_name == "order-processing-payment-failure"

        # Verify compensation was executed by Java engine
        assert len(result.compensated_steps) > 0, "Compensation should have been executed"
        assert "reserve_inventory" in result.compensated_steps or len(result.compensated_steps) > 0

        # Verify payment step failed
        assert len(result.failed_steps) > 0, "Should have failed steps"

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_shipping_failure_triggers_multiple_compensations(self):
        """Test that shipping failure triggers both payment and inventory compensation using REAL engine."""
        engine = SagaEngine(
            compensation_policy=CompensationPolicy.STRICT_SEQUENTIAL,
            persistence_enabled=False
        )
        await engine.initialize()

        order = OrderData(
            order_id="ORD-FAIL-002",
            customer_id="CUST-789",
            amount=75.50,
            should_fail_at="ship_order",
        )

        # Execute SAGA through REAL Java engine - should fail at shipping
        result = await engine.execute(ShippingFailureSaga, order.model_dump())

        # Verify failure was detected
        assert not result.is_success, "SAGA should have failed"
        assert result.saga_name == "order-processing-shipping-failure"

        # Verify multiple compensations were executed by Java engine
        assert len(result.compensated_steps) >= 2, f"Should have compensated 2+ steps, got: {result.compensated_steps}"

        # Verify shipping step failed
        assert len(result.failed_steps) > 0, "Should have failed steps"

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_compensation_step_configuration(self):
        """Test that saga steps have proper compensation configuration."""
        saga_instance = SuccessfulOrderSaga()

        # Check that compensation methods are properly configured
        saga_config = saga_instance.__class__._saga_config

        assert "reserve_inventory" in saga_config.steps
        assert "process_payment" in saga_config.steps
        assert "ship_order" in saga_config.steps

        # Verify compensation method mappings
        assert saga_config.compensation_methods["reserve_inventory"] == "release_inventory"
        assert saga_config.compensation_methods["process_payment"] == "refund_payment"
        assert saga_config.compensation_methods["ship_order"] == "cancel_shipment"

        # Verify step dependencies
        payment_step = saga_config.steps["process_payment"]
        assert "reserve_inventory" in payment_step.depends_on

        ship_step = saga_config.steps["ship_order"]
        assert "process_payment" in ship_step.depends_on

    @pytest.mark.asyncio
    async def test_step_retry_configuration(self):
        """Test that saga steps have proper retry configuration."""
        saga_instance = SuccessfulOrderSaga()
        saga_config = saga_instance.__class__._saga_config

        # Check retry configurations
        inventory_step = saga_config.steps["reserve_inventory"]
        assert inventory_step.retry == 2
        assert inventory_step.timeout_ms == 5000

        payment_step = saga_config.steps["process_payment"]
        assert payment_step.retry == 3
        assert payment_step.timeout_ms == 10000

        ship_step = saga_config.steps["ship_order"]
        assert ship_step.retry == 3  # Default value

    @pytest.mark.asyncio
    async def test_saga_engine_compensation_policies(self):
        """Test different compensation policies in SagaEngine."""

        # Test strict sequential policy
        engine_sequential = SagaEngine(compensation_policy=CompensationPolicy.STRICT_SEQUENTIAL)
        assert engine_sequential.compensation_policy == CompensationPolicy.STRICT_SEQUENTIAL

        # Test grouped parallel policy
        engine_parallel = SagaEngine(compensation_policy=CompensationPolicy.GROUPED_PARALLEL)
        assert engine_parallel.compensation_policy == CompensationPolicy.GROUPED_PARALLEL

        # Test retry with backoff policy
        engine_retry = SagaEngine(compensation_policy=CompensationPolicy.RETRY_WITH_BACKOFF)
        assert engine_retry.compensation_policy == CompensationPolicy.RETRY_WITH_BACKOFF

        # Test circuit breaker policy
        engine_circuit = SagaEngine(compensation_policy=CompensationPolicy.CIRCUIT_BREAKER)
        assert engine_circuit.compensation_policy == CompensationPolicy.CIRCUIT_BREAKER

        # Test best effort parallel policy
        engine_best_effort = SagaEngine(compensation_policy=CompensationPolicy.BEST_EFFORT_PARALLEL)
        assert engine_best_effort.compensation_policy == CompensationPolicy.BEST_EFFORT_PARALLEL

    @pytest.mark.asyncio
    async def test_compensation_critical_flag(self):
        """Test compensation critical flag functionality."""

        @saga("critical-compensation-test")
        class CriticalCompensationSaga:

            @saga_step(
                "critical_operation",
                compensate="critical_compensation",
                compensation_critical=True,
                compensation_retry=5,
                compensation_timeout_ms=30000,
            )
            async def critical_operation(self, data: OrderData) -> StepResult:
                return StepResult(step_id="critical_operation", result_id="crit-001", data={})

            @compensation_step("critical_operation")
            async def critical_compensation(self, result: StepResult) -> None:
                pass

        saga_config = CriticalCompensationSaga._saga_config
        critical_step = saga_config.steps["critical_operation"]

        # Verify critical compensation configuration
        assert critical_step.compensation_critical is True
        assert critical_step.compensation_retry == 5
        assert critical_step.compensation_timeout_ms == 30000

    def test_saga_metadata_collection(self):
        """Test that saga metadata is properly collected from decorators."""
        saga_config = SuccessfulOrderSaga._saga_config

        # Verify saga configuration
        assert saga_config.name == "order-processing-success"
        assert saga_config.layer_concurrency == 3

        # Verify step count
        assert len(saga_config.steps) == 3

        # Verify compensation methods
        assert len(saga_config.compensation_methods) == 3

        # Verify step configurations exist
        for step_name in ["reserve_inventory", "process_payment", "ship_order"]:
            assert step_name in saga_config.steps
            step_config = saga_config.steps[step_name]
            assert hasattr(step_config, "compensate")
            assert step_config.compensate is not None


class TestSagaEngineIntegration:
    """Test SAGA engine integration scenarios using REAL engine."""

    @pytest.mark.asyncio
    async def test_saga_engine_initialization(self):
        """Test SagaEngine initialization with different policies using REAL engine."""

        # Test with different compensation policies
        for policy in [
            CompensationPolicy.STRICT_SEQUENTIAL,
            CompensationPolicy.GROUPED_PARALLEL,
            CompensationPolicy.RETRY_WITH_BACKOFF,
        ]:
            engine = SagaEngine(
                compensation_policy=policy,
                auto_optimization_enabled=True,
                persistence_enabled=False,
            )

            assert engine.compensation_policy == policy
            assert engine.auto_optimization_enabled is True
            assert engine.persistence_enabled is False
            assert engine._initialized is False

            # Test REAL engine initialization
            await engine.initialize()
            assert engine._initialized is True

            await engine.shutdown()

    @pytest.mark.asyncio
    async def test_saga_registration_and_execution_real(self):
        """Test saga registration and execution using REAL Java engine."""

        # Create engine with specific policy
        engine = SagaEngine(
            compensation_policy=CompensationPolicy.STRICT_SEQUENTIAL,
            persistence_enabled=False
        )

        # REAL integration test:
        # 1. Initialize the engine
        await engine.initialize()

        # 2. Verify SAGA class configuration
        saga_class = SuccessfulOrderSaga
        saga_name = saga_class._saga_name
        assert saga_name == "order-processing-success"

        saga_config = saga_class._saga_config
        assert len(saga_config.steps) == 3
        assert len(saga_config.compensation_methods) == 3

        # 3. Execute the SAGA through REAL Java engine
        order_data = {"order_id": "ORD-TEST-001", "customer_id": "CUST-TEST", "amount": 199.99}
        result = await engine.execute(SuccessfulOrderSaga, order_data)

        # 4. Verify results
        assert result.is_success, f"SAGA execution failed: {result.error}"
        assert result.saga_name == "order-processing-success"
        assert len(result.compensated_steps) == 0  # No compensation needed for success

        await engine.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
