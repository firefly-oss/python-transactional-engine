# FireflyTX Developers Guide

> **🎯 Complete technical reference for FireflyTX contributors and advanced users**

**Last Updated:** 2025-10-19

---

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Core Components](#core-components)
4. [Development Setup](#development-setup)
5. [Python-Java Integration](#python-java-integration)
6. [Engine Internals](#engine-internals)
7. [Decorator System](#decorator-system)
8. [Testing & Debugging](#testing--debugging)
9. [Contributing Guidelines](#contributing-guidelines)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

### What is FireflyTX?

FireflyTX is a **Python wrapper** for the enterprise-grade Java library `lib-transactional-engine`, enabling distributed transaction patterns (SAGA and TCC) in Python applications with genuine Java execution.

### Core Architectural Principle

**"Python defines, Java executes"**

- **Python**: Provides decorators, API, business logic, and developer experience
- **Java**: Handles orchestration, retry, compensation, persistence, and transaction management
- **Communication**: Subprocess IPC via JSON files + HTTP callbacks

### Key Design Goals

1. **Zero Mocks**: Real `lib-transactional-engine` integration, not simulations
2. **Type Safety**: Comprehensive Pydantic models and type hints
3. **Developer Experience**: Pythonic API with async/await support
4. **Production Ready**: Battle-tested Java engine with enterprise features
5. **Extensibility**: Pluggable events, persistence, and configuration

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Python Application Layer                   │
│  • Business Logic (async/await)                             │
│  • @saga, @saga_step, @tcc, @tcc_participant decorators     │
│  • SagaEngine.execute() / TccEngine.execute()               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  FireflyTX Python Package                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Engines    │  │  Decorators  │  │     Core     │       │
│  │ SagaEngine   │  │    @saga     │  │   Types &    │       │
│  │  TccEngine   │  │  @saga_step  │  │   Context    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Integration  │  │    Config    │  │    Events    │       │
│  │    Bridge    │  │  Management  │  │ Persistence  │       │
│  │  Callbacks   │  │              │  │   Logging    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼ IPC (JSON files + HTTP)
┌─────────────────────────────────────────────────────────────┐
│              Java Subprocess (Separate JVM)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         lib-transactional-engine (Spring Boot)       │   │
│  │  • SagaEngine (orchestration, retry, compensation)   │   │
│  │  • TccEngine (Try-Confirm-Cancel coordination)       │   │
│  │  • Reactive execution (Project Reactor)              │   │
│  │  • Persistence & recovery                            │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         JavaSubprocessBridge (IPC Handler)           │   │
│  │  • Polls request directory for JSON files            │   │
│  │  • Executes Java methods via reflection              │   │
│  │  • Writes responses to response directory            │   │
│  │  • Makes HTTP callbacks to Python for business logic │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Communication Flow

**1. Python → Java (Method Calls)**
```
Python                          Java
  │                              │
  ├─ Write request.json ────────>│
  │  {requestId, className,      │
  │   methodName, args}          │
  │                              ├─ Poll requests/
  │                              ├─ Read request.json
  │                              ├─ Execute method
  │                              ├─ Write response.json
  │<──── Read response.json ─────┤
  │  {success, result}           │
```

**2. Java → Python (Callbacks)**
```
Java                            Python
  │                              │
  ├─ HTTP POST /callback ───────>│
  │  {method_name, step_id,      │
  │   input_data, context_data}  │
  │                              ├─ Execute Python method
  │                              ├─ Return result
  │<──── HTTP 200 OK ────────────┤
  │  {success, result,           │
  │   context_updates}           │
```

---

## Core Components

### 1. Engine Layer (`fireflytx/engine/`)

#### SagaEngine

**Purpose**: Python wrapper for `lib-transactional-engine` SagaEngine

**Lifecycle**:
```python
from fireflytx import SagaEngine

# 1. Create engine
engine = SagaEngine(
    compensation_policy="STRICT_SEQUENTIAL",
    auto_optimization_enabled=True,
    java_bridge=None  # Creates new bridge if not provided
)

# 2. Initialize (starts Java subprocess)
await engine.initialize()

# 3. Execute SAGAs
result = await engine.execute(MySaga, input_data, context)

# 4. Shutdown
await engine.shutdown()
```

**Key Methods**:
- `__init__()`: Configure engine (compensation policy, persistence, events)
- `initialize()`: Start Java subprocess bridge, create Java SagaEngine instance
- `execute(saga_class, step_inputs, context)`: Execute SAGA with Java orchestration
- `register_saga(saga_class)`: Register SAGA definition with Java engine
- `shutdown()`: Stop Java subprocess and cleanup resources

**Internal Flow**:
1. `execute()` calls `register_saga()` to send SAGA definition to Java
2. Java engine validates and stores SAGA structure
3. `execute()` calls Java `SagaEngine.execute()` via IPC
4. Java orchestrates execution, making HTTP callbacks to Python for each step
5. Python executes business logic and returns results
6. Java handles retry, compensation, and persistence
7. Final `SagaResult` returned to Python

#### TccEngine

**Purpose**: Python wrapper for TCC pattern execution

**Lifecycle**:
```python
from fireflytx import TccEngine

# 1. Create engine
engine = TccEngine(
    timeout_ms=30000,
    enable_monitoring=True,
    java_bridge=None
)

# 2. Start (initializes Java subprocess)
engine.start()

# 3. Execute TCC transactions
result = await engine.execute(MyTcc, input_data, correlation_id)

# 4. Stop
engine.stop()
```

**Key Differences from SagaEngine**:
- Uses `start()` instead of `initialize()` (synchronous)
- Uses `stop()` instead of `shutdown()`
- TCC execution is synchronous (blocking)
- Three-phase protocol: Try → Confirm/Cancel

### 2. Integration Layer (`fireflytx/integration/`)

#### JavaSubprocessBridge (`bridge.py`)

**Purpose**: Manages Java subprocess and IPC communication

**Initialization**:
```python
from fireflytx.integration import JavaSubprocessBridge

bridge = JavaSubprocessBridge()
bridge.start_jvm(config=jvm_config)
```

**Key Responsibilities**:
1. **JAR Management**: Locates `lib-transactional-engine` JARs in `fireflytx/deps/`
2. **Process Management**: Starts Java subprocess with Spring Boot application
3. **IPC Communication**: JSON file-based request/response
4. **Callback Server**: Manages HTTP callback handlers for Java → Python calls
5. **Lifecycle**: Handles startup, shutdown, and error recovery

**IPC Mechanism**:
- **Request Directory**: `{temp_dir}/requests/` - Python writes, Java reads
- **Response Directory**: `{temp_dir}/responses/` - Java writes, Python reads
- **Polling**: Java polls requests directory every 100ms
- **Timeout**: Python waits up to 30 seconds for response

**Java Process Startup**:
```bash
java -Xmx2g -Xms512m \
  -Djava.awt.headless=true \
  -cp "fireflytx/deps/*" \
  com.firefly.transactional.BridgeApplication \
  /tmp/fireflytx_bridge_XXXXX
```

#### PythonCallbackHandler (`callbacks.py`)

**Purpose**: HTTP server for Java → Python callbacks (SAGA)

**Implementation**:
```python
from fireflytx.integration.callbacks import PythonCallbackHandler

handler = PythonCallbackHandler(
    saga_instance=my_saga,
    saga_config=saga_config,
    port=8765
)
handler.start()  # Starts Flask server in background thread
```

**Callback Request Format**:
```json
{
  "method_type": "STEP",
  "method_name": "validate_payment",
  "step_id": "validate",
  "input_data": {"order_id": "123"},
  "context_data": {
    "correlation_id": "saga-uuid",
    "step_id": "validate",
    "variables": {"previous_step_result": "..."}
  }
}
```

**Callback Response Format**:
```json
{
  "success": true,
  "result": {"validated": true, "amount": 100.0},
  "context_updates": {
    "correlation_id": "saga-uuid",
    "variables": {"validate_result": "..."}
  }
}
```

#### TccCallbackHandler (`tcc_callbacks.py`)

**Purpose**: HTTP server for Java → Python callbacks (TCC)

**TCC Callback Request Format**:
```json
{
  "phase": "TRY",
  "participant_id": "payment",
  "method_name": "try_payment",
  "input_data": {"amount": 100.0},
  "context_data": {"correlation_id": "tcc-uuid"}
}
```

---

## Python-Java Integration

### IPC Architecture

FireflyTX uses a **dual-channel communication** model:

1. **Python → Java**: JSON file-based IPC (synchronous)
2. **Java → Python**: HTTP callbacks (asynchronous)

### Request/Response Flow

**Python Side** (`fireflytx/integration/bridge.py`):

```python
def call_java_method(self, request: JavaClassCallRequest) -> JavaMethodResponse:
    # 1. Generate unique request ID
    request_id = str(uuid.uuid4())

    # 2. Write request to JSON file
    request_file = Path(self._temp_dir) / "requests" / f"{request_id}.json"
    with open(request_file, "w") as f:
        json.dump({
            "requestId": request_id,
            "className": request.class_name,
            "methodName": request.method_name,
            "methodType": request.method_type,
            "args": request.args,
            "instanceId": request.instance_id
        }, f)

    # 3. Poll for response (timeout: 30s)
    response_file = Path(self._temp_dir) / "responses" / f"{request_id}.json"
    start_time = time.time()
    while time.time() - start_time < 30:
        if response_file.exists():
            with open(response_file, "r") as f:
                response_data = json.load(f)
            response_file.unlink()  # Delete response file
            return JavaMethodResponse(
                success=response_data["success"],
                result=response_data.get("result"),
                error=response_data.get("error"),
                instance_id=response_data.get("instanceId")
            )
        time.sleep(0.1)

    raise TimeoutError(f"No response for request {request_id}")
```

**Java Side** (`fireflytx/integration/java_bridge/src/main/java/.../JavaSubprocessBridge.java`):

```java
public void startProcessing() {
    while (running) {
        try {
            processRequests();
            Thread.sleep(100); // Poll every 100ms
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            break;
        }
    }
}

private void processRequests() throws IOException {
    File[] requestFiles = requestDir.toFile().listFiles(
        (dir, name) -> name.endsWith(".json")
    );

    for (File requestFile : requestFiles) {
        // 1. Read request
        String content = Files.readString(requestFile.toPath());
        JsonNode request = objectMapper.readTree(content);

        String requestId = request.get("requestId").asText();
        String className = request.get("className").asText();
        String methodName = request.get("methodName").asText();

        // 2. Execute method via reflection
        Object result = executeMethod(className, methodName, ...);

        // 3. Write response
        sendSuccessResponse(requestId, result, instanceId);

        // 4. Delete request file
        requestFile.delete();
    }
}
```

### Callback Mechanism

**Java → Python Callback** (for SAGA step execution):

**Java Side** (`ReactiveCallbackClient.java`):

```java
public Mono<Map<String, Object>> executeCallbackReactive(
    String callbackUrl,
    String methodType,
    String methodName,
    String stepId,
    Map<String, Object> inputData,
    Map<String, Object> contextData
) {
    Map<String, Object> callbackRequest = new HashMap<>();
    callbackRequest.put("method_type", methodType);
    callbackRequest.put("method_name", methodName);
    callbackRequest.put("step_id", stepId);
    callbackRequest.put("input_data", inputData);
    callbackRequest.put("context_data", contextData);

    return webClient.post()
        .uri(callbackUrl)
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(callbackRequest)
        .retrieve()
        .bodyToMono(Map.class);
}
```

**Python Side** (`callbacks.py`):

```python
@app.route("/callback", methods=["POST"])
def handle_callback():
    data = request.json
    method_name = data["method_name"]
    step_id = data["step_id"]
    input_data = data["input_data"]
    context_data = data["context_data"]

    # Find and execute Python method
    step_method = getattr(saga_instance, method_name)

    # Reconstruct context
    context = SagaContext(context_data["correlation_id"])
    for key, value in context_data.get("variables", {}).items():
        context.set_data(key, value)

    # Execute step
    if asyncio.iscoroutinefunction(step_method):
        result = asyncio.run(step_method(context, input_data))
    else:
        result = step_method(context, input_data)

    return jsonify({
        "success": True,
        "result": result,
        "context_updates": context.to_dict()
    })
```

---

## Engine Internals

### SagaEngine Execution Flow

```
1. Python: engine.execute(MySaga, input_data)
   │
   ├─> 2. Python: register_saga(MySaga)
   │    │
   │    ├─> Extract metadata from decorators
   │    ├─> Build registration_data dict
   │    └─> IPC call: SagaEngine.registerSaga(name, registration_data)
   │
   ├─> 3. Java: SagaEngine.registerSaga()
   │    │
   │    ├─> Validate SAGA structure
   │    ├─> Create SagaDefinition
   │    └─> Store in registry
   │
   ├─> 4. Python: Start callback server
   │    │
   │    └─> PythonCallbackHandler.start() on port 8765
   │
   ├─> 5. Python: IPC call: SagaEngine.execute(name, inputs, context)
   │    │
   │    └─> Pass callback_url: http://localhost:8765/callback
   │
   ├─> 6. Java: SagaEngine.execute()
   │    │
   │    ├─> Build execution DAG from dependencies
   │    ├─> Execute steps in topological order
   │    │
   │    └─> For each step:
   │         │
   │         ├─> 7. Java: HTTP POST to callback_url
   │         │    │
   │         │    └─> {method_name, step_id, input_data, context_data}
   │         │
   │         ├─> 8. Python: Execute business logic
   │         │    │
   │         │    └─> Return {success, result, context_updates}
   │         │
   │         ├─> 9. Java: Handle result
   │         │    │
   │         │    ├─> If success: Continue to next step
   │         │    └─> If failure: Trigger compensation
   │         │
   │         └─> Retry logic, timeout handling
   │
   ├─> 10. Java: Return SagaResult
   │
   └─> 11. Python: Return SagaResult to caller
```

### TccEngine Execution Flow

```
1. Python: engine.execute(MyTcc, input_data)
   │
   ├─> 2. Python: Extract TCC definition from decorators
   │    │
   │    └─> Build participant list with try/confirm/cancel methods
   │
   ├─> 3. Python: Start TCC callback server
   │    │
   │    └─> TccCallbackHandler.start() on port 8766
   │
   ├─> 4. Python: IPC call: executeTcc(name, inputs, callback_info)
   │    │
   │    └─> Pass callback_endpoint: http://localhost:8766/tcc_callback
   │
   ├─> 5. Java: Execute TRY phase
   │    │
   │    └─> For each participant (in order):
   │         │
   │         ├─> HTTP POST to callback_endpoint
   │         │    {phase: "TRY", participant_id, method_name, input_data}
   │         │
   │         ├─> Python: Execute try_method
   │         │
   │         └─> If any fails: Go to CANCEL phase
   │
   ├─> 6. Java: Execute CONFIRM or CANCEL phase
   │    │
   │    └─> For each participant (reverse order for CANCEL):
   │         │
   │         ├─> HTTP POST to callback_endpoint
   │         │    {phase: "CONFIRM"/"CANCEL", participant_id, method_name}
   │         │
   │         └─> Python: Execute confirm_method or cancel_method
   │
   └─> 7. Java: Return TccResult
        │
        └─> Python: Return TccResult to caller
```

---

## Decorator System

### How Decorators Work

Decorators attach metadata to classes and methods that is later extracted by the engine.

**Example SAGA**:

```python
@saga("payment-processing")
class PaymentSaga:

    @saga_step("validate", retry=3, timeout_ms=5000)
    async def validate_payment(self, ctx, input_data):
        return {"validated": True}

    @saga_step("charge", depends_on=["validate"], compensate="refund")
    async def charge_payment(self, ctx, input_data):
        return {"charged": True, "tx_id": "123"}

    @compensation_step("charge", critical=True)
    async def refund(self, ctx, charge_result):
        # Refund logic
        pass
```

**Metadata Extraction**:

```python
# After decoration, the class has:
PaymentSaga._saga_name = "payment-processing"
PaymentSaga._saga_config = SagaConfig(
    name="payment-processing",
    layer_concurrency=5,
    steps={
        "validate": SagaStepConfig(
            step_id="validate",
            depends_on=[],
            retry=3,
            timeout_ms=5000,
            ...
        ),
        "charge": SagaStepConfig(
            step_id="charge",
            depends_on=["validate"],
            compensate="refund",
            ...
        )
    },
    compensation_methods={
        "charge": "refund"
    },
    compensation_configs={
        "charge": CompensationStepConfig(
            for_step_id="charge",
            critical=True,
            ...
        )
    }
)
```

**Registration with Java**:

```python
async def register_saga(self, saga_class: type) -> None:
    config = saga_class._saga_config

    registration_data = {
        "name": config.name,
        "layerConcurrency": config.layer_concurrency,
        "steps": [
            {
                "stepId": step.step_id,
                "dependsOn": step.depends_on,
                "retry": step.retry,
                "backoffMs": step.backoff_ms,
                "timeoutMs": step.timeout_ms,
                "compensate": step.compensate,
                "compensationRetry": step.compensation_retry,
                "compensationTimeoutMs": step.compensation_timeout_ms,
                "compensationCritical": step.compensation_critical,
                ...
            }
            for step in config.steps.values()
        ]
    }

    # Send to Java
    response = self._java_bridge.call_java_method(
        JavaClassCallRequest(
            class_name="com.firefly.transactional.saga.engine.SagaEngine",
            method_name="registerSaga",
            method_type="instance",
            instance_id=self._saga_engine_id,
            args=[config.name, registration_data]
        )
    )
```

---

## Testing & Debugging

### Unit Testing

```python
import pytest
from fireflytx import SagaEngine
from fireflytx.decorators import saga, saga_step

@saga("test-saga")
class TestSaga:
    @saga_step("step1")
    async def step1(self, ctx, input_data):
        return {"result": "step1"}

@pytest.mark.asyncio
async def test_saga_execution():
    engine = SagaEngine()
    await engine.initialize()

    try:
        result = await engine.execute(TestSaga, {"input": "test"})
        assert result.success
        assert "step1" in result.step_results
    finally:
        await engine.shutdown()
```

### Debugging Java Subprocess

**Enable Java Debug Logging**:

```python
from fireflytx.config import JvmConfig, EngineConfig

jvm_config = JvmConfig(
    heap_size="2g",
    enable_gc_logging=True,
    gc_log_file="/tmp/fireflytx_gc.log",
    additional_args=[
        "-Dlogging.level.com.firefly=DEBUG",
        "-Dlogging.level.root=INFO"
    ]
)

engine = SagaEngine(config=EngineConfig(jvm=jvm_config))
```

**View Java Logs**:

```bash
# Logs are streamed to Python logger
tail -f /tmp/fireflytx_java.log

# Or use shell
python -m fireflytx.shell
> java-logs
```

### Interactive Shell

```bash
python -m fireflytx.shell
```

**Available Commands**:
- `init-engines` - Initialize SAGA and TCC engines
- `run-saga-example` - Run example SAGA
- `run-tcc-example` - Run example TCC
- `java-logs` - View Java subprocess logs
- `process-info` - Show Java process information
- `help` - Show all commands

---

## Contributing Guidelines

### Code Style

- **Python**: Follow PEP 8, use `black` for formatting
- **Type Hints**: Required for all public APIs
- **Docstrings**: Google style for all public functions/classes
- **Java**: Follow Google Java Style Guide

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes with tests
4. Run tests: `pytest`
5. Run linters: `black . && flake8 && mypy fireflytx`
6. Commit with conventional commits: `feat: add new feature`
7. Push and create PR

### Testing Requirements

- Unit tests for all new features
- Integration tests for engine changes
- Minimum 80% code coverage
- All tests must pass in CI

---

## Troubleshooting

### Common Issues

**1. Java subprocess fails to start**

```
Error: Java process exited immediately
```

**Solution**: Check Java version and classpath
```bash
java -version  # Should be 17+
ls fireflytx/deps/*.jar  # Should contain lib-transactional-engine JARs
```

**2. Callback connection refused**

```
Error: Connection refused to http://localhost:8765/callback
```

**Solution**: Ensure callback server started
```python
# Check if handler is running
if handler and handler.is_running():
    print("Callback server running")
```

**3. IPC timeout**

```
TimeoutError: No response for request abc-123
```

**Solution**: Check Java process is alive
```python
if bridge.process and bridge.process.poll() is None:
    print("Java process running")
else:
    print("Java process died - check logs")
```

### Debug Checklist

- [ ] Java 17+ installed
- [ ] All JARs present in `fireflytx/deps/`
- [ ] Python 3.9+ with all dependencies
- [ ] No port conflicts (8765, 8766)
- [ ] Sufficient memory (2GB+ heap)
- [ ] Check Java logs for errors
- [ ] Verify decorator metadata attached correctly

---

## Module Reference

### Directory Structure

```
fireflytx/
├── __init__.py              # Public API exports
├── cli.py                   # CLI entrypoint
│
├── engine/                  # Engine wrappers
│   ├── saga_engine.py       # SagaEngine
│   └── tcc_engine.py        # TccEngine
│
├── decorators/              # Decorators
│   ├── saga.py              # @saga, @saga_step, @compensation_step
│   └── tcc.py               # @tcc, @tcc_participant, @try_method, etc.
│
├── core/                    # Core types
│   ├── saga_context.py      # SagaContext
│   ├── saga_result.py       # SagaResult
│   ├── step_inputs.py       # StepInputs
│   ├── tcc_context.py       # TccContext
│   ├── tcc_inputs.py        # TccInputs
│   └── tcc_result.py        # TccResult
│
├── integration/             # Python-Java bridge
│   ├── bridge.py            # JavaSubprocessBridge
│   ├── callbacks.py         # PythonCallbackHandler (SAGA)
│   ├── tcc_callbacks.py     # TccCallbackHandler (TCC)
│   ├── type_conversion.py   # TypeConverter
│   ├── jar_builder.py       # JAR building utilities
│   └── java_bridge/         # Java source code
│       ├── src/main/java/com/firefly/transactional/
│       │   ├── BridgeApplication.java
│       │   ├── JavaSubprocessBridge.java
│       │   └── ReactiveCallbackClient.java
│       └── pom.xml
│
├── config/                  # Configuration
│   ├── engine_config.py     # EngineConfig, JvmConfig, etc.
│   ├── event_config.py      # EventConfig
│   ├── persistence_config.py # PersistenceConfig
│   └── java_config_generator.py # Python → Java config
│
├── events/                  # Event publishing
│   ├── event_publisher.py   # StepEventPublisher interface
│   ├── saga_events.py       # SAGA event types
│   └── tcc_events.py        # TCC event types
│
├── persistence/             # State persistence
│   ├── saga_persistence.py  # SagaPersistenceProvider
│   └── tcc_persistence.py   # TccPersistenceProvider
│
├── logging/                 # Logging
│   ├── manager.py           # Logging manager
│   ├── json_formatter.py    # JSON log formatting
│   ├── log_viewer.py        # Rich log viewer
│   └── java_log_bridge.py   # Java log integration
│
├── visualization/           # Graph rendering
│   ├── graph_renderer.py    # Graph rendering utilities
│   ├── saga_visualizer.py   # SAGA visualization
│   └── tcc_visualizer.py    # TCC visualization
│
├── shell/                   # Interactive shell
│   ├── __main__.py          # Shell entry point
│   ├── commands/            # Shell commands
│   ├── core/                # Shell core
│   ├── ui/                  # Shell UI components
│   └── utils/               # Shell utilities
│
├── utils/                   # Utilities
│   ├── dependency_installer.py # Auto-install dependencies
│   ├── helpers.py           # General helpers
│   └── logging.py           # Logging utilities
│
├── deps/                    # Java JAR dependencies
│   └── *.jar                # lib-transactional-engine JARs
│
├── internal/                # Internal implementation details
│   └── engine/              # Re-exports engines for public API
│
└── callbacks/               # Legacy (deprecated)
    └── __init__.py
```

---

**For more information**:
- [Architecture Guide](architecture.md)
- [SAGA Pattern Guide](saga-pattern.md)
- [TCC Pattern Guide](tcc-pattern.md)
- [API Reference](api-reference.md)
- [Project Structure](project-structure.md)

