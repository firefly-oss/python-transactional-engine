#!/usr/bin/env python3
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
import uuid
from typing import Any, Dict

from fireflytx import SagaEngine
from fireflytx.core.saga import Saga
from fireflytx.events import (
    KafkaStepEventPublisher,
    NoOpStepEventPublisher,
    create_step_event,
    EventType
)
from fireflytx.persistence import (
    RedisSagaPersistenceProvider,
    DatabaseSagaPersistenceProvider,
    NoOpSagaPersistenceProvider
)
from fireflytx.config import TransactionalEngineConfig, PersistenceConfig, EventsConfig


class PaymentProcessingSaga(Saga):
    """
    Example SAGA demonstrating event publishing and persistence configuration.
    
    This SAGA processes a payment with steps for validation, authorization,
    and settlement, with comprehensive event publishing and state persistence.
    """
    
    def __init__(self, payment_amount: float, customer_id: str, merchant_id: str):
        super().__init__()
        self.payment_amount = payment_amount
        self.customer_id = customer_id
        self.merchant_id = merchant_id
        self.authorization_id = None
        self.settlement_id = None
    
    def define_steps(self):
        """Define the payment processing steps."""
        self.add_step(
            step_id="validate_payment",
            action=self._validate_payment,
            compensation=self._cancel_validation
        )
        
        self.add_step(
            step_id="authorize_payment",
            action=self._authorize_payment,
            compensation=self._reverse_authorization
        )
        
        self.add_step(
            step_id="settle_payment",
            action=self._settle_payment,
            compensation=self._reverse_settlement
        )
    
    async def _validate_payment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payment details."""
        print(f"Validating payment of ${self.payment_amount} for customer {self.customer_id}")
        
        # Simulate validation logic
        if self.payment_amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        if not self.customer_id:
            raise ValueError("Customer ID is required")
        
        validation_result = {
            "validated": True,
            "validation_timestamp": "2025-01-27T10:30:00Z",
            "customer_verified": True
        }
        
        print(f"Payment validation successful: {validation_result}")
        return validation_result
    
    async def _cancel_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel payment validation."""
        print(f"Cancelling payment validation for customer {self.customer_id}")
        return {"validation_cancelled": True}
    
    async def _authorize_payment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Authorize the payment."""
        self.authorization_id = f"auth_{uuid.uuid4().hex[:8]}"
        
        print(f"Authorizing payment ${self.payment_amount} with ID {self.authorization_id}")
        
        # Simulate authorization logic
        auth_result = {
            "authorized": True,
            "authorization_id": self.authorization_id,
            "authorization_timestamp": "2025-01-27T10:31:00Z",
            "available_balance": self.payment_amount + 1000
        }
        
        print(f"Payment authorization successful: {auth_result}")
        return auth_result
    
    async def _reverse_authorization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse the payment authorization."""
        print(f"Reversing authorization {self.authorization_id}")
        
        reversal_result = {
            "authorization_reversed": True,
            "authorization_id": self.authorization_id,
            "reversal_timestamp": "2025-01-27T10:32:00Z"
        }
        
        print(f"Authorization reversal completed: {reversal_result}")
        return reversal_result
    
    async def _settle_payment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Settle the payment."""
        self.settlement_id = f"settle_{uuid.uuid4().hex[:8]}"
        
        print(f"Settling payment ${self.payment_amount} to merchant {self.merchant_id}")
        
        # Simulate settlement logic
        settlement_result = {
            "settled": True,
            "settlement_id": self.settlement_id,
            "settlement_timestamp": "2025-01-27T10:33:00Z",
            "merchant_account_credited": True
        }
        
        print(f"Payment settlement successful: {settlement_result}")
        return settlement_result
    
    async def _reverse_settlement(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse the payment settlement."""
        print(f"Reversing settlement {self.settlement_id}")
        
        reversal_result = {
            "settlement_reversed": True,
            "settlement_id": self.settlement_id,
            "merchant_account_debited": True,
            "reversal_timestamp": "2025-01-27T10:34:00Z"
        }
        
        print(f"Settlement reversal completed: {reversal_result}")
        return reversal_result


async def demonstrate_noop_configuration():
    """Demonstrate SAGA execution with no-op event publishing and persistence."""
    print("=== No-Op Configuration Demo ===")
    
    # Create no-op providers
    event_publisher = NoOpStepEventPublisher()
    persistence_provider = NoOpSagaPersistenceProvider()
    
    # Configure the engine
    config = TransactionalEngineConfig(
        events=EventsConfig(
            enabled=False,
            publisher_type="noop"
        ),
        persistence=PersistenceConfig(
            enabled=False,
            provider_type="noop"
        )
    )
    
    engine = SagaEngine(
        config=config,
        event_publisher=event_publisher,
        persistence_provider=persistence_provider
    )
    
    # Create and execute SAGA
    saga = PaymentProcessingSaga(
        payment_amount=150.00,
        customer_id="cust_12345",
        merchant_id="merch_67890"
    )
    
    result = await engine.execute_saga(saga)
    print(f"SAGA execution result: {result.status}")
    
    # Demonstrate event creation
    event = create_step_event(
        saga_name="PaymentProcessingSaga",
        saga_id=saga.saga_id,
        step_id="validate_payment",
        event_type=EventType.STEP_STARTED,
        payload={"amount": 150.00, "customer": "cust_12345"}
    )
    
    await event_publisher.publish(event)
    print(f"Published event: {event.event_type.value}")


async def demonstrate_kafka_redis_configuration():
    """Demonstrate SAGA execution with Kafka events and Redis persistence."""
    print("\n=== Kafka + Redis Configuration Demo ===")
    
    # Create Kafka event publisher
    event_publisher = KafkaStepEventPublisher(
        bootstrap_servers="localhost:9092",
        default_topic="payment-events",
        key_serializer="string",
        value_serializer="json",
        acks="all",
        retries=3
    )
    
    # Create Redis persistence provider
    persistence_provider = RedisSagaPersistenceProvider(
        host="localhost",
        port=6379,
        database=0,
        key_prefix="payment_saga:",
        ttl_seconds=3600,
        max_connections=10
    )
    
    # Configure the engine
    config = TransactionalEngineConfig(
        events=EventsConfig(
            enabled=True,
            publisher_type="kafka",
            config=event_publisher.get_publisher_config()
        ),
        persistence=PersistenceConfig(
            enabled=True,
            provider_type="redis",
            config=persistence_provider.get_provider_config()
        )
    )
    
    engine = SagaEngine(
        config=config,
        event_publisher=event_publisher,
        persistence_provider=persistence_provider
    )
    
    # Create and execute SAGA
    saga = PaymentProcessingSaga(
        payment_amount=250.00,
        customer_id="cust_54321",
        merchant_id="merch_09876"
    )
    
    result = await engine.execute_saga(saga)
    print(f"SAGA execution result: {result.status}")
    
    # Demonstrate custom event publishing
    events = [
        create_step_event(
            saga_name="PaymentProcessingSaga",
            saga_id=saga.saga_id,
            step_id="validate_payment",
            event_type=EventType.STEP_COMPLETED,
            payload={"validation_result": "success"},
            topic="payment-validation-events"
        ),
        create_step_event(
            saga_name="PaymentProcessingSaga",
            saga_id=saga.saga_id,
            step_id="authorize_payment", 
            event_type=EventType.STEP_COMPLETED,
            payload={"authorization_id": saga.authorization_id},
            topic="payment-authorization-events"
        )
    ]
    
    for event in events:
        await event_publisher.publish(event)
        print(f"Published event to {event.topic}: {event.event_type.value}")


async def demonstrate_database_configuration():
    """Demonstrate SAGA execution with database persistence."""
    print("\n=== Database Configuration Demo ===")
    
    # Create database persistence provider
    persistence_provider = DatabaseSagaPersistenceProvider(
        connection_url="jdbc:postgresql://localhost:5432/saga_db",
        table_prefix="payment_",
        schema="transactions",
        connection_timeout=5000,
        max_pool_size=20
    )
    
    # Create no-op event publisher for this demo
    event_publisher = NoOpStepEventPublisher()
    
    # Configure the engine
    config = TransactionalEngineConfig(
        events=EventsConfig(
            enabled=False,
            publisher_type="noop"
        ),
        persistence=PersistenceConfig(
            enabled=True,
            provider_type="database",
            config=persistence_provider.get_provider_config()
        )
    )
    
    engine = SagaEngine(
        config=config,
        event_publisher=event_publisher,
        persistence_provider=persistence_provider
    )
    
    # Create and execute SAGA
    saga = PaymentProcessingSaga(
        payment_amount=75.00,
        customer_id="cust_99999",
        merchant_id="merch_11111"
    )
    
    result = await engine.execute_saga(saga)
    print(f"SAGA execution result: {result.status}")
    
    # Demonstrate persistence operations
    saga_context = {
        "payment_amount": saga.payment_amount,
        "customer_id": saga.customer_id,
        "merchant_id": saga.merchant_id,
        "status": "completed"
    }
    
    await persistence_provider.persist_saga(saga.saga_id, saga_context)
    print(f"Persisted SAGA context to database")
    
    retrieved_context = await persistence_provider.retrieve_saga(saga.saga_id)
    print(f"Retrieved SAGA context: {retrieved_context}")


async def main():
    """Main demonstration function."""
    print("Firefly Transactional Engine - Events & Persistence Demo")
    print("=" * 60)
    
    try:
        # Demonstrate different configurations
        await demonstrate_noop_configuration()
        await demonstrate_kafka_redis_configuration()
        await demonstrate_database_configuration()
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("\nKey features demonstrated:")
        print("- No-op event publishing and persistence for testing")
        print("- Kafka event publishing with configurable topics")
        print("- Redis-based SAGA state persistence")
        print("- Database-based SAGA state persistence")
        print("- Event creation and publishing APIs")
        print("- Configuration-driven provider selection")
        print("\nArchitecture: Python defines, Java executes")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())