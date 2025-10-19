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
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Engines    │  │  Decorators  │  │     Core     │      │
│  │ SagaEngine   │  │    @saga     │  │   Types &    │      │
│  │  TccEngine   │  │  @saga_step  │  │   Context    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Integration  │  │    Config    │  │    Events    │      │
│  │    Bridge    │  │  Management  │  │ Persistence  │      │
│  │  Callbacks   │  │              │  │   Logging    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
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

### 3. Decorator System (`fireflytx/decorators/`)

#### SAGA Decorators (`saga.py`)

**@saga(name, layer_concurrency)**

Marks a class as a SAGA transaction.

**Metadata Attached**:
```python
cls._saga_name = "payment-processing"
cls._saga_config = SagaConfig(
    name="payment-processing",
    layer_concurrency=5,
    steps={},
    compensation_methods={},
    compensation_configs={}
)
```

**@saga_step(step_id, depends_on, retry, timeout_ms, ...)**

Marks a method as a SAGA step.

**Metadata Attached**:
```python
func._saga_step_config = SagaStepConfig(
    step_id="validate",
    depends_on=["previous_step"],
    retry=3,
    backoff_ms=1000,
    timeout_ms=30000,
    jitter=True,
    jitter_factor=0.3,
    cpu_bound=False,
    idempotency_key=None,
    compensate="undo_validate",
    compensation_retry=3,
    compensation_timeout_ms=10000,
    compensation_critical=False,
    events=None
)
```

**@compensation_step(for_step_id, retry, timeout_ms, critical)**

Marks a method as a compensation step.

**Metadata Attached**:
```python
func._compensation_for_step = "validate"
func._compensation_config = CompensationStepConfig(
    for_step_id="validate",
    retry=3,
    timeout_ms=10000,
    critical=False,
    backoff_ms=1000,
    jitter=True,
    jitter_factor=0.3
)
```

#### TCC Decorators (`tcc.py`)

**@tcc(name, timeout_ms)**

Marks a class as a TCC transaction.

**Metadata Attached**:
```python
cls._tcc_name = "payment-processing"
cls._tcc_config = TccConfig(
    name="payment-processing",
    timeout_ms=30000,
    participants={},
    participant_classes={}
)
```

**@tcc_participant(participant_id, order, timeout_ms)**

Marks a nested class or method as a TCC participant.

**Metadata Attached**:
```python
cls._tcc_participant_config = TccParticipantConfig(
    participant_id="payment",
    order=1,
    timeout_ms=30000,
    try_method=None,
    confirm_method=None,
    cancel_method=None
)
```

**@try_method, @confirm_method, @cancel_method**

Mark methods for TCC phases.

**Metadata Attached**:
```python
func._tcc_method_config = TccMethodConfig(
    method_type="try",  # or "confirm", "cancel"
    timeout_ms=30000,
    retry=3,
    backoff_ms=1000
)
```

### 4. Core Types (`fireflytx/core/`)

#### SagaContext (`saga_context.py`)

Shared data container for SAGA execution.

```python
from fireflytx.core import SagaContext

context = SagaContext(correlation_id="saga-123")
context.set_data("user_id", "user-456")
context.set_data("order_total", 299.99)

# Access in steps
user_id = context.get_data("user_id")
```

#### SagaResult (`saga_result.py`)

Result of SAGA execution.

```python
@dataclass
class SagaResult:
    success: bool
    correlation_id: str
    step_results: Dict[str, Any]
    compensation_results: Dict[str, Any]
    error: Optional[str]
    failed_step: Optional[str]
```

#### TccResult (`tcc_result.py`)

Result of TCC execution.

```python
@dataclass
class TccResult:
    success: bool
    correlation_id: str
    final_phase: str  # "CONFIRMED" or "CANCELLED"
    participant_results: Dict[str, Any]
    error: Optional[str]
    failed_participant: Optional[str]
```

---

## Development Setup

### Prerequisites

- **Python**: 3.9+ (3.11+ recommended)
- **Java**: JDK 17+ (JDK 21 recommended)
- **Maven**: 3.8+ (for building Java bridge)
- **Git**: For version control

### Clone Repository

```bash
git clone https://github.com/firefly-oss/python-transactional-engine.git
cd python-transactional-engine
```

### Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Build Java Bridge (Optional)

The Java bridge JAR is pre-built and included in `fireflytx/integration/java_bridge/target/`. To rebuild:

```bash
cd fireflytx/integration/java_bridge
mvn clean package
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=fireflytx --cov-report=html

# Run specific test file
pytest tests/test_saga.py

# Run with verbose output
pytest -v -s
```

### Interactive Shell

```bash
# Launch FireflyTX shell
python -m fireflytx.shell

# Or use CLI
fireflytx shell
```

---

## Python-Java Integration


