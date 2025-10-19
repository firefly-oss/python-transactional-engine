#!/usr/bin/env python3
"""
Unit tests for utility classes and JVM management.
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

import pytest
import asyncio
from pathlib import Path
import tempfile
import logging

from fireflytx.integration.bridge import JavaSubprocessBridge
from fireflytx.config.engine_config import JvmConfig


class TestJavaSubprocessBridge:
    """Test Java subprocess bridge functionality."""

    def test_bridge_creation(self):
        """Test that JavaSubprocessBridge can be created."""
        bridge = JavaSubprocessBridge()

        assert bridge is not None
        assert hasattr(bridge, "start_jvm")
        assert hasattr(bridge, "shutdown")


# Integration tests removed - were using outdated JVMManager


class TestUtilityFunctions:
    """Test utility helper functions."""

    def test_correlation_id_generation(self):
        """Test correlation ID generation."""
        from fireflytx.utils.helpers import generate_correlation_id

        # Generate multiple IDs
        ids = [generate_correlation_id() for _ in range(10)]

        # All should be unique
        assert len(set(ids)) == 10

        # All should be strings
        assert all(isinstance(id, str) for id in ids)

        # All should have reasonable length
        assert all(len(id) > 10 for id in ids)

    def test_retry_decorator(self):
        """Test retry decorator functionality."""
        from fireflytx.utils.helpers import retry

        # Counter to track attempts
        attempt_count = 0

        @retry(max_attempts=3, initial_delay=0.01, max_delay=0.1)
        def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = failing_function()

        assert result == "success"
        assert attempt_count == 3

    def test_retry_decorator_max_attempts_exceeded(self):
        """Test retry decorator when max attempts is exceeded."""
        from fireflytx.utils.helpers import retry

        attempt_count = 0

        @retry(max_attempts=2, initial_delay=0.01, max_delay=0.1)
        def always_failing_function():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_failing_function()

        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_decorator(self):
        """Test async retry decorator functionality."""
        from fireflytx.utils.helpers import async_retry

        attempt_count = 0

        @async_retry(max_attempts=3, initial_delay=0.01, max_delay=0.1)
        async def failing_async_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "async_success"

        result = await failing_async_function()

        assert result == "async_success"
        assert attempt_count == 3

    def test_timeout_decorator(self):
        """Test timeout decorator functionality."""
        from fireflytx.utils.helpers import timeout
        import time

        @timeout(0.1)
        def quick_function():
            time.sleep(0.05)
            return "quick"

        @timeout(0.1)
        def slow_function():
            time.sleep(0.2)
            return "slow"

        # Quick function should succeed
        result = quick_function()
        assert result == "quick"

        # Slow function should timeout
        with pytest.raises(TimeoutError):
            slow_function()

    @pytest.mark.asyncio
    async def test_async_timeout_decorator(self):
        """Test async timeout decorator functionality."""
        from fireflytx.utils.helpers import async_timeout

        @async_timeout(0.1)
        async def quick_async_function():
            await asyncio.sleep(0.05)
            return "async_quick"

        @async_timeout(0.1)
        async def slow_async_function():
            await asyncio.sleep(0.2)
            return "async_slow"

        # Quick function should succeed
        result = await quick_async_function()
        assert result == "async_quick"

        # Slow function should timeout
        with pytest.raises(asyncio.TimeoutError):
            await slow_async_function()

    def test_safe_json_serialization(self):
        """Test safe JSON serialization utility."""
        from fireflytx.utils.helpers import safe_json_dumps, safe_json_loads
        from datetime import datetime
        from decimal import Decimal

        # Test with complex data structures
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "decimal": Decimal("99.99"),
            "datetime": datetime(2024, 1, 15, 10, 30, 0),
            "nested": {"list": [1, 2, 3], "dict": {"key": "value"}},
        }

        # Serialize
        json_str = safe_json_dumps(data)
        assert isinstance(json_str, str)

        # Deserialize
        restored_data = safe_json_loads(json_str)

        # Basic values should be preserved
        assert restored_data["string"] == "hello"
        assert restored_data["number"] == 42
        assert restored_data["float"] == 3.14
        assert restored_data["nested"]["list"] == [1, 2, 3]
        assert restored_data["nested"]["dict"] == {"key": "value"}

    def test_safe_json_with_invalid_data(self):
        """Test safe JSON serialization with non-serializable data."""
        from fireflytx.utils.helpers import safe_json_dumps

        class NonSerializable:
            pass

        data = {"valid": "data", "invalid": NonSerializable()}

        # Should not raise exception
        json_str = safe_json_dumps(data)
        assert isinstance(json_str, str)

        # Should contain the valid data
        assert "valid" in json_str
        assert "data" in json_str


# Note: Logging utilities tests removed - these were referencing old module structure


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
