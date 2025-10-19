"""
TCC Events - Python event system for TCC observability.
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

from abc import ABC
from typing import Optional

from ..core.tcc_context import TccContext, TccPhase


class TccEvents(ABC):
    """
    Abstract base class for TCC event handling.

    Implement this class to receive TCC lifecycle events
    for monitoring, logging, and observability.
    """

    async def on_tcc_started(
        self, tcc_name: str, correlation_id: str, context: Optional[TccContext] = None
    ) -> None:
        """Called when a TCC transaction starts."""
        pass

    async def on_tcc_completed(
        self, tcc_name: str, correlation_id: str, final_phase: TccPhase, duration_ms: int
    ) -> None:
        """Called when a TCC transaction completes."""
        pass

    async def on_phase_started(self, tcc_name: str, correlation_id: str, phase: TccPhase) -> None:
        """Called when a TCC phase starts."""
        pass

    async def on_phase_completed(
        self, tcc_name: str, correlation_id: str, phase: TccPhase, duration_ms: int
    ) -> None:
        """Called when a TCC phase completes successfully."""
        pass

    async def on_phase_failed(
        self,
        tcc_name: str,
        correlation_id: str,
        phase: TccPhase,
        error: Exception,
        duration_ms: int,
    ) -> None:
        """Called when a TCC phase fails."""
        pass

    async def on_participant_started(
        self, tcc_name: str, correlation_id: str, participant_id: str, phase: TccPhase
    ) -> None:
        """Called when a participant method starts."""
        pass

    async def on_participant_success(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        attempts: int,
        duration_ms: int,
    ) -> None:
        """Called when a participant method succeeds."""
        pass

    async def on_participant_failed(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        error: Exception,
        attempts: int,
        duration_ms: int,
    ) -> None:
        """Called when a participant method fails."""
        pass

    async def on_participant_retry(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        attempts: int,
        last_error: Exception,
    ) -> None:
        """Called when a participant method is being retried."""
        pass

    async def on_participant_registered(
        self, tcc_name: str, correlation_id: str, participant_id: str
    ) -> None:
        """Called when a participant is registered."""
        pass

    async def on_participant_timeout(
        self, tcc_name: str, correlation_id: str, participant_id: str, phase: TccPhase
    ) -> None:
        """Called when a participant method times out."""
        pass

    async def on_resource_reserved(
        self, tcc_name: str, correlation_id: str, participant_id: str, resource_id: str
    ) -> None:
        """Called when a resource is reserved."""
        pass

    async def on_resource_released(
        self, tcc_name: str, correlation_id: str, participant_id: str, resource_id: str
    ) -> None:
        """Called when a resource is released."""
        pass


class LoggingTccEvents(TccEvents):
    """Default logging implementation of TccEvents."""

    def __init__(self, logger_name: str = "pytransactional.tcc"):
        import logging

        self.logger = logging.getLogger(logger_name)

    async def on_tcc_started(
        self, tcc_name: str, correlation_id: str, context: Optional[TccContext] = None
    ) -> None:
        self.logger.info(f"TCC {tcc_name} started: {correlation_id}")

    async def on_tcc_completed(
        self, tcc_name: str, correlation_id: str, final_phase: TccPhase, duration_ms: int
    ) -> None:
        self.logger.info(
            f"TCC {tcc_name} completed in phase {final_phase.value}: {correlation_id} ({duration_ms}ms)"
        )

    async def on_phase_started(self, tcc_name: str, correlation_id: str, phase: TccPhase) -> None:
        self.logger.debug(f"TCC {tcc_name} phase {phase.value} started: {correlation_id}")

    async def on_phase_completed(
        self, tcc_name: str, correlation_id: str, phase: TccPhase, duration_ms: int
    ) -> None:
        self.logger.debug(
            f"TCC {tcc_name} phase {phase.value} completed: {correlation_id} ({duration_ms}ms)"
        )

    async def on_phase_failed(
        self,
        tcc_name: str,
        correlation_id: str,
        phase: TccPhase,
        error: Exception,
        duration_ms: int,
    ) -> None:
        self.logger.error(
            f"TCC {tcc_name} phase {phase.value} failed: {correlation_id} ({duration_ms}ms) - {error}"
        )

    async def on_participant_started(
        self, tcc_name: str, correlation_id: str, participant_id: str, phase: TccPhase
    ) -> None:
        self.logger.debug(
            f"TCC {tcc_name} participant {participant_id} {phase.value} started: {correlation_id}"
        )

    async def on_participant_success(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        attempts: int,
        duration_ms: int,
    ) -> None:
        self.logger.debug(
            f"TCC {tcc_name} participant {participant_id} {phase.value} succeeded: {correlation_id} (attempt {attempts}, {duration_ms}ms)"
        )

    async def on_participant_failed(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        error: Exception,
        attempts: int,
        duration_ms: int,
    ) -> None:
        self.logger.error(
            f"TCC {tcc_name} participant {participant_id} {phase.value} failed: {correlation_id} (attempt {attempts}, {duration_ms}ms) - {error}"
        )

    async def on_participant_retry(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        attempts: int,
        last_error: Exception,
    ) -> None:
        self.logger.warning(
            f"TCC {tcc_name} participant {participant_id} {phase.value} retrying: {correlation_id} (attempt {attempts}) - {last_error}"
        )


class MetricsTccEvents(TccEvents):
    """Metrics collection implementation of TccEvents."""

    def __init__(self, metrics_client=None):
        self.metrics = metrics_client
        self._counters = {}
        self._timers = {}

    def _increment(self, metric_name: str, tags: dict = None):
        """Increment a counter metric."""
        if self.metrics and hasattr(self.metrics, "increment"):
            self.metrics.increment(metric_name, tags=tags)
        else:
            # Fallback to in-memory counters
            key = (metric_name, tuple(sorted(tags.items())) if tags else None)
            self._counters[key] = self._counters.get(key, 0) + 1

    def _timing(self, metric_name: str, duration_ms: int, tags: dict = None):
        """Record timing metric."""
        if self.metrics and hasattr(self.metrics, "timing"):
            self.metrics.timing(metric_name, duration_ms, tags=tags)
        else:
            # Fallback to in-memory timers
            key = (metric_name, tuple(sorted(tags.items())) if tags else None)
            if key not in self._timers:
                self._timers[key] = []
            self._timers[key].append(duration_ms)

    async def on_tcc_started(
        self, tcc_name: str, correlation_id: str, context: Optional[TccContext] = None
    ) -> None:
        self._increment("tcc.started", {"tcc_name": tcc_name})

    async def on_tcc_completed(
        self, tcc_name: str, correlation_id: str, final_phase: TccPhase, duration_ms: int
    ) -> None:
        tags = {"tcc_name": tcc_name, "final_phase": final_phase.value}
        self._increment("tcc.completed", tags)
        self._timing("tcc.duration", duration_ms, tags)

    async def on_phase_started(self, tcc_name: str, correlation_id: str, phase: TccPhase) -> None:
        self._increment("tcc.phase.started", {"tcc_name": tcc_name, "phase": phase.value})

    async def on_phase_completed(
        self, tcc_name: str, correlation_id: str, phase: TccPhase, duration_ms: int
    ) -> None:
        tags = {"tcc_name": tcc_name, "phase": phase.value}
        self._increment("tcc.phase.completed", tags)
        self._timing("tcc.phase.duration", duration_ms, tags)

    async def on_phase_failed(
        self,
        tcc_name: str,
        correlation_id: str,
        phase: TccPhase,
        error: Exception,
        duration_ms: int,
    ) -> None:
        tags = {"tcc_name": tcc_name, "phase": phase.value, "error_type": type(error).__name__}
        self._increment("tcc.phase.failed", tags)
        self._timing("tcc.phase.duration", duration_ms, tags)

    async def on_participant_success(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        attempts: int,
        duration_ms: int,
    ) -> None:
        tags = {"tcc_name": tcc_name, "participant": participant_id, "phase": phase.value}
        self._increment("tcc.participant.success", tags)
        self._timing("tcc.participant.duration", duration_ms, tags)
        if attempts > 1:
            self._increment("tcc.participant.retries", tags)

    async def on_participant_failed(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        error: Exception,
        attempts: int,
        duration_ms: int,
    ) -> None:
        tags = {
            "tcc_name": tcc_name,
            "participant": participant_id,
            "phase": phase.value,
            "error_type": type(error).__name__,
        }
        self._increment("tcc.participant.failed", tags)
        self._timing("tcc.participant.duration", duration_ms, tags)


class CompositeTccEvents(TccEvents):
    """Composite event handler that delegates to multiple handlers."""

    def __init__(self, *handlers: TccEvents):
        self.handlers = list(handlers)

    def add_handler(self, handler: TccEvents) -> None:
        """Add an event handler."""
        self.handlers.append(handler)

    def remove_handler(self, handler: TccEvents) -> None:
        """Remove an event handler."""
        if handler in self.handlers:
            self.handlers.remove(handler)

    async def on_tcc_started(
        self, tcc_name: str, correlation_id: str, context: Optional[TccContext] = None
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_tcc_started(tcc_name, correlation_id, context)
            except Exception as e:
                # Log error but continue with other handlers
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_tcc_completed(
        self, tcc_name: str, correlation_id: str, final_phase: TccPhase, duration_ms: int
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_tcc_completed(tcc_name, correlation_id, final_phase, duration_ms)
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_phase_started(self, tcc_name: str, correlation_id: str, phase: TccPhase) -> None:
        for handler in self.handlers:
            try:
                await handler.on_phase_started(tcc_name, correlation_id, phase)
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_phase_completed(
        self, tcc_name: str, correlation_id: str, phase: TccPhase, duration_ms: int
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_phase_completed(tcc_name, correlation_id, phase, duration_ms)
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_phase_failed(
        self,
        tcc_name: str,
        correlation_id: str,
        phase: TccPhase,
        error: Exception,
        duration_ms: int,
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_phase_failed(tcc_name, correlation_id, phase, error, duration_ms)
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_participant_started(
        self, tcc_name: str, correlation_id: str, participant_id: str, phase: TccPhase
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_participant_started(
                    tcc_name, correlation_id, participant_id, phase
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_participant_success(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        attempts: int,
        duration_ms: int,
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_participant_success(
                    tcc_name, correlation_id, participant_id, phase, attempts, duration_ms
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_participant_failed(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        error: Exception,
        attempts: int,
        duration_ms: int,
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_participant_failed(
                    tcc_name, correlation_id, participant_id, phase, error, attempts, duration_ms
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_participant_retry(
        self,
        tcc_name: str,
        correlation_id: str,
        participant_id: str,
        phase: TccPhase,
        attempts: int,
        last_error: Exception,
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_participant_retry(
                    tcc_name, correlation_id, participant_id, phase, attempts, last_error
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_participant_registered(
        self, tcc_name: str, correlation_id: str, participant_id: str
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_participant_registered(tcc_name, correlation_id, participant_id)
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_participant_timeout(
        self, tcc_name: str, correlation_id: str, participant_id: str, phase: TccPhase
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_participant_timeout(
                    tcc_name, correlation_id, participant_id, phase
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_resource_reserved(
        self, tcc_name: str, correlation_id: str, participant_id: str, resource_id: str
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_resource_reserved(
                    tcc_name, correlation_id, participant_id, resource_id
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")

    async def on_resource_released(
        self, tcc_name: str, correlation_id: str, participant_id: str, resource_id: str
    ) -> None:
        for handler in self.handlers:
            try:
                await handler.on_resource_released(
                    tcc_name, correlation_id, participant_id, resource_id
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in TCC event handler: {e}")
