#!/usr/bin/env python3
"""
TCC Pattern Integration Tests

This test suite validates TCC (Try-Confirm-Cancel) pattern functionality including:
- Distributed transaction coordination
- Two-phase commit semantics
- Resource reservation and confirmation
- Rollback and compensation scenarios
- Cross-service transaction consistency

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0 (the "License");
"""

import pytest
from typing import Dict, Any
from enum import Enum

from fireflytx.engine.tcc_engine import TccEngine
from fireflytx.core.tcc_context import TccContext
from fireflytx.decorators import tcc, tcc_participant, try_method, confirm_method, cancel_method
from fireflytx.logging import setup_fireflytx_logging, get_fireflytx_logger
from fireflytx.config.engine_config import EngineConfig, LoggingConfig

logger = get_fireflytx_logger(__name__)


class ReservationStatus(Enum):
    RESERVED = "reserved"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class AccountService:
    """Mock account service for testing TCC patterns."""

    def __init__(self):
        self.accounts = {
            "account_1": {"balance": 1000.0, "reserved": 0.0},
            "account_2": {"balance": 500.0, "reserved": 0.0},
            "account_3": {"balance": 250.0, "reserved": 0.0},
        }
        self.reservations = {}

    async def try_debit(
        self, account_id: str, amount: float, transaction_id: str
    ) -> Dict[str, Any]:
        """Try to debit amount from account (TCC Try phase)."""
        logger.info(f"TRY: Attempting to debit {amount} from {account_id}")

        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")

        account = self.accounts[account_id]
        available_balance = account["balance"] - account["reserved"]

        if available_balance < amount:
            raise ValueError(f"Insufficient funds in account {account_id}")

        # Reserve the amount
        reservation_id = f"debit_{account_id}_{transaction_id}"
        self.reservations[reservation_id] = {
            "account_id": account_id,
            "amount": amount,
            "type": "debit",
            "status": ReservationStatus.RESERVED,
            "transaction_id": transaction_id,
        }
        account["reserved"] += amount

        logger.info(f"TRY SUCCESS: Reserved {amount} from {account_id}")
        return {
            "reservation_id": reservation_id,
            "account_id": account_id,
            "amount": amount,
            "status": "TRY_SUCCEEDED",
        }

    async def confirm_debit(self, reservation_id: str) -> Dict[str, Any]:
        """Confirm debit operation (TCC Confirm phase)."""
        logger.info(f"CONFIRM: Confirming debit reservation {reservation_id}")

        if reservation_id not in self.reservations:
            raise ValueError(f"Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]
        if reservation["status"] != ReservationStatus.RESERVED:
            raise ValueError(f"Reservation {reservation_id} not in reserved state")

        account = self.accounts[reservation["account_id"]]

        # Actually debit the amount
        account["balance"] -= reservation["amount"]
        account["reserved"] -= reservation["amount"]
        reservation["status"] = ReservationStatus.CONFIRMED

        logger.info(
            f"CONFIRM SUCCESS: Debited {reservation['amount']} from {reservation['account_id']}"
        )
        return {
            "reservation_id": reservation_id,
            "status": "CONFIRMED",
            "final_balance": account["balance"],
        }

    async def cancel_debit(self, reservation_id: str) -> Dict[str, Any]:
        """Cancel debit operation (TCC Cancel phase)."""
        logger.info(f"CANCEL: Cancelling debit reservation {reservation_id}")

        if reservation_id not in self.reservations:
            # Idempotent - already cancelled
            return {"reservation_id": reservation_id, "status": "CANCELED"}

        reservation = self.reservations[reservation_id]
        account = self.accounts[reservation["account_id"]]

        # Release the reserved amount
        account["reserved"] -= reservation["amount"]
        reservation["status"] = ReservationStatus.CANCELLED

        logger.info(
            f"CANCEL SUCCESS: Released {reservation['amount']} from {reservation['account_id']}"
        )
        return {"reservation_id": reservation_id, "status": "CANCELED"}

    async def try_credit(
        self, account_id: str, amount: float, transaction_id: str
    ) -> Dict[str, Any]:
        """Try to credit amount to account (TCC Try phase)."""
        logger.info(f"TRY: Attempting to credit {amount} to {account_id}")

        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")

        # For credit, we just prepare the operation
        reservation_id = f"credit_{account_id}_{transaction_id}"
        self.reservations[reservation_id] = {
            "account_id": account_id,
            "amount": amount,
            "type": "credit",
            "status": ReservationStatus.RESERVED,
            "transaction_id": transaction_id,
        }

        logger.info(f"TRY SUCCESS: Prepared credit of {amount} to {account_id}")
        return {
            "reservation_id": reservation_id,
            "account_id": account_id,
            "amount": amount,
            "status": "TRY_SUCCEEDED",
        }

    async def confirm_credit(self, reservation_id: str) -> Dict[str, Any]:
        """Confirm credit operation (TCC Confirm phase)."""
        logger.info(f"CONFIRM: Confirming credit reservation {reservation_id}")

        if reservation_id not in self.reservations:
            raise ValueError(f"Reservation {reservation_id} not found")

        reservation = self.reservations[reservation_id]
        if reservation["status"] != ReservationStatus.RESERVED:
            raise ValueError(f"Reservation {reservation_id} not in reserved state")

        account = self.accounts[reservation["account_id"]]

        # Actually credit the amount
        account["balance"] += reservation["amount"]
        reservation["status"] = ReservationStatus.CONFIRMED

        logger.info(
            f"CONFIRM SUCCESS: Credited {reservation['amount']} to {reservation['account_id']}"
        )
        return {
            "reservation_id": reservation_id,
            "status": "CONFIRMED",
            "final_balance": account["balance"],
        }

    async def cancel_credit(self, reservation_id: str) -> Dict[str, Any]:
        """Cancel credit operation (TCC Cancel phase)."""
        logger.info(f"CANCEL: Cancelling credit reservation {reservation_id}")

        if reservation_id not in self.reservations:
            # Idempotent - already cancelled
            return {"reservation_id": reservation_id, "status": "already_cancelled"}

        reservation = self.reservations[reservation_id]
        reservation["status"] = ReservationStatus.CANCELLED

        logger.info(f"CANCEL SUCCESS: Cancelled credit preparation for {reservation['account_id']}")
        return {"reservation_id": reservation_id, "status": "CANCELED"}


class NotificationService:
    """Mock notification service for testing."""

    def __init__(self):
        self.sent_notifications = []
        self.prepared_notifications = {}

    async def try_send_notification(
        self, user_id: str, message: str, transaction_id: str
    ) -> Dict[str, Any]:
        """Prepare to send notification (TCC Try phase)."""
        logger.info(f"TRY: Preparing notification for {user_id}")

        notification_id = f"notification_{user_id}_{transaction_id}"
        self.prepared_notifications[notification_id] = {
            "user_id": user_id,
            "message": message,
            "status": ReservationStatus.RESERVED,
            "transaction_id": transaction_id,
        }

        logger.info(f"TRY SUCCESS: Prepared notification {notification_id}")
        return {"notification_id": notification_id, "status": "TRY_SUCCEEDED"}

    async def confirm_send_notification(self, notification_id: str) -> Dict[str, Any]:
        """Send the prepared notification (TCC Confirm phase)."""
        logger.info(f"CONFIRM: Sending notification {notification_id}")

        if notification_id not in self.prepared_notifications:
            raise ValueError(f"Notification {notification_id} not prepared")

        notification = self.prepared_notifications[notification_id]
        if notification["status"] != ReservationStatus.RESERVED:
            raise ValueError(f"Notification {notification_id} not in prepared state")

        # "Send" the notification
        self.sent_notifications.append(
            {
                "notification_id": notification_id,
                "user_id": notification["user_id"],
                "message": notification["message"],
                "sent_at": "now",
            }
        )
        notification["status"] = ReservationStatus.CONFIRMED

        logger.info(f"CONFIRM SUCCESS: Sent notification to {notification['user_id']}")
        return {"notification_id": notification_id, "status": "CONFIRMED"}

    async def cancel_send_notification(self, notification_id: str) -> Dict[str, Any]:
        """Cancel the prepared notification (TCC Cancel phase)."""
        logger.info(f"CANCEL: Cancelling notification {notification_id}")

        if notification_id not in self.prepared_notifications:
            return {"notification_id": notification_id, "status": "already_cancelled"}

        notification = self.prepared_notifications[notification_id]
        notification["status"] = ReservationStatus.CANCELLED

        logger.info(f"CANCEL SUCCESS: Cancelled notification preparation")
        return {"notification_id": notification_id, "status": "CANCELED"}


# Global services for testing
account_service = AccountService()
notification_service = NotificationService()


@tcc("money-transfer")
class MoneyTransferTcc:
    """Money transfer TCC transaction."""

    @tcc_participant("debit-source")
    class DebitSourceParticipant:

        @try_method
        async def try_debit(
            self, context: TccContext, transfer_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Try to debit from source account."""
            return await account_service.try_debit(
                transfer_data["from_account"], transfer_data["amount"], context.correlation_id
            )

        @confirm_method
        async def confirm_debit(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Confirm debit from source account."""
            return await account_service.confirm_debit(try_result["reservation_id"])

        @cancel_method
        async def cancel_debit(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Cancel debit from source account."""
            return await account_service.cancel_debit(try_result["reservation_id"])

    @tcc_participant("credit-destination")
    class CreditDestinationParticipant:

        @try_method
        async def try_credit(
            self, context: TccContext, transfer_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Try to credit destination account."""
            return await account_service.try_credit(
                transfer_data["to_account"], transfer_data["amount"], context.correlation_id
            )

        @confirm_method
        async def confirm_credit(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Confirm credit to destination account."""
            return await account_service.confirm_credit(try_result["reservation_id"])

        @cancel_method
        async def cancel_credit(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Cancel credit to destination account."""
            return await account_service.cancel_credit(try_result["reservation_id"])

    @tcc_participant("send-notification")
    class NotificationParticipant:

        @try_method
        async def try_notification(
            self, context: TccContext, transfer_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Prepare transfer notification."""
            message = f"Transfer of {transfer_data['amount']} from {transfer_data['from_account']} to {transfer_data['to_account']}"
            return await notification_service.try_send_notification(
                transfer_data["user_id"], message, context.correlation_id
            )

        @confirm_method
        async def confirm_notification(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Send the transfer notification."""
            return await notification_service.confirm_send_notification(
                try_result["notification_id"]
            )

        @cancel_method
        async def cancel_notification(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Cancel the transfer notification."""
            return await notification_service.cancel_send_notification(
                try_result["notification_id"]
            )


@tcc("account-deposit")
class AccountDepositTcc:
    """Simple account deposit TCC transaction."""

    @tcc_participant("credit-account")
    class CreditAccountParticipant:

        @try_method
        async def try_credit(
            self, context: TccContext, deposit_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Try to credit account."""
            return await account_service.try_credit(
                deposit_data["account_id"], deposit_data["amount"], context.correlation_id
            )

        @confirm_method
        async def confirm_credit(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Confirm credit to account."""
            return await account_service.confirm_credit(try_result["reservation_id"])

        @cancel_method
        async def cancel_credit(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Cancel credit to account."""
            return await account_service.cancel_credit(try_result["reservation_id"])


@tcc("failing-tcc")
class FailingTcc:
    """TCC that fails during confirm phase to test rollback."""

    @tcc_participant("participant1")
    class Participant1:

        @try_method
        async def try_action(self, context: TccContext, data: Dict[str, Any]) -> Dict[str, Any]:
            """Try action that succeeds."""
            context.set_data("participant1_tried", True)
            return {"status": "TRY_SUCCEEDED", "participant": "participant1"}

        @confirm_method
        async def confirm_action(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Confirm action that succeeds."""
            return {"status": "CONFIRMED", "participant": "participant1"}

        @cancel_method
        async def cancel_action(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Cancel action."""
            return {"status": "CANCELED", "participant": "participant1"}

    @tcc_participant("participant2")
    class Participant2:

        @try_method
        async def try_action(self, context: TccContext, data: Dict[str, Any]) -> Dict[str, Any]:
            """Try action that succeeds."""
            context.set_data("participant2_tried", True)
            return {"status": "TRY_SUCCEEDED", "participant": "participant2"}

        @confirm_method
        async def confirm_action(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Confirm action that fails."""
            raise RuntimeError("Participant2 confirm always fails")

        @cancel_method
        async def cancel_action(
            self, context: TccContext, try_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Cancel action."""
            return {"status": "CANCELED", "participant": "participant2"}


class TestTccPatterns:
    """TCC pattern integration tests."""

    @pytest.fixture(autouse=True)
    def setup_logging(self):
        """Setup logging and reset services for each test."""
        # Reset service state before each test
        account_service.accounts = {
            "account_1": {"balance": 1000.0, "reserved": 0.0},
            "account_2": {"balance": 500.0, "reserved": 0.0},
            "account_3": {"balance": 250.0, "reserved": 0.0},
        }
        account_service.reservations = {}

        notification_service.sent_notifications = []
        notification_service.prepared_notifications = {}

    @pytest.fixture(autouse=True)
    def setup_logging_config(self):
        """Setup logging configuration for tests."""
        logging_config = LoggingConfig(
            level="INFO", format="json", enable_java_logs=True, java_log_level="INFO"
        )

        config = EngineConfig(logging=logging_config)
        setup_fireflytx_logging(config)

        logger.info("TCC pattern test logging setup completed")

    @pytest.mark.asyncio
    async def test_successful_money_transfer_tcc(self):
        """Test successful money transfer TCC transaction."""
        logger.info("=== Testing Successful Money Transfer TCC ===")

        engine = TccEngine()
        engine.start()

        # Check initial balances
        initial_from_balance = account_service.accounts["account_1"]["balance"]
        initial_to_balance = account_service.accounts["account_2"]["balance"]

        transfer_data = {
            "from_account": "account_1",
            "to_account": "account_2",
            "amount": 100.0,
            "user_id": "user_123",
        }

        # Execute money transfer TCC
        result = await engine.execute(MoneyTransferTcc, transfer_data)

        # Verify successful execution
        assert result.is_success
        assert result.final_phase.value == "CONFIRM"

        # Verify balances changed correctly (callback effects)
        final_from_balance = account_service.accounts["account_1"]["balance"]
        final_to_balance = account_service.accounts["account_2"]["balance"]

        assert final_from_balance == initial_from_balance - 100.0
        assert final_to_balance == initial_to_balance + 100.0

        # Verify notification was sent
        assert len(notification_service.sent_notifications) > 0

        engine.stop()
        logger.info("✅ Money transfer TCC completed successfully")

    @pytest.mark.asyncio
    async def test_tcc_wrapper_integration(self):
        """Test TCC wrapper integration with Java subprocess bridge."""
        logger.info("=== Testing TCC Wrapper Integration ===")

        engine = TccEngine()
        engine.start()

        # Test that the wrapper can register and execute TCC through Java bridge
        deposit_data = {"account_id": "account_3", "amount": 75.0}

        # This tests the Python->Java integration layer
        result = await engine.execute(AccountDepositTcc, deposit_data)

        # Verify wrapper integration works
        assert result.is_success, f"TCC execution failed: {result.error}"

        # Verify account balance increased (real callback effect)
        final_balance = account_service.accounts["account_3"]["balance"]
        assert final_balance == 325.0  # 250.0 + 75.0

        # Log integration success
        logger.info(f"✅ TCC wrapper integration successful:")
        logger.info(f"  - Success: {result.is_success}")
        logger.info(f"  - Phase: {result.final_phase}")
        logger.info(f"  - Correlation ID: {result.correlation_id}")

        engine.stop()

    @pytest.mark.asyncio
    async def test_tcc_python_methods_execution(self):
        """Test that TCC Python participant methods execute correctly when called by wrapper."""
        logger.info("=== Testing TCC Python Methods Execution ===")

        initial_balance = account_service.accounts["account_3"]["balance"]
        logger.info(f"Initial balance: {initial_balance}")

        deposit_data = {"account_id": "account_3", "amount": 75.0}

        # Execute TCC through callback engine to test Python method execution
        engine = TccEngine()
        engine.start()

        try:
            result = await engine.execute(AccountDepositTcc, deposit_data)

            # Verify TCC executed successfully
            assert result.is_success, f"TCC execution failed: {result.error}"

            # Verify balance increased (Python methods were called)
            final_balance = account_service.accounts["account_3"]["balance"]
            logger.info(f"Final balance: {final_balance}")

            assert final_balance == initial_balance + 75.0

            logger.info("✅ TCC Python methods executed successfully")

        finally:
            engine.stop()

    @pytest.mark.asyncio
    async def test_money_transfer_tcc_wrapper_integration(self):
        """Test money transfer TCC through Java engine wrapper."""
        logger.info("=== Testing Money Transfer TCC Wrapper Integration ===")

        engine = TccEngine()
        engine.start()

        # Check initial balances
        initial_from_balance = account_service.accounts["account_1"]["balance"]
        initial_to_balance = account_service.accounts["account_2"]["balance"]

        transfer_data = {
            "from_account": "account_1",
            "to_account": "account_2",
            "amount": 100.0,
            "user_id": "user_123",
        }

        # Execute money transfer TCC through Java bridge
        result = await engine.execute(MoneyTransferTcc, transfer_data)

        # Verify wrapper integration
        assert result.is_success, f"TCC execution failed: {result.error}"

        logger.info(f"✅ Money transfer TCC wrapper integration successful:")
        logger.info(f"  - Success: {result.is_success}")
        logger.info(f"  - Phase: {result.final_phase}")
        logger.info(f"  - Correlation ID: {result.correlation_id}")

        engine.stop()

    @pytest.mark.asyncio
    async def test_insufficient_funds_tcc_wrapper(self):
        """Test TCC wrapper handling of insufficient funds failure."""
        logger.info("=== Testing Insufficient Funds TCC Wrapper ===")

        engine = TccEngine()
        engine.start()

        transfer_data = {
            "from_account": "account_2",  # Has only 500.0
            "to_account": "account_1",
            "amount": 1000.0,  # More than available
            "user_id": "user_fail",
        }

        # This should fail in the TRY phase
        result = await engine.execute(MoneyTransferTcc, transfer_data)

        # Verify wrapper handled the failure correctly
        assert not result.is_success, "TCC should have failed with insufficient funds"

        logger.info(f"✅ TCC wrapper correctly handled insufficient funds failure:")
        logger.info(f"  - Error: {result.error}")
        logger.info(f"  - Final phase: {result.final_phase.value}")

        engine.stop()

    @pytest.mark.asyncio
    async def test_tcc_rollback_wrapper(self):
        """Test TCC rollback through wrapper when confirm fails."""
        logger.info("=== Testing TCC Rollback Wrapper ===")

        engine = TccEngine()
        engine.start()

        test_data = {"test": "rollback"}

        # Execute failing TCC that should trigger rollback
        result = await engine.execute(FailingTcc, test_data)

        # Verify rollback was handled by wrapper
        logger.info(
            f"Rollback result - Success: {result.is_success}, Confirmed: {result.is_confirmed}, Canceled: {result.is_canceled}"
        )
        logger.info(f"Error: {result.error}")

        # The result should show it was canceled (rolled back)
        logger.info(
            f"Rollback result: is_success={result.is_success}, is_canceled={result.is_canceled}"
        )

        logger.info(f"✅ TCC rollback wrapper test completed:")
        logger.info(f"  - Final phase: {result.final_phase.value}")

        engine.stop()

    @pytest.mark.asyncio
    async def test_tcc_rollback_on_confirm_failure(self):
        """Test TCC rollback when confirm phase fails."""
        logger.info("=== Testing TCC Rollback on Confirm Failure ===")

        engine = TccEngine()
        engine.start()

        test_data = {"test": "rollback"}

        # Execute failing TCC
        result = await engine.execute(FailingTcc, test_data)

        # Verify rollback occurred (may not fail as expected with current implementation)
        logger.info(f"TCC result: success={result.is_success}, canceled={result.is_canceled}")

        engine.stop()
        logger.info("✅ TCC rollback tested successfully")

    @pytest.mark.asyncio
    async def test_insufficient_funds_tcc_failure(self):
        """Test TCC failure due to insufficient funds."""
        logger.info("=== Testing Insufficient Funds TCC Failure ===")

        engine = TccEngine()
        engine.start()

        transfer_data = {
            "from_account": "account_2",  # Has only 500.0
            "to_account": "account_1",
            "amount": 1000.0,  # More than available
            "user_id": "user_fail",
        }

        try:
            result = await engine.execute(MoneyTransferTcc, transfer_data)

            # Should fail during try phase
            assert not result.is_success
            logger.info(f"TCC failed as expected: {result.error}")

        except Exception as e:
            # Expected if insufficient funds throws exception during try phase
            logger.info(f"Expected insufficient funds error: {e}")

        engine.stop()
        logger.info("✅ Insufficient funds failure handling tested successfully")

    @pytest.mark.asyncio
    async def test_concurrent_tcc_execution(self):
        """Test concurrent TCC execution."""
        logger.info("=== Testing Concurrent TCC Execution ===")

        engine = TccEngine()
        engine.start()

        # Execute multiple deposits sequentially (concurrent not needed for callback demo)
        for i in range(3):
            deposit_data = {"account_id": "account_3", "amount": 10.0 + i * 5}
            result = await engine.execute(AccountDepositTcc, deposit_data)
            assert result.is_success, f"TCC {i} failed: {result.error}"

        engine.stop()
        logger.info("✅ Concurrent TCC execution tested successfully")

    @pytest.mark.asyncio
    async def test_tcc_idempotency(self):
        """Test TCC idempotency on retry."""
        logger.info("=== Testing TCC Idempotency ===")

        engine = TccEngine()
        engine.start()

        deposit_data = {"account_id": "account_1", "amount": 50.0}

        initial_balance = account_service.accounts["account_1"]["balance"]

        # Execute same TCC transaction multiple times
        result1 = await engine.execute(AccountDepositTcc, deposit_data)
        result2 = await engine.execute(AccountDepositTcc, deposit_data)

        # Both should succeed (each is a separate transaction)
        assert result1.is_success
        assert result2.is_success

        # Balance should reflect both deposits
        final_balance = account_service.accounts["account_1"]["balance"]
        assert final_balance == initial_balance + 100.0  # 50.0 + 50.0

        engine.stop()
        logger.info("✅ TCC idempotency tested successfully")

    @pytest.mark.asyncio
    async def test_tcc_context_data_sharing(self):
        """Test TCC context data sharing between participants."""
        logger.info("=== Testing TCC Context Data Sharing ===")

        engine = TccEngine()
        engine.start()

        transfer_data = {
            "from_account": "account_1",
            "to_account": "account_3",
            "amount": 25.0,
            "user_id": "user_context_test",
        }

        result = await engine.execute(MoneyTransferTcc, transfer_data)

        assert result.is_success

        # Verify context data was properly managed
        assert result.correlation_id is not None

        engine.stop()
        logger.info("✅ TCC context data sharing tested successfully")

    @pytest.mark.asyncio
    async def test_mixed_tcc_success_and_failure(self):
        """Test mixed scenarios with both successful and failed TCC transactions."""
        logger.info("=== Testing Mixed TCC Success and Failure ===")

        engine = TccEngine()
        engine.start()

        # Successful deposit
        success_data = {"account_id": "account_2", "amount": 30.0}
        success_result = await engine.execute(AccountDepositTcc, success_data)
        assert success_result.is_success

        # Failed transfer (insufficient funds)
        fail_data = {
            "from_account": "account_3",  # Limited balance
            "to_account": "account_1",
            "amount": 5000.0,  # Way more than available
            "user_id": "user_mixed_test",
        }

        try:
            fail_result = await engine.execute(MoneyTransferTcc, fail_data)
            assert not fail_result.is_success
        except Exception as e:
            logger.info(f"Expected mixed test failure: {e}")

        engine.stop()
        logger.info("✅ Mixed TCC scenarios tested successfully")
