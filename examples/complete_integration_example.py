#!/usr/bin/env python3
"""
Complete Integration Example: Python Defines, Java Executes

This example demonstrates the complete "Python defines, Java executes" architecture
with step event decorators, configuration generation, callback interfaces, and
clean APIs for SAGA definition and execution.

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0 (the "License");
"""

import asyncio
import logging
from typing import Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all required components
from fireflytx import (
    SagaEngine,
    saga, saga_step, compensation_step, step_events,
    KafkaStepEventPublisher, NoOpStepEventPublisher,
    RedisSagaPersistenceProvider, NoOpSagaPersistenceProvider,
    generate_saga_engine_config
)


# Define comprehensive SAGA with step events
@saga("e-commerce-order-processing", layer_concurrency=3)
class ECommerceOrderSaga:
    """
    Comprehensive e-commerce order processing SAGA.
    
    This SAGA demonstrates:
    - Step event configuration with decorators
    - Multiple step dependencies
    - Compensation logic
    - Parameter injection
    - Custom event topics and headers
    """
    
    def __init__(self):
        self.order_id = None
        self.customer_id = None
        self.total_amount = 0.0
        self.inventory_reserved = False
        self.payment_charged = False
        self.shipping_scheduled = False
    
    @step_events(
        topic="order-validation-events",
        key_template="{saga_id}-validation",
        include_timing=True,
        custom_headers={"service": "validation", "priority": "high"},
        publish_on_retry=True
    )
    @saga_step("validate-order", retry=5, timeout_ms=10000)
    async def validate_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the incoming order."""
        self.order_id = order_data.get("order_id")
        self.customer_id = order_data.get("customer_id")
        self.total_amount = order_data.get("total_amount", 0.0)
        
        logger.info(f"Validating order {self.order_id} for customer {self.customer_id}")
        
        # Simulate validation logic
        if not self.order_id:
            raise ValueError("Order ID is required")
        
        if self.total_amount <= 0:
            raise ValueError("Order amount must be positive")
        
        if not self.customer_id:
            raise ValueError("Customer ID is required")
        
        # Simulate async validation
        await asyncio.sleep(0.1)
        
        validation_result = {
            "validated": True,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "total_amount": self.total_amount,
            "validation_timestamp": "2025-01-27T12:00:00Z"
        }
        
        logger.info(f"Order {self.order_id} validation successful")
        return validation_result
    
    @step_events(
        topic="inventory-events",
        key_template="{saga_id}-inventory",
        include_context=True,
        include_result=True,
        custom_headers={"service": "inventory", "operation": "reserve"}
    )
    @saga_step("reserve-inventory", depends_on=["validate-order"], 
               retry=3, backoff_ms=2000, compensate="release_inventory")
    async def reserve_inventory(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reserve inventory for the order."""
        logger.info(f"Reserving inventory for order {self.order_id}")
        
        # Simulate inventory check
        await asyncio.sleep(0.05)
        
        # Simulate inventory reservation
        items = order_data.get("items", [])
        reserved_items = []
        
        for item in items:
            reserved_items.append({
                "item_id": item.get("item_id"),
                "quantity": item.get("quantity"),
                "reserved_at": "2025-01-27T12:01:00Z",
                "reservation_id": f"res_{item.get('item_id')}_{self.order_id}"
            })
        
        self.inventory_reserved = True
        
        reservation_result = {
            "reserved": True,
            "order_id": self.order_id,
            "reserved_items": reserved_items,
            "reservation_expires_at": "2025-01-27T12:15:00Z"
        }
        
        logger.info(f"Inventory reserved for order {self.order_id}")
        return reservation_result
    
    @step_events(
        topic="payment-events", 
        key_template="{customer_id}-payment",
        include_payload=True,
        include_timing=True,
        custom_headers={"service": "payment", "operation": "charge"},
        publish_on_failure=True
    )
    @saga_step("process-payment", depends_on=["validate-order", "reserve-inventory"],
               retry=3, timeout_ms=15000, compensate="refund_payment")
    async def process_payment(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for the order."""
        logger.info(f"Processing payment for order {self.order_id}")
        
        # Simulate payment processing
        await asyncio.sleep(0.1)
        
        payment_method = order_data.get("payment_method", "credit_card")
        
        # Simulate payment charge
        payment_result = {
            "charged": True,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "amount": self.total_amount,
            "payment_method": payment_method,
            "transaction_id": f"txn_{self.order_id}_001",
            "charged_at": "2025-01-27T12:02:00Z"
        }
        
        self.payment_charged = True
        logger.info(f"Payment processed for order {self.order_id}: ${self.total_amount}")
        return payment_result
    
    @step_events(
        topic="shipping-events",
        key_template="{order_id}-shipping",
        include_result=True,
        custom_headers={"service": "shipping", "operation": "schedule"}
    )
    @saga_step("schedule-shipping", depends_on=["process-payment"],
               timeout_ms=5000, compensate="cancel_shipping")
    async def schedule_shipping(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule shipping for the order."""
        logger.info(f"Scheduling shipping for order {self.order_id}")
        
        # Simulate shipping scheduling
        await asyncio.sleep(0.05)
        
        shipping_address = order_data.get("shipping_address", {})
        
        shipping_result = {
            "scheduled": True,
            "order_id": self.order_id,
            "shipping_id": f"ship_{self.order_id}",
            "estimated_delivery": "2025-01-30T12:00:00Z",
            "shipping_address": shipping_address,
            "scheduled_at": "2025-01-27T12:03:00Z"
        }
        
        self.shipping_scheduled = True
        logger.info(f"Shipping scheduled for order {self.order_id}")
        return shipping_result
    
    @step_events(
        topic="notification-events",
        key_template="{customer_id}-notification",
        custom_headers={"service": "notification", "type": "confirmation"}
    )
    @saga_step("send-confirmation", depends_on=["schedule-shipping"])
    async def send_confirmation(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send order confirmation to customer."""
        logger.info(f"Sending confirmation for order {self.order_id}")
        
        # Simulate notification sending
        await asyncio.sleep(0.02)
        
        confirmation_result = {
            "sent": True,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "confirmation_id": f"conf_{self.order_id}",
            "sent_at": "2025-01-27T12:04:00Z"
        }
        
        logger.info(f"Confirmation sent for order {self.order_id}")
        return confirmation_result
    
    # Compensation methods
    @compensation_step("reserve-inventory")
    async def release_inventory(self, reservation_data: Dict[str, Any]) -> None:
        """Release reserved inventory."""
        logger.info(f"Releasing inventory for order {self.order_id}")
        await asyncio.sleep(0.02)
        self.inventory_reserved = False
        logger.info(f"Inventory released for order {self.order_id}")
    
    @compensation_step("process-payment")
    async def refund_payment(self, payment_data: Dict[str, Any]) -> None:
        """Refund the processed payment."""
        logger.info(f"Refunding payment for order {self.order_id}")
        await asyncio.sleep(0.05)
        self.payment_charged = False
        logger.info(f"Payment refunded for order {self.order_id}: ${self.total_amount}")
    
    @compensation_step("schedule-shipping")
    async def cancel_shipping(self, shipping_data: Dict[str, Any]) -> None:
        """Cancel scheduled shipping."""
        logger.info(f"Cancelling shipping for order {self.order_id}")
        await asyncio.sleep(0.01)
        self.shipping_scheduled = False
        logger.info(f"Shipping cancelled for order {self.order_id}")


async def demonstrate_configuration_generation():
    """Demonstrate Java configuration generation."""
    print("\n=== Configuration Generation Demo ===")
    
    # Create event publisher and persistence provider
    event_publisher = KafkaStepEventPublisher(
        bootstrap_servers="kafka-cluster:9092",
        default_topic="ecommerce-saga-events",
        key_serializer="string",
        value_serializer="json",
        acks="all",
        retries=5,
        compression_type="snappy"
    )
    
    persistence_provider = RedisSagaPersistenceProvider(
        host="redis-cluster",
        port=6379,
        database=1,
        key_prefix="ecommerce_saga:",
        ttl_seconds=7200,
        max_connections=50
    )
    
    # Generate complete configuration
    config = generate_saga_engine_config(
        engine_name="ecommerce-production-engine",
        saga_classes=[ECommerceOrderSaga],
        event_publisher=event_publisher,
        persistence_provider=persistence_provider,
        compensation_policy="STRICT_SEQUENTIAL",
        auto_optimization_enabled=True,
        thread_pool_size=20,
        max_concurrent_sagas=500
    )
    
    print(f"Generated configuration with {len(config)} top-level sections:")
    print(f"  - Engine config: {len(config['engine'])} properties")
    print(f"  - SAGA configs: {len(config['sagas'])} SAGAs")
    print(f"  - Global metadata: {len(config['global_metadata'])} properties")
    
    # Show step event configurations
    saga_config = config['sagas'][0]
    event_steps = [
        step for step in saga_config['steps']
        if step.get('events', {}).get('enabled', False)
    ]
    
    print(f"  - Steps with events: {len(event_steps)} out of {len(saga_config['steps'])}")
    
    for step in event_steps:
        step_id = step['step_id']
        events = step['events']
        topic = events.get('topic', 'default')
        print(f"    • {step_id}: topic={topic}, timing={events['include_timing']}")
    
    print("✅ Configuration generation completed")


async def demonstrate_saga_execution():
    """Demonstrate SAGA execution with event publishing and persistence."""
    print("\n=== SAGA Execution Demo ===")
    
    # Create execution engine with Kafka and Redis (in production)
    # For demo, we'll use NoOp implementations
    engine = SagaEngine(
        event_publisher=NoOpStepEventPublisher(),
        persistence_provider=NoOpSagaPersistenceProvider(),
        compensation_policy="STRICT_SEQUENTIAL",
        auto_optimization_enabled=True
    )

    # Initialize the engine
    await engine.initialize()
    print("✅ Engine initialized")
    
    try:
        # Execute the SAGA with sample order data
        order_data = {
            "order_id": "ORDER-001",
            "customer_id": "CUST-12345",
            "total_amount": 299.99,
            "items": [
                {"item_id": "ITEM-001", "quantity": 2, "price": 149.99},
                {"item_id": "ITEM-002", "quantity": 1, "price": 149.99}
            ],
            "payment_method": "credit_card",
            "shipping_address": {
                "street": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105"
            }
        }
        
        print(f"Executing SAGA for order: {order_data['order_id']}")

        # Execute the SAGA via Java engine
        result = await engine.execute(ECommerceOrderSaga, order_data)

        if result.is_success:
            print(f"✅ SAGA completed successfully")
            print(f"   Duration: {result.duration_ms}ms")
            print(f"   Steps completed: {len(result.steps) if result.steps else 0}")
        else:
            print(f"❌ SAGA failed: {result.error}")
            print(f"   Failed steps: {result.failed_steps}")
            print(f"   Compensated steps: {result.compensated_steps}")
            
    except Exception as e:
        print(f"❌ SAGA execution failed: {e}")
    
    finally:
        await engine.shutdown()
        print("✅ SAGA execution demonstration completed")


async def demonstrate_callback_interfaces():
    """Demonstrate callback interface functionality."""
    print("\n=== Callback Interface Demo ===")

    from fireflytx.integration.callbacks import PythonCallbackHandler

    # Create callback handler with SAGA class
    callback_handler = PythonCallbackHandler(saga_class=ECommerceOrderSaga)

    print("✅ Callback handler created and SAGA registered")
    print(f"   Callback URL: http://{callback_handler.host}:{callback_handler.port}")
    print(f"   SAGA class: {callback_handler.saga_class.__name__}")
    print("✅ Callback interface demonstration completed")


async def main():
    """Run the complete integration demonstration."""
    print("🚀 Complete Integration Example: Python Defines, Java Executes")
    print("=" * 70)
    
    try:
        await demonstrate_configuration_generation()
        await demonstrate_callback_interfaces()
        await demonstrate_saga_execution()
        
        print("\n" + "=" * 70)
        print("🎉 Complete Integration Demonstration Successful!")
        print("\n✨ Features Demonstrated:")
        print("   ✅ Step event decorators with custom configuration")
        print("   ✅ Java configuration generation for lib-transactional-engine")
        print("   ✅ Python callback interfaces for business logic")
        print("   ✅ Clean API for SAGA definition and execution")
        print("   ✅ Orchestration delegation to Java subprocess bridge")
        print("   ✅ Event publishing configuration and execution")
        print("   ✅ Persistence provider configuration")
        print("   ✅ Compensation logic and error handling")
        print("\n🏗️  Architecture: Python defines, Java executes")
        print("   • Python defines SAGA structure, events, and business logic")
        print("   • Java lib-transactional-engine handles orchestration, persistence, events")
        print("   • Clean separation of concerns with maximum reliability")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())