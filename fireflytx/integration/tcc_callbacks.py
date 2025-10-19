"""
TCC Callback Handler for Python TCC Participant Method Execution.

This module provides the callback system that allows the Java subprocess bridge
to call back into Python to execute TCC participant methods (try, confirm, cancel).

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0.
"""

import asyncio
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Optional

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
            future = self.executor.submit(self._execute_tcc_method, method, context, input_data)
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

    def _execute_tcc_method(self, method: Callable, context, input_data: Any) -> Any:
        """Execute a TCC method, handling both sync and async methods.

        Supports two patterns:
        1. Class-based: method(self, context, input_data) - uses @try_method, @confirm_method decorators
        2. Method-based: method(self, **input_data) - uses @tcc_participant on method directly
        """
        try:
            # Detect method signature - unwrap decorators first
            import inspect
            original_func = method
            while hasattr(original_func, '__wrapped__'):
                original_func = original_func.__wrapped__

            sig = inspect.signature(original_func)
            params = list(sig.parameters.values())

            # Class-based pattern: (self, context, input_data) = 3 params
            # Method-based pattern: (self, amount, ...) = 2+ params
            # If method has 3+ params and second param is named 'context', use class-based pattern
            uses_context = len(params) >= 3 and params[1].name == 'context'

            # Check if method is async
            if asyncio.iscoroutinefunction(method):
                # Run async method in new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if uses_context:
                        # Class-based pattern: method(context, input_data)
                        result = loop.run_until_complete(method(context, input_data))
                    else:
                        # Method-based pattern: method(**input_data)
                        if isinstance(input_data, dict):
                            result = loop.run_until_complete(method(**input_data))
                        else:
                            result = loop.run_until_complete(method(input_data))
                finally:
                    loop.close()
            else:
                # Execute sync method directly
                if uses_context:
                    # Class-based pattern: method(context, input_data)
                    result = method(context, input_data)
                else:
                    # Method-based pattern: method(**input_data)
                    if isinstance(input_data, dict):
                        result = method(**input_data)
                    else:
                        result = method(input_data)

            return result

        except Exception as e:
            logger.error(f"TCC method execution failed: {e}")
            raise
