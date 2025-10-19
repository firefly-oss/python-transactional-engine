#!/usr/bin/env python3
"""
Context Variables Integration Tests

This test suite validates that context variables are properly passed between
SAGA steps through the Python-Java bridge.

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0 (the "License");
"""

import pytest
import pytest_asyncio
import asyncio
import logging
from typing import Dict, Any

from fireflytx import SagaEngine, SagaContext
from fireflytx.decorators import saga, saga_step
from fireflytx.logging import get_fireflytx_logger

logger = get_fireflytx_logger(__name__)


@saga("context-variables-test")
class ContextVariablesSaga:
    """Test SAGA that explicitly uses context variables to pass data between steps."""
    
    def __init__(self):
        self.logger = get_fireflytx_logger(__name__)
    
    @saga_step("step1")
    async def step_one(self, data: dict, context: SagaContext):
        """First step - sets context variables explicitly."""
        self.logger.info("=== STEP 1: Setting context variables ===")
        
        # Explicitly set context variables
        context.set_variable("user_id", "USER-123")
        context.set_variable("session_id", "SESSION-456")
        context.set_variable("step1_result", "completed")
        
        self.logger.info(f"Set context variables: {list(context.variables.keys())}")
        
        # Also return a dict (should auto-create variables as step1_status, step1_timestamp)
        return {
            "status": "success",
            "timestamp": "2024-01-15T10:00:00Z"
        }
    
    @saga_step("step2", depends_on=["step1"])
    async def step_two(self, data: dict, context: SagaContext):
        """Second step - reads context variables from step 1."""
        self.logger.info("=== STEP 2: Reading context variables ===")
        
        # Read variables set by step 1
        user_id = context.get_variable("user_id")
        session_id = context.get_variable("session_id")
        step1_result = context.get_variable("step1_result")
        
        self.logger.info(f"Read from context: user_id={user_id}, session_id={session_id}")
        self.logger.info(f"Read from context: step1_result={step1_result}")
        
        # Verify values
        assert user_id == "USER-123", f"Expected user_id=USER-123, got {user_id}"
        assert session_id == "SESSION-456", f"Expected session_id=SESSION-456, got {session_id}"
        assert step1_result == "completed", f"Expected step1_result=completed, got {step1_result}"
        
        # Check auto-created variables from step1's return value
        step1_status = context.get_variable("step1_status")
        step1_timestamp = context.get_variable("step1_timestamp")
        
        self.logger.info(f"Read auto-created: step1_status={step1_status}, step1_timestamp={step1_timestamp}")
        
        # Set new variables for step 3
        context.set_variable("step2_processed", True)
        context.set_variable("total_steps", 3)
        
        return {
            "step2_status": "completed",
            "user_verified": True
        }
    
    @saga_step("step3", depends_on=["step2"])
    async def step_three(self, data: dict, context: SagaContext):
        """Third step - reads all context variables."""
        self.logger.info("=== STEP 3: Reading all context variables ===")
        
        # Read all variables
        all_vars = context.variables
        self.logger.info(f"All context variables ({len(all_vars)}): {list(all_vars.keys())}")
        
        # Verify we have variables from previous steps
        assert context.get_variable("user_id") == "USER-123", "user_id not found or incorrect!"
        assert context.get_variable("session_id") == "SESSION-456", "session_id not found or incorrect!"
        assert context.get_variable("step1_result") == "completed", "step1_result not found or incorrect!"
        assert context.get_variable("step2_processed") == True, "step2_processed not found or incorrect!"
        assert context.get_variable("total_steps") == 3, "total_steps not found or incorrect!"
        
        self.logger.info("✅ All context variables verified successfully!")
        
        return {
            "final_status": "all_steps_completed",
            "total_variables": len(all_vars)
        }


@saga("simple-context-test")
class SimpleContextSaga:
    """Simpler SAGA for basic context variable testing."""
    
    @saga_step("create")
    async def create_resource(self, data: dict, context: SagaContext):
        """Create a resource and store its ID in context."""
        resource_id = f"RES-{data.get('name', 'default')}"
        context.set_variable("resource_id", resource_id)
        logger.info(f"Created resource: {resource_id}")
        return {"id": resource_id, "status": "created"}
    
    @saga_step("process", depends_on=["create"])
    async def process_resource(self, data: dict, context: SagaContext):
        """Process the resource using ID from context."""
        resource_id = context.get_variable("resource_id")
        assert resource_id is not None, "resource_id not found in context!"
        logger.info(f"Processing resource: {resource_id}")
        context.set_variable("processed", True)
        return {"id": resource_id, "status": "processed"}
    
    @saga_step("finalize", depends_on=["process"])
    async def finalize_resource(self, data: dict, context: SagaContext):
        """Finalize the resource."""
        resource_id = context.get_variable("resource_id")
        processed = context.get_variable("processed")
        assert resource_id is not None, "resource_id not found in context!"
        assert processed == True, "processed flag not found in context!"
        logger.info(f"Finalizing resource: {resource_id}")
        return {"id": resource_id, "status": "finalized"}


@pytest_asyncio.fixture
async def saga_engine():
    """Fixture to create and initialize a SAGA engine."""
    engine = SagaEngine()
    await engine.initialize()
    yield engine
    await engine.shutdown()


@pytest.mark.asyncio
async def test_context_variables_flow(saga_engine):
    """Test that context variables are properly passed between SAGA steps."""
    logger.info("\n" + "=" * 70)
    logger.info("🧪 Testing Context Variable Flow Between SAGA Steps")
    logger.info("=" * 70)
    
    # Execute SAGA
    result = await saga_engine.execute(
        ContextVariablesSaga,
        {"test_input": "context_test"}
    )
    
    # Verify success
    assert result.is_success, f"SAGA failed: {result.error if hasattr(result, 'error') else 'Unknown error'}"
    
    logger.info("✅ Context variable flow test PASSED!")


@pytest.mark.asyncio
async def test_simple_context_variables(saga_engine):
    """Test simple context variable passing between steps."""
    logger.info("\n" + "=" * 70)
    logger.info("🧪 Testing Simple Context Variables")
    logger.info("=" * 70)
    
    # Execute SAGA
    result = await saga_engine.execute(
        SimpleContextSaga,
        {"name": "test-resource"}
    )
    
    # Verify success
    assert result.is_success, f"SAGA failed: {result.error if hasattr(result, 'error') else 'Unknown error'}"
    
    logger.info("✅ Simple context variable test PASSED!")


@pytest.mark.asyncio
async def test_context_variables_with_dict_return():
    """Test that dict return values automatically create context variables."""
    
    @saga("dict-return-test")
    class DictReturnSaga:
        @saga_step("step1")
        async def first_step(self, data: dict):
            # Return dict without using context parameter
            return {"order_id": "ORD-123", "amount": 99.99}
        
        @saga_step("step2", depends_on=["step1"])
        async def second_step(self, data: dict, context: SagaContext):
            # Should be able to access auto-created variables
            order_id = context.get_variable("step1_order_id")
            amount = context.get_variable("step1_amount")
            
            assert order_id == "ORD-123", f"Expected order_id=ORD-123, got {order_id}"
            assert amount == 99.99, f"Expected amount=99.99, got {amount}"
            
            return {"status": "verified"}
    
    engine = SagaEngine()
    await engine.initialize()
    
    try:
        result = await engine.execute(DictReturnSaga, {})
        assert result.is_success, f"SAGA failed: {result.error if hasattr(result, 'error') else 'Unknown error'}"
        logger.info("✅ Dict return value test PASSED!")
    finally:
        await engine.shutdown()


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))

