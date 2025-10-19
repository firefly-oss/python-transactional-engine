# SAGA Pattern Guide

> **📚 Learning Objectives:** By the end of this guide, you'll understand how to design, implement, and troubleshoot SAGA patterns using FireflyTX.

**Last Updated:** 2025-10-19

---

## Table of Contents

1. [What is the SAGA Pattern?](#what-is-the-saga-pattern)
2. [When to Use SAGAs](#when-to-use-sagas)
3. [Basic Concepts](#basic-concepts)
4. [Step-by-Step Tutorial](#step-by-step-tutorial)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [Common Pitfalls](#common-pitfalls)
8. [Troubleshooting](#troubleshooting)
9. [Real-World Examples](#real-world-examples)

---

## What is the SAGA Pattern?

### The Problem

Imagine you're building an e-commerce system. When a customer places an order, you need to:

1. Validate the order
2. Reserve inventory
3. Charge the customer's payment method
4. Send a confirmation email

**What if step 3 (payment) fails?** You need to:
- Release the inventory reservation (undo step 2)
- Mark the order as failed (undo step 1)

In a distributed system, you can't use traditional database transactions across services. **This is where SAGAs come in.**

### The Solution

A **SAGA** is a sequence of local transactions where each transaction:
- Updates data within a single service
- Has a **compensation** (undo) operation

If any step fails, the SAGA executes compensations in reverse order to undo the work.

### Visual Example

```
Success Path:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Validate   │ ──>│  Reserve    │ ──>│   Charge    │ ──>│    Send     │
│   Order     │    │  Inventory  │    │   Payment   │    │    Email    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘

Failure Path (Payment fails):
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Validate   │ ──>│  Reserve    │ ──>│   Charge    │ ❌ FAILED
│   Order     │    │  Inventory  │    │   Payment   │
└─────────────┘    └─────────────┘    └─────────────┘
      │                  │                 │
      │                  ▼                 │
      │         ┌─────────────┐            │
      │         │  Release    │ <──────────┘
      │         │  Inventory  │ (Compensation)
      │         └─────────────┘
      │                ✅
      ▼
┌─────────────┐
│   Cancel    │
│   Order     │ (Compensation)
└─────────────┘
      ✅
```

---

## When to Use SAGAs

### ✅ Use SAGAs When:

| Scenario | Why SAGA? |
|----------|-----------|
| **Microservices coordination** | Each service manages its own data |
| **Long-running workflows** | Can span minutes, hours, or days |
| **Eventually consistent is OK** | Don't need immediate consistency |
| **Complex business processes** | Multiple steps with dependencies |
| **Need observability** | Built-in events and logging |

### ❌ Don't Use SAGAs When:

| Scenario | Use Instead |
|----------|-------------|
| **Need strong consistency** | TCC pattern or distributed transactions |
| **Single database** | Local database transactions |
| **Simple CRUD operations** | Direct API calls |
| **No compensation possible** | Rethink your design |

---

## Basic Concepts

### Prerequisites

Before diving in, you should understand:
- **Python async/await** - SAGAs use asyncio
- **Decorators** - SAGAs are defined with decorators
- **Distributed systems basics** - Understanding of microservices helps

### Core Components

#### 1. SAGA Definition

A SAGA is a Python class decorated with `@saga`:

```python
from fireflytx.decorators.saga import saga

@saga("payment-processing")  # ← SAGA name (must be unique)
class PaymentSaga:
    """Process payments with automatic rollback on failure."""
    pass
```

#### 2. SAGA Steps

Steps are methods decorated with `@saga_step`:

```python
from fireflytx.decorators.saga import saga_step

@saga_step("validate-payment")  # ← Step ID (must be unique within SAGA)
async def validate_payment(self, payment_data):
    """Validate payment information."""
    # Your business logic here
    return {"validated": True}
```

**Step Signature:**
```python
async def step_name(
    self,
    input_data: dict,           # Input data for this step
) -> dict:                      # Must return a dictionary
    ...
```

> **Note:** The actual step methods receive input data directly. The Java engine handles context management internally.

#### 3. Compensation Steps

Compensations undo the work of a step:

```python
from fireflytx.decorators.saga import saga_step, compensation_step

@saga_step("charge-payment")
async def charge_payment(self, payment_data):
    """Charge the customer's payment method."""
    charge_id = await payment_service.charge(payment_data["amount"])
    return {"charge_id": charge_id}

@compensation_step("charge-payment")  # ← Links to the step above
async def refund_payment(self, charge_result):
    """Refund the payment (compensation)."""
    await payment_service.refund(charge_result["charge_id"])
    return {"refunded": True}
```

**Compensation Signature:**
```python
async def compensation_name(
    self,
    step_result: dict,          # Result from the original step
) -> None:                      # Can return None or dict for logging
    ...
```

#### 4. Dependencies

Control execution order with `depends_on`:

```python
@saga_step("validate-order")
async def validate_order(self, order_data):
    return {"validated": True}

@saga_step("reserve-inventory", depends_on=["validate-order"])
async def reserve_inventory(self, order_data):
    # This runs AFTER validate-order completes
    return {"reserved": True}

@saga_step("charge-payment", depends_on=["reserve-inventory"])
async def charge_payment(self, order_data):
    # This runs AFTER reserve-inventory completes
    return {"charged": True}
```

**Dependency Graph:**
```
validate-order
      │
      ▼
reserve-inventory
      │
      ▼
charge-payment
```

**Multiple Dependencies (Parallel Execution):**
```python
@saga_step("validate-customer")
async def validate_customer(self, data):
    return {"valid": True}

@saga_step("validate-product")
async def validate_product(self, data):
    return {"valid": True}

@saga_step("process-order", depends_on=["validate-customer", "validate-product"])
async def process_order(self, data):
    # This runs AFTER BOTH validations complete
    # validate-customer and validate-product run in PARALLEL
    return {"processed": True}
```

**Dependency Graph:**
```
validate-customer ─┐
                   ├─> process-order
validate-product ──┘
```

---

## Step-by-Step Tutorial

### Tutorial: Build an E-Commerce Order SAGA

Let's build a complete order processing SAGA from scratch.

#### Step 1: Define the SAGA Class

```python
from fireflytx.decorators.saga import saga, saga_step, compensation_step

@saga("e-commerce-order")
class OrderProcessingSaga:
    """
    Process e-commerce orders with automatic rollback.

    Steps:
    1. Validate order data
    2. Reserve inventory
    3. Charge payment
    4. Send confirmation email
    """

    def __init__(self):
        # Optional: Initialize any instance variables
        pass
```

#### Step 2: Add the First Step (Validation)

```python
@saga_step("validate-order", retry=3, timeout_ms=5000)
async def validate_order(self, order_data):
    """
    Validate order data and business rules.

    Args:
        order_data: Order information

    Returns:
        Validation result
    """
    # Validate required fields
    if not order_data.get("customer_id"):
        raise ValueError("Missing customer_id")

    if not order_data.get("items") or len(order_data["items"]) == 0:
        raise ValueError("Order must have at least one item")

    # Validate total amount
    total = sum(item["price"] * item["quantity"] for item in order_data["items"])
    if total <= 0:
        raise ValueError("Invalid order total")

    validation_id = f"VAL-{order_data['order_id']}"

    return {
        "validation_id": validation_id,
        "total_amount": total,
        "status": "validated"
    }
```

**Key Points:**
- `retry=3` - Retry up to 3 times on failure
- `timeout_ms=5000` - Timeout after 5 seconds
- Return a dictionary with the result
- The Java engine handles context management internally

#### Step 3: Add Inventory Reservation

```python
@saga_step("reserve-inventory", depends_on=["validate-order"])
async def reserve_inventory(self, order_data, context: SagaContext):
    """
    Reserve inventory for order items.
    
    This step depends on validate-order completing first.
    """
    reservations = []
    
    for item in order_data["items"]:
        # Call inventory service to reserve items
        reservation = await inventory_service.reserve(
            product_id=item["product_id"],
            quantity=item["quantity"],
            order_id=order_data["order_id"]
        )
        reservations.append(reservation)
    
    # Store reservation IDs for compensation
    reservation_ids = [r["reservation_id"] for r in reservations]
    context.set_data("reservation_ids", reservation_ids)
    
    return {
        "reservations": reservations,
        "status": "reserved"
    }

@compensation_step("reserve-inventory")
async def release_inventory(self, reservation_result, context: SagaContext):
    """
    Release inventory reservations (compensation).
    
    This is called if a later step fails.
    """
    reservation_ids = context.get_data("reservation_ids", [])
    
    for reservation_id in reservation_ids:
        await inventory_service.release(reservation_id)
    
    return {
        "released": len(reservation_ids),
        "status": "compensated"
    }
```

**Key Points:**
- `depends_on=["validate-order"]` - Runs after validation
- Always provide compensation for state-changing operations
- Use context to pass data to compensation

#### Step 4: Add Payment Processing

```python
@saga_step("charge-payment", depends_on=["reserve-inventory"], retry=5)
async def charge_payment(self, order_data, context: SagaContext):
    """
    Charge the customer's payment method.
    
    Uses idempotency key to prevent double-charging on retry.
    """
    total_amount = context.get_data("total_amount")
    
    # Use correlation_id as idempotency key
    idempotency_key = f"{context.correlation_id}-payment"
    
    # Charge payment (idempotent)
    charge = await payment_service.charge(
        amount=total_amount,
        customer_id=order_data["customer_id"],
        payment_method=order_data["payment_method"],
        idempotency_key=idempotency_key
    )
    
    context.set_data("charge_id", charge["id"])
    
    return {
        "charge_id": charge["id"],
        "amount": total_amount,
        "status": "charged"
    }

@compensation_step("charge-payment")
async def refund_payment(self, charge_result, context: SagaContext):
    """
    Refund the payment (compensation).
    """
    charge_id = context.get_data("charge_id")
    
    if charge_id:
        refund = await payment_service.refund(charge_id)
        return {
            "refund_id": refund["id"],
            "status": "refunded"
        }
    
    return {"status": "no_charge_to_refund"}
```

**Key Points:**
- Use idempotency keys to prevent double-charging
- `retry=5` - Payment operations often have transient failures
- Check if charge exists before refunding

#### Step 5: Add Confirmation Email

```python
@saga_step("send-confirmation", depends_on=["charge-payment"])
async def send_confirmation(self, order_data, context: SagaContext):
    """
    Send order confirmation email.
    
    Note: Email sending typically doesn't need compensation
    (it's OK if customer gets an email even if we later cancel)
    """
    await email_service.send(
        to=order_data["customer_email"],
        template="order_confirmation",
        data={
            "order_id": order_data["order_id"],
            "total": context.get_data("total_amount"),
            "items": order_data["items"]
        }
    )
    
    return {
        "email_sent": True,
        "status": "completed"
    }
```

**Key Points:**
- Not all steps need compensation
- Email sending is typically idempotent (OK to send multiple times)

#### Step 6: Execute the SAGA

```python
from fireflytx import SagaEngine
import asyncio

async def main():
    # Create and initialize engine
    engine = SagaEngine()
    await engine.initialize()

    # Order data
    order_data = {
        "order_id": "ORD-12345",
        "customer_id": "CUST-789",
        "customer_email": "customer@example.com",
        "payment_method": "card_xyz",
        "items": [
            {"product_id": "PROD-001", "quantity": 2, "price": 29.99},
            {"product_id": "PROD-002", "quantity": 1, "price": 49.99}
        ]
    }

    # Execute SAGA by class
    result = await engine.execute_by_class(
        OrderProcessingSaga,
        order_data
    )

    # Check result
    if result.is_success:
        print(f"✅ Order {order_data['order_id']} processed successfully!")
        print(f"   Duration: {result.duration_ms}ms")
        print(f"   Steps completed: {list(result.steps.keys())}")
    else:
        print(f"❌ Order {order_data['order_id']} failed!")
        print(f"   Error: {result.error}")
        print(f"   Failed at step: {result.failed_step}")
        print(f"   Compensated steps: {result.compensated_steps}")

    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

**Output (Success):**
```
✅ Order ORD-12345 processed successfully!
   Duration: 1234ms
   Steps completed: ['validate-order', 'reserve-inventory', 'charge-payment', 'send-confirmation']
```

**Output (Failure at payment):**
```
❌ Order ORD-12345 failed!
   Error: Payment declined
   Failed at step: charge-payment
   Compensated steps: ['reserve-inventory']
```

---

## Advanced Features

### 1. Parallel Execution

Steps without dependencies run in parallel:

```python
@saga("parallel-validation")
class ParallelValidationSaga:
    # These three steps have no dependencies - run in PARALLEL
    @saga_step("validate-customer")
    async def validate_customer(self, data):
        await asyncio.sleep(1)  # Simulates API call
        return {"valid": True}
    
    @saga_step("validate-product")
    async def validate_product(self, data):
        await asyncio.sleep(1)  # Simulates API call
        return {"valid": True}
    
    @saga_step("validate-payment-method")
    async def validate_payment_method(self, data):
        await asyncio.sleep(1)  # Simulates API call
        return {"valid": True}
    
    # This step waits for ALL three validations
    @saga_step("process", depends_on=["validate-customer", "validate-product", "validate-payment-method"])
    async def process(self, data):
        return {"processed": True}
```

**Execution Timeline:**
```
Time 0ms:  validate-customer    ─┐
           validate-product      ─┼─> All start simultaneously
           validate-payment-method─┘

Time 1000ms: All three complete

Time 1001ms: process starts
```

**Total time: ~1000ms** (not 3000ms!)

### 2. Data Flow Between Steps

> **Note:** In the current implementation, the Java engine manages data flow between steps based on dependencies. Step results are automatically passed to dependent steps.

```python
from fireflytx.decorators.saga import saga_step

@saga_step("calculate-tax")
async def calculate_tax(self, order_data):
    tax = order_data["subtotal"] * 0.08
    return {"tax": tax, "subtotal": order_data["subtotal"]}

@saga_step("calculate-shipping", depends_on=["calculate-tax"])
async def calculate_shipping(self, order_data):
    shipping = 10.00 if order_data["subtotal"] < 50 else 0.00
    return {"shipping": shipping, "subtotal": order_data["subtotal"], "tax": order_data["tax"]}

@saga_step("generate-invoice", depends_on=["calculate-tax", "calculate-shipping"])
async def generate_invoice(self, order_data):
    # The Java engine provides results from dependent steps
    subtotal = order_data["subtotal"]
    tax = order_data["tax"]
    shipping = order_data["shipping"]
    total = subtotal + tax + shipping

    return {
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": total
    }
```

### 3. Event Publishing

Publish events for monitoring and integration:

```python
from fireflytx.decorators.saga import saga_step, step_events

@step_events(
    topic="order-events",
    include_timing=True,
    include_payload=True,
    publish_on_start=True,
    publish_on_success=True,
    publish_on_failure=True
)
@saga_step("process-order")
async def process_order(self, order_data):
    # Events automatically published:
    # - order.process.started
    # - order.process.completed (or failed)
    return {"processed": True}
```

### 4. Conditional Execution

Execute steps conditionally:

```python
@saga_step("apply-discount", condition=lambda data: data.get("discount_code") is not None)
async def apply_discount(self, order_data):
    """Only runs if discount_code is provided."""
    discount = await discount_service.apply(order_data["discount_code"])
    return {"discount": discount}
```

---

## Best Practices

> **💡 Learn from experience:** These practices will save you hours of debugging and prevent production issues.

### 1. Always Make Operations Idempotent

**Why?** Steps can be retried multiple times. Non-idempotent operations cause duplicate charges, double emails, etc.

**❌ Bad Example:**
```python
@saga_step("create-user")
async def create_user(self, user_data):
    # Will create duplicate users on retry!
    user = await db.users.insert(user_data)
    return {"user_id": user.id}
```

**✅ Good Example:**
```python
@saga_step("create-user")
async def create_user(self, user_data, context: SagaContext):
    # Check if already created
    existing = await db.users.find_one({"email": user_data["email"]})
    if existing:
        return {"user_id": existing.id, "already_existed": True}

    # Create with idempotency key
    user = await db.users.insert({
        **user_data,
        "idempotency_key": context.correlation_id
    })
    return {"user_id": user.id, "already_existed": False}
```

---

### 2. Design Compensations Carefully

**Principles:**
- Compensations should be **idempotent** (can run multiple times safely)
- Compensations should be **reliable** (rarely fail)
- Compensations should **log** their actions for auditing

**❌ Bad Example:**
```python
@compensation_step("reserve-inventory")
async def release_inventory(self, reservation_result):
    # What if this fails? No logging, no error handling
    await inventory_service.release(reservation_result["reservation_id"])
```

**✅ Good Example:**
```python
@compensation_step("reserve-inventory")
async def release_inventory(self, reservation_result, context: SagaContext):
    reservation_id = reservation_result.get("reservation_id")

    if not reservation_id:
        logger.warning("No reservation_id to release")
        return {"status": "nothing_to_release"}

    try:
        # Check if already released (idempotency)
        status = await inventory_service.get_reservation_status(reservation_id)
        if status == "released":
            logger.info(f"Reservation {reservation_id} already released")
            return {"status": "already_released"}

        # Release the reservation
        await inventory_service.release(reservation_id)

        # Log for audit trail
        logger.info(
            f"Released inventory reservation",
            extra={
                "reservation_id": reservation_id,
                "correlation_id": context.correlation_id,
                "reason": "saga_compensation"
            }
        )

        return {"status": "released", "reservation_id": reservation_id}

    except Exception as e:
        # Log but don't fail - compensation failures are serious
        logger.error(
            f"Failed to release reservation {reservation_id}: {e}",
            extra={"correlation_id": context.correlation_id}
        )
        # Consider: send alert, create manual task, etc.
        raise
```

---

### 3. Set Appropriate Timeouts

Different operations need different timeouts:

```python
# Quick validation - short timeout
@saga_step("validate-input", timeout_ms=1000)
async def validate_input(self, data):
    return {"valid": True}

# External API call - medium timeout
@saga_step("call-payment-api", timeout_ms=10000)
async def call_payment_api(self, data):
    return await payment_api.charge(data)

# Long-running process - long timeout
@saga_step("generate-report", timeout_ms=60000)
async def generate_report(self, data):
    return await report_generator.create(data)

# Async webhook wait - very long timeout
@saga_step("wait-for-approval", timeout_ms=3600000)  # 1 hour
async def wait_for_approval(self, data):
    return await approval_service.wait(data)
```

---

### 4. Use Retry Wisely

**Retry for transient failures:**
```python
# Network calls - retry makes sense
@saga_step("call-external-api", retry=5, backoff_ms=1000)
async def call_api(self, data):
    return await external_api.call(data)
```

**Don't retry for permanent failures:**
```python
@saga_step("validate-business-rules", retry=1)  # No retry needed
async def validate(self, data):
    if data["amount"] < 0:
        raise ValueError("Amount must be positive")  # Permanent error
    return {"valid": True}
```

**Custom retry logic:**
```python
from fireflytx.exceptions import RetryableError, NonRetryableError

@saga_step("smart-api-call", retry=3)
async def smart_api_call(self, data):
    try:
        return await api.call(data)
    except api.RateLimitError as e:
        # Transient - retry
        raise RetryableError(f"Rate limited: {e}")
    except api.AuthenticationError as e:
        # Permanent - don't retry
        raise NonRetryableError(f"Auth failed: {e}")
    except api.NetworkError as e:
        # Transient - retry
        raise RetryableError(f"Network error: {e}")
```

---

### 5. Leverage Context for Data Sharing

**Use context instead of instance variables:**

**❌ Bad Example:**
```python
class OrderSaga:
    def __init__(self):
        self.order_id = None  # Instance variable - not safe!

    @saga_step("create-order")
    async def create_order(self, data):
        self.order_id = await create_order_in_db(data)
        return {"order_id": self.order_id}

    @saga_step("send-email", depends_on=["create-order"])
    async def send_email(self, data):
        # What if multiple SAGAs run concurrently?
        # self.order_id might be from a different SAGA!
        await send_email(self.order_id)
```

**✅ Good Example:**
```python
class OrderSaga:
    @saga_step("create-order")
    async def create_order(self, data, context: SagaContext):
        order_id = await create_order_in_db(data)
        context.set_data("order_id", order_id)  # Thread-safe!
        return {"order_id": order_id}

    @saga_step("send-email", depends_on=["create-order"])
    async def send_email(self, data, context: SagaContext):
        order_id = context.get_data("order_id")  # Safe!
        await send_email(order_id)
```

---

### 6. Add Comprehensive Logging

**Log at key points:**

```python
import logging

logger = logging.getLogger(__name__)

@saga_step("process-payment")
async def process_payment(self, payment_data, context: SagaContext):
    logger.info(
        "Starting payment processing",
        extra={
            "correlation_id": context.correlation_id,
            "amount": payment_data["amount"],
            "customer_id": payment_data["customer_id"]
        }
    )

    try:
        result = await payment_service.charge(payment_data)

        logger.info(
            "Payment processed successfully",
            extra={
                "correlation_id": context.correlation_id,
                "charge_id": result["charge_id"],
                "amount": payment_data["amount"]
            }
        )

        return result

    except Exception as e:
        logger.error(
            "Payment processing failed",
            extra={
                "correlation_id": context.correlation_id,
                "error": str(e),
                "amount": payment_data["amount"]
            },
            exc_info=True
        )
        raise
```

---

### 7. Test Thoroughly

**Unit test individual steps:**

```python
import pytest

@pytest.mark.asyncio
async def test_validate_order_success():
    saga = OrderProcessingSaga()
    context = SagaContext(correlation_id="test-123")

    order_data = {
        "order_id": "ORD-001",
        "customer_id": "CUST-001",
        "items": [{"product_id": "PROD-001", "quantity": 1, "price": 10.00}]
    }

    result = await saga.validate_order(order_data, context)

    assert result["status"] == "validated"
    assert result["total_amount"] == 10.00
    assert context.get_data("validation_id") == "VAL-ORD-001"

@pytest.mark.asyncio
async def test_validate_order_missing_customer():
    saga = OrderProcessingSaga()
    context = SagaContext(correlation_id="test-123")

    order_data = {"order_id": "ORD-001", "items": []}

    with pytest.raises(ValueError, match="Missing customer_id"):
        await saga.validate_order(order_data, context)
```

**Integration test full SAGA:**

```python
@pytest.mark.asyncio
async def test_order_saga_success():
    engine = create_saga_engine()

    order_data = create_valid_order()

    result = await engine.execute_saga_class(OrderProcessingSaga, order_data)

    assert result.is_success
    assert len(result.steps) == 4
    assert result.compensated_steps == []

@pytest.mark.asyncio
async def test_order_saga_payment_failure():
    engine = create_saga_engine()

    # Order that will fail at payment
    order_data = create_order_with_invalid_payment()

    result = await engine.execute_saga_class(OrderProcessingSaga, order_data)

    assert not result.is_success
    assert result.failed_step == "charge-payment"
    assert "reserve-inventory" in result.compensated_steps
```

---

## Common Pitfalls

> **⚠️ Avoid these mistakes:** Learn from common errors to save debugging time.

### Pitfall 1: Forgetting Compensation

**Problem:**
```python
@saga_step("reserve-inventory")
async def reserve_inventory(self, data):
    await inventory_service.reserve(data["items"])
    return {"reserved": True}

# ❌ No compensation! Can't rollback!
```

**Impact:** If a later step fails, inventory stays reserved forever.

**Solution:**
```python
@saga_step("reserve-inventory")
async def reserve_inventory(self, data, context: SagaContext):
    reservation = await inventory_service.reserve(data["items"])
    context.set_data("reservation_id", reservation.id)
    return {"reservation_id": reservation.id}

@compensation_step("reserve-inventory")
async def release_inventory(self, result, context: SagaContext):
    reservation_id = context.get_data("reservation_id")
    await inventory_service.release(reservation_id)
```

---

### Pitfall 2: Circular Dependencies

**Problem:**
```python
@saga_step("step-a", depends_on=["step-b"])
async def step_a(self, data):
    return {"done": True}

@saga_step("step-b", depends_on=["step-a"])
async def step_b(self, data):
    return {"done": True}

# ❌ Circular dependency! Neither can run!
```

**Impact:** SAGA will never execute. FireflyTX will detect this and raise an error at registration.

**Solution:** Fix the dependency chain:
```python
@saga_step("step-a")
async def step_a(self, data):
    return {"done": True}

@saga_step("step-b", depends_on=["step-a"])
async def step_b(self, data):
    return {"done": True}
```

---

### Pitfall 3: Non-Idempotent Operations

**Problem:**
```python
@saga_step("send-email", retry=3)
async def send_email(self, data):
    await email_service.send(data["email"], "Welcome!")
    return {"sent": True}

# ❌ Customer gets 3 emails if first attempt times out!
```

**Impact:** Duplicate emails, charges, database records, etc.

**Solution:**
```python
@saga_step("send-email", retry=3)
async def send_email(self, data, context: SagaContext):
    # Use idempotency key
    idempotency_key = f"{context.correlation_id}-email"

    await email_service.send(
        to=data["email"],
        template="welcome",
        idempotency_key=idempotency_key
    )
    return {"sent": True}
```

---

### Pitfall 4: Blocking Operations in Async Methods

**Problem:**
```python
@saga_step("call-api")
async def call_api(self, data):
    # ❌ Blocking call in async method!
    response = requests.get("http://api.example.com")
    return response.json()
```

**Impact:** Blocks the event loop, preventing other SAGAs from running.

**Solution:**
```python
import httpx

@saga_step("call-api")
async def call_api(self, data):
    # ✅ Use async HTTP client
    async with httpx.AsyncClient() as client:
        response = await client.get("http://api.example.com")
        return response.json()
```

---

### Pitfall 5: Not Handling Partial Failures

**Problem:**
```python
@saga_step("process-items")
async def process_items(self, data):
    for item in data["items"]:
        await process_item(item)  # What if 3rd item fails?
    return {"processed": len(data["items"])}

# ❌ No way to know which items were processed!
```

**Impact:** Can't properly compensate - don't know what to undo.

**Solution:**
```python
@saga_step("process-items")
async def process_items(self, data, context: SagaContext):
    processed_items = []

    for item in data["items"]:
        result = await process_item(item)
        processed_items.append(result)

    # Store for compensation
    context.set_data("processed_item_ids", [r["id"] for r in processed_items])

    return {"processed": processed_items}

@compensation_step("process-items")
async def undo_process_items(self, result, context: SagaContext):
    processed_ids = context.get_data("processed_item_ids", [])

    for item_id in processed_ids:
        await undo_process_item(item_id)
```

---

## Troubleshooting

> **🔧 Debug like a pro:** Common issues and how to fix them.

### Issue 1: SAGA Never Completes

**Symptoms:**
- SAGA execution hangs
- No error messages
- Steps seem to run but never finish

**Diagnosis:**

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check which step is hanging
result = await engine.execute_saga_class(MySaga, data, timeout_ms=30000)
```

**Common Causes:**

1. **Blocking operation in async method:**
   ```python
   # ❌ This blocks forever
   @saga_step("bad-step")
   async def bad_step(self, data):
       time.sleep(10)  # Blocks event loop!
   ```

   **Fix:** Use `await asyncio.sleep(10)` instead

2. **Missing await:**
   ```python
   # ❌ Forgot await
   @saga_step("bad-step")
   async def bad_step(self, data):
       result = async_function()  # Should be: await async_function()
       return result
   ```

   **Fix:** Add `await`

3. **Deadlock in dependencies:**
   ```python
   # ❌ Both wait for each other
   @saga_step("a", depends_on=["b"])
   async def a(self, data): ...

   @saga_step("b", depends_on=["a"])
   async def b(self, data): ...
   ```

   **Fix:** Remove circular dependency

---

### Issue 2: Compensation Not Running

**Symptoms:**
- Step fails but compensation doesn't run
- Resources not cleaned up

**Diagnosis:**

```python
# Check result
result = await engine.execute_saga_class(MySaga, data)
print(f"Failed step: {result.failed_step}")
print(f"Compensated steps: {result.compensated_steps}")
```

**Common Causes:**

1. **No compensation defined:**
   ```python
   @saga_step("reserve")
   async def reserve(self, data):
       return {"reserved": True}

   # ❌ Missing @compensation_step("reserve")
   ```

   **Fix:** Add compensation

2. **Wrong step ID:**
   ```python
   @saga_step("reserve-inventory")
   async def reserve(self, data): ...

   @compensation_step("reserve")  # ❌ Wrong ID!
   async def release(self, data): ...
   ```

   **Fix:** Use correct step ID: `@compensation_step("reserve-inventory")`

---

### Issue 3: Timeout Errors

**Symptoms:**
```
Error: Step execution timeout after 5000ms
```

**Diagnosis:**

```python
import time

@saga_step("slow-step", timeout_ms=5000)
async def slow_step(self, data):
    start = time.time()
    result = await do_work(data)
    duration = (time.time() - start) * 1000
    print(f"Step took {duration}ms")
    return result
```

**Solutions:**

1. **Increase timeout:**
   ```python
   @saga_step("slow-step", timeout_ms=30000)  # 30 seconds
   async def slow_step(self, data): ...
   ```

2. **Optimize the operation:**
   - Use connection pooling
   - Add caching
   - Parallelize sub-operations

3. **Break into smaller steps:**
   ```python
   @saga_step("step-1", timeout_ms=5000)
   async def step_1(self, data): ...

   @saga_step("step-2", depends_on=["step-1"], timeout_ms=5000)
   async def step_2(self, data): ...
   ```

---

### Issue 4: Context Data Lost

**Symptoms:**
- `context.get_data()` returns `None`
- Data not available in later steps

**Common Causes:**

1. **Forgot to set data:**
   ```python
   @saga_step("step-1")
   async def step_1(self, data, context: SagaContext):
       order_id = create_order()
       # ❌ Forgot to store in context!
       return {"order_id": order_id}
   ```

   **Fix:**
   ```python
   context.set_data("order_id", order_id)
   ```

2. **Wrong key:**
   ```python
   context.set_data("orderId", order_id)  # camelCase
   # ...
   order_id = context.get_data("order_id")  # snake_case - returns None!
   ```

   **Fix:** Use consistent naming

---

## Real-World Examples

### Example 1: Travel Booking System

Book flight + hotel + car rental with automatic cancellation on failure.

```python
@saga("travel-booking")
class TravelBookingSaga:
    """Book complete travel package with rollback."""

    @saga_step("book-flight", retry=3, timeout_ms=15000)
    async def book_flight(self, booking_data, context: SagaContext):
        """Book flight reservation."""
        flight = await flight_api.book(
            from_city=booking_data["from"],
            to_city=booking_data["to"],
            date=booking_data["date"],
            passengers=booking_data["passengers"]
        )

        context.set_data("flight_confirmation", flight["confirmation_code"])

        return {
            "confirmation_code": flight["confirmation_code"],
            "price": flight["price"]
        }

    @compensation_step("book-flight")
    async def cancel_flight(self, flight_result, context: SagaContext):
        """Cancel flight reservation."""
        confirmation = context.get_data("flight_confirmation")
        await flight_api.cancel(confirmation)
        return {"cancelled": confirmation}

    @saga_step("book-hotel", depends_on=["book-flight"], retry=3)
    async def book_hotel(self, booking_data, context: SagaContext):
        """Book hotel reservation."""
        hotel = await hotel_api.book(
            city=booking_data["to"],
            check_in=booking_data["date"],
            check_out=booking_data["return_date"],
            guests=booking_data["passengers"]
        )

        context.set_data("hotel_confirmation", hotel["confirmation_code"])

        return {
            "confirmation_code": hotel["confirmation_code"],
            "price": hotel["price"]
        }

    @compensation_step("book-hotel")
    async def cancel_hotel(self, hotel_result, context: SagaContext):
        """Cancel hotel reservation."""
        confirmation = context.get_data("hotel_confirmation")
        await hotel_api.cancel(confirmation)
        return {"cancelled": confirmation}

    @saga_step("book-car", depends_on=["book-flight"], retry=3)
    async def book_car(self, booking_data, context: SagaContext):
        """Book car rental."""
        car = await car_rental_api.book(
            location=booking_data["to"],
            pickup_date=booking_data["date"],
            return_date=booking_data["return_date"]
        )

        context.set_data("car_confirmation", car["confirmation_code"])

        return {
            "confirmation_code": car["confirmation_code"],
            "price": car["price"]
        }

    @compensation_step("book-car")
    async def cancel_car(self, car_result, context: SagaContext):
        """Cancel car rental."""
        confirmation = context.get_data("car_confirmation")
        await car_rental_api.cancel(confirmation)
        return {"cancelled": confirmation}

    @saga_step("charge-payment", depends_on=["book-hotel", "book-car"], retry=5)
    async def charge_payment(self, booking_data, context: SagaContext):
        """Charge total amount."""
        flight_price = context.get_data("flight_price", 0)
        hotel_price = context.get_data("hotel_price", 0)
        car_price = context.get_data("car_price", 0)
        total = flight_price + hotel_price + car_price

        charge = await payment_api.charge(
            amount=total,
            customer_id=booking_data["customer_id"],
            idempotency_key=context.correlation_id
        )

        return {"charge_id": charge["id"], "amount": total}

    @compensation_step("charge-payment")
    async def refund_payment(self, charge_result, context: SagaContext):
        """Refund payment."""
        await payment_api.refund(charge_result["charge_id"])
        return {"refunded": charge_result["amount"]}
```

**Usage:**
```python
booking_data = {
    "from": "NYC",
    "to": "LAX",
    "date": "2025-11-01",
    "return_date": "2025-11-05",
    "passengers": 2,
    "customer_id": "CUST-123"
}

result = await engine.execute_saga_class(TravelBookingSaga, booking_data)

if result.is_success:
    print("✅ Travel package booked!")
else:
    print(f"❌ Booking failed: {result.error}")
    print(f"All reservations cancelled: {result.compensated_steps}")
```

---

### Example 2: User Registration with External Services

Register user across multiple systems with rollback.

```python
@saga("user-registration")
class UserRegistrationSaga:
    """Register user with database, auth service, and email."""

    @saga_step("create-database-record")
    async def create_db_record(self, user_data, context: SagaContext):
        """Create user in database."""
        user = await db.users.insert({
            "email": user_data["email"],
            "name": user_data["name"],
            "created_at": datetime.utcnow()
        })

        context.set_data("user_id", user.id)

        return {"user_id": user.id}

    @compensation_step("create-database-record")
    async def delete_db_record(self, result, context: SagaContext):
        """Delete user from database."""
        user_id = context.get_data("user_id")
        await db.users.delete({"_id": user_id})
        return {"deleted": user_id}

    @saga_step("create-auth-account", depends_on=["create-database-record"])
    async def create_auth_account(self, user_data, context: SagaContext):
        """Create account in Auth0."""
        auth_user = await auth0.create_user(
            email=user_data["email"],
            password=user_data["password"],
            user_metadata={"db_user_id": context.get_data("user_id")}
        )

        context.set_data("auth_user_id", auth_user["user_id"])

        return {"auth_user_id": auth_user["user_id"]}

    @compensation_step("create-auth-account")
    async def delete_auth_account(self, result, context: SagaContext):
        """Delete account from Auth0."""
        auth_user_id = context.get_data("auth_user_id")
        await auth0.delete_user(auth_user_id)
        return {"deleted": auth_user_id}

    @saga_step("send-welcome-email", depends_on=["create-auth-account"])
    async def send_welcome_email(self, user_data, context: SagaContext):
        """Send welcome email."""
        await email_service.send(
            to=user_data["email"],
            template="welcome",
            data={"name": user_data["name"]},
            idempotency_key=context.correlation_id
        )

        return {"email_sent": True}

    # Note: Email doesn't need compensation (OK if user gets email even if we rollback)
```

---

## Summary & Next Steps

### Key Takeaways

1. **SAGAs are for distributed transactions** - Use when you need to coordinate across services
2. **Always provide compensations** - Every state-changing step needs a way to undo
3. **Make everything idempotent** - Steps and compensations can run multiple times
4. **Use context for data sharing** - Thread-safe way to pass data between steps
5. **Test thoroughly** - Unit test steps, integration test full SAGAs

### Learning Path

**Next Steps:**
1. Try the [Step-by-Step Tutorial](#step-by-step-tutorial)
2. Review [Best Practices](#best-practices)
3. Study [Real-World Examples](#real-world-examples)
4. Read [TCC Pattern Guide](tcc-pattern.md) for strong consistency
5. Explore [Architecture Guide](architecture.md) for deep dive

### Getting Help

- **Documentation:** [docs/](../docs/)
- **Examples:** [examples/](../examples/)
- **Issues:** [GitHub Issues](https://github.com/firefly-oss/python-transactional-engine/issues)

---

**Happy SAGA building! 🚀**

