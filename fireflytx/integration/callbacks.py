"""
Python Callback Handler for SAGA Step Execution.

This module provides the callback system that allows the Java subprocess bridge
to call back into Python to execute SAGA step and compensation methods.

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0.
"""

import asyncio
import inspect
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Optional, Union, get_type_hints

logger = logging.getLogger(__name__)


class PythonCallbackHandler:
    """
    HTTP-based callback handler for receiving calls from Java subprocess bridge.

    This handler starts a local HTTP server that the Java bridge can call
    to execute Python SAGA step and compensation methods.
    """

    def __init__(self, saga_class: type, host: str = "localhost", port: int = 0):
        self.saga_class = saga_class
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._running = False

        # Store instance of saga class for method execution
        self.saga_instance = saga_class()

    def start(self) -> str:
        """Start the callback server and return the endpoint URL."""
        if self._running:
            return self.get_callback_endpoint()

        # Create HTTP server
        handler = self._create_request_handler()
        self.server = HTTPServer((self.host, self.port), handler)

        # Get actual port if auto-assigned
        if self.port == 0:
            self.port = self.server.server_address[1]

        logger.info(f"Starting Python callback server on {self.host}:{self.port}")

        # Start server in background thread
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self._running = True

        # Wait a moment for server to start
        time.sleep(0.1)

        endpoint = self.get_callback_endpoint()
        logger.info(f"Python callback server ready at: {endpoint}")
        return endpoint

    def stop(self):
        """Stop the callback server."""
        if not self._running:
            return

        logger.info("Stopping Python callback server")

        if self.server:
            self.server.shutdown()
            self.server.server_close()

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)

        self.executor.shutdown(wait=True)
        self._running = False

    def get_callback_endpoint(self) -> str:
        """Get the callback endpoint URL."""
        return f"http://{self.host}:{self.port}/callback"

    def _create_request_handler(self):
        """Create the HTTP request handler class."""
        callback_handler = self

        class CallbackRequestHandler(BaseHTTPRequestHandler):

            def log_message(self, format, *args):
                # Suppress default HTTP server logging
                pass

            def do_POST(self):
                """Handle POST requests for step execution callbacks."""
                try:
                    # Parse request
                    if self.path != "/callback":
                        self.send_error(404, "Not Found")
                        return

                    # Read request body
                    content_length = int(self.headers.get("Content-Length", 0))
                    request_body = self.rfile.read(content_length).decode("utf-8")

                    # Parse JSON request
                    request_data = json.loads(request_body)

                    # Execute callback
                    result = callback_handler._handle_callback(request_data)

                    # Send response
                    response_data = json.dumps(result).encode("utf-8")

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(response_data)))
                    self.end_headers()
                    self.wfile.write(response_data)

                except Exception as e:
                    logger.error(f"Error handling callback request: {e}", exc_info=True)

                    # Send error response
                    error_response = json.dumps({"success": False, "error": str(e)}).encode("utf-8")

                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(error_response)))
                    self.end_headers()
                    self.wfile.write(error_response)

        return CallbackRequestHandler

    def _handle_callback(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a callback request from Java."""
        try:
            method_type = request_data.get("method_type")  # "step" or "compensation"
            method_name = request_data.get("method_name")
            step_id = request_data.get("step_id")
            input_data = request_data.get("input_data", {})
            context_data = request_data.get("context_data", {})

            logger.info(
                f"Executing callback: {method_type} method '{method_name}' for step '{step_id}'"
            )

            # Create context from context data
            from ..core.saga_context import SagaContext

            # Log what we received from Java
            incoming_variables = context_data.get("variables", {})
            if incoming_variables:
                logger.debug(f"📥 [IPC] Received {len(incoming_variables)} context variables from Java: {list(incoming_variables.keys())}")

            context = SagaContext(
                correlation_id=context_data.get("correlation_id", "unknown"),
                saga_name=context_data.get("saga_name"),
                variables=incoming_variables,
            )

            # Add step results from context data to make them available to current step
            step_results = context_data.get("step_results", {})
            for step_id_key, step_result in step_results.items():
                # Store step-specific result
                context.set_step_result(step_id_key, step_result)

                # Also extract specific data from step results and add to variables
                if isinstance(step_result, dict):
                    for key, value in step_result.items():
                        context.set_data(key, value)

            # Get the method to execute
            if not hasattr(self.saga_instance, method_name):
                raise AttributeError(
                    f"Method {method_name} not found in {self.saga_class.__name__}"
                )

            method = getattr(self.saga_instance, method_name)

            logger.info(f"🔄 [IPC] Java → Python: Executing {method_type} '{method_name}' for step '{step_id}'")

            # Execute method in thread pool to handle async methods
            future = self.executor.submit(self._execute_method, method, context, input_data)
            result = future.result(timeout=30)  # 30 second timeout

            logger.info(f"✅ [IPC] Python → Java: Callback '{method_name}' completed successfully")

            # Convert result to dict if it's a Pydantic model or dataclass
            serialized_result = self._serialize_result(result)

            # Automatically store the step result in context for downstream steps
            # This ensures that even if the step doesn't explicitly call context.set_variable(),
            # the result is still available to dependent steps
            if serialized_result is not None:
                context.set_step_result(step_id, serialized_result)

                # Also add result fields to variables if result is a dict
                if isinstance(serialized_result, dict):
                    for key, value in serialized_result.items():
                        # Only add if not already set by the step method
                        if key not in context.variables:
                            context.set_variable(f"{step_id}_{key}", value)

            # Get context dict with all variables
            context_dict = context.to_dict()

            # Log context variables being sent back to Java
            variables = context_dict.get("variables", {})
            if variables:
                logger.info(f"📤 [IPC] Sending {len(variables)} context variables to Java: {list(variables.keys())}")
                logger.debug(f"📤 [IPC] Context variable values: {variables}")
            else:
                logger.info(f"📤 [IPC] No context variables to send to Java (step may not have set any)")

            # Include context updates so Java can persist context variables between steps
            return {
                "success": True,
                "result": serialized_result,
                "step_id": step_id,
                "method_name": method_name,
                "context_updates": context_dict,  # Include full context with variables
            }

        except Exception as e:
            logger.error(f"Callback execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "step_id": request_data.get("step_id"),
                "method_name": request_data.get("method_name"),
            }

    def _execute_method(self, method: Callable, context, input_data: Any) -> Any:
        """Execute a method, handling both sync and async methods.

        Supports two API styles:
        1. Simple: method(self, input_data: TypedModel) - for independent steps
        2. With context: method(self, input_data: TypedModel, context: SagaContext) - for sharing data between steps

        The framework auto-detects which signature to use based on the method's parameter count.
        """
        try:
            # Get the original unwrapped function to check signature
            original_func = method
            if hasattr(method, '__wrapped__'):
                original_func = method.__wrapped__

            # Detect method signature by checking parameter count
            sig = inspect.signature(original_func)
            params = list(sig.parameters.values())

            # 1 param = (self) - no input, 2 params = (self, input_data), 3+ params = (self, input_data, context)
            expects_context = len(params) >= 3
            expects_input = len(params) >= 2

            logger.debug(f"🔍 [IPC] Method {method.__name__} has {len(params)} params, expects_context={expects_context}, expects_input={expects_input}")

            # Convert input_data to the expected type based on method signature
            converted_input = None
            if expects_input:
                converted_input = self._convert_input_to_type(method, input_data, expects_context)

            # Check if method is async
            if asyncio.iscoroutinefunction(method):
                # Run async method in new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if expects_context:
                        # Signature: method(self, data, context)
                        result = loop.run_until_complete(method(converted_input, context))
                    elif expects_input:
                        result = loop.run_until_complete(method(converted_input))
                    else:
                        result = loop.run_until_complete(method())
                finally:
                    loop.close()
            else:
                # Execute sync method directly
                if expects_context:
                    # Signature: method(self, data, context)
                    result = method(converted_input, context)
                elif expects_input:
                    result = method(converted_input)
                else:
                    result = method()

            return result

        except Exception as e:
            logger.error(f"Method execution failed: {e}")
            raise

    def _convert_input_to_type(self, method: Callable, input_data: Any, expects_context: bool = False) -> Any:
        """Convert input_data to the expected type based on method's type hints.

        Supports two signatures:
        1. Simple: method(self, input_data: Type) - param index 1
        2. Advanced: method(self, context: SagaContext, input_data: Type) - param index 2
        """
        try:
            # Try to get the original unwrapped function if it exists
            original_func = method
            if hasattr(method, '__wrapped__'):
                original_func = method.__wrapped__

            # Get type hints - try both the wrapper and original function
            type_hints = None
            try:
                type_hints = get_type_hints(original_func)
            except Exception:
                try:
                    type_hints = get_type_hints(method)
                except Exception:
                    pass

            if not type_hints:
                return input_data

            # Get the parameter index based on signature
            sig = inspect.signature(original_func)
            params = list(sig.parameters.values())

            # Determine which parameter is input_data
            # New signature: method(self, data, context) - data is always at index 1
            if expects_context:
                # Advanced API: method(self, data, context) - data at param index 1
                if len(params) < 3:
                    return input_data
                param_index = 1
            else:
                # Simple API: method(self, data) - data at param index 1
                if len(params) < 2:
                    return input_data
                param_index = 1

            param_name = params[param_index].name
            param_type = type_hints.get(param_name)

            if param_type is None or param_type == dict or param_type == Any:
                # No type hint or dict type - return as is
                return input_data

            logger.debug(f"🔄 [IPC] Converting input from dict to {param_type.__name__}")

            # Check if it's a Pydantic model
            if hasattr(param_type, 'model_validate'):
                # Pydantic v2
                logger.debug(f"✅ [IPC] Using Pydantic v2 model_validate")
                return param_type.model_validate(input_data)
            elif hasattr(param_type, 'parse_obj'):
                # Pydantic v1
                logger.debug(f"✅ [IPC] Using Pydantic v1 parse_obj")
                return param_type.parse_obj(input_data)
            elif hasattr(param_type, '__dataclass_fields__'):
                # Dataclass
                logger.debug(f"✅ [IPC] Using dataclass constructor")
                return param_type(**input_data)
            else:
                # Unknown type - return as is
                logger.debug(f"⚠️ [IPC] Unknown type, returning raw dict")
                return input_data

        except Exception as e:
            logger.warning(f"❌ [IPC] Failed to convert input to type: {e}. Using raw dict.")
            return input_data

    def _serialize_result(self, result: Any) -> Any:
        """Convert result to JSON-serializable format."""
        if result is None:
            return None

        # Check if it's a Pydantic model
        if hasattr(result, 'model_dump'):
            # Pydantic v2
            logger.debug(f"🔄 [IPC] Serializing Pydantic v2 model to dict")
            return result.model_dump()
        elif hasattr(result, 'dict'):
            # Pydantic v1
            logger.debug(f"🔄 [IPC] Serializing Pydantic v1 model to dict")
            return result.dict()
        elif hasattr(result, '__dataclass_fields__'):
            # Dataclass
            import dataclasses
            logger.debug(f"🔄 [IPC] Serializing dataclass to dict")
            return dataclasses.asdict(result)
        else:
            # Already serializable (dict, list, str, int, etc.)
            return result


class CallbackRegistry:
    """
    Registry for Python callback handlers used by the Java subprocess bridge.

    This provides a minimal API expected by higher-level components
    (e.g., SagaEngine) for registering SAGA classes and
    retrieving their callback endpoints.
    """

    def __init__(self, host: str = "localhost", port: int = 0):
        self.host = host
        self.port = port
        # Map of saga class -> PythonCallbackHandler
        self._handlers: Dict[type, PythonCallbackHandler] = {}
        # Map of saga name -> PythonCallbackHandler for convenience
        self._name_handlers: Dict[str, PythonCallbackHandler] = {}

    def register_saga_class(self, saga_class: type) -> str:
        """
        Register a SAGA class and start its callback handler if not already running.

        Returns the callback endpoint URL (http://host:port/callback).
        """
        if saga_class in self._handlers:
            return self._handlers[saga_class].get_callback_endpoint()

        handler = PythonCallbackHandler(saga_class, host=self.host, port=self.port)
        endpoint = handler.start()

        self._handlers[saga_class] = handler
        saga_name = getattr(getattr(saga_class, "_saga_config", None), "name", saga_class.__name__)
        self._name_handlers[saga_name] = handler
        return endpoint

    def get_callback_endpoint(self, saga: Optional[Union[type, str]] = None) -> Optional[str]:
        """
        Get the callback endpoint for a specific registered SAGA or, if only one
        exists, return that endpoint.
        """
        if isinstance(saga, str):
            handler = self._name_handlers.get(saga)
            return handler.get_callback_endpoint() if handler else None
        if isinstance(saga, type):
            handler = self._handlers.get(saga)
            return handler.get_callback_endpoint() if handler else None
        # No saga specified - if only one handler, return it; otherwise None
        if len(self._handlers) == 1:
            return next(iter(self._handlers.values())).get_callback_endpoint()
        return None

    def shutdown(self) -> None:
        """Stop all running callback handlers and clear the registry."""
        for handler in list(self._handlers.values()):
            try:
                handler.stop()
            except Exception:
                # Best-effort shutdown
                pass
        self._handlers.clear()
        self._name_handlers.clear()
