# Project Structure Guide

> **📁 Navigate the codebase:** Understand where everything lives and how it all fits together.

**Last Updated:** 2025-10-19

---

## Table of Contents

1. [Overview](#overview)
2. [Repository Layout](#repository-layout)
3. [Core Package Structure](#core-package-structure)
4. [Module Responsibilities](#module-responsibilities)
5. [Execution Flow](#execution-flow)
6. [Finding What You Need](#finding-what-you-need)
7. [Design Principles](#design-principles)

---

## Overview

FireflyTX follows a **feature-oriented architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Python Application                  │
│                                                             │
│  Uses: @saga, @saga_step, @tcc, @tcc_participant decorators │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      FireflyTX Package                      │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   API    │  │ Engines  │  │  Config  │  │   Core   │     │
│  │ (Facade) │  │ (Wrapper)│  │(Settings)│  │  (Types) │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │Integration  │  Events  │  │Persistence  │ Logging  │     │
│  │(Java IPC)   │(Observ.) │  │ (State)  │  │(Monitor) │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Java lib-transactional-engine                │
│         Real enterprise-grade transaction processing        │
└─────────────────────────────────────────────────────────────┘
```

**Key Principle:** "Python defines, Java executes"
- Python provides the API, decorators, and business logic
- Java handles orchestration, retry, compensation, and transaction management

---

## Repository Layout

### Top-Level Structure

```
python-transactional-engine/
├── fireflytx/              # Core Python package (runtime code)
│   ├── api/                # High-level API facade
│   ├── core/               # Core types and contexts
│   ├── decorators/         # @saga, @tcc decorators
│   ├── engine/             # Engine wrappers
│   ├── integration/        # Python-Java bridge (NEW!)
│   ├── config/             # Configuration management
│   ├── events/             # Event publishing
│   ├── persistence/        # State persistence
│   ├── logging/            # Logging infrastructure
│   ├── visualization/      # Graph rendering
│   ├── utils/              # Utilities
│   └── cli.py              # CLI entrypoint
│
├── docs/                   # Documentation
│   ├── architecture.md     # System architecture
│   ├── saga-pattern.md     # SAGA pattern guide
│   ├── tcc-pattern.md      # TCC pattern guide
│   ├── configuration.md    # Configuration guide
│   ├── developers-guide.md # Developer documentation
│   └── project-structure.md # This file
│
├── tests/                  # Test suite
│   ├── test_saga.py        # SAGA tests
│   ├── test_tcc.py         # TCC tests
│   ├── test_integration.py # Integration tests
│   └── test_utils.py       # Utility tests
│
├── examples/               # Example applications
│   ├── saga/               # SAGA examples
│   ├── tcc/                # TCC examples
│   └── advanced/           # Advanced patterns
│
├── README.md               # Project overview
├── INSTALL.md              # Installation guide
├── pyproject.toml          # Python project config
├── Taskfile.yml            # Developer automation
└── .github/                # GitHub workflows
```

---

## Core Package Structure

### Detailed Module Breakdown

```
fireflytx/
│
├── __init__.py             # Public API exports
│
├── api/                    # 🎯 High-Level API (Start Here!)
│   ├── __init__.py
│   └── saga_executor.py    # SagaExecutionEngine, create_saga_engine()
│
├── core/                   # 📦 Core Types & Contexts
│   ├── __init__.py
│   ├── saga_context.py     # SagaContext (shared data between steps)
│   ├── saga_result.py      # SagaResult (execution results)
│   ├── step_inputs.py      # StepInputs (input helpers)
│   ├── tcc_context.py      # TccContext (TCC shared data)
│   ├── tcc_inputs.py       # TccInputs (TCC input helpers)
│   └── tcc_result.py       # TccResult (TCC execution results)
│
├── decorators/             # 🎨 Decorators (Define Transactions)
│   ├── __init__.py
│   ├── saga.py             # @saga, @saga_step, @compensation_step
│   └── tcc.py              # @tcc, @tcc_participant, @try_method, etc.
│
├── engine/                 # ⚙️ Engine Wrappers
│   ├── __init__.py
│   ├── saga_engine.py      # SagaEngine (full-featured SAGA wrapper)
│   └── tcc_engine.py       # TccEngine (full-featured TCC wrapper)
│
├── integration/            # 🔌 Python-Java Integration (NEW!)
│   ├── __init__.py
│   ├── bridge.py           # JavaSubprocessBridge (main IPC bridge)
│   ├── callbacks.py        # PythonCallbackHandler (HTTP server)
│   ├── tcc_callbacks.py    # TccCallbackHandler (TCC HTTP server)
│   ├── type_conversion.py  # TypeConverter (Python ↔ Java types)
│   ├── jar_builder.py      # JAR building and caching
│   └── java_bridge/        # Java source code
│       ├── src/main/java/com/firefly/transactional/
│       │   ├── JavaSubprocessBridge.java
│       │   └── PythonCallbackHandler.java
│       ├── pom.xml
│       └── build.sh
│
├── config/                 # ⚙️ Configuration
│   ├── __init__.py
│   ├── engine_config.py    # EngineConfig, JvmConfig
│   ├── event_config.py     # EventConfig
│   ├── persistence_config.py # PersistenceConfig
│   └── java_config_generator.py # Python → Java config translation
│
├── events/                 # 📡 Event Publishing
│   ├── __init__.py
│   ├── event_publisher.py  # StepEventPublisher interface
│   ├── saga_events.py      # SAGA event types
│   └── tcc_events.py       # TCC event types
│
├── persistence/            # 💾 State Persistence
│   ├── __init__.py
│   ├── saga_persistence.py # SagaPersistenceProvider interface
│   └── tcc_persistence.py  # TccPersistenceProvider interface
│
├── logging/                # 📊 Logging Infrastructure
│   ├── __init__.py
│   ├── manager.py          # Logging manager
│   ├── json_formatter.py   # JSON log formatting
│   ├── log_viewer.py       # Rich log viewer
│   └── java_log_bridge.py  # Java log integration
│
├── visualization/          # 📈 Graph Rendering
│   ├── __init__.py
│   ├── graph_renderer.py   # Graph rendering utilities
│   ├── saga_visualizer.py  # SAGA visualization
│   └── tcc_visualizer.py   # TCC visualization
│
├── utils/                  # 🛠️ Utilities
│   ├── __init__.py
│   ├── dependency_installer.py # Auto-install dependencies
│   ├── helpers.py          # General helpers
│   └── logging.py          # Logging utilities
│
├── callbacks/              # ⚠️ DEPRECATED (use integration/)
│   └── __init__.py         # Backwards compatibility wrapper
│
├── internal/               # 🔒 Internal Implementation Details
│   └── engine/             # Internal engine implementations
│       └── __init__.py
│
└── cli.py                  # 🖥️ CLI Entrypoint
```

---

## Module Responsibilities

### 1. API Layer (`api/`)

**Purpose:** High-level, user-friendly API facade

**Key Components:**
- `SagaExecutionEngine` - Main entry point for SAGA execution
- `create_saga_engine()` - Factory function for engine creation
- `execute_saga_once()` - One-shot SAGA execution

**When to use:**
- ✅ Building applications (most common use case)
- ✅ Need simple, async-first API
- ❌ Need low-level control (use `engine/` instead)

**Example:**
```python
from fireflytx import create_saga_engine

engine = create_saga_engine()
result = await engine.execute_saga_class(MySaga, data)
```

---

### 2. Core Types (`core/`)

**Purpose:** Fundamental types used throughout the system

**Key Components:**
- `SagaContext` / `TccContext` - Share data between steps/participants
- `SagaResult` / `TccResult` - Structured execution results
- `StepInputs` / `TccInputs` - Input helpers and validation

**When to use:**
- ✅ Defining step/participant methods
- ✅ Accessing shared data
- ✅ Type hints and validation

**Example:**
```python
from fireflytx import SagaContext

@saga_step("process-payment")
async def process_payment(self, data, context: SagaContext):
    # Use context to share data
    context.set_data("payment_id", payment.id)
    return {"success": True}
```

---

### 3. Decorators (`decorators/`)

**Purpose:** Define SAGA and TCC transactions declaratively

**Key Components:**

**SAGA Decorators:**
- `@saga` - Define a SAGA transaction
- `@saga_step` - Define a SAGA step
- `@compensation_step` - Define compensation logic
- `@step_events` - Configure event publishing

**TCC Decorators:**
- `@tcc` - Define a TCC transaction
- `@tcc_participant` - Define a TCC participant
- `@try_method` - Define try phase
- `@confirm_method` - Define confirm phase
- `@cancel_method` - Define cancel phase

**When to use:**
- ✅ Defining business logic
- ✅ Configuring retry, timeout, dependencies
- ✅ Setting up event publishing

**Example:**
```python
from fireflytx import saga, saga_step, compensation_step

@saga("order-processing")
class OrderSaga:
    @saga_step("reserve-inventory", retry=3)
    async def reserve(self, data):
        return {"reserved": True}

    @compensation_step("reserve-inventory")
    async def release(self, result):
        # Undo the reservation
        pass
```

---

### 4. Engine Layer (`engine/`)

**Purpose:** Full-featured engine wrappers with low-level control

## Finding What You Need

### By Task

| **I want to...** | **Look in...** | **Key Files** |
|------------------|----------------|---------------|
| Define a SAGA transaction | `decorators/` | `saga.py` |
| Define a TCC transaction | `decorators/` | `tcc.py` |
| Execute a transaction | `api/` | `saga_executor.py` |
| Configure the engine | `config/` | `engine_config.py` |
| Publish events | `events/` | `event_publisher.py` |
| Persist state | `persistence/` | `saga_persistence.py` |
| Debug Java integration | `integration/` | `bridge.py`, `callbacks.py` |
| View logs | `logging/` | `log_viewer.py` |
| Visualize workflows | `visualization/` | `saga_visualizer.py` |
| Run CLI commands | Root | `cli.py` |

### By Use Case

#### 🎯 **Building a New Application**

**Start here:**
1. `examples/` - See working examples
2. `decorators/saga.py` - Learn decorators
3. `api/saga_executor.py` - Use high-level API
4. `docs/saga-pattern.md` - Read pattern guide

**Typical imports:**
```python
from fireflytx import (
    saga,
    saga_step,
    compensation_step,
    create_saga_engine,
    SagaContext
)
```

#### 🔧 **Extending the Framework**

**Start here:**
1. `docs/developers-guide.md` - Architecture deep dive
2. `integration/` - Java bridge internals
3. `engine/` - Engine implementation
4. `config/java_config_generator.py` - Config translation

**Typical imports:**
```python
from fireflytx.engine import SagaEngine
from fireflytx.integration import JavaSubprocessBridge
from fireflytx.config import EngineConfig
```

#### 🐛 **Debugging Issues**

**Start here:**
1. `logging/log_viewer.py` - View structured logs
2. `integration/bridge.py` - Check Java IPC
3. `integration/callbacks.py` - Check HTTP callbacks
4. `cli.py` - Use CLI diagnostics

**Useful commands:**
```bash
# View logs
fireflytx logs --follow

# Check Java status
fireflytx status

# Run tests
task test
```

#### 📊 **Production Deployment**

**Start here:**
1. `config/` - Configure for production
2. `events/` - Set up event publishing
3. `persistence/` - Set up state persistence
4. `logging/` - Configure structured logging

**Typical configuration:**
```python
from fireflytx import create_saga_engine
from fireflytx.config import EngineConfig, EventConfig, PersistenceConfig
from fireflytx.events import KafkaStepEventPublisher
from fireflytx.persistence import RedisSagaPersistenceProvider

config = EngineConfig(
    max_concurrent_executions=100,
    default_timeout_ms=30000,
    event_config=EventConfig(
        enabled=True,
        kafka_bootstrap_servers="kafka:9092"
    ),
    persistence_config=PersistenceConfig(
        enabled=True,
        redis_host="redis"
    )
)

engine = create_saga_engine(config=config)
```

---

## Design Principles

### 1. **Feature-Oriented Organization**

Each directory represents a distinct feature or concern:
- ✅ Easy to find related code
- ✅ Easy to extend without touching unrelated code
- ✅ Clear boundaries between modules

### 2. **Separation of Concerns**

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: User API (api/, decorators/)                   │
│ - What users interact with                              │
│ - High-level, ergonomic, async-first                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Engine & Config (engine/, config/, core/)      │
│ - Business logic orchestration                          │
│ - Configuration management                              │
│ - Type definitions                                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Integration (integration/)                     │
│ - Python-Java bridge                                    │
│ - IPC and callbacks                                     │
│ - Type conversion                                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Cross-Cutting (events/, persistence/, logging/)│
│ - Observability                                         │
│ - State management                                      │
│ - Monitoring                                            │
└─────────────────────────────────────────────────────────┘
```

### 3. **Real Integration, No Mocks**

- ✅ All runtime code uses real `lib-transactional-engine`
- ✅ Tests run against actual Java engine
- ✅ No simulation or fake implementations in production paths
- ✅ Subprocess bridge provides genuine Java integration

### 4. **Progressive Disclosure**

- **Simple use cases:** Use `api/` - minimal configuration
- **Advanced use cases:** Use `engine/` - full control
- **Extension:** Use `integration/` - low-level access

### 5. **Backwards Compatibility**

- Deprecated modules (`callbacks/`) provide compatibility wrappers
- Deprecation warnings guide users to new APIs
- Old imports continue to work during migration period

### 6. **Clear Dependencies**

```
api/ ──────────> engine/ ──────────> integration/
  │                │                      │
  └──> decorators/ │                      │
       core/       │                      │
                   └──> config/           │
                        events/           │
                        persistence/      │
                        logging/          │
                                          │
                                          └──> Java Process
```

---

## Migration Guide

### From Old Structure to New Structure

If you have existing code using the old structure, here's how to migrate:

#### ✅ **Update Imports**

**Old:**
```python
from fireflytx.utils.java_subprocess_bridge import JavaSubprocessBridge
from fireflytx.utils.python_callback_handler import PythonCallbackHandler
from fireflytx.utils.type_conversion import TypeConverter
from fireflytx.callbacks import CallbackRegistry
```

**New:**
```python
from fireflytx.integration import JavaSubprocessBridge
from fireflytx.integration import PythonCallbackHandler
from fireflytx.integration import TypeConverter
from fireflytx.integration import CallbackRegistry
```

**Or use the main package exports:**
```python
from fireflytx import JavaSubprocessBridge, TypeConverter
```

#### ⚠️ **Deprecated Modules**

These modules still work but will be removed in a future version:

- `fireflytx.callbacks.*` → Use `fireflytx.integration.*`
- `fireflytx.utils.java_subprocess_bridge` → Use `fireflytx.integration.bridge`
- `fireflytx.utils.python_callback_handler` → Use `fireflytx.integration.callbacks`
- `fireflytx.utils.type_conversion` → Use `fireflytx.integration.type_conversion`

You'll see deprecation warnings when using old imports:
```
DeprecationWarning: fireflytx.callbacks is deprecated.
Import from fireflytx.integration instead.
```

---

## Frequently Asked Questions

### Why `integration/` instead of keeping things in `utils/`?

**Answer:** The Java bridge components are not generic utilities - they're a cohesive integration layer with specific responsibilities:
- Managing Java subprocess lifecycle
- Handling IPC communication
- Processing HTTP callbacks
- Converting types between Python and Java

Grouping them in `integration/` makes the architecture clearer and easier to understand.

### Where did `deps/` go?

**Answer:** JAR files should not be in the source tree. They're now managed as build artifacts:
- Development: Built on-demand and cached in `.cache/fireflytx/`
- Production: Installed via package manager or CI/CD pipeline

### Why keep `callbacks/` if it's deprecated?

**Answer:** Backwards compatibility. Existing code continues to work during the migration period. The module will be removed in version 2.0.

### How do I know which layer to use?

**Answer:** Follow this decision tree:

```
Are you building an application?
├─ Yes → Use api/ (create_saga_engine, execute_saga_class)
└─ No
   │
   Are you extending the framework?
   ├─ Yes → Use engine/ and integration/
   └─ No
      │
      Are you implementing a custom provider?
      ├─ Yes → Use events/ or persistence/ interfaces
      └─ No → You probably want api/
```

### Where are the Java sources?

**Answer:** `fireflytx/integration/java_bridge/src/main/java/`

This Java code is compiled into a shaded JAR that runs as a subprocess, bridging Python and the real `lib-transactional-engine`.

---

## Related Documentation

- **[Architecture Guide](architecture.md)** - Deep dive into system architecture
- **[SAGA Pattern Guide](saga-pattern.md)** - Complete SAGA pattern documentation
- **[TCC Pattern Guide](tcc-pattern.md)** - Complete TCC pattern documentation
- **[Configuration Guide](configuration.md)** - Configuration options and examples
- **[Developer's Guide](developers-guide.md)** - Contributing and extending the framework

---

## Summary

### Key Takeaways

1. **Feature-oriented structure** - Each directory has a clear purpose
2. **Layered architecture** - API → Engine → Integration → Java
3. **New `integration/` module** - Consolidates all Java bridge components
4. **Deprecated `callbacks/`** - Use `integration/` instead
5. **Real integration** - No mocks, uses actual `lib-transactional-engine`
6. **Progressive disclosure** - Simple API for common cases, full control when needed

### Quick Reference

| **Module** | **Purpose** | **When to Use** |
|------------|-------------|-----------------|
| `api/` | High-level API | Building applications |
| `decorators/` | Define transactions | All use cases |
| `core/` | Core types | All use cases |
| `engine/` | Engine wrappers | Advanced control |
| `integration/` | Java bridge | Extending framework |
| `config/` | Configuration | Production deployments |
| `events/` | Event publishing | Observability |
| `persistence/` | State persistence | Production deployments |
| `logging/` | Logging | Debugging, monitoring |
| `visualization/` | Graph rendering | Documentation, debugging |

---

**Last Updated:** 2025-10-19
**Version:** 1.0.0
**Maintainer:** FireflyTX Team


**Key Components:**
- `SagaEngine` - Complete SAGA engine wrapper
- `TccEngine` - Complete TCC engine wrapper

**When to use:**
- ✅ Need fine-grained control
- ✅ Custom configuration
- ✅ Advanced features (recovery, monitoring)
- ❌ Simple use cases (use `api/` instead)

**Example:**
```python
from fireflytx.engine import SagaEngine
from fireflytx.config import EngineConfig

config = EngineConfig(max_concurrent_executions=100)
engine = SagaEngine(config=config)
await engine.initialize()
result = await engine.execute_saga_class(MySaga, data)
```

---

### 5. Integration Layer (`integration/`) **NEW!**

**Purpose:** Python-Java communication bridge

**Key Components:**
- `JavaSubprocessBridge` - Manages Java subprocess and IPC
- `PythonCallbackHandler` - HTTP server for Java callbacks
- `TccCallbackHandler` - TCC-specific callback handler
- `TypeConverter` - Convert between Python and Java types
- `jar_builder` - Build and cache JARs
- `java_bridge/` - Java source code

**Architecture:**
```
Python                          Java
  │                              │
  ├─> JavaSubprocessBridge ─────┼─> Start Java Process
  │                              │
  │   JSON IPC (temp files)      │
  ├────────────────────────────> │ Execute method
  │ <──────────────────────────── │ Return result
  │                              │
  │   HTTP Callbacks             │
  │ <──────────────────────────── │ Call Python method
  ├────────────────────────────> │ Return result
  │                              │
```

**When to use:**
- ✅ Extending Java integration
- ✅ Custom type conversion
- ✅ Debugging IPC issues
- ❌ Normal application development (use `api/` instead)

**Example:**
```python
from fireflytx.integration import JavaSubprocessBridge

bridge = JavaSubprocessBridge()
result = bridge.call_java_method(
    class_name="com.example.MyClass",
    method_name="myMethod",
    args={"key": "value"}
)
```

---

### 6. Configuration (`config/`)

**Purpose:** Configure engine behavior and Java integration

**Key Components:**
- `EngineConfig` - Engine settings (timeouts, concurrency, etc.)
- `EventConfig` - Event publishing configuration
- `PersistenceConfig` - State persistence configuration
- `JavaConfigGenerator` - Translate Python config to Java

**When to use:**
- ✅ Production deployments
- ✅ Performance tuning
- ✅ Enabling features (events, persistence)

**Example:**
```python
from fireflytx.config import EngineConfig, EventConfig, PersistenceConfig

config = EngineConfig(
    max_concurrent_executions=100,
    default_timeout_ms=30000,
    event_config=EventConfig(
        enabled=True,
        kafka_bootstrap_servers="localhost:9092"
    ),
    persistence_config=PersistenceConfig(
        enabled=True,
        redis_host="localhost"
    )
)
```

---

### 7. Events (`events/`)

**Purpose:** Publish events for observability and integration

**Key Components:**
- `StepEventPublisher` - Event publisher interface
- `NoOpStepEventPublisher` - No-op implementation
- `KafkaStepEventPublisher` - Kafka implementation
- Event types: `StepStarted`, `StepCompleted`, `StepFailed`, etc.

**When to use:**
- ✅ Monitoring and observability
- ✅ Integration with external systems
- ✅ Audit trails

**Example:**
```python
from fireflytx.events import KafkaStepEventPublisher

publisher = KafkaStepEventPublisher(
    bootstrap_servers="localhost:9092",
    topic="saga-events"
)

engine = create_saga_engine(event_publisher=publisher)
```

---

### 8. Persistence (`persistence/`)

**Purpose:** Persist transaction state for recovery

**Key Components:**
- `SagaPersistenceProvider` - Persistence interface
- `NoOpSagaPersistenceProvider` - No-op implementation
- `RedisSagaPersistenceProvider` - Redis implementation
- `DatabaseSagaPersistenceProvider` - Database implementation

**When to use:**
- ✅ Production deployments
- ✅ Need recovery after crashes
- ✅ Long-running transactions

**Example:**
```python
from fireflytx.persistence import RedisSagaPersistenceProvider

persistence = RedisSagaPersistenceProvider(
    host="localhost",
    port=6379
)

engine = create_saga_engine(persistence_provider=persistence)
```

---

### 9. Logging (`logging/`)

**Purpose:** Structured logging and Java log integration

**Key Components:**
- `LoggingManager` - Centralized logging setup
- `JsonFormatter` - JSON log formatting
- `LogViewer` - Rich log viewer
- `JavaLogBridge` - Java log integration

**When to use:**
- ✅ Debugging
- ✅ Production monitoring
- ✅ Structured logging

**Example:**
```python
from fireflytx.logging import setup_logging

setup_logging(level="DEBUG", format="json")
```

---

### 10. Visualization (`visualization/`)

**Purpose:** Visualize SAGA and TCC execution graphs

**Key Components:**
- `SagaVisualizer` - SAGA graph visualization
- `TccVisualizer` - TCC graph visualization
- `GraphRenderer` - Graph rendering utilities

**When to use:**
- ✅ Understanding complex workflows
- ✅ Documentation
- ✅ Debugging

**Example:**
```python
from fireflytx.visualization import SagaVisualizer

visualizer = SagaVisualizer()
graph = visualizer.visualize_saga(MySaga)
graph.render("saga.png")
```

---

## Execution Flow

### "Python Defines, Java Executes"

Here's how a SAGA execution flows through the system:

```
1. Define SAGA (Your Code)
   ┌─────────────────────────────────────┐
   │ @saga("order-processing")           │
   │ class OrderSaga:                    │
   │     @saga_step("validate")          │
   │     async def validate(self, data): │
   │         ...                         │
   └─────────────────────────────────────┘
                    │
                    ▼
2. Execute SAGA (API Layer)
   ┌─────────────────────────────────────┐
   │ engine = create_saga_engine()       │
   │ result = await engine.execute_saga_ │
   │     class(OrderSaga, data)          │
   └─────────────────────────────────────┘
                    │
                    ▼
3. Engine Initialization (Engine Layer)
   ┌─────────────────────────────────────┐
   │ - Start Java subprocess             │
   │ - Start callback HTTP server        │
   │ - Register SAGA definition          │
   └─────────────────────────────────────┘
                    │
                    ▼
4. Java Orchestration (Integration Layer)
   ┌─────────────────────────────────────┐
   │ Python → Java (JSON IPC)            │
   │ - Send SAGA definition              │
   │ - Send execution request            │
   └─────────────────────────────────────┘
                    │
                    ▼
5. Step Execution (Callbacks)
   ┌─────────────────────────────────────┐
   │ Java → Python (HTTP Callbacks)      │
   │ - Call validate() method            │
   │ - Get result                        │
   │ - Continue orchestration            │
   └─────────────────────────────────────┘
                    │
                    ▼
6. Result (Core Types)
   ┌─────────────────────────────────────┐
   │ SagaResult(                         │
   │     is_success=True,                │
   │     steps={"validate": {...}},      │
   │     duration_ms=1234                │
   │ )                                   │
   └─────────────────────────────────────┘
```

---

This is the first part of the project structure documentation. Let me continue with the rest.

