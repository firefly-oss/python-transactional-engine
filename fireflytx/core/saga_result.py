"""SagaResult - Results of saga execution."""

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

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SagaResult:
    """Results of saga execution."""

    saga_name: str
    correlation_id: str
    is_success: bool
    duration_ms: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps: Dict[str, Any] = None
    failed_steps: List[str] = None
    compensated_steps: List[str] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SagaResult":
        """Create from dictionary."""
        result = cls(
            saga_name=data.get("saga_name", ""),
            correlation_id=data.get("correlation_id", ""),
            is_success=data.get("is_success", False),
            duration_ms=data.get("duration_ms", 0),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            steps=data.get("steps", {}),
            failed_steps=data.get("failed_steps", []),
            compensated_steps=data.get("compensated_steps", []),
            error=data.get("error"),
        )

        # Store additional attributes from data
        for key, value in data.items():
            if not hasattr(result, key):
                setattr(result, key, value)

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "saga_name": self.saga_name,
            "correlation_id": self.correlation_id,
            "is_success": self.is_success,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "steps": self.steps or {},
            "failed_steps": self.failed_steps or [],
            "compensated_steps": self.compensated_steps or [],
            "error": self.error,
        }

        # Include any additional attributes
        for attr_name in dir(self):
            if (
                not attr_name.startswith("_")
                and attr_name not in result
                and not callable(getattr(self, attr_name))
            ):
                result[attr_name] = getattr(self, attr_name)

        return result
