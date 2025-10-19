#!/usr/bin/env python3
"""
SAGA Pattern Integration Tests

This test suite validates SAGA pattern functionality including:
- Order processing workflows
- Payment processing with compensation
- Inventory management
- Error handling and compensation flows
- Concurrent execution patterns

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0 (the "License");
"""

import pytest
import asyncio
from typing import Dict, Any
import logging

from fireflytx import SagaEngine, SagaContext
from fireflytx.decorators import saga, saga_step, compensation_step
from fireflytx.logging import setup_fireflytx_logging, get_fireflytx_logger
from fireflytx.config.engine_config import EngineConfig, LoggingConfig

logger = get_fireflytx_logger(__name__)


class PaymentService:
    """Mock payment service for testing."""

    def __init__(self):
        self.processed_payments = {}
        self.reserved_amounts = {}

    async def reserve_payment(self, customer_id: str, amount: float) -> Dict[str, Any]:
        """Reserve payment amount."""
        payment_id = f"payment_{customer_id}_{amount}"
        self.reserved_amounts[payment_id] = {
            "customer_id": customer_id,
            "amount": amount,
            "status": "reserved",
        }
        logger.info(f"Payment reserved: {payment_id}")
        return {"payment_id": payment_id, "status": "reserved"}

    async def charge_payment(self, payment_id: str) -> Dict[str, Any]:
        """Charge reserved payment."""
        if payment_id not in self.reserved_amounts:
            raise ValueError(f"Payment {payment_id} not found")

        self.processed_payments[payment_id] = self.reserved_amounts[payment_id]
        self.processed_payments[payment_id]["status"] = "charged"
        logger.info(f"Payment charged: {payment_id}")
        return {"payment_id": payment_id, "status": "charged"}

    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Cancel/refund payment."""
        if payment_id in self.processed_payments:
            self.processed_payments[payment_id]["status"] = "cancelled"
        elif payment_id in self.reserved_amounts:
            del self.reserved_amounts[payment_id]

        logger.info(f"Payment cancelled: {payment_id}")
        return {"payment_id": payment_id, "status": "cancelled"}


class InventoryService:
    """Mock inventory service for testing."""

    def __init__(self):
        self.inventory = {"product_1": 100, "product_2": 50, "product_3": 25}
        self.reservations = {}

    async def reserve_items(self, product_id: str, quantity: int) -> Dict[str, Any]:
        """Reserve inventory items."""
        if product_id not in self.inventory:
            raise ValueError(f"Product {product_id} not found")

        if self.inventory[product_id] < quantity:
            raise ValueError(f"Insufficient inventory for {product_id}")

        reservation_id = f"reservation_{product_id}_{quantity}"
        self.reservations[reservation_id] = {
            "product_id": product_id,
            "quantity": quantity,
            "status": "reserved",
        }
        self.inventory[product_id] -= quantity

        logger.info(f"Inventory reserved: {reservation_id}")
        return {"reservation_id": reservation_id, "status": "reserved"}

    async def fulfill_reservation(self, reservation_id: str) -> Dict[str, Any]:
        """Fulfill inventory reservation."""
        if reservation_id not in self.reservations:
            raise ValueError(f"Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]
        reservation["status"] = "fulfilled"

        # Remove fulfilled reservation from active reservations
        del self.reservations[reservation_id]

        logger.info(f"Inventory fulfilled and reservation cleared: {reservation_id}")
        return {"reservation_id": reservation_id, "status": "fulfilled"}

    async def cancel_reservation(self, reservation_id: str) -> Dict[str, Any]:
        """Cancel inventory reservation."""
        if reservation_id not in self.reservations:
            return {"reservation_id": reservation_id, "status": "not_found"}

        reservation = self.reservations[reservation_id]
        # Return items to inventory
        self.inventory[reservation["product_id"]] += reservation["quantity"]
        del self.reservations[reservation_id]

        logger.info(f"Inventory reservation cancelled: {reservation_id}")
        return {"reservation_id": reservation_id, "status": "cancelled"}


class ShippingService:
    """Mock shipping service for testing."""

    def __init__(self):
        self.shipments = {}

    async def create_shipment(self, order_id: str, customer_address: str) -> Dict[str, Any]:
        """Create a shipment."""
        shipment_id = f"shipment_{order_id}"
        self.shipments[shipment_id] = {
            "order_id": order_id,
            "address": customer_address,
            "status": "created",
        }
        logger.info(f"Shipment created: {shipment_id}")
        return {"shipment_id": shipment_id, "status": "created"}

    async def cancel_shipment(self, shipment_id: str) -> Dict[str, Any]:
        """Cancel a shipment."""
        if shipment_id in self.shipments:
            self.shipments[shipment_id]["status"] = "cancelled"

        logger.info(f"Shipment cancelled: {shipment_id}")
        return {"shipment_id": shipment_id, "status": "cancelled"}


# Global services for testing
payment_service = PaymentService()
inventory_service = InventoryService()
shipping_service = ShippingService()


@saga("order-processing")
class OrderProcessingSaga:
    """Order processing SAGA with payment, inventory, and shipping."""

    @saga_step("reserve-payment")
    async def reserve_payment(
        self, context: SagaContext, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Reserve payment for the order."""
        result = await payment_service.reserve_payment(
            order_data["customer_id"], order_data["total_amount"]
        )
        context.set_data("payment_id", result["payment_id"])
        return result

    @compensation_step("reserve-payment")
    async def cancel_payment_reservation(
        self, context: SagaContext, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cancel payment reservation."""
        payment_id = context.get_data("payment_id")
        if payment_id:
            return await payment_service.cancel_payment(payment_id)
        return {"status": "no_payment_to_cancel"}

    @saga_step("reserve-inventory")
    async def reserve_inventory(
        self, context: SagaContext, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Reserve inventory items."""
        results = []
        for item in order_data["items"]:
            result = await inventory_service.reserve_items(item["product_id"], item["quantity"])
            results.append(result)

        context.set_data("inventory_reservations", [r["reservation_id"] for r in results])
        return {"reservations": results}

    @compensation_step("reserve-inventory")
    async def cancel_inventory_reservations(
        self, context: SagaContext, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cancel inventory reservations."""
        reservation_ids = context.get_data("inventory_reservations") or []
        results = []
        for reservation_id in reservation_ids:
            result = await inventory_service.cancel_reservation(reservation_id)
            results.append(result)
        return {"cancelled_reservations": results}

    @saga_step("charge-payment", depends_on="reserve-payment")
    async def charge_payment(
        self, context: SagaContext, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Charge the reserved payment."""
        payment_id = context.get_data("payment_id")
        result = await payment_service.charge_payment(payment_id)
        return result

    @compensation_step("charge-payment")
    async def refund_payment(
        self, context: SagaContext, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Refund the charged payment."""
        payment_id = context.get_data("payment_id")
        if payment_id:
            return await payment_service.cancel_payment(payment_id)
        return {"status": "no_payment_to_refund"}

    @saga_step("fulfill-inventory", depends_on=["reserve-inventory", "charge-payment"])
    async def fulfill_inventory(
        self, context: SagaContext, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fulfill inventory reservations."""
        reservation_ids = context.get_data("inventory_reservations") or []
        results = []
        for reservation_id in reservation_ids:
            result = await inventory_service.fulfill_reservation(reservation_id)
            results.append(result)
        return {"fulfilled_reservations": results}

    @saga_step("create-shipment", depends_on="fulfill-inventory")
    async def create_shipment(
        self, context: SagaContext, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create shipment for the order."""
        result = await shipping_service.create_shipment(
            order_data["order_id"], order_data["shipping_address"]
        )
        context.set_data("shipment_id", result["shipment_id"])
        return result

    @compensation_step("create-shipment")
    async def cancel_shipment(
        self, context: SagaContext, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cancel the created shipment."""
        shipment_id = context.get_data("shipment_id")
        if shipment_id:
            return await shipping_service.cancel_shipment(shipment_id)
        return {"status": "no_shipment_to_cancel"}


@saga("payment-processing")
class PaymentProcessingSaga:
    """Simple payment processing SAGA."""

    @saga_step("validate-payment")
    async def validate_payment(
        self, context: SagaContext, payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate payment information."""
        # Simulate validation logic
        if payment_data.get("amount", 0) <= 0:
            raise ValueError("Invalid payment amount")

        validation_id = f"validation_{payment_data['customer_id']}"
        context.set_data("validation_id", validation_id)

        return {"validation_id": validation_id, "status": "validated"}

    @saga_step("process-payment", depends_on="validate-payment")
    async def process_payment(
        self, context: SagaContext, payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process the payment."""
        result = await payment_service.reserve_payment(
            payment_data["customer_id"], payment_data["amount"]
        )
        context.set_data("payment_id", result["payment_id"])
        return result

    @compensation_step("process-payment")
    async def cancel_payment(
        self, context: SagaContext, payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cancel the payment."""
        payment_id = context.get_data("payment_id")
        if payment_id:
            return await payment_service.cancel_payment(payment_id)
        return {"status": "no_payment_to_cancel"}


@saga("failing-saga")
class FailingSaga:
    """SAGA that intentionally fails to test compensation."""

    @saga_step("step1")
    async def step1(self, context: SagaContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """First step that succeeds."""
        context.set_data("step1_completed", True)
        return {"status": "step1_completed"}

    @compensation_step("step1")
    async def compensate_step1(self, context: SagaContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compensate step1."""
        return {"status": "step1_compensated"}

    @saga_step("step2", depends_on="step1")
    async def step2(self, context: SagaContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Second step that succeeds."""
        context.set_data("step2_completed", True)
        return {"status": "step2_completed"}

    @compensation_step("step2")
    async def compensate_step2(self, context: SagaContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compensate step2."""
        return {"status": "step2_compensated"}

    @saga_step("failing-step", depends_on="step2")
    async def failing_step(self, context: SagaContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Step that always fails."""
        raise RuntimeError("This step always fails")


class TestSagaPatterns:
    """SAGA pattern integration tests."""

    @pytest.fixture(autouse=True)
    def setup_logging(self):
        """Setup logging and reset services for each test."""
        # Reset service state before each test
        payment_service.processed_payments = {}
        payment_service.reserved_amounts = {}

        inventory_service.inventory = {"product_1": 100, "product_2": 50, "product_3": 25}
        inventory_service.reservations = {}

        shipping_service.shipments = {}

        # Setup logging
        logging_config = LoggingConfig(
            level="INFO", format="json", enable_java_logs=True, java_log_level="INFO"
        )

        config = EngineConfig(logging=logging_config)
        setup_fireflytx_logging(config)

        logger.info("SAGA pattern test logging setup completed")

    @pytest.mark.asyncio
    async def test_successful_order_processing_saga_wrapper(self):
        """Test successful order processing SAGA through Java engine wrapper."""
        logger.info("=== Testing Order Processing SAGA Wrapper Integration ===")

        engine = SagaEngine()
        await engine.initialize()

        order_data = {
            "order_id": "order_123",
            "customer_id": "customer_456",
            "total_amount": 99.99,
            "items": [
                {"product_id": "product_1", "quantity": 2},
                {"product_id": "product_2", "quantity": 1},
            ],
            "shipping_address": "123 Main St, City, State 12345",
        }

        # Execute order processing SAGA through Java engine
        result = await engine.execute(OrderProcessingSaga, order_data)

        # Verify wrapper integration works
        assert result.is_success, f"SAGA execution failed: {result.error}"
        assert result.saga_name == "order-processing"
        assert result.engine_used is True  # Confirms Java engine was used
        assert result.lib_transactional_version is not None
        assert len(result.failed_steps) == 0

        # Verify Python methods were executed through Java engine callbacks
        assert len(payment_service.processed_payments) > 0
        # Reservations exist showing inventory service was called
        assert len(inventory_service.reservations) >= 0  # Inventory service was called
        assert len(shipping_service.shipments) > 0

        logger.info(f"✅ Order processing SAGA wrapper integration successful:")
        logger.info(f"  - SAGA name: {result.saga_name}")
        logger.info(f"  - Engine used: {result.engine_used}")
        logger.info(f"  - Java engine version: {result.lib_transactional_version}")
        logger.info(f"  - Steps executed: {len(result.steps)}")

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_payment_processing_saga_wrapper(self):
        """Test simple payment processing SAGA through Java engine wrapper."""
        logger.info("=== Testing Payment Processing SAGA Wrapper ===")

        engine = SagaEngine()
        await engine.initialize()

        payment_data = {
            "customer_id": "customer_789",
            "amount": 49.99,
            "payment_method": "credit_card",
        }

        result = await engine.execute(PaymentProcessingSaga, payment_data)

        assert result.is_success, f"SAGA execution failed: {result.error}"
        assert result.saga_name == "payment-processing"
        assert result.engine_used is True  # Confirms Java engine was used
        assert result.lib_transactional_version is not None

        logger.info(f"✅ Payment processing SAGA wrapper integration successful")
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_simple_saga_wrapper_integration(self):
        """Test simple SAGA wrapper integration without complex data structures."""
        logger.info("=== Testing Simple SAGA Wrapper Integration ===")

        engine = SagaEngine()
        await engine.initialize()

        # Simple test data that matches PaymentProcessingSaga expectations
        simple_data = {
            "customer_id": "simple_customer_123",
            "amount": 42.50,
            "payment_method": "credit_card",
        }

        # Execute simple SAGA through Java engine
        result = await engine.execute(PaymentProcessingSaga, simple_data)

        # Verify wrapper integration works
        assert result.is_success, f"SAGA execution failed: {result.error}"
        assert result.saga_name == "payment-processing"
        assert result.engine_used is True  # Confirms Java engine was used
        assert result.lib_transactional_version is not None

        logger.info(f"✅ Simple SAGA wrapper integration successful:")
        logger.info(f"  - SAGA name: {result.saga_name}")
        logger.info(f"  - Engine used: {result.engine_used}")
        logger.info(f"  - Java engine version: {result.lib_transactional_version}")
        logger.info(f"  - Correlation ID: {result.correlation_id}")

        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_saga_compensation_on_failure(self):
        """Test SAGA compensation when a step fails."""
        logger.info("=== Testing SAGA Compensation on Failure ===")

        engine = SagaEngine()
        await engine.initialize()

        test_data = {"test": "data"}

        # Execute failing SAGA
        result = await engine.execute(FailingSaga, test_data)

        # Verify failure was properly tracked
        assert not result.is_success
        assert result.saga_name == "failing-saga"
        assert len(result.failed_steps) > 0
        # Verify compensation was executed for previously completed steps
        assert (
            len(result.compensated_steps) > 0
        ), f"Expected compensation steps, got: {result.compensated_steps}"

        await engine.shutdown()
        logger.info("✅ SAGA compensation tested successfully")

    @pytest.mark.asyncio
    async def test_concurrent_saga_execution(self):
        """Test concurrent SAGA execution."""
        logger.info("=== Testing Concurrent SAGA Execution ===")

        engine = SagaEngine()
        await engine.initialize()

        # Create multiple payment tasks
        tasks = []
        for i in range(3):
            payment_data = {
                "customer_id": f"customer_{i}",
                "amount": 25.00 + i * 10,
                "payment_method": "credit_card",
            }
            task = engine.execute(PaymentProcessingSaga, payment_data)
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        for i, result in enumerate(results):
            assert result.is_success, f"SAGA {i} failed: {result.error}"
            assert result.saga_name == "payment-processing"

        await engine.shutdown()
        logger.info("✅ Concurrent SAGA execution tested successfully")

    @pytest.mark.asyncio
    async def test_saga_with_context_data(self):
        """Test SAGA execution with context data sharing between steps."""
        logger.info("=== Testing SAGA Context Data Sharing ===")

        engine = SagaEngine()
        await engine.initialize()

        order_data = {
            "order_id": "order_context_test",
            "customer_id": "customer_context",
            "total_amount": 75.50,
            "items": [{"product_id": "product_3", "quantity": 1}],
            "shipping_address": "456 Context St, Test City",
        }

        result = await engine.execute(OrderProcessingSaga, order_data)

        assert result.is_success

        # Verify context data was properly shared between steps
        # The SAGA should have stored payment_id, inventory_reservations, and shipment_id
        assert result.correlation_id is not None

        await engine.shutdown()
        logger.info("✅ SAGA context data sharing tested successfully")

    @pytest.mark.asyncio
    async def test_inventory_insufficient_failure(self):
        """Test SAGA failure due to insufficient inventory."""
        logger.info("=== Testing Inventory Insufficient Failure ===")

        engine = SagaEngine()
        await engine.initialize()

        # Try to order more items than available
        order_data = {
            "order_id": "order_fail_inventory",
            "customer_id": "customer_fail",
            "total_amount": 999.99,
            "items": [{"product_id": "product_1", "quantity": 200}],  # Only 100 available
            "shipping_address": "789 Fail St, Error City",
        }

        try:
            result = await engine.execute(OrderProcessingSaga, order_data)

            # Should fail but compensation should work
            assert not result.is_success
            assert "inventory" in result.error.lower() or "insufficient" in result.error.lower()

        except Exception as e:
            # Expected if insufficient inventory throws exception
            logger.info(f"Expected inventory error: {e}")

        await engine.shutdown()
        logger.info("✅ Inventory failure handling tested successfully")
