"""
TCC (Try-Confirm-Cancel) Engine for Firefly Transactional Framework.

This module provides the TCC engine that executes Try-Confirm-Cancel pattern transactions
with HTTP callback support for Python participant methods.

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0.
"""

import logging
import threading
import time
from typing import Any, Optional, Type

from fireflytx.core.tcc_result import TccResult
from fireflytx.decorators.tcc import TccConfig
from fireflytx.integration.bridge import JavaSubprocessBridge
from fireflytx.integration.tcc_callbacks import TccCallbackHandler

logger = logging.getLogger(__name__)


class TccEngine:
    """
    TCC (Try-Confirm-Cancel) Engine.

    Executes TCC pattern transactions using Java orchestration with Python callbacks.
    Similar to SAGA engine but for TCC semantics.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        java_bridge: Optional[JavaSubprocessBridge] = None,
        timeout_ms: int = 30000,
        enable_monitoring: bool = True,
    ):
        """
        Initialize the TCC Engine.

        Args:
            config: Optional transactional engine configuration (EngineConfig instance)
            java_bridge: Optional Java bridge instance. If not provided, a new one is created.
            timeout_ms: Default timeout for TCC transactions in milliseconds
            enable_monitoring: Enable transaction monitoring and metrics
        """
        # Store configuration - if EngineConfig is provided, extract settings from it
        if config is not None:
            from fireflytx.config.engine_config import EngineConfig
            if isinstance(config, EngineConfig):
                self.config = config
                self.timeout_ms = config.default_timeout_ms
                self.enable_monitoring = config.enable_monitoring
                self._thread_pool_size = getattr(config, 'thread_pool_size', 4)
            else:
                # Config is some other type, store as-is
                self.config = config
                self.timeout_ms = timeout_ms
                self.enable_monitoring = enable_monitoring
                self._thread_pool_size = 4
        else:
            # No config provided, use individual parameters
            self.config = None
            self.timeout_ms = timeout_ms
            self.enable_monitoring = enable_monitoring
            self._thread_pool_size = 4

        self.java_bridge = java_bridge or JavaSubprocessBridge()
        self._is_running = False
        self._lock = threading.Lock()
        self._callback_handler: Optional[TccCallbackHandler] = None
        logger.info("TCC Engine initialized")

    def start(self):
        """
        Start the TCC engine.
        """
        with self._lock:
            if self._is_running:
                return

            logger.info("Starting TCC Engine")

            # Start the Java bridge with configuration
            # Pass JVM config if available from EngineConfig
            jvm_config = None
            if self.config is not None:
                from fireflytx.config.engine_config import EngineConfig
                if isinstance(self.config, EngineConfig):
                    jvm_config = self.config.jvm
                    logger.debug(f"Using JVM config: heap_size={jvm_config.heap_size}")

            self.java_bridge.start_jvm(config=jvm_config)
            self._is_running = True
            logger.info("TCC Engine started")

    async def execute(
        self, tcc_class: Type, input_data: dict = None, correlation_id: str = None
    ) -> TccResult:
        """
        Execute a TCC transaction with Python-defined participants via Java subprocess bridge.

        Args:
            tcc_class: The TCC transaction class decorated with @tcc
            input_data: Input data for TCC participants
            correlation_id: Unique identifier for this transaction instance

        Returns:
            TccResult with execution outcome and phase details
        """
        if not self._is_running:
            raise RuntimeError("TCC Engine is not running. Call start() first.")

        tcc_config: TccConfig = getattr(tcc_class, "_tcc_config", None)
        if not tcc_config:
            raise ValueError(f"Class {tcc_class.__name__} is not decorated with @tcc")

        correlation_id = correlation_id or f"tcc_{int(time.time() * 1000)}"
        input_data = input_data or {}
        tcc_name = getattr(tcc_class, "_tcc_name", tcc_class.__name__)

        logger.info(
            f"Executing TCC transaction: {tcc_name} (correlation_id: {correlation_id})"
        )

        # Start callback handler for this TCC execution
        callback_handler = TccCallbackHandler(tcc_class)
        callback_endpoint = callback_handler.start()

        try:
            # Register TCC definition with Java bridge
            tcc_definition = self._build_tcc_definition(tcc_class, tcc_config)
            self.java_bridge.registerTccDefinition(tcc_definition)

            # Prepare callback info for Java bridge
            callback_info = {
                "callback_endpoint": callback_endpoint,
                "tcc_name": tcc_name,
            }

            # Execute TCC using Java bridge orchestration
            java_result = await self._execute_via_java_bridge(
                tcc_name, correlation_id, input_data, callback_info
            )

            # Convert Java bridge result to TccResult using from_dict method
            if isinstance(java_result, dict):
                # Ensure proper field mapping
                result_data = {
                    "tcc_name": tcc_name,
                    "correlation_id": correlation_id,
                    "is_success": java_result.get("success", False),
                    "is_confirmed": java_result.get("phase") == "CONFIRM",
                    "is_canceled": java_result.get("phase") == "CANCEL",
                    "final_phase": java_result.get("phase", "UNKNOWN"),
                    "duration_ms": java_result.get("duration_ms", 0),
                    "try_results": java_result.get("try_results", {}),
                    "participant_results": java_result.get("participant_results", {}),
                    "error": java_result.get("error"),
                }
                return TccResult.from_dict(result_data)
            else:
                # Fallback case
                result_data = {
                    "tcc_name": tcc_name,
                    "correlation_id": correlation_id,
                    "is_success": True,
                    "is_confirmed": True,
                    "is_canceled": False,
                    "final_phase": "CONFIRM",
                    "duration_ms": 0,
                    "try_results": {},
                    "participant_results": {},
                    "error": None,
                }
                return TccResult.from_dict(result_data)

        except Exception as e:
            logger.error(f"TCC execution failed: {e}")
            result_data = {
                "tcc_name": tcc_name,
                "correlation_id": correlation_id,
                "is_success": False,
                "is_confirmed": False,
                "is_canceled": False,
                "final_phase": "CANCEL",
                "duration_ms": 0,
                "try_results": {},
                "participant_results": {},
                "error": str(e),
            }
            return TccResult.from_dict(result_data)
        finally:
            # Always stop the callback handler
            callback_handler.stop()

    def _build_tcc_definition(self, tcc_class: Type, tcc_config: TccConfig) -> dict:
        """Build TCC definition dict for Java bridge registration."""
        tcc_name = getattr(tcc_class, "_tcc_name", tcc_class.__name__)

        # Build participants dict
        participants = {}
        for participant_id, participant_config in tcc_config.participants.items():
            # Determine if this is a class-based or method-based participant
            is_class_based = participant_id in tcc_config.participant_classes

            participants[participant_id] = {
                "participant_id": participant_id,
                "order": participant_config.order,
                "timeout_ms": participant_config.timeout_ms,
                "try_method": participant_config.try_method,
                "confirm_method": participant_config.confirm_method,
                "cancel_method": participant_config.cancel_method,
                "is_class_based": is_class_based,  # Flag to distinguish patterns
            }

        return {
            "tcc_name": tcc_name,
            "class_name": tcc_class.__name__,
            "module": tcc_class.__module__,
            "participants": participants,
        }

    async def _execute_via_java_bridge(
        self, tcc_name: str, correlation_id: str, input_data: dict, callback_info: dict
    ) -> dict:
        """Execute TCC via Java bridge orchestration in async context."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        # Run the synchronous Java bridge call in a thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool,
                self.java_bridge.executeTcc,
                tcc_name,
                correlation_id,
                input_data,
                callback_info
            )
        return result

    def stop(self):
        """
        Stop the TCC engine and cleanup resources.
        """
        with self._lock:
            if not self._is_running:
                return

            logger.info("Stopping TCC Engine")

            # Stop callback handler if running
            if self._callback_handler:
                self._callback_handler.stop()
                self._callback_handler = None

            self.java_bridge.shutdown()
            self._is_running = False
            logger.info("TCC Engine stopped")

    def is_running(self) -> bool:
        """Check if the engine is running."""
        return self._is_running
