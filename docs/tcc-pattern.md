# TCC Pattern Guide

> **📚 Learning Objectives:** By the end of this guide, you'll understand how to design, implement, and troubleshoot TCC (Try-Confirm-Cancel) patterns using FireflyTX.

**Last Updated:** 2025-10-19

---

## Table of Contents

1. [What is the TCC Pattern?](#what-is-the-tcc-pattern)
2. [TCC vs SAGA: When to Use Which?](#tcc-vs-saga-when-to-use-which)
3. [Basic Concepts](#basic-concepts)
4. [Step-by-Step Tutorial](#step-by-step-tutorial)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [Common Pitfalls](#common-pitfalls)
8. [Troubleshooting](#troubleshooting)
9. [Real-World Examples](#real-world-examples)

---

## What is the TCC Pattern?

### The Problem

Imagine you're building a payment system. When processing a payment, you need to:

1. Reserve funds from the customer's account
2. Reserve inventory for the product
3. Create a shipping label

**What if step 3 (shipping) fails?** You need to:
- Release the inventory reservation
- Release the funds reservation

But here's the challenge: **You need STRONG CONSISTENCY** - either all operations succeed or all fail, with no in-between state visible to users.

### The Solution

**TCC (Try-Confirm-Cancel)** is a two-phase commit protocol where each participant implements three methods:

1. **Try**: Reserve resources (prepare for commit)
2. **Confirm**: Make the reservation permanent (commit)
3. **Cancel**: Release the reservation (rollback)

### Visual Example

```
Success Path (All participants succeed):

TRY PHASE:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Reserve   │    │   Reserve   │    │   Reserve   │
│   Payment   │    │  Inventory  │    │   Shipping  │
└─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │
      └──────────────────┴──────────────────┘
                         │
                         ▼
CONFIRM PHASE:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Confirm   │    │   Confirm   │    │   Confirm   │
│   Payment   │    │  Inventory  │    │   Shipping  │
└─────────────┘    └─────────────┘    └─────────────┘
      ✅                 ✅                 ✅

Result: Transaction COMMITTED


Failure Path (Inventory reservation fails):

TRY PHASE:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Reserve   │    │   Reserve   │    │   Reserve   │
│   Payment   │    │  Inventory  │    │   Shipping  │
└─────────────┘    └─────────────┘    └─────────────┘
      ✅                ❌             (not started)
      │                  │
      └──────────────────┘
                │
                ▼
CANCEL PHASE:
┌─────────────┐
│   Cancel    │
│   Payment   │ (Release reservation)
└─────────────┘
      ✅

Result: Transaction ABORTED
```

### Key Differences from SAGA

| Aspect | TCC | SAGA |
|--------|-----|------|
| **Consistency** | Strong (2PC) | Eventual |
| **Isolation** | Resources locked during transaction | No locks |
| **Performance** | Slower (2 phases) | Faster (1 phase) |
| **Complexity** | Higher (3 methods per participant) | Lower (2 methods per step) |
| **Use Case** | Financial transactions, inventory | Long-running workflows |

---

## TCC vs SAGA: When to Use Which?

### ✅ Use TCC When:

| Scenario | Why TCC? |
|----------|----------|
| **Need strong consistency** | All-or-nothing guarantee |
| **Financial transactions** | Money transfers, payments |
| **Inventory management** | Stock reservations |
| **Short-lived transactions** | Complete in seconds/minutes |
| **Can lock resources** | Resources can be reserved |

### ✅ Use SAGA When:

| Scenario | Why SAGA? |
|----------|-----------|
| **Long-running workflows** | Hours, days, or weeks |
| **Eventually consistent is OK** | Don't need immediate consistency |
| **Can't lock resources** | Resources can't be reserved |
| **Complex dependencies** | Many steps with conditional logic |
| **Microservices orchestration** | Coordinating many services |

### Quick Decision Tree

```
Need strong consistency? ──Yes──> Can lock resources? ──Yes──> TCC
                │                                        │
                No                                       No
                │                                        │
                ▼                                        ▼
            Use SAGA                                 Use SAGA
```

---

## Basic Concepts

### Prerequisites

Before diving in, you should understand:
- **Python async/await** - TCC uses asyncio
- **Decorators** - TCC is defined with decorators
- **Two-phase commit** - Understanding of 2PC helps
- **Resource locking** - Concept of reservations

### Core Components

#### 1. TCC Transaction Definition

A TCC transaction is a Python class decorated with `@tcc`:

```python
from fireflytx.decorators.tcc import tcc

@tcc("payment-processing")  # ← TCC transaction name (must be unique)
class PaymentProcessingTcc:
    """Process payments with two-phase commit."""

    def __init__(self):
        # Optional: Initialize any instance variables
        pass
```

#### 2. TCC Participants

Participants are nested classes that implement the three-phase protocol:

```python
from fireflytx.decorators.tcc import (
    tcc, tcc_participant, try_method, confirm_method, cancel_method
)

@tcc("order-processing")
class OrderProcessingTcc:

    @tcc_participant("payment", order=1)  # ← Participant name and execution order
    class PaymentParticipant:
        """Handles payment reservation and confirmation."""

        def __init__(self):
            # Optional: Initialize any instance variables
            pass

        @try_method(timeout_ms=10000, retry=3)
        async def try_payment(self, order_data):
            """TRY: Reserve payment amount."""
            # Reserve funds (don't charge yet!)
            reservation_id = f"RES-{order_data['order_id']}"
            # In real implementation, call payment service
            return {"reservation_id": reservation_id, "amount": order_data["amount"]}

        @confirm_method(timeout_ms=5000)
        async def confirm_payment(self, reservation_data):
            """CONFIRM: Actually charge the payment."""
            # In real implementation, confirm with payment service
            pass

        @cancel_method(timeout_ms=5000, retry=5)
        async def cancel_payment(self, reservation_data):
            """CANCEL: Release the payment reservation."""
            # In real implementation, release reservation with payment service
            pass
```

**Method Signatures:**

```python
# TRY method
async def try_method_name(
    self,
    input_data: dict,           # Input data for this participant
    context: TccContext = None  # Optional: shared context
) -> dict:                      # Must return reservation data
    ...

# CONFIRM method
async def confirm_method_name(
    self,
    try_result: dict,           # Result from try method
    context: TccContext = None  # Optional: shared context
) -> None:                      # Return value ignored
    ...

# CANCEL method
async def cancel_method_name(
    self,
    try_result: dict,           # Result from try method
    context: TccContext = None  # Optional: shared context
) -> None:                      # Return value ignored
    ...
```

#### 3. Execution Order

Control the order in which participants execute:

```python
@tcc("multi-service-transaction")
class MultiServiceTcc:
    
    @tcc_participant("authentication", order=1)  # Runs first
    class AuthParticipant:
        ...
    
    @tcc_participant("payment", order=2)  # Runs second
    class PaymentParticipant:
        ...
    
    @tcc_participant("inventory", order=3)  # Runs third
    class InventoryParticipant:
        ...
```

**Execution Flow:**
```
TRY Phase:    auth(1) → payment(2) → inventory(3)
CONFIRM Phase: auth(1) → payment(2) → inventory(3)
CANCEL Phase:  inventory(3) → payment(2) → auth(1)  (reverse order!)
```

---

## Step-by-Step Tutorial

### Tutorial: Build an E-Commerce Order TCC Transaction

Let's build a complete order processing TCC transaction from scratch.

#### Step 1: Define the TCC Transaction Class

```python
from fireflytx.decorators.tcc import (
    tcc, tcc_participant, try_method, confirm_method, cancel_method
)

@tcc("e-commerce-order")
class OrderProcessingTcc:
    """
    Process e-commerce orders with two-phase commit.

    Participants:
    1. Inventory - Reserve and confirm stock
    2. Payment - Reserve and charge payment
    3. Shipping - Reserve and create shipping label
    """

    def __init__(self):
        # Optional: Initialize any instance variables
        pass
```

#### Step 2: Add Inventory Participant

```python
@tcc_participant("inventory", order=1)
class InventoryParticipant:
    """
    Manage inventory reservations.
    
    Try: Reserve stock
    Confirm: Decrement stock permanently
    Cancel: Release reservation
    """
    
    @try_method(timeout_ms=5000, retry=3)
    async def reserve_inventory(self, order_data, context: TccContext):
        """
        TRY: Reserve inventory for order items.
        
        This creates a temporary hold on inventory that expires
        if not confirmed within a timeout period.
        """
        reservations = []
        
        for item in order_data["items"]:
            # Check if enough stock available
            available = await inventory_service.get_available_stock(
                product_id=item["product_id"]
            )
            
            if available < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for {item['product_id']}: "
                    f"need {item['quantity']}, have {available}"
                )
            
            # Create reservation (temporary hold)
            reservation = await inventory_service.create_reservation(
                product_id=item["product_id"],
                quantity=item["quantity"],
                order_id=order_data["order_id"],
                ttl_seconds=300  # Expires in 5 minutes if not confirmed
            )
            
            reservations.append({
                "reservation_id": reservation.id,
                "product_id": item["product_id"],
                "quantity": item["quantity"]
            })
        
        # Store reservation IDs in context for other participants
        context.set_data("inventory_reservations", reservations)
        
        return {
            "reservations": reservations,
            "total_items": sum(r["quantity"] for r in reservations)
        }
    
    @confirm_method(timeout_ms=3000)
    async def confirm_inventory(self, try_result, context: TccContext):
        """
        CONFIRM: Make inventory reservations permanent.
        
        This decrements the actual stock count and removes the reservation.
        """
        reservations = try_result["reservations"]
        
        for reservation in reservations:
            # Commit the reservation (decrement stock)
            await inventory_service.commit_reservation(
                reservation_id=reservation["reservation_id"]
            )
            
            logger.info(
                f"Confirmed inventory reservation",
                extra={
                    "reservation_id": reservation["reservation_id"],
                    "product_id": reservation["product_id"],
                    "quantity": reservation["quantity"],
                    "correlation_id": context.correlation_id
                }
            )
    
    @cancel_method(timeout_ms=3000, retry=5)
    async def cancel_inventory(self, try_result, context: TccContext):
        """
        CANCEL: Release inventory reservations.
        
        This returns the reserved stock to available inventory.
        """
        reservations = try_result.get("reservations", [])
        
        for reservation in reservations:
            try:
                # Release the reservation
                await inventory_service.cancel_reservation(
                    reservation_id=reservation["reservation_id"]
                )
                
                logger.info(
                    f"Cancelled inventory reservation",
                    extra={
                        "reservation_id": reservation["reservation_id"],
                        "product_id": reservation["product_id"],
                        "correlation_id": context.correlation_id
                    }
                )
            except ReservationNotFoundError:
                # Idempotent - already cancelled or expired
                logger.warning(
                    f"Reservation {reservation['reservation_id']} not found (already cancelled?)"
                )
```

**Key Points:**
- **Try**: Creates temporary reservation with TTL (time-to-live)
- **Confirm**: Makes reservation permanent by decrementing stock
- **Cancel**: Releases reservation (idempotent - can run multiple times)
- Use `context.set_data()` to share data with other participants

#### Step 3: Add Payment Participant

```python
@tcc_participant("payment", order=2)
class PaymentParticipant:
    """
    Manage payment reservations and charges.
    
    Try: Reserve payment amount (authorization)
    Confirm: Capture the payment
    Cancel: Release the authorization
    """
    
    @try_method(timeout_ms=10000, retry=5)
    async def reserve_payment(self, order_data, context: TccContext):
        """
        TRY: Authorize payment (reserve funds).
        
        This creates a payment authorization that holds funds
        but doesn't charge the customer yet.
        """
        # Calculate total amount
        total = sum(
            item["price"] * item["quantity"]
            for item in order_data["items"]
        )
        
        # Use correlation_id as idempotency key
        idempotency_key = f"{context.correlation_id}-payment-auth"
        
        # Authorize payment (reserve funds, don't charge yet)
        authorization = await payment_service.authorize(
            amount=total,
            customer_id=order_data["customer_id"],
            payment_method=order_data["payment_method"],
            idempotency_key=idempotency_key,
            ttl_seconds=300  # Authorization expires in 5 minutes
        )
        
        # Store for other participants
        context.set_data("payment_amount", total)
        context.set_data("authorization_id", authorization.id)
        
        return {
            "authorization_id": authorization.id,
            "amount": total,
            "status": "authorized"
        }
    
    @confirm_method(timeout_ms=5000, retry=3)
    async def confirm_payment(self, try_result, context: TccContext):
        """
        CONFIRM: Capture the payment (actually charge).
        
        This converts the authorization into an actual charge.
        """
        authorization_id = try_result["authorization_id"]
        
        # Capture the authorized payment
        charge = await payment_service.capture(
            authorization_id=authorization_id,
            idempotency_key=f"{context.correlation_id}-payment-capture"
        )
        
        logger.info(
            f"Payment captured",
            extra={
                "authorization_id": authorization_id,
                "charge_id": charge.id,
                "amount": try_result["amount"],
                "correlation_id": context.correlation_id
            }
        )
    
    @cancel_method(timeout_ms=5000, retry=5)
    async def cancel_payment(self, try_result, context: TccContext):
        """
        CANCEL: Release the payment authorization.
        
        This releases the hold on funds without charging.
        """
        authorization_id = try_result.get("authorization_id")
        
        if not authorization_id:
            logger.warning("No authorization_id to cancel")
            return
        
        try:
            # Release the authorization
            await payment_service.void_authorization(
                authorization_id=authorization_id
            )
            
            logger.info(
                f"Payment authorization voided",
                extra={
                    "authorization_id": authorization_id,
                    "correlation_id": context.correlation_id
                }
            )
        except AuthorizationNotFoundError:
            # Idempotent - already voided or expired
            logger.warning(
                f"Authorization {authorization_id} not found (already voided?)"
            )
```

**Key Points:**
- **Try**: Authorizes payment (holds funds, doesn't charge)
- **Confirm**: Captures payment (actually charges customer)
- **Cancel**: Voids authorization (releases hold)
- Use idempotency keys to prevent duplicate charges on retry

#### Step 4: Add Shipping Participant

```python
@tcc_participant("shipping", order=3)
class ShippingParticipant:
    """
    Manage shipping label reservations.
    
    Try: Reserve shipping capacity
    Confirm: Create shipping label
    Cancel: Release shipping reservation
    """
    
    @try_method(timeout_ms=8000, retry=3)
    async def reserve_shipping(self, order_data, context: TccContext):
        """
        TRY: Reserve shipping capacity.
        
        This checks if shipping is available and reserves a slot.
        """
        # Calculate shipping details
        weight = sum(item.get("weight", 1.0) for item in order_data["items"])
        
        # Reserve shipping slot
        reservation = await shipping_service.reserve_slot(
            destination=order_data["shipping_address"],
            weight=weight,
            service_level=order_data.get("shipping_speed", "standard"),
            ttl_seconds=300
        )
        
        context.set_data("shipping_reservation_id", reservation.id)
        
        return {
            "reservation_id": reservation.id,
            "estimated_delivery": reservation.estimated_delivery,
            "cost": reservation.cost
        }
    
    @confirm_method(timeout_ms=10000)
    async def confirm_shipping(self, try_result, context: TccContext):
        """
        CONFIRM: Create actual shipping label.
        
        This generates the shipping label and schedules pickup.
        """
        reservation_id = try_result["reservation_id"]
        
        # Create shipping label
        label = await shipping_service.create_label(
            reservation_id=reservation_id
        )
        
        logger.info(
            f"Shipping label created",
            extra={
                "reservation_id": reservation_id,
                "tracking_number": label.tracking_number,
                "correlation_id": context.correlation_id
            }
        )
    
    @cancel_method(timeout_ms=5000, retry=3)
    async def cancel_shipping(self, try_result, context: TccContext):
        """
        CANCEL: Release shipping reservation.
        """
        reservation_id = try_result.get("reservation_id")
        
        if reservation_id:
            try:
                await shipping_service.cancel_reservation(reservation_id)
                logger.info(f"Shipping reservation {reservation_id} cancelled")
            except ReservationNotFoundError:
                logger.warning(f"Shipping reservation {reservation_id} not found")
```

#### Step 5: Execute the TCC Transaction

```python
from fireflytx import TccEngine

def main():
    # Create and start TCC engine
    engine = TccEngine()
    engine.start()
    
    # Order data
    order_data = {
        "order_id": "ORD-12345",
        "customer_id": "CUST-789",
        "payment_method": "card_xyz",
        "shipping_address": {
            "street": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94105"
        },
        "items": [
            {
                "product_id": "PROD-001",
                "quantity": 2,
                "price": 29.99,
                "weight": 1.5
            },
            {
                "product_id": "PROD-002",
                "quantity": 1,
                "price": 49.99,
                "weight": 2.0
            }
        ]
    }
    
    # Execute TCC transaction
    result = await engine.execute(
        OrderProcessingTcc,
        order_data
    )

    # Check result
    if result.is_confirmed:
        print(f"✅ Order {order_data['order_id']} processed successfully!")
        print(f"   Duration: {result.duration_ms}ms")
        print(f"   Participants: {list(result.participants.keys())}")
        print(f"   Phase: {result.final_phase}")  # Should be "CONFIRMED"
    else:
        print(f"❌ Order {order_data['order_id']} failed!")
        print(f"   Error: {result.error}")
        print(f"   Failed at: {result.failed_participant}")
        print(f"   Phase: {result.final_phase}")  # Should be "CANCELLED"

    engine.stop()

if __name__ == "__main__":
    main()
```

**Output (Success):**
```
✅ Order ORD-12345 processed successfully!
   Duration: 2345ms
   Participants: ['inventory', 'payment', 'shipping']
   Phase: CONFIRMED
```

**Output (Failure at payment):**
```
❌ Order ORD-12345 failed!
   Error: Insufficient funds
   Failed at: payment
   Phase: CANCELLED
```

---

## Advanced Features

> **🚀 Level up:** Advanced patterns for complex scenarios.

### 1. Context Sharing Between Participants

Share data between participants using `TccContext`:

```python
@tcc("order-with-tax")
class OrderWithTaxTcc:

    @tcc_participant("inventory", order=1)
    class InventoryParticipant:
        @try_method()
        async def reserve_inventory(self, order_data, context: TccContext):
            total_weight = sum(item["weight"] for item in order_data["items"])
            context.set_data("total_weight", total_weight)
            return {"reserved": True}

        @confirm_method()
        async def confirm_inventory(self, try_result, context: TccContext):
            pass

        @cancel_method()
        async def cancel_inventory(self, try_result, context: TccContext):
            pass

    @tcc_participant("shipping", order=2)
    class ShippingParticipant:
        @try_method()
        async def calculate_shipping(self, order_data, context: TccContext):
            # Use weight from inventory participant
            weight = context.get_data("total_weight")
            shipping_cost = await shipping_service.calculate(weight)
            context.set_data("shipping_cost", shipping_cost)
            return {"cost": shipping_cost}

        @confirm_method()
        async def confirm_shipping(self, try_result, context: TccContext):
            pass

        @cancel_method()
        async def cancel_shipping(self, try_result, context: TccContext):
            pass

    @tcc_participant("payment", order=3)
    class PaymentParticipant:
        @try_method()
        async def reserve_payment(self, order_data, context: TccContext):
            # Use shipping cost from shipping participant
            item_total = sum(item["price"] * item["qty"] for item in order_data["items"])
            shipping = context.get_data("shipping_cost", 0)
            total = item_total + shipping

            authorization = await payment_service.authorize(total)
            return {"authorization_id": authorization.id, "total": total}

        @confirm_method()
        async def confirm_payment(self, try_result, context: TccContext):
            await payment_service.capture(try_result["authorization_id"])

        @cancel_method()
        async def cancel_payment(self, try_result, context: TccContext):
            await payment_service.void(try_result["authorization_id"])
```

**Data Flow:**
```
inventory (order=1)
    ↓ sets "total_weight"
shipping (order=2)
    ↓ reads "total_weight", sets "shipping_cost"
payment (order=3)
    ↓ reads "shipping_cost"
```

---

### 2. Conditional Participants

Execute participants conditionally based on input data:

```python
@tcc("order-with-optional-gift-wrap")
class OrderWithGiftWrapTcc:

    @tcc_participant("inventory", order=1)
    class InventoryParticipant:
        # Always executes
        ...

    @tcc_participant("gift_wrap", order=2, condition=lambda data: data.get("gift_wrap", False))
    class GiftWrapParticipant:
        """Only executes if gift_wrap=True in input data."""

        @try_method()
        async def reserve_gift_wrap(self, order_data, context: TccContext):
            # Only called if order_data["gift_wrap"] == True
            reservation = await gift_wrap_service.reserve()
            return {"reservation_id": reservation.id}

        @confirm_method()
        async def confirm_gift_wrap(self, try_result, context: TccContext):
            await gift_wrap_service.confirm(try_result["reservation_id"])

        @cancel_method()
        async def cancel_gift_wrap(self, try_result, context: TccContext):
            await gift_wrap_service.cancel(try_result["reservation_id"])

    @tcc_participant("payment", order=3)
    class PaymentParticipant:
        # Always executes
        ...
```

**Usage:**
```python
# Without gift wrap - gift_wrap participant skipped
result1 = await engine.execute(
    OrderWithGiftWrapTcc,
    {"items": [...], "gift_wrap": False}
)

# With gift wrap - gift_wrap participant executes
result2 = await engine.execute(
    OrderWithGiftWrapTcc,
    {"items": [...], "gift_wrap": True}
)
```

---

### 3. Timeout Configuration

Set different timeouts for different phases:

```python
@tcc_participant("external_api", order=1)
class ExternalAPIParticipant:

    # Try phase: Longer timeout for external API call
    @try_method(timeout_ms=15000, retry=3)
    async def try_external_call(self, data):
        return await external_api.reserve(data)

    # Confirm phase: Quick confirmation
    @confirm_method(timeout_ms=3000, retry=1)
    async def confirm_external_call(self, try_result):
        await external_api.confirm(try_result["id"])

    # Cancel phase: Longer timeout with more retries for cleanup
    @cancel_method(timeout_ms=10000, retry=5)
    async def cancel_external_call(self, try_result):
        await external_api.cancel(try_result["id"])
```

**Timeout Guidelines:**

| Phase | Typical Timeout | Retry Count | Reason |
|-------|----------------|-------------|---------|
| **Try** | 5-15 seconds | 2-3 | External calls, validation |
| **Confirm** | 3-5 seconds | 1-2 | Should be fast (already reserved) |
| **Cancel** | 5-10 seconds | 3-5 | Must succeed (cleanup critical) |

---

### 4. Error Handling and Classification

Distinguish between retryable and non-retryable errors:

```python
from fireflytx.exceptions import TccRetryableError, TccNonRetryableError

@try_method(timeout_ms=10000, retry=3)
async def try_payment(self, order_data):
    try:
        authorization = await payment_service.authorize(order_data["amount"])
        return {"authorization_id": authorization.id}

    except InsufficientFundsError as e:
        # Business error - don't retry
        raise TccNonRetryableError(f"Insufficient funds: {e}")

    except PaymentGatewayTimeoutError as e:
        # Network error - retry
        raise TccRetryableError(f"Gateway timeout: {e}")

    except PaymentGatewayError as e:
        # Check error code to determine if retryable
        if e.code in ['NETWORK_ERROR', 'TEMPORARY_UNAVAILABLE']:
            raise TccRetryableError(f"Temporary error: {e}")
        else:
            raise TccNonRetryableError(f"Permanent error: {e}")
```

---

### 5. Event Publishing

Publish events for monitoring and integration:

```python
from fireflytx import participant_events

@participant_events(
    topic="order-events",
    include_timing=True,
    publish_on_try=True,
    publish_on_confirm=True,
    publish_on_cancel=True
)
@tcc_participant("payment", order=1)
class PaymentParticipant:
    # Events automatically published:
    # - payment.try.started
    # - payment.try.completed
    # - payment.confirm.started
    # - payment.confirm.completed
    # - payment.cancel.started (if cancelled)
    # - payment.cancel.completed

    @try_method()
    async def try_payment(self, data):
        return {"authorized": True}

    @confirm_method()
    async def confirm_payment(self, try_result):
        pass

    @cancel_method()
    async def cancel_payment(self, try_result):
        pass
```

---

## Best Practices

> **💡 Learn from experience:** These practices will save you hours of debugging and prevent production issues.

### 1. Always Make Operations Idempotent

**Why?** Methods can be retried multiple times. Non-idempotent operations cause duplicate charges, double reservations, etc.

**❌ Bad Example:**
```python
@try_method()
async def reserve_payment(self, order_data):
    # Will create duplicate authorizations on retry!
    auth = await payment_service.authorize(order_data["amount"])
    return {"auth_id": auth.id}
```

**✅ Good Example:**
```python
@try_method()
async def reserve_payment(self, order_data, context: TccContext):
    # Use idempotency key
    idempotency_key = f"{context.correlation_id}-payment-auth"

    auth = await payment_service.authorize(
        amount=order_data["amount"],
        idempotency_key=idempotency_key
    )
    return {"auth_id": auth.id}
```

---

### 2. Set Reservation Timeouts (TTL)

**Why?** If confirm never happens (e.g., system crash), reservations should auto-expire.

**❌ Bad Example:**
```python
@try_method()
async def reserve_inventory(self, order_data):
    # Reservation never expires - resources locked forever!
    reservation = await inventory_service.reserve(
        product_id=order_data["product_id"],
        quantity=order_data["quantity"]
    )
    return {"reservation_id": reservation.id}
```

**✅ Good Example:**
```python
@try_method()
async def reserve_inventory(self, order_data):
    # Reservation expires in 5 minutes if not confirmed
    reservation = await inventory_service.reserve(
        product_id=order_data["product_id"],
        quantity=order_data["quantity"],
        ttl_seconds=300  # Auto-release after 5 minutes
    )
    return {"reservation_id": reservation.id}
```

**Recommended TTL:**
- **Short transactions** (< 1 minute): 2-5 minutes
- **Medium transactions** (1-5 minutes): 10-15 minutes
- **Long transactions** (> 5 minutes): 30-60 minutes

---

### 3. Make Cancel Highly Reliable

**Why?** Cancel must succeed to release resources. If cancel fails, resources are locked forever.

**❌ Bad Example:**
```python
@cancel_method()
async def cancel_payment(self, try_result):
    # No error handling - what if this fails?
    await payment_service.void(try_result["auth_id"])
```

**✅ Good Example:**
```python
@cancel_method(timeout_ms=10000, retry=5)
async def cancel_payment(self, try_result, context: TccContext):
    auth_id = try_result.get("auth_id")

    if not auth_id:
        logger.warning("No auth_id to cancel")
        return

    try:
        # Try to void the authorization
        await payment_service.void(auth_id)

        logger.info(
            f"Payment authorization voided",
            extra={"auth_id": auth_id, "correlation_id": context.correlation_id}
        )

    except AuthorizationNotFoundError:
        # Idempotent - already voided or expired
        logger.info(f"Authorization {auth_id} already voided or expired")

    except Exception as e:
        # Log error and re-raise for retry
        logger.error(
            f"Failed to void authorization {auth_id}: {e}",
            extra={"correlation_id": context.correlation_id},
            exc_info=True
        )

        # Consider: Send alert, create manual task, etc.
        raise
```

---

### 4. Use Appropriate Execution Order

**Why?** Order matters! Fail fast by validating first, reserve expensive resources last.

**❌ Bad Example:**
```python
@tcc_participant("payment", order=1)  # Expensive operation first
class PaymentParticipant:
    ...

@tcc_participant("validation", order=2)  # Validation last
class ValidationParticipant:
    ...
```

**Problem:** If validation fails, we've already reserved payment (expensive undo).

**✅ Good Example:**
```python
@tcc_participant("validation", order=1)  # Validate first (cheap, fast)
class ValidationParticipant:
    ...

@tcc_participant("inventory", order=2)  # Reserve inventory (medium cost)
class InventoryParticipant:
    ...

@tcc_participant("payment", order=3)  # Reserve payment last (expensive)
class PaymentParticipant:
    ...
```

**Ordering Guidelines:**
1. **Validation** (order=1) - Fast, cheap, likely to fail
2. **Inventory/Resources** (order=2) - Medium cost
3. **Payment/Financial** (order=3) - Expensive, should succeed

---

### 5. Log Comprehensively

**Why?** TCC transactions are complex. Good logging is essential for debugging.

**✅ Good Example:**
```python
import logging

logger = logging.getLogger(__name__)

@try_method()
async def reserve_payment(self, order_data, context: TccContext):
    logger.info(
        "Starting payment authorization",
        extra={
            "correlation_id": context.correlation_id,
            "amount": order_data["amount"],
            "customer_id": order_data["customer_id"],
            "phase": "TRY"
        }
    )

    try:
        auth = await payment_service.authorize(order_data["amount"])

        logger.info(
            "Payment authorized successfully",
            extra={
                "correlation_id": context.correlation_id,
                "auth_id": auth.id,
                "amount": order_data["amount"],
                "phase": "TRY"
            }
        )

        return {"auth_id": auth.id}

    except Exception as e:
        logger.error(
            "Payment authorization failed",
            extra={
                "correlation_id": context.correlation_id,
                "error": str(e),
                "amount": order_data["amount"],
                "phase": "TRY"
            },
            exc_info=True
        )
        raise

@confirm_method()
async def confirm_payment(self, try_result, context: TccContext):
    logger.info(
        "Capturing payment",
        extra={
            "correlation_id": context.correlation_id,
            "auth_id": try_result["auth_id"],
            "phase": "CONFIRM"
        }
    )

    await payment_service.capture(try_result["auth_id"])

    logger.info(
        "Payment captured successfully",
        extra={
            "correlation_id": context.correlation_id,
            "auth_id": try_result["auth_id"],
            "phase": "CONFIRM"
        }
    )
```

---

### 6. Test All Three Phases

**Why?** All three phases must work correctly. Test each one.

**✅ Good Example:**
```python
import pytest

@pytest.mark.asyncio
async def test_payment_try_phase():
    """Test TRY phase."""
    participant = PaymentParticipant()
    context = TccContext(correlation_id="test-123")

    order_data = {"amount": 99.99, "customer_id": "CUST-123"}

    result = await participant.reserve_payment(order_data, context)

    assert result["auth_id"] is not None
    assert result["amount"] == 99.99

@pytest.mark.asyncio
async def test_payment_confirm_phase():
    """Test CONFIRM phase."""
    participant = PaymentParticipant()
    context = TccContext(correlation_id="test-123")

    # First do try
    order_data = {"amount": 99.99, "customer_id": "CUST-123"}
    try_result = await participant.reserve_payment(order_data, context)

    # Then confirm
    await participant.confirm_payment(try_result, context)

    # Verify payment was captured
    payment = await payment_service.get(try_result["auth_id"])
    assert payment.status == "captured"

@pytest.mark.asyncio
async def test_payment_cancel_phase():
    """Test CANCEL phase."""
    participant = PaymentParticipant()
    context = TccContext(correlation_id="test-123")

    # First do try
    order_data = {"amount": 99.99, "customer_id": "CUST-123"}
    try_result = await participant.reserve_payment(order_data, context)

    # Then cancel
    await participant.cancel_payment(try_result, context)

    # Verify authorization was voided
    payment = await payment_service.get(try_result["auth_id"])
    assert payment.status == "voided"

@pytest.mark.asyncio
async def test_full_tcc_transaction_success():
    """Test full TCC transaction (happy path)."""
    engine = create_tcc_engine()

    order_data = create_valid_order()

    result = await engine.execute(OrderProcessingTcc, order_data)

    assert result.is_success
    assert result.final_phase == "CONFIRMED"
    assert len(result.participants) == 3

@pytest.mark.asyncio
async def test_full_tcc_transaction_failure():
    """Test full TCC transaction (failure path)."""
    engine = create_tcc_engine()

    # Order that will fail at payment
    order_data = create_order_with_insufficient_funds()

    result = await engine.execute(OrderProcessingTcc, order_data)

    assert not result.is_success
    assert result.final_phase == "CANCELLED"
    assert result.failed_participant == "payment"
```

---

## Common Pitfalls

> **⚠️ Avoid these mistakes:** Learn from common errors to save debugging time.

### Pitfall 1: Forgetting Cancel Method

**Problem:**
```python
@tcc_participant("inventory", order=1)
class InventoryParticipant:
    @try_method()
    async def reserve_inventory(self, data):
        return {"reserved": True}

    @confirm_method()
    async def confirm_inventory(self, try_result):
        pass

    # ❌ No cancel method! Can't rollback!
```

**Impact:** If transaction fails, inventory stays reserved forever.

**Solution:**
```python
@cancel_method(retry=5)
async def cancel_inventory(self, try_result):
    await inventory_service.release(try_result["reservation_id"])
```

---

### Pitfall 2: No Reservation Timeout

**Problem:**
```python
@try_method()
async def reserve_inventory(self, data):
    # ❌ No TTL - reservation never expires!
    reservation = await inventory_service.reserve(
        product_id=data["product_id"],
        quantity=data["quantity"]
    )
    return {"reservation_id": reservation.id}
```

**Impact:** If system crashes before confirm/cancel, resources locked forever.

**Solution:**
```python
@try_method()
async def reserve_inventory(self, data):
    # ✅ Reservation expires in 5 minutes
    reservation = await inventory_service.reserve(
        product_id=data["product_id"],
        quantity=data["quantity"],
        ttl_seconds=300
    )
    return {"reservation_id": reservation.id}
```

---

### Pitfall 3: Non-Idempotent Operations

**Problem:**
```python
@confirm_method(retry=3)
async def confirm_payment(self, try_result):
    # ❌ Will charge customer 3 times if first attempt times out!
    await payment_service.charge(try_result["amount"])
```

**Impact:** Duplicate charges, angry customers, refunds.

**Solution:**
```python
@confirm_method(retry=3)
async def confirm_payment(self, try_result, context: TccContext):
    # ✅ Use idempotency key
    await payment_service.capture(
        authorization_id=try_result["auth_id"],
        idempotency_key=f"{context.correlation_id}-capture"
    )
```

---

### Pitfall 4: Wrong Execution Order

**Problem:**
```python
@tcc_participant("payment", order=1)  # Expensive operation first
class PaymentParticipant:
    ...

@tcc_participant("validation", order=2)  # Validation last
class ValidationParticipant:
    ...
```

**Impact:** Waste money on payment authorizations that fail validation.

**Solution:**
```python
@tcc_participant("validation", order=1)  # Validate first
class ValidationParticipant:
    ...

@tcc_participant("payment", order=2)  # Payment after validation
class PaymentParticipant:
    ...
```

---

### Pitfall 5: Not Handling Partial Try Failures

**Problem:**
```python
@try_method()
async def reserve_multiple_items(self, data):
    for item in data["items"]:
        await inventory_service.reserve(item)  # What if 3rd item fails?
    return {"reserved": len(data["items"])}

# ❌ No way to know which items were reserved!
```

**Impact:** Can't properly cancel - don't know what to undo.

**Solution:**
```python
@try_method()
async def reserve_multiple_items(self, data, context: TccContext):
    reservations = []

    for item in data["items"]:
        reservation = await inventory_service.reserve(item)
        reservations.append(reservation)

    # Store for cancel
    context.set_data("reservations", reservations)

    return {"reservations": reservations}

@cancel_method()
async def cancel_multiple_items(self, try_result, context: TccContext):
    reservations = try_result.get("reservations", [])

    for reservation in reservations:
        await inventory_service.release(reservation["id"])
```

---

## Troubleshooting

> **🔧 Debug like a pro:** Common issues and how to fix them.

### Issue 1: Transaction Hangs in TRY Phase

**Symptoms:**
- Transaction never completes
- No error messages
- Participants seem to run but never finish

**Diagnosis:**

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check which participant is hanging
result = await engine.execute(MyTcc, data, timeout_ms=30000)
print(f"Failed at: {result.failed_participant}")
```

**Common Causes:**

1. **Blocking operation in async method:**
   ```python
   # ❌ This blocks forever
   @try_method()
   async def bad_try(self, data):
       time.sleep(10)  # Blocks event loop!
   ```

   **Fix:** Use `await asyncio.sleep(10)` instead

2. **Missing await:**
   ```python
   # ❌ Forgot await
   @try_method()
   async def bad_try(self, data):
       result = async_function()  # Should be: await async_function()
       return result
   ```

   **Fix:** Add `await`

---

### Issue 2: Cancel Not Running

**Symptoms:**
- Try phase fails but cancel doesn't run
- Resources not released

**Diagnosis:**

```python
result = await engine.execute(MyTcc, data)
print(f"Final phase: {result.final_phase}")  # Should be "CANCELLED"
print(f"Cancelled participants: {result.cancelled_participants}")
```

**Common Causes:**

1. **No cancel method defined:**
   ```python
   @try_method()
   async def try_reserve(self, data):
       return {"reserved": True}

   # ❌ Missing @cancel_method
   ```

   **Fix:** Add cancel method

2. **Cancel method crashes:**
   ```python
   @cancel_method()
   async def cancel_reserve(self, try_result):
       # ❌ Crashes if key doesn't exist
       await service.release(try_result["reservation_id"])
   ```

   **Fix:** Add error handling:
   ```python
   @cancel_method()
   async def cancel_reserve(self, try_result):
       reservation_id = try_result.get("reservation_id")
       if reservation_id:
           await service.release(reservation_id)
   ```

---

### Issue 3: Timeout Errors

**Symptoms:**
```
Error: Participant execution timeout after 5000ms
```

**Solutions:**

1. **Increase timeout:**
   ```python
   @try_method(timeout_ms=30000)  # 30 seconds
   async def slow_try(self, data): ...
   ```

2. **Optimize the operation:**
   - Use connection pooling
   - Add caching
   - Parallelize sub-operations

---

### Issue 4: Resources Not Released After Crash

**Symptoms:**
- System crashed during transaction
- Reservations still locked after restart

**Diagnosis:**

```bash
# Check for orphaned reservations
SELECT * FROM reservations WHERE status='reserved' AND created_at < NOW() - INTERVAL '10 minutes';
```

**Solutions:**

1. **Use TTL on reservations:**
   ```python
   @try_method()
   async def reserve(self, data):
       return await service.reserve(data, ttl_seconds=300)
   ```

2. **Run cleanup job:**
   ```python
   # Cron job to clean up expired reservations
   async def cleanup_expired_reservations():
       await inventory_service.cleanup_expired()
       await payment_service.void_expired_authorizations()
   ```

3. **Enable persistence and recovery:**
   ```python
   from fireflytx import create_tcc_engine, RedisPersistenceProvider

   engine = create_tcc_engine(
       persistence_provider=RedisPersistenceProvider(host="redis")
   )

   # After restart, recover in-flight transactions
   await engine.recover_transactions()
   ```

---

## Real-World Examples

### Example 1: Money Transfer Between Accounts

Transfer money between two bank accounts with two-phase commit.

```python
@tcc("money-transfer")
class MoneyTransferTcc:
    """Transfer money between accounts with strong consistency."""

    @tcc_participant("source_account", order=1)
    class SourceAccountParticipant:
        """Debit source account."""

        @try_method(timeout_ms=5000, retry=3)
        async def reserve_debit(self, transfer_data, context: TccContext):
            """TRY: Reserve funds in source account."""
            # Check balance
            balance = await account_service.get_balance(
                transfer_data["source_account_id"]
            )

            if balance < transfer_data["amount"]:
                raise ValueError("Insufficient funds")

            # Create hold on funds
            hold = await account_service.create_hold(
                account_id=transfer_data["source_account_id"],
                amount=transfer_data["amount"],
                ttl_seconds=300
            )

            return {"hold_id": hold.id}

        @confirm_method(timeout_ms=3000)
        async def confirm_debit(self, try_result, context: TccContext):
            """CONFIRM: Actually debit the account."""
            await account_service.commit_hold(try_result["hold_id"])

        @cancel_method(timeout_ms=3000, retry=5)
        async def cancel_debit(self, try_result, context: TccContext):
            """CANCEL: Release the hold."""
            hold_id = try_result.get("hold_id")
            if hold_id:
                await account_service.release_hold(hold_id)

    @tcc_participant("destination_account", order=2)
    class DestinationAccountParticipant:
        """Credit destination account."""

        @try_method(timeout_ms=5000, retry=3)
        async def reserve_credit(self, transfer_data, context: TccContext):
            """TRY: Reserve credit in destination account."""
            # Create pending credit
            pending = await account_service.create_pending_credit(
                account_id=transfer_data["destination_account_id"],
                amount=transfer_data["amount"],
                ttl_seconds=300
            )

            return {"pending_id": pending.id}

        @confirm_method(timeout_ms=3000)
        async def confirm_credit(self, try_result, context: TccContext):
            """CONFIRM: Actually credit the account."""
            await account_service.commit_pending_credit(try_result["pending_id"])

        @cancel_method(timeout_ms=3000, retry=5)
        async def cancel_credit(self, try_result, context: TccContext):
            """CANCEL: Remove the pending credit."""
            pending_id = try_result.get("pending_id")
            if pending_id:
                await account_service.cancel_pending_credit(pending_id)
```

**Usage:**
```python
transfer_data = {
    "source_account_id": "ACC-123",
    "destination_account_id": "ACC-456",
    "amount": 100.00,
    "reference": "Payment for invoice #789"
}

result = await engine.execute(MoneyTransferTcc, transfer_data)

if result.is_success:
    print(f"✅ Transfer completed: ${transfer_data['amount']}")
else:
    print(f"❌ Transfer failed: {result.error}")
```

---

### Example 2: Hotel + Flight Booking

Book hotel and flight together with rollback if either fails.

```python
@tcc("travel-booking")
class TravelBookingTcc:
    """Book flight and hotel together."""

    @tcc_participant("flight", order=1)
    class FlightParticipant:
        @try_method(timeout_ms=15000, retry=3)
        async def reserve_flight(self, booking_data, context: TccContext):
            """TRY: Reserve flight seat."""
            reservation = await flight_api.reserve(
                from_city=booking_data["from"],
                to_city=booking_data["to"],
                date=booking_data["date"],
                passengers=booking_data["passengers"],
                ttl_minutes=10
            )

            context.set_data("flight_price", reservation.price)

            return {
                "confirmation_code": reservation.confirmation_code,
                "price": reservation.price
            }

        @confirm_method(timeout_ms=10000)
        async def confirm_flight(self, try_result, context: TccContext):
            """CONFIRM: Issue flight ticket."""
            await flight_api.confirm(try_result["confirmation_code"])

        @cancel_method(timeout_ms=10000, retry=5)
        async def cancel_flight(self, try_result, context: TccContext):
            """CANCEL: Release flight reservation."""
            await flight_api.cancel(try_result["confirmation_code"])

    @tcc_participant("hotel", order=2)
    class HotelParticipant:
        @try_method(timeout_ms=15000, retry=3)
        async def reserve_hotel(self, booking_data, context: TccContext):
            """TRY: Reserve hotel room."""
            reservation = await hotel_api.reserve(
                city=booking_data["to"],
                check_in=booking_data["date"],
                check_out=booking_data["return_date"],
                guests=booking_data["passengers"],
                ttl_minutes=10
            )

            context.set_data("hotel_price", reservation.price)

            return {
                "confirmation_code": reservation.confirmation_code,
                "price": reservation.price
            }

        @confirm_method(timeout_ms=10000)
        async def confirm_hotel(self, try_result, context: TccContext):
            """CONFIRM: Confirm hotel booking."""
            await hotel_api.confirm(try_result["confirmation_code"])

        @cancel_method(timeout_ms=10000, retry=5)
        async def cancel_hotel(self, try_result, context: TccContext):
            """CANCEL: Cancel hotel reservation."""
            await hotel_api.cancel(try_result["confirmation_code"])

    @tcc_participant("payment", order=3)
    class PaymentParticipant:
        @try_method(timeout_ms=10000, retry=5)
        async def reserve_payment(self, booking_data, context: TccContext):
            """TRY: Authorize total payment."""
            flight_price = context.get_data("flight_price", 0)
            hotel_price = context.get_data("hotel_price", 0)
            total = flight_price + hotel_price

            auth = await payment_service.authorize(
                amount=total,
                customer_id=booking_data["customer_id"],
                idempotency_key=context.correlation_id
            )

            return {"auth_id": auth.id, "total": total}

        @confirm_method(timeout_ms=5000, retry=3)
        async def confirm_payment(self, try_result, context: TccContext):
            """CONFIRM: Capture payment."""
            await payment_service.capture(try_result["auth_id"])

        @cancel_method(timeout_ms=5000, retry=5)
        async def cancel_payment(self, try_result, context: TccContext):
            """CANCEL: Void authorization."""
            await payment_service.void(try_result["auth_id"])
```

---

## Summary & Next Steps

### Key Takeaways

1. **TCC is for strong consistency** - Use when you need all-or-nothing guarantees
2. **Three methods required** - Try (reserve), Confirm (commit), Cancel (rollback)
3. **Always use TTL** - Reservations must expire to prevent resource leaks
4. **Make everything idempotent** - All three methods can run multiple times
5. **Cancel must be reliable** - Use high retry counts and error handling

### TCC vs SAGA Quick Reference

| Use TCC When | Use SAGA When |
|--------------|---------------|
| Need strong consistency | Eventually consistent is OK |
| Financial transactions | Long-running workflows |
| Can lock resources | Can't lock resources |
| Short-lived (seconds/minutes) | Long-lived (hours/days) |
| Simple coordination | Complex dependencies |

### Learning Path

**Next Steps:**
1. Try the [Step-by-Step Tutorial](#step-by-step-tutorial)
2. Review [Best Practices](#best-practices)
3. Study [Real-World Examples](#real-world-examples)
4. Compare with [SAGA Pattern Guide](saga-pattern.md)
5. Explore [Architecture Guide](architecture.md) for deep dive

### Getting Help

- **Documentation:** [docs/](../docs/)
- **Examples:** [examples/](../examples/)
- **Issues:** [GitHub Issues](https://github.com/firefly-oss/python-transactional-engine/issues)

---

**Happy TCC building! 🚀**

