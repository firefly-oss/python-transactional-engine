#!/usr/bin/env python3
"""
Basic SAGA pattern example demonstrating order fulfillment workflow.

This example shows how to implement a simple order processing SAGA with 
inventory reservation, payment processing, and shipping steps.
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

import asyncio
import logging
from pydantic import BaseModel
from fireflytx import SagaEngine
from fireflytx.decorators.saga import saga, saga_step, compensation_step


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# Data models
class Order(BaseModel):
    order_id: str
    customer_id: str
    product_id: str
    quantity: int
    amount: float


class InventoryReservation(BaseModel):
    reservation_id: str
    product_id: str
    quantity: int
    reserved_at: str


class PaymentTransaction(BaseModel):
    transaction_id: str
    amount: float
    status: str
    processed_at: str


class ShippingLabel(BaseModel):
    label_id: str
    tracking_number: str
    carrier: str
    created_at: str


# SAGA implementation
@saga("order-fulfillment")
class OrderFulfillmentSaga:
    """
    SAGA for handling order fulfillment with inventory, payment, and shipping.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @saga_step("inventory", retry=3, timeout_ms=5000, compensate="release_inventory")
    async def reserve_inventory(self, order: Order) -> InventoryReservation:
        """Reserve inventory for the order."""
        self.logger.info(f"Reserving inventory for order {order.order_id}")
        
        # Simulate inventory check and reservation
        await asyncio.sleep(0.1)  # Simulate async work
        
        # Simulate failure for specific products
        if order.product_id == "OUT_OF_STOCK":
            raise Exception("Product is out of stock")
        
        reservation = InventoryReservation(
            reservation_id=f"inv-{order.order_id}",
            product_id=order.product_id,
            quantity=order.quantity,
            reserved_at="2024-01-15T10:30:00Z"
        )
        
        self.logger.info(f"Inventory reserved: {reservation.reservation_id}")
        return reservation
    
    @saga_step("payment", depends_on=["inventory"], compensate="refund_payment")
    async def process_payment(self, order: Order) -> PaymentTransaction:
        """Process payment for the order."""
        self.logger.info(f"Processing payment for order {order.order_id}")
        
        await asyncio.sleep(0.2)  # Simulate payment processing
        
        # Simulate payment failure for high amounts
        if order.amount > 1000:
            raise Exception("Payment declined - amount exceeds limit")
        
        transaction = PaymentTransaction(
            transaction_id=f"pay-{order.order_id}",
            amount=order.amount,
            status="completed",
            processed_at="2024-01-15T10:30:05Z"
        )
        
        self.logger.info(f"Payment processed: {transaction.transaction_id}")
        return transaction
    
    @saga_step("shipping", depends_on=["payment"], compensate="cancel_shipping")
    async def create_shipping_label(self, order: Order) -> ShippingLabel:
        """Create shipping label for the order."""
        self.logger.info(f"Creating shipping label for order {order.order_id}")
        
        await asyncio.sleep(0.1)  # Simulate label creation
        
        label = ShippingLabel(
            label_id=f"ship-{order.order_id}",
            tracking_number=f"TRK{order.order_id}123",
            carrier="FastShip Express",
            created_at="2024-01-15T10:32:00Z"
        )
        
        self.logger.info(f"Shipping label created: {label.label_id}")
        return label
    
    # Compensation methods
    @compensation_step("inventory")
    async def release_inventory(self, reservation: InventoryReservation) -> None:
        """Release reserved inventory."""
        # Handle both Pydantic model and dict (Java may send dict)
        res_id = reservation.reservation_id if hasattr(reservation, 'reservation_id') else reservation.get('reservation_id', 'unknown')
        self.logger.info(f"Releasing inventory reservation: {res_id}")
        await asyncio.sleep(0.05)
        self.logger.info(f"Inventory released: {res_id}")

    @compensation_step("payment")
    async def refund_payment(self, transaction: PaymentTransaction) -> None:
        """Refund payment."""
        tx_id = transaction.transaction_id if hasattr(transaction, 'transaction_id') else transaction.get('transaction_id', 'unknown')
        self.logger.info(f"Refunding payment: {tx_id}")
        await asyncio.sleep(0.1)
        self.logger.info(f"Payment refunded: {tx_id}")

    @compensation_step("shipping")
    async def cancel_shipping(self, label: ShippingLabel) -> None:
        """Cancel shipping label."""
        label_id = label.label_id if hasattr(label, 'label_id') else label.get('label_id', 'unknown')
        self.logger.info(f"Canceling shipping label: {label_id}")
        await asyncio.sleep(0.05)
        self.logger.info(f"Shipping label canceled: {label_id}")


async def run_successful_saga():
    """Run a successful order SAGA."""
    print("\n=== Running Successful Order SAGA ===")
    
    # Create SAGA engine
    saga_engine = SagaEngine()
    
    # Initialize engine - this connects to the Java lib-transactional-engine
    print("🚀 Initializing SAGA engine (connecting to Java subprocess)...")
    await saga_engine.initialize()
    print("✅ SAGA engine initialized and connected to Java\n")

    # Create test order
    order = Order(
        order_id="ORD-001",
        customer_id="CUST-123",
        product_id="WIDGET-42",
        quantity=2,
        amount=99.99
    )

    print(f"Processing order: {order.order_id}")
    print(f"Customer: {order.customer_id}")
    print(f"Product: {order.product_id} (qty: {order.quantity})")
    print(f"Amount: ${order.amount}")

    try:
        # Execute SAGA using the real Java engine
        # The Java engine orchestrates the execution, handles retries, and manages compensation
        print("\n📦 Executing SAGA via Java lib-transactional-engine...")

        result = await saga_engine.execute(
            OrderFulfillmentSaga,
            order.model_dump()
        )

        if result.is_success:
            print(f"\n🎉 Order {order.order_id} completed successfully!")
            print(f"Result: {result.result if hasattr(result, 'result') else 'Success'}")
        else:
            print(f"\n❌ SAGA failed: {result.error}")
            print(f"Compensation executed: {result.compensated_steps}")

    except Exception as e:
        print(f"\n❌ SAGA execution error: {e}")

    finally:
        # Shutdown engine
        print("\n🛑 Shutting down SAGA engine...")
        await saga_engine.shutdown()
        print("✅ SAGA engine shutdown complete")


async def run_failing_saga():
    """Run a SAGA that fails due to payment limit."""
    print("\n=== Running Failing Order SAGA ===")
    
    saga_engine = SagaEngine()
    
    print("🚀 Initializing SAGA engine...")
    await saga_engine.initialize()
    print("✅ SAGA engine initialized\n")

    # Create order that will fail payment
    order = Order(
        order_id="ORD-FAIL",
        customer_id="CUST-456",
        product_id="EXPENSIVE-ITEM",
        quantity=1,
        amount=1500.0  # Exceeds limit
    )

    print(f"Processing order: {order.order_id}")
    print(f"Amount: ${order.amount} (will exceed limit)")

    try:
        print("\n📦 Executing SAGA via Java engine...")
        
        result = await saga_engine.execute(
            OrderFulfillmentSaga,
            order.model_dump()
        )

        if result.is_success:
            print(f"\n🎉 Order {order.order_id} completed successfully!")
        else:
            print(f"\n❌ SAGA failed: {result.error}")
            print(f"✅ Compensation executed: {result.compensated_steps}")

    except Exception as e:
        print(f"\n💥 SAGA execution error: {e}")

    finally:
        print("\n🛑 Shutting down SAGA engine...")
        await saga_engine.shutdown()
        print("✅ SAGA engine shutdown complete")


async def main():
    """Run all examples."""
    print("🚀 SAGA Pattern Basic Examples")
    print("=" * 50)
    
    # Run successful SAGA
    await run_successful_saga()
    
    # Run failing SAGA
    await run_failing_saga()
    
    print("\n✨ All examples completed!")
    print("\nKey Takeaways:")
    print("- SAGAs ensure data consistency across distributed services")
    print("- Failed steps trigger compensation of successful steps")
    print("- Step dependencies ensure proper execution order")
    print("- Retry and timeout policies handle transient failures")


if __name__ == "__main__":
    asyncio.run(main())

