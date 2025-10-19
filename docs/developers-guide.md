# FireflyTX Developers Guide

Purpose: This guide explains how the Python wrapper is designed over the real Java lib-transactional-engine. It covers architecture, data flow, key components, coding conventions, and how to extend and debug the system.

Date: 2025-10-19

## 1. Design Principles

- Python defines, Java executes: All business logic and configuration live in Python; orchestration and execution reliability runs in Java.
- No mocks or simulations: The runtime path integrates with the real lib-transactional-engine JAR. Examples may demonstrate business logic, but the engine path is real.
- Async-first in Python: SAGA steps are designed to support asyncio, with automatic handling from the callback server.
- Subprocess isolation: We avoid in-process embedding (e.g., JPype) and run Java as a managed subprocess for maximal compatibility and stability.
- Observability: Java logs are streamed into Python logging. Results are mapped into Pythonic objects.

## 2. High-Level Architecture

```
Python App                Python Wrapper                        Java Side
-----------              -------------------            ------------------------------
@saga / @tcc  --->  Config Generator (JSON)  --->  SagaEngine / TccEngine (JAR)
step methods     <--- HTTP Callback Server   <---  JavaSubprocessBridge (bridge JAR)

                                 ^
                                 | JSON over files (requests/responses) + HTTP callbacks
                                 v
                           JavaSubprocessBridge (Python)
```

Core components:
- fireflytx.decorators: Python decorators for SAGA/TCC definitions.
- fireflytx.config.java_config_generator: Converts Python definitions to Java-readable configuration.
- fireflytx.utils.java_subprocess_bridge: Starts the JVM as a subprocess, implements JSON file IPC to call Java classes/methods, and streams Java logs back to Python.
- fireflytx.callbacks: Lightweight HTTP server and registry that Java calls to execute Python methods for steps/compensations.
- fireflytx.api.saga_executor.SagaExecutionEngine: High-level API that brings it all together for SAGA. A similar path exists for TCC.

## 3. Process Lifecycle

1. Engine initialization
   - SagaExecutionEngine.initialize() -> JavaSubprocessBridge.start_jvm() builds/loads the lib-transactional-engine JAR if needed and starts the Java bridge main class.
   - The bridge prepares temp directories for request/response JSON files and starts log readers for stdout/stderr.
2. Saga/TCC registration
   - Python classes decorated with @saga or @tcc are registered. We build a complete definition (steps, compensations, dependencies, timings) and send it to Java via call_java_method().
3. Execution
   - For SAGA: execute_saga() creates a request which Java executes. When Java needs to run a Python step, it POSTs to the callback HTTP endpoint with method metadata.
   - For TCC: Java orchestrates TRY/CONFIRM/CANCEL phases and calls back to Python participant methods in order.
4. Results
   - Java returns a structured map of the execution outcome. Python maps it to SagaResult/TccResult with duration, failed/compensated steps, etc.
5. Shutdown
   - The bridge terminates the Java subprocess, joins reader threads, and cleans resources.

## 4. Subprocess Bridge (Python)

Module: fireflytx/utils/java_subprocess_bridge.py

Responsibilities:
- Build or locate the lib-transactional-engine JAR from GitHub using JarBuilder when needed.
- Start the Java bridge JAR (java_bridge/java-subprocess-bridge.jar) with a classpath including the real engine.
- Create a temp directory with requests/ and responses/ folders for IPC.
- Expose call_java_method() to send method invocation requests and wait for responses with timeouts.
- Stream Java stdout/stderr into a dedicated logger fireflytx.java and provide helper APIs: set_java_log_level, get_java_logs, follow_java_logs, enable_java_log_file.

Key data structures:
- JavaClassCallRequest/Response: simple dataclasses that carry the call metadata and results.

## 5. Java Bridge (JAR)

Location: fireflytx/java_bridge/src/main/java/com/firefly/transactional/

Responsibilities:
- Main entry point JavaSubprocessBridge: reads JSON requests from the temp folder, performs reflection-based calls, manages Java instances, and writes JSON responses.
- Integrates with SagaEngine/TccEngine of the real lib-transactional-engine.
- Performs HTTP callbacks back to Python for method executions during orchestration.
- Performs topological ordering (SAGA) and proper two-phase flow (TCC) based on definitions received from Python.

Logging:
- Prints informative lines to stdout/stderr which are captured by the Python side and re-emitted into Python logging.

## 6. Python Callback Server

Module: fireflytx/utils/python_callback_handler.py

- A small HTTP server per registered class exposes /callback.
- Receives POST payloads of the form: method_type, method_name, step_id, input_data, context_data.
- Executes the requested Python method (async or sync supported).
- Returns { success, result, step_id, method_name } or an error payload.

Threading/async notes:
- Async methods run in a dedicated event loop within a thread pool so we can safely call into coroutine functions from the HTTP handler thread.

## 7. Configuration Generator

Module: fireflytx/config/java_config_generator.py

- Extracts decorator metadata and produces a comprehensive structure usable by the Java engine.
- Maps step IDs to Python method names, includes timing/retry settings, events, and compensation method mappings.
- Produces engine-level config (event publishers, persistence providers) and per-saga details.

## 8. Observability and Logs

- All Java engine logs are streamed to logger name fireflytx.java.
- Use environment variable FIREFLYTX_JAVA_LOG_LEVEL to set initial verbosity.
- Programmatic APIs allow tailing or teeing logs to a file for operations.

## 9. Testing Strategy

- Unit tests focus on Python decorator behavior, configuration generation, and utility functions.
- Integration tests run against the real lib-transactional-engine via the subprocess bridge. No mock engine is used in integration tests.
- Examples demonstrate business logic patterns in Python; they are not substitutes for engine execution.

## 10. Extending the Wrapper

- Adding new engine capabilities: create Python-side configuration fields and map them into java_config_generator.py; extend Java bridge handlers as needed.
- Adding new decorators: follow existing patterns in fireflytx.decorators; include metadata extraction and integration with the config generator.
- CLI: fireflytx/cli.py offers administrative commands; keep them decoupled from runtime concerns.

## 11. Coding Conventions

- Keep Java-facing payloads simple (dicts with primitive values) to minimize serialization risk.
- Avoid tight coupling to Java types; perform mapping at the boundaries.
- Maintain strict separation: Python business logic vs Java orchestration.

## 12. Troubleshooting

- If Java fails to start, confirm Java 11+ is installed and accessible in PATH.
- Use get_java_logs() and follow_java_logs() to inspect Java engine output.
- If callbacks fail, check that the PythonCallbackHandler is running and the endpoint URL matches.

## 13. Security Considerations

- The callback server binds to localhost by default; if exposing externally, ensure proper network controls.
- Treat callback payloads as trusted within the application boundary; do not accept arbitrary external traffic.

## 14. Roadmap Notes

- Additional CLI commands for direct log following may be added. The runtime path already supports real-time log streaming programmatically.

This guide reflects the current, real integration design. For a big-picture overview, also read docs/architecture.md and the top-level README sections on Architecture and Java Logging Integration.


## Appendix: Directory and Module Map

For a quick, feature-oriented overview of where things live, see docs/project-structure.md. Highlights:

- High-level API: fireflytx/api/saga_executor.py
- Engine wrappers: fireflytx/engine/saga_engine.py, fireflytx/engine/tcc_engine.py
- Decorators: fireflytx/decorators/
- Core types: fireflytx/core/
- Java integration bridge (Python): fireflytx/utils/java_subprocess_bridge.py
- Python callback HTTP server: fireflytx/callbacks/
- Java bridge sources (JAR main class): fireflytx/java_bridge/src/main/java/com/firefly/transactional/
- Config generator: fireflytx/config/java_config_generator.py
- Events: fireflytx/events/
- Persistence: fireflytx/persistence/
- Logging: fireflytx/logging/
- CLI: fireflytx/cli.py
