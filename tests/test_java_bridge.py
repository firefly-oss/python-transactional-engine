#!/usr/bin/env python3
"""
Test script for "Python defines, Java executes" SAGA architecture.

This script demonstrates how Python defines SAGA structure and business logic
while Java lib-transactional-engine handles all orchestration, retry, and compensation.
"""

import asyncio
import logging
import pytest
from fireflytx.engine.saga_engine import SagaEngine
from fireflytx.decorators.saga import saga, saga_step
from fireflytx.core.saga_context import SagaContext

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@saga(name="TestPaymentSaga", layer_concurrency=2)
class TestPaymentSaga:
    """Simple SAGA for testing the Java bridge architecture."""

    @saga_step(step_id="validate_payment", depends_on=[], retry=3, timeout_ms=5000)
    async def validate_payment(self, input_data: dict, context: SagaContext) -> dict:
        """Validate payment information."""
        logger.info(f"🔍 Validating payment: {input_data.get('payment_id', 'unknown')}")

        # Simulate validation logic
        payment_id = input_data.get("payment_id")
        amount = input_data.get("amount", 0)

        if not payment_id:
            raise ValueError("Payment ID is required")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Store validation result in context
        context.set_data("payment_validated", True)
        context.set_data("validated_amount", amount)

        return {
            "status": "validated",
            "payment_id": payment_id,
            "amount": amount,
            "timestamp": "2025-01-18T14:46:00Z",
        }

    @saga_step(
        step_id="process_payment", depends_on=["validate_payment"], retry=2, timeout_ms=10000
    )
    async def process_payment(self, input_data: dict, context: SagaContext) -> dict:
        """Process the validated payment."""
        logger.info(f"💳 Processing payment: {input_data.get('payment_id', 'unknown')}")

        # Get validated amount from context
        validated_amount = context.get_data("validated_amount", 0)

        # Simulate payment processing
        transaction_id = f"txn_{input_data.get('payment_id', 'unknown')}_001"

        # Store transaction info in context
        context.set_data("transaction_id", transaction_id)
        context.set_data("payment_processed", True)

        return {
            "status": "processed",
            "transaction_id": transaction_id,
            "amount_processed": validated_amount,
            "processor": "test_processor",
            "timestamp": "2025-01-18T14:46:15Z",
        }

    @saga_step(
        step_id="send_confirmation", depends_on=["process_payment"], retry=1, timeout_ms=3000
    )
    async def send_confirmation(self, input_data: dict, context: SagaContext) -> dict:
        """Send payment confirmation."""
        logger.info(
            f"📧 Sending confirmation for payment: {input_data.get('payment_id', 'unknown')}"
        )

        transaction_id = context.get_data("transaction_id")

        # Simulate sending confirmation
        confirmation_id = f"conf_{transaction_id}"

        context.set_data("confirmation_sent", True)
        context.set_data("confirmation_id", confirmation_id)

        return {
            "status": "confirmation_sent",
            "confirmation_id": confirmation_id,
            "recipient": input_data.get("customer_email", "test@example.com"),
            "timestamp": "2025-01-18T14:46:30Z",
        }


@pytest.mark.asyncio
async def test_java_bridge_architecture():
    """Test the complete Python defines, Java executes architecture."""
    logger.info("🚀 Testing 'Python defines, Java executes' SAGA architecture")

    try:
        # Initialize SAGA engine
        engine = SagaEngine(
            compensation_policy="STRICT_SEQUENTIAL",
            auto_optimization_enabled=True,
            persistence_enabled=False,
        )

        # Initialize the engine (this will start the Java subprocess bridge)
        logger.info("Initializing SAGA engine with Java bridge...")
        await engine.initialize()

        # Define test payment data
        payment_data = {
            "payment_id": "pay_123456",
            "amount": 99.99,
            "currency": "USD",
            "customer_email": "customer@example.com",
            "merchant_id": "merchant_789",
        }

        logger.info(f"Executing SAGA with test data: {payment_data}")

        # Execute SAGA - Python defines, Java orchestrates
        result = await engine.execute(TestPaymentSaga, payment_data)

        # Check results
        logger.info(f"🎯 SAGA execution completed:")
        logger.info(f"   Success: {result.is_success}")
        logger.info(f"   Duration: {result.duration_ms}ms")
        logger.info(f"   Steps completed: {len(result.steps)}")
        logger.info(f"   Failed steps: {result.failed_steps}")
        logger.info(f"   Compensated steps: {result.compensated_steps}")

        if result.error:
            logger.error(f"   Error: {result.error}")

        # Print step results
        for step_name, step_result in result.steps.items():
            logger.info(f"   Step '{step_name}': {step_result}")

        # Shutdown engine
        await engine.shutdown()

        if result.is_success:
            logger.info("✅ Test completed successfully - Java bridge architecture working!")
            return True
        else:
            logger.error("❌ Test failed - SAGA execution was not successful")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()

        # Try to shutdown engine if it was created
        try:
            await engine.shutdown()
        except:
            pass

        return False


async def main():
    """Main test function."""
    success = await test_java_bridge_architecture()
    exit_code = 0 if success else 1

    if success:
        print("\n🎉 'Python defines, Java executes' architecture test PASSED!")
    else:
        print("\n💥 'Python defines, Java executes' architecture test FAILED!")

    exit(exit_code)


@pytest.mark.asyncio
async def test_java_bridge_architecture_pytest():
    """Pytest wrapper for java bridge architecture test."""
    success = await test_java_bridge_architecture()
    assert success, "Java bridge architecture test should succeed"


if __name__ == "__main__":
    asyncio.run(main())
