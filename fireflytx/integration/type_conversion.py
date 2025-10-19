"""
Type conversion utilities for Python-Java interoperability.

This module provides utilities for converting between Python and Java types,
handling the complex task of bridging the two type systems.
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

import json
import logging
from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta
from typing import Any, Optional, Type

from pydantic import BaseModel

# Removed JVM manager dependency - using subprocess bridge only

logger = logging.getLogger(__name__)


class TypeConverter:
    """
    Simplified type converter for subprocess bridge communication.

    This class provides basic type conversion utilities for preparing
    Python objects for JSON serialization to communicate with the real
    lib-transactional-engine via subprocess bridge.
    """

    def __init__(self):
        # Simplified for subprocess bridge - no JVM manager needed
        pass

    def python_to_java_serializable(self, value: Any) -> Any:
        """
        Convert a Python object to a JSON-serializable format for subprocess bridge.

        Args:
            value: Python object to convert

        Returns:
            JSON-serializable equivalent for subprocess communication
        """
        if value is None:
            return None

        # Handle primitive types (already JSON serializable)
        if isinstance(value, (bool, int, float, str)):
            return value

        # Handle datetime objects -> ISO string
        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, timedelta):
            return value.total_seconds()

        # Handle collections
        if isinstance(value, dict):
            return {k: self.python_to_java_serializable(v) for k, v in value.items()}

        if isinstance(value, (list, tuple)):
            return [self.python_to_java_serializable(item) for item in value]

        # Handle Pydantic models
        if isinstance(value, BaseModel):
            return value.model_dump()

        # Handle dataclasses
        if is_dataclass(value):
            if hasattr(value, "to_dict"):
                return value.to_dict()
            else:
                return {field.name: getattr(value, field.name) for field in fields(value)}

        # Handle custom objects by converting to string
        try:
            # Try to serialize to JSON first
            return json.loads(json.dumps(value, default=str))
        except (TypeError, ValueError):
            logger.debug(f"Converting object of type {type(value)} to string")
            return str(value)

    def parse_java_response(self, response_data: Any, target_type: Optional[Type] = None) -> Any:
        """
        Parse response data from subprocess bridge (already Python objects).

        Since subprocess bridge returns Python objects (via JSON), this is minimal.

        Args:
            response_data: Data from subprocess bridge response
            target_type: Optional target Python type

        Returns:
            Python object (usually already correct type)
        """
        # Subprocess bridge already returns Python objects
        return response_data

    # Minimal methods for subprocess bridge - no complex JVM conversions needed
    pass


# Global type converter instance
_type_converter = TypeConverter()


def get_type_converter() -> TypeConverter:
    """Get the global type converter instance."""
    return _type_converter
