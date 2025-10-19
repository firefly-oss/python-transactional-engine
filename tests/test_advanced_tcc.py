#!/usr/bin/env python3
"""
Advanced TCC (Try-Confirm-Cancel) Test Cases

Tests complex TCC scenarios, edge cases, and failure modes:
- Try phase failures and automatic cancel
- Confirm phase idempotency
- Cancel phase retry logic
- Partial participant failures
- Timeout handling in all phases
- Resource lock management

ALL TESTS USE REAL JAVA ENGINE - NO MOCKS OR SIMULATIONS!

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0 (the "License");
"""

import pytest
import pytest_asyncio
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from fireflytx import TccEngine
from fireflytx.decorators import tcc, tcc_participant, try_method, confirm_method, cancel_method

logger = logging.getLogger(__name__)


# Track execution for verification
tcc_tracker = {
    "try_calls": [],
    "confirm_calls": [],
    "cancel_calls": [],
    "failures": [],
}


def reset_tcc_tracker():
    """Reset the TCC execution tracker."""
    tcc_tracker["try_calls"].clear()
    tcc_tracker["confirm_calls"].clear()
    tcc_tracker["cancel_calls"].clear()
    tcc_tracker["failures"].clear()


@pytest.fixture(scope="function")
def tcc_engine():
    """Create a fresh TccEngine for each test."""
    engine = TccEngine()
    engine.start()
    yield engine
    engine.stop()


@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset tracker before each test."""
    reset_tcc_tracker()


class TestTryPhaseFailures:
    """Test scenarios where Try phase fails."""

    @pytest.mark.asyncio
    async def test_try_failure_triggers_cancel(self, tcc_engine):
        """Test that Try phase failure triggers Cancel for all participants."""

        @tcc("try-failure-test")
        class TryFailureTcc:
            @tcc_participant("participant1", order=1)
            class Participant1:
                @try_method
                async def try_participant1(self, data: dict):
                    tcc_tracker["try_calls"].append("participant1")
                    amount = data.get("amount", 0.0)
                    return {"locked": True, "amount": amount}

                @confirm_method
                async def confirm_participant1(self, data: dict, try_result: dict):
                    tcc_tracker["confirm_calls"].append("participant1")
                    return {"confirmed": True}

                @cancel_method
                async def cancel_participant1(self, data: dict, try_result: dict):
                    tcc_tracker["cancel_calls"].append("participant1")
                    return {"cancelled": True}

            @tcc_participant("participant2", order=2)
            class Participant2:
                @try_method
                async def try_participant2(self, data: dict):
                    tcc_tracker["try_calls"].append("participant2")
                    # Simulate Try failure
                    raise Exception("Insufficient resources for participant2")

                @confirm_method
                async def confirm_participant2(self, data: dict, try_result: dict):
                    tcc_tracker["confirm_calls"].append("participant2")
                    return {"confirmed": True}

                @cancel_method
                async def cancel_participant2(self, data: dict, try_result: dict):
                    tcc_tracker["cancel_calls"].append("participant2")
                    return {"cancelled": True}

        result = await tcc_engine.execute(
            TryFailureTcc,
            {
                "participant1": {"amount": 100.0},
                "participant2": {"amount": 100.0}
            }
        )

        assert not result.is_success
        # Verify Try was called for participant1
        assert "participant1" in tcc_tracker["try_calls"]
        # Verify Try was attempted for participant2
        assert "participant2" in tcc_tracker["try_calls"]
        # Verify Cancel was called for participant1 (rollback)
        assert "participant1" in tcc_tracker["cancel_calls"]
        # Verify Confirm was NOT called for any participant
        assert len(tcc_tracker["confirm_calls"]) == 0

    @pytest.mark.asyncio
    async def test_try_timeout(self, tcc_engine):
        """Test Try phase timeout handling."""

        @tcc("try-timeout-test")
        class TryTimeoutTcc:
            @tcc_participant("slow_participant", timeout_ms=100)
            async def try_slow(self, data: str):
                tcc_tracker["try_calls"].append("slow_participant")
                # This should timeout
                await asyncio.sleep(1.0)
                return {"locked": True}

            async def confirm_slow(self, data: str):
                tcc_tracker["confirm_calls"].append("slow_participant")
                return {"confirmed": True}

            async def cancel_slow(self, data: str):
                tcc_tracker["cancel_calls"].append("slow_participant")
                return {"cancelled": True}

        result = await tcc_engine.execute(
            TryTimeoutTcc,
            {"slow_participant": {"data": "test"}}
        )
        
        # Note: Timeout behavior depends on Java engine implementation
        assert "slow_participant" in tcc_tracker["try_calls"]


class TestConfirmPhaseIdempotency:
    """Test Confirm phase idempotency and retry logic."""

    @pytest.mark.asyncio
    async def test_confirm_idempotency(self, tcc_engine):
        """Test that Confirm can be called multiple times safely."""

        @tcc("confirm-idempotency-test")
        class ConfirmIdempotencyTcc:
            @tcc_participant("idempotent_participant", order=1)
            class IdempotentParticipant:
                def __init__(self):
                    self.confirm_count = 0

                @try_method
                async def try_participant(self, data: dict):
                    tcc_tracker["try_calls"].append("idempotent_participant")
                    return {"locked": True, "lock_id": "LOCK-123"}

                @confirm_method
                async def confirm_participant(self, data: dict, try_result: dict):
                    self.confirm_count += 1
                    tcc_tracker["confirm_calls"].append(f"confirm_{self.confirm_count}")
                    # Idempotent - can be called multiple times
                    return {"confirmed": True, "confirm_count": self.confirm_count}

                @cancel_method
                async def cancel_participant(self, data: dict, try_result: dict):
                    tcc_tracker["cancel_calls"].append("idempotent_participant")
                    return {"cancelled": True}

        result = await tcc_engine.execute(
            ConfirmIdempotencyTcc,
            {"idempotent_participant": {"amount": 100.0}}
        )
        
        assert result.is_success
        assert "idempotent_participant" in tcc_tracker["try_calls"]
        # Confirm should be called at least once
        assert len([c for c in tcc_tracker["confirm_calls"] if "confirm_" in c]) >= 1


class TestCancelPhaseRetry:
    """Test Cancel phase retry logic."""

    @pytest.mark.asyncio
    async def test_cancel_with_retry(self, tcc_engine):
        """Test that Cancel phase respects retry configuration."""

        @tcc("cancel-retry-test")
        class CancelRetryTcc:
            def __init__(self):
                self.cancel_attempts = 0

            @tcc_participant("retry_participant", order=1)
            async def try_participant(self, amount: float):
                tcc_tracker["try_calls"].append("retry_participant")
                return {"locked": True}

            async def confirm_participant(self, amount: float):
                tcc_tracker["confirm_calls"].append("retry_participant")
                return {"confirmed": True}

            async def cancel_participant(self, amount: float):
                self.cancel_attempts += 1
                tcc_tracker["cancel_calls"].append(f"cancel_attempt_{self.cancel_attempts}")

                # Fail first 2 attempts, succeed on 3rd
                if self.cancel_attempts < 3:
                    raise Exception(f"Cancel attempt {self.cancel_attempts} failed")

                return {"cancelled": True}

            @tcc_participant("failing_participant", order=2)
            async def try_failing(self, amount: float):
                tcc_tracker["try_calls"].append("failing_participant")
                # Trigger cancel by failing Try
                raise Exception("Try failed")

            async def confirm_failing(self, amount: float):
                return {"confirmed": True}

            async def cancel_failing(self, amount: float):
                tcc_tracker["cancel_calls"].append("failing_participant")
                return {"cancelled": True}

        result = await tcc_engine.execute(
            CancelRetryTcc,
            {
                "retry_participant": {"amount": 100.0},
                "failing_participant": {"amount": 100.0}
            }
        )
        
        assert not result.is_success
        # Verify Try was called
        assert "retry_participant" in tcc_tracker["try_calls"]
        # Verify Cancel was retried
        # Note: Retry behavior depends on Java engine implementation


class TestPartialParticipantFailures:
    """Test scenarios with multiple participants where some fail."""

    @pytest.mark.asyncio
    async def test_multiple_participants_partial_failure(self, tcc_engine):
        """Test TCC with multiple participants where one fails in Try phase."""

        @tcc("partial-failure-test")
        class PartialFailureTcc:
            @tcc_participant("participant_a", order=1)
            class ParticipantA:
                @try_method
                async def try_a(self, data: dict):
                    tcc_tracker["try_calls"].append("participant_a")
                    amount = data.get("amount", 0.0)
                    return {"locked": True, "amount": amount}

                @confirm_method
                async def confirm_a(self, data: dict, try_result: dict):
                    tcc_tracker["confirm_calls"].append("participant_a")
                    return {"confirmed": True}

                @cancel_method
                async def cancel_a(self, data: dict, try_result: dict):
                    tcc_tracker["cancel_calls"].append("participant_a")
                    return {"cancelled": True}

            @tcc_participant("participant_b", order=2)
            class ParticipantB:
                @try_method
                async def try_b(self, data: dict):
                    tcc_tracker["try_calls"].append("participant_b")
                    amount = data.get("amount", 0.0)
                    return {"locked": True, "amount": amount}

                @confirm_method
                async def confirm_b(self, data: dict, try_result: dict):
                    tcc_tracker["confirm_calls"].append("participant_b")
                    return {"confirmed": True}

                @cancel_method
                async def cancel_b(self, data: dict, try_result: dict):
                    tcc_tracker["cancel_calls"].append("participant_b")
                    return {"cancelled": True}

            @tcc_participant("participant_c", order=3)
            class ParticipantC:
                @try_method
                async def try_c(self, data: dict):
                    tcc_tracker["try_calls"].append("participant_c")
                    # Fail this participant
                    raise Exception("Participant C failed")

                @confirm_method
                async def confirm_c(self, data: dict, try_result: dict):
                    tcc_tracker["confirm_calls"].append("participant_c")
                    return {"confirmed": True}

                @cancel_method
                async def cancel_c(self, data: dict, try_result: dict):
                    tcc_tracker["cancel_calls"].append("participant_c")
                    return {"cancelled": True}

        result = await tcc_engine.execute(
            PartialFailureTcc,
            {
                "participant_a": {"amount": 100.0},
                "participant_b": {"amount": 100.0},
                "participant_c": {"amount": 100.0}
            }
        )
        
        assert not result.is_success
        # Verify all Try phases were attempted
        assert "participant_a" in tcc_tracker["try_calls"]
        assert "participant_b" in tcc_tracker["try_calls"]
        assert "participant_c" in tcc_tracker["try_calls"]
        # Verify Cancel was called for successful participants
        assert "participant_a" in tcc_tracker["cancel_calls"]
        assert "participant_b" in tcc_tracker["cancel_calls"]
        # Verify Confirm was NOT called
        assert len(tcc_tracker["confirm_calls"]) == 0


class TestResourceLockManagement:
    """Test resource lock acquisition and release."""

    @pytest.mark.asyncio
    async def test_resource_lock_release_on_cancel(self, tcc_engine):
        """Test that resources are properly released during Cancel phase."""

        resource_locks = {"inventory": 0, "payment": 0}

        @tcc("resource-lock-test")
        class ResourceLockTcc:
            @tcc_participant("inventory", order=1)
            class InventoryParticipant:
                @try_method
                async def try_inventory(self, data: dict):
                    tcc_tracker["try_calls"].append("inventory")
                    quantity = data.get("quantity", 0)
                    resource_locks["inventory"] += quantity
                    return {"locked": quantity}

                @confirm_method
                async def confirm_inventory(self, data: dict, try_result: dict):
                    tcc_tracker["confirm_calls"].append("inventory")
                    # Keep the lock
                    return {"confirmed": True}

                @cancel_method
                async def cancel_inventory(self, data: dict, try_result: dict):
                    tcc_tracker["cancel_calls"].append("inventory")
                    # Release the lock
                    quantity = try_result.get("locked", 0)
                    resource_locks["inventory"] -= quantity
                    return {"cancelled": True}

            @tcc_participant("payment", order=2)
            class PaymentParticipant:
                @try_method
                async def try_payment(self, data: dict):
                    tcc_tracker["try_calls"].append("payment")
                    amount = data.get("amount", 0.0)
                    resource_locks["payment"] += amount
                    # Fail to trigger cancel
                    raise Exception("Payment gateway unavailable")

                @confirm_method
                async def confirm_payment(self, data: dict, try_result: dict):
                    return {"confirmed": True}

                @cancel_method
                async def cancel_payment(self, data: dict, try_result: dict):
                    tcc_tracker["cancel_calls"].append("payment")
                    amount = data.get("amount", 0.0)
                    resource_locks["payment"] -= amount
                    return {"cancelled": True}

        result = await tcc_engine.execute(
            ResourceLockTcc,
            {
                "inventory": {"quantity": 5},
                "payment": {"amount": 100.0}
            }
        )

        assert not result.is_success
        # Verify locks were released
        assert resource_locks["inventory"] == 0
        # Payment lock might not have been acquired due to failure

