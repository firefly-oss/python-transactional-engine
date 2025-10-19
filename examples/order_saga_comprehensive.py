#!/usr/bin/env python3
"""
Comprehensive SAGA pattern example following Java lib-transactional-engine patterns.

This example demonstrates:
1. Proper SAGA step configuration with compensation methods
2. Step dependencies and data flow
3. Compensation execution on failures
4. Parameter injection patterns
5. Context variable handling
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
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from fireflytx import SagaEngine
from fireflytx.decorators.saga import saga, saga_step
from fireflytx.core.saga_context import SagaContext
from pytransactional.events.saga_events import LoggingSagaEvents


# Data Models (equivalent to Java records/DTOs)
class OrderRequest(BaseModel):
    order_id: str
    customer_id: str
    items: List["OrderItem"]
    payment_method: str
    shipping_address: str
    amount: float


class OrderItem(BaseModel):
    product_id: str
    name: str
    quantity: int
    price: float


class OrderValidation(BaseModel):
    order_id: str
    customer_id: str
    items: List[OrderItem]
    valid: bool
    validation_id: str


class InventoryReservation(BaseModel):
    reservation_id: str
    order_id: str
    items: List[OrderItem]
    reserved_at: datetime


class PaymentResult(BaseModel):
    payment_id: str
    transaction_id: str
    order_id: str
    amount: float
    status: str
    processed_at: datetime


class ShippingLabel(BaseModel):
    label_id: str
    shipment_id: str
    order_id: str
    tracking_number: str
    carrier: str
    estimated_delivery: datetime
    created_at: datetime


# Main SAGA Implementation
@saga(name="order-processing")
class OrderProcessingSaga:
    """
    Comprehensive order processing SAGA demonstrating:
    - Step dependencies
    - Compensation methods
    - Parameter injection
    - Context variables
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # Step 1: Validate Order (no dependencies, no compensation needed)
    @saga_step(
        step_id="validate-order",
        retry=3,
        timeout_ms=5000
    )
    async def validate_order(self, order_request: OrderRequest, context: SagaContext) -> OrderValidation:
        """
        Validate the order request.
        This step has no compensation because validation doesn't change external state.
        """
        self.logger.info(f"Validating order {order_request.order_id}")
        
        # Simulate validation logic
        await asyncio.sleep(0.1)
        
        # Simulate validation failure for specific orders
        if order_request.customer_id == "INVALID_CUSTOMER":
            raise ValueError("Invalid customer ID")
        
        if order_request.amount <= 0:
            raise ValueError("Order amount must be positive")
        
        validation = OrderValidation(
            order_id=order_request.order_id,
            customer_id=order_request.customer_id,
            items=order_request.items,
            valid=True,
            validation_id=f"VAL-{uuid.uuid4().hex[:8]}"
        )
        
        # Store validation info in context for other steps
        context.set_variable("validation_id", validation.validation_id)
        context.set_variable("customer_id", order_request.customer_id)
        
        self.logger.info(f"Order validated: {validation.validation_id}")
        return validation
    
    # Step 2: Reserve Inventory (depends on validation, has compensation)
    @saga_step(
        step_id="reserve-inventory",
        depends_on=["validate-order"],
        compensate="release_inventory",
        retry=3,
        timeout_ms=10000,
        compensation_retry=2,
        compensation_timeout_ms=5000,
        compensation_critical=True
    )
    async def reserve_inventory(self, validation: OrderValidation, context: SagaContext) -> InventoryReservation:
        """
        Reserve inventory for the order.
        This step has compensation because it locks inventory resources.
        """
        self.logger.info(f"Reserving inventory for order {validation.order_id}")
        
        # Simulate inventory reservation
        await asyncio.sleep(0.2)
        
        # Simulate out-of-stock scenario
        for item in validation.items:
            if item.product_id == "OUT_OF_STOCK":
                raise Exception(f"Product {item.product_id} is out of stock")
        
        reservation = InventoryReservation(
            reservation_id=f"RES-{uuid.uuid4().hex[:8]}",
            order_id=validation.order_id,
            items=validation.items,
            reserved_at=datetime.now()
        )
        
        # Store reservation info for other steps and compensation
        context.set_variable("reservation_id", reservation.reservation_id)
        context.set_variable("reserved_items", len(validation.items))
        
        self.logger.info(f"Inventory reserved: {reservation.reservation_id}")
        return reservation
    
    # Step 3: Process Payment (depends on inventory, has compensation)
    @saga_step(
        step_id="process-payment",
        depends_on=["reserve-inventory"],
        compensate="refund_payment",
        retry=2,
        timeout_ms=15000,
        backoff_ms=2000,
        compensation_retry=3,
        compensation_timeout_ms=10000,
        compensation_critical=True
    )
    async def process_payment(self, validation: OrderValidation, 
                            reservation: InventoryReservation,
                            order_request: OrderRequest,
                            context: SagaContext) -> PaymentResult:
        """
        Process payment for the order.
        This step has compensation because it charges the customer.
        """
        self.logger.info(f"Processing payment for order {validation.order_id}")
        
        # Simulate payment processing
        await asyncio.sleep(0.3)
        
        # Simulate payment failures
        if order_request.amount > 5000:
            raise Exception("Payment amount exceeds limit")
        
        if order_request.payment_method == "DECLINED_CARD":
            raise Exception("Payment method declined")
        
        payment = PaymentResult(
            payment_id=f"PAY-{uuid.uuid4().hex[:8]}",
            transaction_id=f"TXN-{uuid.uuid4().hex[:8]}",
            order_id=validation.order_id,
            amount=order_request.amount,
            status="COMPLETED",
            processed_at=datetime.now()
        )
        
        # Store payment info for shipping and compensation
        context.set_variable("payment_id", payment.payment_id)
        context.set_variable("transaction_id", payment.transaction_id)
        context.set_variable("paid_amount", payment.amount)
        
        self.logger.info(f"Payment processed: {payment.payment_id}")
        return payment
    
    # Step 4: Create Shipping Label (depends on payment, has compensation)
    @saga_step(
        step_id="create-shipping",
        depends_on=["process-payment"],
        compensate="cancel_shipping",
        retry=2,
        timeout_ms=8000
    )
    async def create_shipping_label(self, validation: OrderValidation,
                                  payment: PaymentResult,
                                  order_request: OrderRequest,
                                  context: SagaContext) -> ShippingLabel:
        """
        Create shipping label for the order.
        This step has compensation because it creates shipping commitments.
        """
        self.logger.info(f"Creating shipping label for order {validation.order_id}")
        
        # Simulate shipping label creation
        await asyncio.sleep(0.15)
        
        label = ShippingLabel(
            label_id=f"LBL-{uuid.uuid4().hex[:8]}",
            shipment_id=f"SHIP-{uuid.uuid4().hex[:8]}",
            order_id=validation.order_id,
            tracking_number=f"TRK{uuid.uuid4().hex[:12].upper()}",
            carrier="FastShip Express",
            estimated_delivery=datetime.now() + timedelta(days=3),
            created_at=datetime.now()
        )
        
        # Store shipping info
        context.set_variable("shipment_id", label.shipment_id)
        context.set_variable("tracking_number", label.tracking_number)
        
        self.logger.info(f"Shipping label created: {label.label_id}")
        return label
    
    # Compensation Methods
    # These are called automatically by the SAGA engine when later steps fail
    
    async def release_inventory(self, reservation: InventoryReservation, context: SagaContext) -> None:
        """
        Compensation for reserve_inventory step.
        Release the inventory reservation.
        """
        self.logger.warning(f"Releasing inventory reservation: {reservation.reservation_id}")
        
        # Simulate inventory release
        await asyncio.sleep(0.1)
        
        # In real implementation, this would call inventory service to release
        self.logger.info(f"Inventory reservation {reservation.reservation_id} released")
    
    async def refund_payment(self, payment: PaymentResult, context: SagaContext) -> None:
        """
        Compensation for process_payment step.
        Refund the payment to the customer.
        """
        self.logger.warning(f"Refunding payment: {payment.payment_id}")
        
        # Simulate refund processing
        await asyncio.sleep(0.2)
        
        # In real implementation, this would call payment service to refund
        self.logger.info(f"Payment {payment.payment_id} refunded: ${payment.amount}")
    
    async def cancel_shipping(self, label: ShippingLabel, context: SagaContext) -> None:
        """
        Compensation for create_shipping_label step.
        Cancel the shipping label and any shipping commitments.
        """
        self.logger.warning(f"Cancelling shipping label: {label.label_id}")
        
        # Simulate shipping cancellation
        await asyncio.sleep(0.1)
        
        # In real implementation, this would call shipping service to cancel
        self.logger.info(f"Shipping label {label.label_id} cancelled")


# Test scenarios
async def run_successful_order():
    """Test a successful order processing scenario."""
    print("\n🚀 === Successful Order Processing ===")
    
    order = OrderRequest(
        order_id=f"ORD-{uuid.uuid4().hex[:8]}",
        customer_id="CUST-123",
        items=[
            OrderItem(product_id="WIDGET-A", name="Super Widget", quantity=2, price=25.99),
            OrderItem(product_id="GADGET-B", name="Cool Gadget", quantity=1, price=49.99)
        ],
        payment_method="VISA-4111",
        shipping_address="123 Main St, Anytown, ST 12345",
        amount=101.97
    )
    
    print(f"Processing order: {order.order_id}")
    print(f"Customer: {order.customer_id}")
    print(f"Items: {len(order.items)} items, Total: ${order.amount}")
    
    # In real implementation, this would use the SagaEngine
    # For demonstration, we'll simulate the execution
    saga = OrderProcessingSaga()
    context = SagaContext(correlation_id=f"SAGA-{uuid.uuid4().hex[:8]}")
    
    try:
        print("\n📋 Step 1: Validating order...")
        validation = await saga.validate_order(order, context)
        print(f"✅ Order validated: {validation.validation_id}")
        
        print("\n📦 Step 2: Reserving inventory...")
        reservation = await saga.reserve_inventory(validation, context)
        print(f"✅ Inventory reserved: {reservation.reservation_id}")
        
        print("\n💳 Step 3: Processing payment...")
        payment = await saga.process_payment(validation, reservation, order, context)
        print(f"✅ Payment processed: {payment.payment_id} (${payment.amount})")
        
        print("\n🚚 Step 4: Creating shipping label...")
        shipping = await saga.create_shipping_label(validation, payment, order, context)
        print(f"✅ Shipping label created: {shipping.tracking_number}")
        
        print(f"\n🎉 Order {order.order_id} processed successfully!")
        print(f"📍 Tracking: {shipping.tracking_number}")
        print(f"📅 Estimated delivery: {shipping.estimated_delivery.strftime('%Y-%m-%d')}")
        
    except Exception as e:
        print(f"\n❌ Order processing failed: {e}")


async def run_payment_failure_scenario():
    """Test scenario where payment fails, triggering compensation."""
    print("\n💥 === Payment Failure Scenario ===")
    
    order = OrderRequest(
        order_id=f"ORD-{uuid.uuid4().hex[:8]}",
        customer_id="CUST-456",
        items=[
            OrderItem(product_id="EXPENSIVE-ITEM", name="Luxury Product", quantity=1, price=6000.00)
        ],
        payment_method="VISA-4111",
        shipping_address="456 Oak Ave, Somewhere, ST 67890",
        amount=6000.00  # This will trigger payment failure
    )
    
    print(f"Processing order: {order.order_id}")
    print(f"Amount: ${order.amount} (exceeds payment limit)")
    
    saga = OrderProcessingSaga()
    context = SagaContext(correlation_id=f"SAGA-{uuid.uuid4().hex[:8]}")
    
    try:
        print("\n📋 Step 1: Validating order...")
        validation = await saga.validate_order(order, context)
        print(f"✅ Order validated: {validation.validation_id}")
        
        print("\n📦 Step 2: Reserving inventory...")
        reservation = await saga.reserve_inventory(validation, context)
        print(f"✅ Inventory reserved: {reservation.reservation_id}")
        
        print("\n💳 Step 3: Processing payment...")
        try:
            payment = await saga.process_payment(validation, reservation, order, context)
            print(f"✅ Payment processed: {payment.payment_id}")
        except Exception as payment_error:
            print(f"❌ Payment failed: {payment_error}")
            
            # SAGA engine would automatically trigger compensation here
            print("\n🔄 Starting compensation...")
            print("⚠️  Compensating reserve-inventory step...")
            await saga.release_inventory(reservation, context)
            print("✅ Inventory compensation completed")
            
            raise payment_error
            
    except Exception as e:
        print(f"\n💥 Order processing failed after compensation: {e}")


async def run_inventory_failure_scenario():
    """Test scenario where inventory check fails (no compensation needed)."""
    print("\n📦 === Inventory Failure Scenario ===")
    
    order = OrderRequest(
        order_id=f"ORD-{uuid.uuid4().hex[:8]}",
        customer_id="CUST-789",
        items=[
            OrderItem(product_id="OUT_OF_STOCK", name="Unavailable Item", quantity=1, price=99.99)
        ],
        payment_method="VISA-4111",
        shipping_address="789 Pine St, Elsewhere, ST 11111",
        amount=99.99
    )
    
    print(f"Processing order: {order.order_id}")
    print(f"Product: {order.items[0].product_id} (out of stock)")
    
    saga = OrderProcessingSaga()
    context = SagaContext(correlation_id=f"SAGA-{uuid.uuid4().hex[:8]}")
    
    try:
        print("\n📋 Step 1: Validating order...")
        validation = await saga.validate_order(order, context)
        print(f"✅ Order validated: {validation.validation_id}")
        
        print("\n📦 Step 2: Reserving inventory...")
        reservation = await saga.reserve_inventory(validation, context)
        print(f"✅ Inventory reserved: {reservation.reservation_id}")
        
    except Exception as e:
        print(f"❌ Inventory reservation failed: {e}")
        print("ℹ️  No compensation needed - no external state was changed")


async def main():
    """Main example runner demonstrating comprehensive SAGA patterns."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("🏛️  SAGA Pattern Comprehensive Examples")
    print("=" * 50)
    print()
    print("This example demonstrates the key concepts of SAGA pattern:")
    print("• Step dependencies and execution order")
    print("• Compensation methods for rollback")
    print("• Context variables for data sharing")
    print("• Error handling and recovery")
    
    # Run different scenarios
    await run_successful_order()
    await run_payment_failure_scenario()
    await run_inventory_failure_scenario()
    
    print("\n✨ All SAGA examples completed!")
    print("\n📚 Key SAGA Pattern Concepts Demonstrated:")
    print("1. Forward Recovery: Steps execute in dependency order")
    print("2. Backward Recovery: Compensation methods undo completed steps")
    print("3. Eventual Consistency: System reaches consistent state over time")
    print("4. Data Flow: Results from previous steps inform later steps")
    print("5. Context Variables: Share data between steps and compensations")
    
    print("\n🔧 Integration with Java lib-transactional-engine:")
    print("• Python decorators map to Java @SagaStep annotations")
    print("• Compensation methods correspond to compensate attribute")
    print("• Context variables enable data sharing between steps")
    print("• Step dependencies ensure proper execution ordering")


if __name__ == "__main__":
    asyncio.run(main())