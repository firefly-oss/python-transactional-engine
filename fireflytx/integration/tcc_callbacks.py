"""
TCC Callback Handler for Python TCC Participant Method Execution.

This module provides the callback system that allows the Java subprocess bridge
to call back into Python to execute TCC participant methods (try, confirm, cancel).

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
from typing import Any, Callable, Dict, Optional, get_type_hints

logger = logging.getLogger(__name__)


class TccCallbackHandler:
    """
    HTTP-based callback handler for receiving TCC participant method calls from Java subprocess bridge.

    This handler starts a local HTTP server that the Java bridge can call
    to execute Python TCC participant methods (try, confirm, cancel).
    """

    def __init__(self, tcc_class: type, host: str = "localhost", port: int = 0):
        self.tcc_class = tcc_class
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._running = False

        # Create instance of TCC class for method-based participants
        self.tcc_instance = tcc_class()

        # Create instances of TCC participant classes (for class-based participants)
        self.participant_instances = {}
        tcc_config = getattr(tcc_class, "_tcc_config", None)
        if tcc_config:
            for participant_id, participant_config in tcc_config.participants.items():
                # Check if this is a class-based participant
                if participant_id in tcc_config.participant_classes:
                    participant_class = tcc_config.participant_classes[participant_id]
                    self.participant_instances[participant_id] = participant_class()

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

        logger.info(f"Starting TCC callback server on {self.host}:{self.port}")

        # Start server in background thread
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self._running = True

        # Wait a moment for server to start
        time.sleep(0.1)

        endpoint = self.get_callback_endpoint()
        logger.info(f"TCC callback server ready at: {endpoint}")
        return endpoint

    def stop(self):
        """Stop the callback server."""
        if not self._running:
            return

        logger.info("Stopping TCC callback server")

        if self.server:
            self.server.shutdown()
            self.server.server_close()

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)

        self.executor.shutdown(wait=True)
        self._running = False

    def get_callback_endpoint(self) -> str:
        """Get the callback endpoint URL."""
        return f"http://{self.host}:{self.port}/tcc-callback"

    def _create_request_handler(self):
        """Create the HTTP request handler class."""
        callback_handler = self

        class TccCallbackRequestHandler(BaseHTTPRequestHandler):

            def log_message(self, format, *args):
                # Suppress default HTTP server logging
                pass

            def do_POST(self):
                """Handle POST requests for TCC method execution callbacks."""
                try:
                    # Parse request
                    if self.path != "/tcc-callback":
                        self.send_error(404, "Not Found")
                        return

                    # Read request body
                    content_length = int(self.headers.get("Content-Length", 0))
                    request_body = self.rfile.read(content_length).decode("utf-8")

                    # Parse JSON request
                    request_data = json.loads(request_body)

                    # Execute callback
                    result = callback_handler._handle_tcc_callback(request_data)

                    # Send response
                    response_data = json.dumps(result).encode("utf-8")

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(response_data)))
                    self.end_headers()
                    self.wfile.write(response_data)

                except Exception as e:
                    logger.error(f"Error handling TCC callback request: {e}", exc_info=True)

                    # Send error response
                    error_response = json.dumps({"success": False, "error": str(e)}).encode("utf-8")

                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(error_response)))
                    self.end_headers()
                    self.wfile.write(error_response)

        return TccCallbackRequestHandler

    def _handle_tcc_callback(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a TCC callback request from Java."""
        try:
            phase = request_data.get("phase")  # "TRY", "CONFIRM", or "CANCEL"
            participant_id = request_data.get("participant_id")
            method_name = request_data.get("method_name")
            input_data = request_data.get("input_data", {})
            context_data = request_data.get("context_data", {})

            logger.info(
                f"Executing TCC callback: {phase} phase, participant '{participant_id}', method '{method_name}'"
            )

            # Get participant instance (class-based) or TCC instance (method-based)
            if participant_id in self.participant_instances:
                # Class-based participant
                participant_instance = self.participant_instances[participant_id]
            else:
                # Method-based participant - use TCC instance
                participant_instance = self.tcc_instance

            # Get the method to execute
            if not hasattr(participant_instance, method_name):
                raise AttributeError(
                    f"Method {method_name} not found in participant {participant_id}"
                )

            method = getattr(participant_instance, method_name)

            # Create context from context data
            from ..core.tcc_context import TccContext

            context = TccContext(
                correlation_id=context_data.get("correlation_id", "unknown"),
                tcc_name=context_data.get("tcc_name"),
            )

            # Execute method in thread pool to handle async methods
            future = self.executor.submit(self._execute_tcc_method, method, context, input_data, phase)
            result = future.result(timeout=30)  # 30 second timeout

            logger.info(f"TCC callback completed successfully: {method_name} ({phase})")

            return {
                "success": True,
                "result": result,
                "participant_id": participant_id,
                "method_name": method_name,
                "phase": phase,
            }

        except Exception as e:
            logger.error(f"TCC callback execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "participant_id": request_data.get("participant_id"),
                "method_name": request_data.get("method_name"),
                "phase": request_data.get("phase"),
            }

    def _execute_tcc_method(self, method: Callable, context, input_data: Any, phase: str) -> Any:
        """Execute a TCC method, handling both sync and async methods.

        STANDARD PATTERN with Pydantic support:
        - TRY: method(self, data: Model) - receives input data (dict or Pydantic model)
        - CONFIRM: method(self, data: Model, try_result: Model) - receives original data AND try result
        - CANCEL: method(self, data: Model, try_result: Model) - receives original data AND try result

        Supports:
        - Pydantic models (v1 and v2)
        - Dataclasses
        - Plain dicts
        """
        try:
            # For CONFIRM/CANCEL phases, extract data and try_result from input_data
            if phase in ("CONFIRM", "CANCEL") and isinstance(input_data, dict) and "data" in input_data:
                raw_data = input_data.get("data", {})
                raw_try_result = input_data.get("try_result", {})

                # Convert to Pydantic models if method expects them
                data = self._convert_input_to_type(method, raw_data, param_index=0)
                try_result = self._convert_input_to_type(method, raw_try_result, param_index=1)
            else:
                # TRY phase - input_data is just the data
                data = self._convert_input_to_type(method, input_data, param_index=0)
                try_result = None

            # Check if method is async
            if asyncio.iscoroutinefunction(method):
                # Run async method in new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if try_result is not None:
                        # CONFIRM/CANCEL: method(data, try_result)
                        result = loop.run_until_complete(method(data, try_result))
                    else:
                        # TRY: method(data)
                        result = loop.run_until_complete(method(data))
                finally:
                    loop.close()
            else:
                # Execute sync method directly
                if try_result is not None:
                    # CONFIRM/CANCEL: method(data, try_result)
                    result = method(data, try_result)
                else:
                    # TRY: method(data)
                    result = method(data)

            # Serialize result if it's a Pydantic model
            return self._serialize_result(result)

        except Exception as e:
            logger.error(f"TCC method execution failed: {e}")
            raise

    def _convert_input_to_type(self, method: Callable, input_data: Any, param_index: int = 0) -> Any:
        """
        Convert input_data to the expected type based on method signature.

        Supports:
        - Pydantic models (v1 and v2)
        - Dataclasses
        - Plain dicts

        Args:
            method: The method to inspect for type hints
            input_data: The input data (usually a dict from Java)
            param_index: Which parameter to check (0 for first param after self, 1 for second, etc.)

        Returns:
            Converted input data or original if no conversion needed
        """
        if not isinstance(input_data, dict):
            return input_data

        try:
            # Get the original function (unwrap if decorated)
            original_func = method
            while hasattr(original_func, '__wrapped__'):
                original_func = original_func.__wrapped__

            # Get type hints
            type_hints = get_type_hints(original_func)
            sig = inspect.signature(original_func)
            params = list(sig.parameters.values())

            # Skip 'self' parameter, get the parameter at param_index
            if len(params) <= param_index + 1:  # +1 for 'self'
                return input_data

            param_name = params[param_index + 1].name  # +1 to skip 'self'
            param_type = type_hints.get(param_name)

            if param_type is None or param_type == dict or param_type == Any:
                # No type hint or dict type - return as is
                return input_data

            logger.debug(f"🔄 [TCC] Converting input from dict to {param_type.__name__}")

            # Check if it's a Pydantic model
            if hasattr(param_type, 'model_validate'):
                # Pydantic v2
                logger.debug(f"✅ [TCC] Using Pydantic v2 model_validate")
                return param_type.model_validate(input_data)
            elif hasattr(param_type, 'parse_obj'):
                # Pydantic v1
                logger.debug(f"✅ [TCC] Using Pydantic v1 parse_obj")
                return param_type.parse_obj(input_data)
            elif hasattr(param_type, '__dataclass_fields__'):
                # Dataclass
                logger.debug(f"✅ [TCC] Using dataclass constructor")
                return param_type(**input_data)
            else:
                # Unknown type - return as is
                logger.debug(f"⚠️ [TCC] Unknown type, returning raw dict")
                return input_data

        except Exception as e:
            logger.warning(f"❌ [TCC] Failed to convert input to type: {e}. Using raw dict.")
            return input_data

    def _serialize_result(self, result: Any) -> Any:
        """
        Convert result to JSON-serializable format.

        Supports:
        - Pydantic models (v1 and v2)
        - Dataclasses
        - Plain dicts/lists/primitives

        Args:
            result: The result to serialize

        Returns:
            JSON-serializable dict or original value
        """
        if result is None:
            return None

        # Check if it's a Pydantic model
        if hasattr(result, 'model_dump'):
            # Pydantic v2
            logger.debug(f"🔄 [TCC] Serializing Pydantic v2 model to dict")
            return result.model_dump()
        elif hasattr(result, 'dict'):
            # Pydantic v1
            logger.debug(f"🔄 [TCC] Serializing Pydantic v1 model to dict")
            return result.dict()
        elif hasattr(result, '__dataclass_fields__'):
            # Dataclass
            import dataclasses
            logger.debug(f"🔄 [TCC] Serializing dataclass to dict")
            return dataclasses.asdict(result)
        else:
            # Already serializable (dict, list, str, int, etc.)
            return result
