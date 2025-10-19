"""TccResult - Results of TCC execution."""

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
from typing import Any, Dict, Optional

from .tcc_context import TccParticipantStatus, TccPhase


@dataclass
class TccParticipantResult:
    """Result of a TCC participant execution."""

    participant_id: str
    try_result: Optional[Any] = None
    status: TccParticipantStatus = TccParticipantStatus.INITIALIZED
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class TccResult:
    """Results of TCC execution."""

    tcc_name: str
    correlation_id: str
    is_success: bool
    is_confirmed: bool
    is_canceled: bool
    final_phase: TccPhase
    duration_ms: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    try_results: Dict[str, Any] = None
    participant_results: Dict[str, TccParticipantResult] = None
    error: Optional[str] = None

    def get_try_result(self, participant_id: str) -> Any:
        """Get try result for a specific participant."""
        if self.try_results:
            return self.try_results.get(participant_id)
        return None

    def get_participant_result(self, participant_id: str) -> Optional[TccParticipantResult]:
        """Get participant result."""
        if self.participant_results:
            return self.participant_results.get(participant_id)
        return None

    def get_all_try_results(self) -> Dict[str, Any]:
        """Get all try results."""
        return self.try_results.copy() if self.try_results else {}

    def get_participant_results(self) -> Dict[str, TccParticipantResult]:
        """Get all participant results."""
        return self.participant_results.copy() if self.participant_results else {}

    def get_error(self) -> Optional[str]:
        """Get error message."""
        return self.error

    def get_error_message(self) -> Optional[str]:
        """Get error message (alias for get_error)."""
        return self.error

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TccResult":
        """Create from dictionary."""
        # Parse participant results
        participant_results = {}
        participant_data = data.get("participant_results", {})
        for pid, presult in participant_data.items():
            if isinstance(presult, dict):
                participant_results[pid] = TccParticipantResult(
                    participant_id=pid,
                    try_result=presult.get("try_result"),
                    status=TccParticipantStatus(presult.get("status", "INITIALIZED")),
                    error=presult.get("error"),
                    duration_ms=presult.get("duration_ms", 0),
                )
            else:
                participant_results[pid] = presult

        result = cls(
            tcc_name=data.get("tcc_name", ""),
            correlation_id=data.get("correlation_id", ""),
            is_success=data.get("is_success", False),
            is_confirmed=data.get("is_confirmed", False),
            is_canceled=data.get("is_canceled", False),
            final_phase=TccPhase(data.get("final_phase", "TRY")),
            duration_ms=data.get("duration_ms", 0),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            try_results=data.get("try_results", {}),
            participant_results=participant_results,
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
            "tcc_name": self.tcc_name,
            "correlation_id": self.correlation_id,
            "is_success": self.is_success,
            "is_confirmed": self.is_confirmed,
            "is_canceled": self.is_canceled,
            "final_phase": (
                self.final_phase.value
                if hasattr(self.final_phase, "value")
                else str(self.final_phase)
            ),
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "try_results": self.try_results or {},
            "participant_results": {
                k: v.__dict__ if hasattr(v, "__dict__") else v
                for k, v in (self.participant_results or {}).items()
            },
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
