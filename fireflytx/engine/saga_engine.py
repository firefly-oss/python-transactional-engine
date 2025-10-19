"""
Python wrapper for the lib-transactional-engine SagaEngine.

PURE ARCHITECTURE: Python defines SAGA structure, Java executes everything.

This module provides a Python interface to the Java SagaEngine from
lib-transactional-engine, enabling SAGA pattern execution in Python
applications via subprocess bridge communication.

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
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Union

from ..core.saga_context import SagaContext
from ..core.saga_result import SagaResult
from ..core.step_inputs import StepInputs
from ..integration.bridge import JavaClassCallRequest, JavaSubprocessBridge
from ..integration.type_conversion import get_type_converter

# Event publishing is handled through persistence and configuration

logger = logging.getLogger(__name__)


class CompensationPolicy:
    """Compensation policy enumeration."""

    STRICT_SEQUENTIAL = "STRICT_SEQUENTIAL"
    GROUPED_PARALLEL = "GROUPED_PARALLEL"
    RETRY_WITH_BACKOFF = "RETRY_WITH_BACKOFF"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    BEST_EFFORT_PARALLEL = "BEST_EFFORT_PARALLEL"


class SagaEngine:
    """
    Python wrapper for the lib-transactional-engine SagaEngine.

    PURE ARCHITECTURE: Python defines SAGA structure, Java executes everything.

    This class provides a Python interface where:
    1. Python defines SAGA structure using decorators
    2. Java lib-transactional-engine handles ALL execution:
       - Orchestration and dependency management
       - Retry logic and timeout handling
       - Compensation execution
       - Transaction persistence and recovery
       - Calling back to Python methods for business logic
    3. Python receives final results from Java

    Example:
        engine = SagaEngine()
        await engine.initialize()
        result = await engine.execute(PaymentProcessingSaga, payment_data)
    """

    def __init__(
        self,
        compensation_policy: str = CompensationPolicy.STRICT_SEQUENTIAL,
        auto_optimization_enabled: bool = True,
        persistence_enabled: bool = False,
        config: Optional[Any] = None,
        event_publisher: Optional[Any] = None,
        persistence_provider: Optional[Any] = None,
        java_bridge: Optional[JavaSubprocessBridge] = None,
    ):
        """
        Initialize the SagaEngine wrapper.

        Args:
            compensation_policy: Policy for handling compensations
            auto_optimization_enabled: Enable automatic optimizations
            persistence_enabled: Enable saga persistence
            config: Optional transactional engine configuration (EngineConfig instance)
            event_publisher: Optional event publisher implementation
            persistence_provider: Optional persistence provider implementation
            java_bridge: Optional Java bridge instance. If not provided, a new one is created.
        """
        # Store configuration - if EngineConfig is provided, extract settings from it
        if config is not None:
            # If config is an EngineConfig instance, use its settings
            from fireflytx.config.engine_config import EngineConfig
            if isinstance(config, EngineConfig):
                # Override individual settings with config values if not explicitly set
                self.compensation_policy = compensation_policy
                self.auto_optimization_enabled = auto_optimization_enabled
                self.persistence_enabled = persistence_enabled or config.persistence.type != "memory"
                self.config = config
                # Extract thread pool size from config if available
                self._thread_pool_size = getattr(config, 'thread_pool_size', 4)
            else:
                # Config is some other type, store as-is
                self.compensation_policy = compensation_policy
                self.auto_optimization_enabled = auto_optimization_enabled
                self.persistence_enabled = persistence_enabled
                self.config = config
                self._thread_pool_size = 4
        else:
            # No config provided, use individual parameters
            self.compensation_policy = compensation_policy
            self.auto_optimization_enabled = auto_optimization_enabled
            self.persistence_enabled = persistence_enabled
            self.config = None
            self._thread_pool_size = 4

        self.event_publisher = event_publisher
        self.persistence_provider = persistence_provider

        self._java_bridge = java_bridge or JavaSubprocessBridge()
        self._saga_engine_id: Optional[str] = None
        self._orchestrator_id: Optional[str] = None
        self._type_converter = get_type_converter()
        self._executor = ThreadPoolExecutor(max_workers=self._thread_pool_size)
        self._initialized = False
        self._callback_handlers = {}  # Store callback handlers for Java callbacks

    async def initialize(self) -> None:
        """
        Initialize the engine using lib-transactional-engine.

        This method starts the subprocess bridge and creates Java
        SagaEngine and SagaExecutionOrchestrator instances.
        """
        if self._initialized:
            logger.debug("SagaEngine already initialized")
            return

        logger.info("Initializing lib-transactional-engine SagaEngine...")

        # Start the subprocess bridge with configuration
        # Pass JVM config if available from EngineConfig
        jvm_config = None
        if self.config is not None:
            from fireflytx.config.engine_config import EngineConfig
            if isinstance(self.config, EngineConfig):
                jvm_config = self.config.jvm
                logger.debug(f"Using JVM config: heap_size={jvm_config.heap_size}")

        self._java_bridge.start_jvm(config=jvm_config)

        # Create Java engine components
        await self._create_saga_engine()

        self._initialized = True

        # Log lib-transactional-engine version and path
        lib_version = self._java_bridge.get_lib_transactional_version()
        jar_path = getattr(self._java_bridge, "_jar_path", "unknown")
        if lib_version:
            logger.info(
                f"🏁 SagaEngine using lib-transactional-engine {lib_version} from {jar_path}"
            )
        else:
            logger.info(f"🏁 SagaEngine using lib-transactional-engine from {jar_path}")

        logger.info("SagaEngine from lib-transactional-engine initialized successfully")

    async def _create_saga_engine(self) -> str:
        """Create a SagaEngine instance from lib-transactional-engine."""
        logger.info("Creating SagaEngine instance...")

        saga_request = JavaClassCallRequest(
            class_name="com.firefly.transactional.saga.engine.SagaEngine",
            method_name="__constructor__",
            method_type="constructor",
            args=[],
        )

        response = self._java_bridge.call_java_method(saga_request)
        if response.success:
            self._saga_engine_id = response.instance_id
            logger.info(f"✅ SagaEngine created: {self._saga_engine_id}")
            return self._saga_engine_id
        else:
            raise RuntimeError(f"Failed to create SagaEngine: {response.error}")



    async def execute(
        self,
        saga_class: type,
        step_inputs: Union[Dict[str, Any], StepInputs] = None,
        context: Optional[SagaContext] = None,
    ) -> SagaResult:
        """
        Execute a SAGA by Python class with pure Java orchestration.

        Args:
            saga_class: Python class decorated with @saga
            step_inputs: Inputs for saga steps (optional, defaults to empty dict)
            context: Optional saga context

        Returns:
            SagaResult containing execution results from Java engine
        """
        # First register the SAGA class with the Java engine
        await self.register_saga(saga_class)

        # Extract saga name from class metadata
        saga_name = getattr(saga_class, "_saga_name", saga_class.__name__)

        # Execute the full SAGA flow through Java engine with Python callbacks
        return await self._execute_full_saga_flow(saga_name, saga_class, step_inputs or {}, context)



    async def _execute_full_saga_flow(
        self,
        saga_name: str,
        saga_class: type,
        step_inputs: Union[Dict[str, Any], StepInputs],
        context: Optional[SagaContext] = None,
    ) -> SagaResult:
        """
        Execute a complete SAGA flow through pure Java orchestration.

        ARCHITECTURE: Java handles ALL orchestration, Python provides callbacks.
        """
        logger.info(
            f"🔄 Delegating SAGA '{saga_name}' orchestration to Java lib-transactional-engine"
        )

        input_data = step_inputs if isinstance(step_inputs, dict) else step_inputs.to_dict()
        correlation_id = context.correlation_id if context else f"saga_{saga_name}_{id(self)}"

        # Step 1: Register Python SAGA definition with Java engine
        await self._register_python_saga_definition(saga_name, saga_class)

        # Step 2: Set up Python callback handler for Java engine
        callback_handler = self._setup_python_callback_handler(saga_class)

        # Step 3: Execute SAGA entirely in Java with Python method callbacks
        callback_info = {"callback_url": callback_handler.get_callback_endpoint()}

        execution_request = JavaClassCallRequest(
            class_name="com.firefly.transactional.saga.engine.SagaEngine",
            method_name="executeSaga",
            method_type="instance",
            instance_id=self._saga_engine_id,
            args=[saga_name, input_data, correlation_id, callback_info],
        )

        response = self._java_bridge.call_java_method(execution_request)

        if response.success:
            # Java returns complete execution results including compensation if needed
            result_data = response.result

            # Handle different result formats from Java engine
            if isinstance(result_data, str):
                # Java engine returned a string result, create proper structure
                result_data = {
                    "saga_name": saga_name,
                    "correlation_id": correlation_id,
                    "is_success": response.success,
                    "duration_ms": 0,
                    "steps": {},
                    "failed_steps": [],
                    "compensated_steps": [],
                    "error": None,
                    "engine_used": True,
                    "lib_transactional_version": self._java_bridge.get_lib_transactional_version()
                    or "1.0.0-SNAPSHOT",
                    "java_result": result_data,  # Store original Java result
                }
            elif isinstance(result_data, dict):
                # Ensure required fields are present
                result_data.update(
                    {
                        "saga_name": saga_name,
                        "correlation_id": correlation_id,
                        "engine_used": True,
                        "lib_transactional_version": self._java_bridge.get_lib_transactional_version()
                        or "1.0.0-SNAPSHOT",
                    }
                )
            else:
                # Handle None or other result types
                result_data = {
                    "saga_name": saga_name,
                    "correlation_id": correlation_id,
                    "is_success": response.success,
                    "duration_ms": 0,
                    "steps": {},
                    "failed_steps": [],
                    "compensated_steps": [],
                    "error": None,
                    "engine_used": True,
                    "lib_transactional_version": self._java_bridge.get_lib_transactional_version()
                    or "1.0.0-SNAPSHOT",
                }

            logger.info(
                f"✅ Java engine completed SAGA '{saga_name}' - Success: {result_data.get('is_success', False)}"
            )
            return SagaResult.from_dict(result_data)
        else:
            logger.error(f"❌ Java engine failed to execute SAGA '{saga_name}': {response.error}")
            return SagaResult.from_dict(
                {
                    "saga_name": saga_name,
                    "correlation_id": correlation_id,
                    "is_success": False,
                    "duration_ms": 0,
                    "steps": {},
                    "failed_steps": [saga_name],
                    "compensated_steps": [],
                    "error": response.error or "Java engine execution failed",
                    "engine_used": True,
                }
            )

    async def _register_python_saga_definition(self, saga_name: str, saga_class: type) -> None:
        """
        Register Python SAGA definition with Java engine for orchestration.

        Sends the complete SAGA structure defined in Python to the Java engine
        so it can orchestrate execution with full knowledge of:
        - Steps and their dependencies
        - Compensation methods
        - Retry policies and timeouts
        - Method signatures for callbacks
        """
        logger.info(f"📝 Registering SAGA definition '{saga_name}' with Java engine")

        saga_config = getattr(saga_class, "_saga_config", None)
        if not saga_config:
            raise ValueError(
                f"SAGA class {saga_class.__name__} missing @saga decorator configuration"
            )

        # Build complete SAGA definition for Java engine
        saga_definition = {
            "saga_name": saga_name,
            "class_name": saga_class.__name__,
            "module": saga_class.__module__,
            "steps": {},
            "compensations": {},
            "layer_concurrency": saga_config.layer_concurrency,
        }

        # Register all step definitions
        for step_id, step_config in saga_config.steps.items():
            method_name = self._find_method_name_for_step(saga_class, step_id)

            # Get compensation method name if defined
            compensation_method_name = saga_config.compensation_methods.get(step_id)

            saga_definition["steps"][step_id] = {
                "step_id": step_id,
                "python_method": method_name,
                "compensation_method": compensation_method_name,  # Add compensation method to step
                "depends_on": step_config.depends_on or [],
                "retry": step_config.retry,
                "backoff_ms": step_config.backoff_ms,
                "timeout_ms": step_config.timeout_ms,
                "jitter": step_config.jitter,
                "jitter_factor": step_config.jitter_factor,
                "cpu_bound": step_config.cpu_bound,
                "idempotency_key": step_config.idempotency_key,
            }

        # Register all compensation method definitions
        for step_id, compensation_method_name in saga_config.compensation_methods.items():
            # Check if we have a dedicated compensation config
            if step_id in saga_config.compensation_configs:
                comp_config = saga_config.compensation_configs[step_id]
                saga_definition["compensations"][step_id] = {
                    "step_id": step_id,
                    "python_method": compensation_method_name,
                    "retry": comp_config.retry,
                    "timeout_ms": comp_config.timeout_ms,
                    "critical": comp_config.critical,
                    "backoff_ms": comp_config.backoff_ms,
                    "jitter": comp_config.jitter,
                    "jitter_factor": comp_config.jitter_factor,
                }
            else:
                # Fall back to step-level compensation config
                saga_definition["compensations"][step_id] = {
                    "step_id": step_id,
                    "python_method": compensation_method_name,
                    "retry": (
                        saga_config.steps[step_id].compensation_retry
                        if step_id in saga_config.steps
                        else 3
                    ),
                    "timeout_ms": (
                        saga_config.steps[step_id].compensation_timeout_ms
                        if step_id in saga_config.steps
                        else 10000
                    ),
                    "critical": (
                        saga_config.steps[step_id].compensation_critical
                        if step_id in saga_config.steps
                        else False
                    ),
                    "backoff_ms": 1000,
                    "jitter": True,
                    "jitter_factor": 0.3,
                }

        # Send SAGA definition to Java engine for orchestration setup
        register_request = JavaClassCallRequest(
            class_name="com.firefly.transactional.saga.engine.SagaEngine",
            method_name="registerSagaDefinition",
            method_type="instance",
            instance_id=self._saga_engine_id,
            args=[saga_definition],
        )

        response = self._java_bridge.call_java_method(register_request)
        if not response.success:
            raise RuntimeError(f"Failed to register SAGA definition: {response.error}")

        logger.info(
            f"✅ SAGA '{saga_name}' definition registered with {len(saga_definition['steps'])} steps"
        )

    def _setup_python_callback_handler(self, saga_class: type):
        """
        Set up callback handler for Java engine to call Python methods.

        Creates an HTTP-based callback mechanism that allows the Java lib-transactional-engine
        to invoke Python SAGA step and compensation methods during orchestration.
        """
        logger.info(f"🔄 Setting up Python callback handler for {saga_class.__name__}")

        from ..integration.callbacks import PythonCallbackHandler

        handler = PythonCallbackHandler(saga_class)

        # Start the callback server
        endpoint_url = handler.start()

        # Store handler for cleanup later
        correlation_id = f"saga_{saga_class.__name__}_{id(self)}"
        self._callback_handlers[correlation_id] = handler

        logger.info(f"Callback handler ready at: {endpoint_url}")
        return handler

    def _find_method_name_for_step(self, saga_class: type, step_id: str) -> str:
        """Find the Python method name for a given step ID."""
        for attr_name in dir(saga_class):
            attr = getattr(saga_class, attr_name)
            if hasattr(attr, "_saga_step_config"):
                if attr._saga_step_config.step_id == step_id:
                    return attr_name
        raise ValueError(f"No method found for step '{step_id}' in {saga_class.__name__}")

    # ============================================================================
    # ARCHITECTURE: Python Defines, Java Executes
    # ============================================================================
    # All SAGA orchestration, step execution, compensation, retry logic, and
    # transaction management is handled by the Java lib-transactional-engine.
    # Python serves as the definition layer and callback provider.
    # ============================================================================

    async def register_saga(self, saga_class: type, saga_name: Optional[str] = None) -> None:
        """
        Register a Python saga class with the lib-transactional-engine.

        Args:
            saga_class: Python class decorated with @saga
            saga_name: Optional name override
        """
        if not self._initialized:
            raise RuntimeError("SagaEngine not initialized. Call initialize() first.")

        name = saga_name or getattr(saga_class, "_saga_name", saga_class.__name__)

        # Extract SAGA configuration
        saga_config = getattr(saga_class, "_saga_config", None)
        if not saga_config:
            raise ValueError(
                f"SAGA class {saga_class.__name__} missing @saga decorator configuration"
            )

        # Build registration data for Java engine
        registration_data = {
            "class_name": saga_class.__name__,
            "module": saga_class.__module__,
            "saga_name": name,
            "layer_concurrency": saga_config.layer_concurrency,
            "steps": {},
        }

        # Add step information
        for step_id, step_config in saga_config.steps.items():
            registration_data["steps"][step_id] = {
                "step_id": step_id,
                "depends_on": step_config.depends_on,
                "retry": step_config.retry,
                "timeout_ms": step_config.timeout_ms,
                "backoff_ms": step_config.backoff_ms,
                "compensate": step_config.compensate,
                "compensation_retry": step_config.compensation_retry,
                "compensation_timeout_ms": step_config.compensation_timeout_ms,
            }

        logger.info(f"Registering SAGA '{name}' with {len(registration_data['steps'])} steps")

        # Register saga definition using lib-transactional-engine
        registration_request = JavaClassCallRequest(
            class_name="com.firefly.transactional.saga.engine.SagaEngine",
            method_name="registerSaga",
            method_type="instance",
            instance_id=self._saga_engine_id,
            args=[name, registration_data],
        )

        response = self._java_bridge.call_java_method(registration_request)
        if response.success:
            logger.info(f"✅ Registered saga '{name}' with lib-transactional-engine")
        else:
            logger.error(f"❌ Failed to register saga '{name}': {response.error}")
            raise RuntimeError(f"Failed to register saga '{name}': {response.error}")

    def is_initialized(self) -> bool:
        """Check if the engine is initialized."""
        return self._initialized

    async def shutdown(self) -> None:
        """Shutdown the engine and cleanup resources."""
        # Cleanup callback handlers first
        for handler in self._callback_handlers.values():
            if hasattr(handler, "stop"):
                handler.stop()
        self._callback_handlers.clear()

        if self._java_bridge:
            self._java_bridge.shutdown()

        self._saga_engine_id = None
        self._orchestrator_id = None

        self._executor.shutdown(wait=True)
        self._initialized = False

        logger.info("lib-transactional-engine SagaEngine shutdown complete")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()

    def is_initialized(self) -> bool:
        """Check if the engine is initialized."""
        return self._initialized

    async def get_saga_names(self) -> List[str]:
        """Get list of registered SAGA names."""
        if not self._initialized:
            return []

        try:
            request = JavaClassCallRequest(
                class_name="com.firefly.transactional.saga.engine.SagaEngine",
                method_name="getRegisteredSagas",
                method_type="instance",
                instance_id=self._saga_engine_id,
                args=[],
            )

            response = self._java_bridge.call_java_method(request)
            if response.success and isinstance(response.result, list):
                return response.result
            return []
        except Exception:
            return []

    async def is_persistence_healthy(self) -> bool:
        """Check if persistence is healthy."""
        if not self._initialized:
            return False

        try:
            request = JavaClassCallRequest(
                class_name="com.firefly.transactional.saga.engine.SagaEngine",
                method_name="isPersistenceHealthy",
                method_type="instance",
                instance_id=self._saga_engine_id,
                args=[],
            )

            response = self._java_bridge.call_java_method(request)
            return response.success and bool(response.result)
        except Exception:
            return False


class PythonSagaCallbackHandler:
    """
    Handles callbacks from Java lib-transactional-engine to Python SAGA methods.

    This class enables the pure 'Python defines, Java executes' architecture by
    providing a bridge for Java to call Python SAGA step and compensation methods.
    """

    def __init__(self, saga_class: type, java_bridge):
        self.saga_class = saga_class
        self.java_bridge = java_bridge
        self.saga_instance = saga_class()
        self.logger = logging.getLogger(__name__)

    def get_callback_endpoint(self):
        """Get callback endpoint information for Java engine."""
        return {
            "callback_type": "python_handler",
            "handler_id": id(self),
            "class_name": self.saga_class.__name__,
        }

    async def execute_step(self, step_id: str, input_data: dict, context_data: dict) -> dict:
        """
        Execute a SAGA step method called back from Java engine.

        This method is invoked by the Java lib-transactional-engine when it needs
        to execute a Python SAGA step during orchestration.
        """
        self.logger.info(f"Java callback: executing step '{step_id}'")

        try:
            # Import here to avoid circular imports
            from ..core.saga_context import SagaContext

            # Reconstruct context from Java data
            context = SagaContext(context_data.get("correlation_id", ""))
            for key, value in context_data.get("variables", {}).items():
                context.set_data(key, value)

            # Find and execute the step method
            step_method = self._find_step_method(step_id)

            # Execute the step method (handle both sync and async)
            if asyncio.iscoroutinefunction(step_method):
                result = await step_method(context, input_data)
            else:
                result = step_method(context, input_data)

            self.logger.info(f"✅ Java callback: step '{step_id}' completed")
            return {"success": True, "result": result, "context_updates": context.to_dict()}

        except Exception as e:
            self.logger.error(f"❌ Java callback: step '{step_id}' failed: {e}")
            return {"success": False, "error": str(e), "context_updates": {}}

    async def execute_compensation(
        self, step_id: str, step_result: dict, context_data: dict
    ) -> dict:
        """
        Execute a compensation method called back from Java engine.

        This method is invoked by the Java lib-transactional-engine when it needs
        to execute compensation during SAGA rollback.
        """
        self.logger.info(f"Java callback: executing compensation for step '{step_id}'")

        try:
            # Import here to avoid circular imports
            from ..core.saga_context import SagaContext

            # Reconstruct context from Java data
            context = SagaContext(context_data.get("correlation_id", ""))
            for key, value in context_data.get("variables", {}).items():
                context.set_data(key, value)

            # Find and execute the compensation method
            compensation_method = self._find_compensation_method(step_id)
            if compensation_method:
                # Execute the compensation method (handle both sync and async)
                if asyncio.iscoroutinefunction(compensation_method):
                    result = await compensation_method(context, step_result)
                else:
                    result = compensation_method(context, step_result)

                self.logger.info(f"✅ Java callback: compensation for '{step_id}' completed")
                return {"success": True, "result": result, "context_updates": context.to_dict()}
            else:
                self.logger.warning(f"⚠️ Java callback: no compensation method for step '{step_id}'")
                return {
                    "success": True,
                    "result": {"status": "no_compensation_method"},
                    "context_updates": {},
                }

        except Exception as e:
            self.logger.error(f"❌ Java callback: compensation for step '{step_id}' failed: {e}")
            return {"success": False, "error": str(e), "context_updates": {}}

    def _find_step_method(self, step_id: str):
        """Find the Python method for a given step ID."""
        for attr_name in dir(self.saga_instance):
            attr = getattr(self.saga_instance, attr_name)
            if hasattr(attr, "_saga_step_config"):
                if attr._saga_step_config.step_id == step_id:
                    return attr
        raise ValueError(f"No step method found for '{step_id}' in {self.saga_class.__name__}")

    def _find_compensation_method(self, step_id: str):
        """Find the Python compensation method for a given step ID."""
        for attr_name in dir(self.saga_instance):
            attr = getattr(self.saga_instance, attr_name)
            if hasattr(attr, "_compensation_for_step"):
                if attr._compensation_for_step == step_id:
                    return attr
        return None
