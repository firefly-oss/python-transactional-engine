#!/usr/bin/env python3
"""
Basic TCC (Try-Confirm-Cancel) pattern example demonstrating payment processing.

This example shows how to implement a TCC transaction with multiple participants
for payment authorization, fraud checking, and account management.
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
from fireflytx import TccEngine
from fireflytx.decorators.tcc import tcc, tcc_participant, try_method, confirm_method, cancel_method
from fireflytx.events.tcc_events import LoggingTccEvents


# Data models
class PaymentRequest(BaseModel):
    payment_id: str
    customer_id: str
    merchant_id: str
    amount: float
    currency: str = "USD"
    payment_method: str


class PaymentReservation(BaseModel):
    reservation_id: str
    amount: float
    expires_at: str


class FraudCheck(BaseModel):
    check_id: str
    risk_score: float
    status: str


class AccountLock(BaseModel):
    lock_id: str
    account_id: str
    amount: float


# TCC implementation
@tcc("payment-processing")
class PaymentProcessingTcc:
    """
    TCC transaction for processing payments with fraud detection and account management.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @tcc_participant("payment", order=1)
    class PaymentParticipant:
        """Handles payment authorization and processing."""
        
        def __init__(self):
            self.logger = logging.getLogger(__name__)
        
        @try_method(timeout_ms=10000, retry=2)
        async def try_payment(self, request: PaymentRequest) -> PaymentReservation:
            """Try to reserve payment authorization."""
            self.logger.info(f"Trying payment reservation for {request.payment_id}")
            
            await asyncio.sleep(0.2)  # Simulate payment gateway call
            
            # Simulate failure for specific payment methods
            if request.payment_method == "DECLINED_CARD":
                raise Exception("Card declined by issuer")
            
            # Simulate high amount failure
            if request.amount > 5000:
                raise Exception("Amount exceeds daily limit")
            
            reservation = PaymentReservation(
                reservation_id=f"res-{request.payment_id}",
                amount=request.amount,
                expires_at="2024-01-15T11:00:00Z"
            )
            
            self.logger.info(f"Payment reserved: {reservation.reservation_id}")
            return reservation
        
        @confirm_method(timeout_ms=5000)
        async def confirm_payment(self, reservation: PaymentReservation) -> None:
            """Confirm the payment - actually charge the customer."""
            self.logger.info(f"Confirming payment: {reservation.reservation_id}")
            
            await asyncio.sleep(0.1)  # Simulate final charge
            
            self.logger.info(f"Payment confirmed and charged: ${reservation.amount}")
        
        @cancel_method(timeout_ms=3000)
        async def cancel_payment(self, reservation: PaymentReservation) -> None:
            """Cancel the payment reservation."""
            self.logger.info(f"Cancelling payment reservation: {reservation.reservation_id}")
            
            await asyncio.sleep(0.1)  # Simulate cancellation
            
            self.logger.info("Payment reservation cancelled")
    
    @tcc_participant("fraud", order=2)
    class FraudParticipant:
        """Handles fraud detection and risk assessment."""
        
        def __init__(self):
            self.logger = logging.getLogger(__name__)
        
        @try_method(timeout_ms=3000)
        async def try_fraud_check(self, request: PaymentRequest) -> FraudCheck:
            """Perform fraud risk assessment."""
            self.logger.info(f"Running fraud check for payment {request.payment_id}")
            
            await asyncio.sleep(0.1)  # Simulate fraud analysis
            
            # Simulate high-risk detection
            if request.customer_id == "HIGH_RISK_CUSTOMER":
                raise Exception("High fraud risk detected")
            
            # Calculate risk score based on amount
            risk_score = min(request.amount / 10000, 0.9)  # Higher amounts = higher risk
            
            check = FraudCheck(
                check_id=f"fraud-{request.payment_id}",
                risk_score=risk_score,
                status="approved" if risk_score < 0.5 else "flagged"
            )
            
            self.logger.info(f"Fraud check completed: {check.check_id} (risk: {risk_score:.2f})")
            return check
        
        @confirm_method
        async def confirm_fraud_check(self, check: FraudCheck) -> None:
            """Log the successful fraud check."""
            self.logger.info(f"Confirming fraud check: {check.check_id}")
            
            await asyncio.sleep(0.05)
            
            self.logger.info("Fraud check logged as successful")
        
        @cancel_method
        async def cancel_fraud_check(self, check: FraudCheck) -> None:
            """Clean up fraud check data."""
            self.logger.info(f"Cancelling fraud check: {check.check_id}")
            
            await asyncio.sleep(0.05)
            
            self.logger.info("Fraud check data cleaned up")
    
    @tcc_participant("account", order=3)
    class AccountParticipant:
        """Manages account locks and balance holds."""
        
        def __init__(self):
            self.logger = logging.getLogger(__name__)
        
        @try_method(timeout_ms=2000)
        async def try_account_lock(self, request: PaymentRequest) -> AccountLock:
            """Lock the customer account for the transaction amount."""
            self.logger.info(f"Trying account lock for customer {request.customer_id}")
            
            await asyncio.sleep(0.1)  # Simulate account service call
            
            # Simulate insufficient funds
            if request.amount > 1000 and request.customer_id == "LOW_BALANCE_CUSTOMER":
                raise Exception("Insufficient account balance")
            
            lock = AccountLock(
                lock_id=f"lock-{request.payment_id}",
                account_id=request.customer_id,
                amount=request.amount
            )
            
            self.logger.info(f"Account locked: {lock.lock_id} for ${lock.amount}")
            return lock
        
        @confirm_method
        async def confirm_account_lock(self, lock: AccountLock) -> None:
            """Convert the lock to an actual debit."""
            self.logger.info(f"Confirming account debit: {lock.lock_id}")
            
            await asyncio.sleep(0.1)  # Simulate account update
            
            self.logger.info(f"Account debited: ${lock.amount}")
        
        @cancel_method
        async def cancel_account_lock(self, lock: AccountLock) -> None:
            """Release the account lock."""
            self.logger.info(f"Releasing account lock: {lock.lock_id}")
            
            await asyncio.sleep(0.1)  # Simulate lock release
            
            self.logger.info("Account lock released")


async def run_successful_tcc():
    """Run a successful TCC payment transaction."""
    print("\n=== Running Successful TCC Payment ===")
    
    # Create TCC engine with events
    tcc_engine = TccEngine()
    events_handler = LoggingTccEvents()
    
    # Initialize engine (in real usage, this would connect to Java)
    # await tcc_engine.initialize(events_handler=events_handler)
    
    # Create test payment request
    payment_request = PaymentRequest(
        payment_id="PAY-001",
        customer_id="CUST-123",
        merchant_id="MERCH-456",
        amount=299.99,
        payment_method="VISA_4111"
    )
    
    print(f"Processing payment: {payment_request.payment_id}")
    print(f"Customer: {payment_request.customer_id}")
    print(f"Amount: ${payment_request.amount}")
    print(f"Payment method: {payment_request.payment_method}")
    
    try:
        # Execute TCC (this would use the real Java engine)
        # For demo purposes, we'll simulate the execution
        tcc_instance = PaymentProcessingTcc()
        payment_participant = tcc_instance.PaymentParticipant()
        fraud_participant = tcc_instance.FraudParticipant()
        account_participant = tcc_instance.AccountParticipant()
        
        print("\n🔄 TCC Try Phase...")
        
        # Try phase - all participants reserve resources
        payment_reservation = await payment_participant.try_payment(payment_request)
        print(f"✓ Payment reserved: {payment_reservation.reservation_id}")
        
        fraud_check = await fraud_participant.try_fraud_check(payment_request)
        print(f"✓ Fraud check passed: {fraud_check.check_id} (risk: {fraud_check.risk_score:.2f})")
        
        account_lock = await account_participant.try_account_lock(payment_request)
        print(f"✓ Account locked: {account_lock.lock_id}")
        
        print("\n✅ TCC Confirm Phase...")
        
        # Confirm phase - all participants commit their changes
        await payment_participant.confirm_payment(payment_reservation)
        print("✓ Payment confirmed and charged")
        
        await fraud_participant.confirm_fraud_check(fraud_check)
        print("✓ Fraud check logged")
        
        await account_participant.confirm_account_lock(account_lock)
        print("✓ Account debited")
        
        print(f"\n🎉 Payment {payment_request.payment_id} completed successfully!")
        print(f"Final amount charged: ${payment_request.amount}")
        
    except Exception as e:
        print(f"\n❌ TCC failed: {e}")
    
    # await tcc_engine.shutdown()


async def run_failing_tcc():
    """Run a TCC that fails during try phase and requires cancellation."""
    print("\n=== Running Failing TCC Payment ===")
    
    # Create payment that will fail at fraud check
    failing_request = PaymentRequest(
        payment_id="PAY-FAIL",
        customer_id="HIGH_RISK_CUSTOMER",
        merchant_id="MERCH-789",
        amount=999.99,
        payment_method="VISA_4111"
    )
    
    print(f"Processing payment: {failing_request.payment_id}")
    print(f"Customer: {failing_request.customer_id} (high risk)")
    print(f"Amount: ${failing_request.amount}")
    
    tcc_instance = PaymentProcessingTcc()
    payment_participant = tcc_instance.PaymentParticipant()
    fraud_participant = tcc_instance.FraudParticipant()
    account_participant = tcc_instance.AccountParticipant()
    
    payment_reservation = None
    
    try:
        print("\n🔄 TCC Try Phase...")
        
        # Try phase - payment succeeds
        payment_reservation = await payment_participant.try_payment(failing_request)
        print(f"✓ Payment reserved: {payment_reservation.reservation_id}")
        
        # Try phase - fraud check fails
        try:
            fraud_check = await fraud_participant.try_fraud_check(failing_request)
            print(f"✓ Fraud check passed: {fraud_check.check_id}")
        except Exception as fraud_error:
            print(f"❌ Fraud check failed: {fraud_error}")
            
            # Cancel phase - rollback successful operations
            print("\n🔄 TCC Cancel Phase...")
            
            if payment_reservation:
                await payment_participant.cancel_payment(payment_reservation)
                print("✓ Payment reservation cancelled")
            
            raise fraud_error
        
    except Exception as e:
        print(f"\n💥 TCC failed after cancellation: {e}")


async def run_insufficient_funds_tcc():
    """Run a TCC that fails due to insufficient account funds."""
    print("\n=== Running Insufficient Funds TCC ===")
    
    # Create payment that will fail at account lock
    insufficient_request = PaymentRequest(
        payment_id="PAY-INSUFFICIENT",
        customer_id="LOW_BALANCE_CUSTOMER",
        merchant_id="MERCH-999",
        amount=1500.00,  # This will exceed available balance
        payment_method="VISA_4111"
    )
    
    print(f"Processing payment: {insufficient_request.payment_id}")
    print(f"Customer: {insufficient_request.customer_id} (low balance)")
    print(f"Amount: ${insufficient_request.amount}")
    
    tcc_instance = PaymentProcessingTcc()
    payment_participant = tcc_instance.PaymentParticipant()
    fraud_participant = tcc_instance.FraudParticipant()
    account_participant = tcc_instance.AccountParticipant()
    
    payment_reservation = None
    fraud_check = None
    
    try:
        print("\n🔄 TCC Try Phase...")
        
        # Step 1: Payment reservation succeeds
        payment_reservation = await payment_participant.try_payment(insufficient_request)
        print(f"✓ Payment reserved: {payment_reservation.reservation_id}")
        
        # Step 2: Fraud check succeeds
        fraud_check = await fraud_participant.try_fraud_check(insufficient_request)
        print(f"✓ Fraud check passed: {fraud_check.check_id}")
        
        # Step 3: Account lock fails
        try:
            account_lock = await account_participant.try_account_lock(insufficient_request)
            print(f"✓ Account locked: {account_lock.lock_id}")
        except Exception as account_error:
            print(f"❌ Account lock failed: {account_error}")
            
            # Cancel phase - rollback all successful operations
            print("\n🔄 TCC Cancel Phase...")
            
            if fraud_check:
                await fraud_participant.cancel_fraud_check(fraud_check)
                print("✓ Fraud check cancelled")
            
            if payment_reservation:
                await payment_participant.cancel_payment(payment_reservation)
                print("✓ Payment reservation cancelled")
            
            raise account_error
        
    except Exception as e:
        print(f"\n💥 TCC failed after cancellation: {e}")


async def main():
    """Main example runner."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("🚀 TCC Pattern Basic Examples")
    print("=" * 50)
    
    # Run different scenarios
    await run_successful_tcc()
    await run_failing_tcc()
    await run_insufficient_funds_tcc()
    
    print("\n✨ All examples completed!")
    print("\nKey Takeaways:")
    print("- TCC ensures ACID properties across distributed resources")
    print("- Try phase reserves resources without committing changes")
    print("- Confirm phase commits all reserved changes atomically")
    print("- Cancel phase releases all reservations if any step fails")
    print("- Participant order ensures proper dependency management")


if __name__ == "__main__":
    asyncio.run(main())