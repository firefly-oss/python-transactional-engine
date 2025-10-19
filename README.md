# 🔥 FireflyTX - Python Transactional Engine

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)](tests/)
[![Examples](https://img.shields.io/badge/examples-5-blue)](examples/)

> **🚀 Enterprise-grade distributed transactions made simple**

**FireflyTX** implements the **"Python defines, Java executes"** architecture for distributed transactions. Write your business logic in Python with simple decorators, while the battle-tested Java lib-transactional-engine handles all the complex orchestration, reliability, and execution.

```python
from fireflytx import SagaEngine
from fireflytx.decorators.saga import saga, saga_step

@saga("payment-processing")
class PaymentSaga:
    @saga_step("validate", retry=3, timeout_ms=5000)
    async def validate_payment(self, amount: float):
        return {"validated": True, "amount": amount}

    @saga_step("charge", depends_on=["validate"])
    async def charge_payment(self, amount: float):
        return {"charged": True, "transaction_id": "tx_123"}

# Execute with enterprise reliability
engine = SagaEngine()
await engine.initialize()
result = await engine.execute(PaymentSaga, {"amount": 100.0})
print(f"✅ Payment completed: {result.is_success}")
await engine.shutdown()
```

## ✨ Why FireflyTX?

### 🧠 **Python Simplicity + Java Reliability**
| You Write (Python) | Engine Handles (Java) |
|---|---|
| `@saga` business logic | Transaction orchestration |
| `@saga_step` methods | Retry & timeout logic |
| Event configuration | Kafka/Redis integration |
| Compensation logic | Automatic rollbacks |

### ⚡ **Key Features**
- **🔥 Zero Boilerplate**: Write business logic, not infrastructure code
- **🏗️ Production Ready**: Battle-tested Java lib-transactional-engine under the hood
- **📊 Built-in Observability**: Events, logging, and distributed tracing
- **🔄 Automatic Compensation**: Rollbacks handled transparently
- **⚡ Async Native**: Full asyncio support for modern Python apps
- **🛡️ Type Safe**: Complete type hints and validation

## 📚 Navigation

| Getting Started | Advanced | Resources |
|---|---|---|
| [🚀 Installation](#-installation) | [🛠️ Advanced Usage](#-advanced-usage) | [📝 Examples](examples/) |
| [📝 Quick Example](#-5-minute-example) | [🏗️ Architecture](#-architecture) | [🧪 Tests](tests/) |
| [🎯 Step-by-Step Guide](#-step-by-step-guide) | [⚙️ Configuration](#-configuration) | [📚 API Docs](docs/) |
| [🔥 Production Setup](#-production-setup) | [🔧 Troubleshooting](#-troubleshooting) | [💬 Support](#-support) |


## 🚀 Installation

> **⚠️ Important:** FireflyTX is **not published to PyPI**. You must install from source or use the install script.

### 🔥 **Quick Install (Recommended)**

**One-line install script:**
```bash
curl -fsSL https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh | bash
```

This automated script will:
- ✅ Check system requirements (Python 3.9+, Java 11+)
- ✅ Clone the repository from GitHub
- ✅ Install FireflyTX and all dependencies
- ✅ Download/build lib-transactional-engine JAR
- ✅ Verify the installation
- ✅ Show you next steps

### 📦 **Manual Installation from Source**

If you prefer manual control:

```bash
# 1. Clone the repository
git clone https://github.com/firefly-oss/python-transactional-engine.git
cd python-transactional-engine

# 2. Install FireflyTX
pip install .

# For development (editable mode):
pip install -e .

# 3. Verify installation
python -c "import fireflytx; print(f'✅ FireflyTX {fireflytx.__version__} installed')"
```

### 📋 **Requirements**

- **Python**: 3.9 or higher
- **Java**: JDK 11 or higher (for lib-transactional-engine)
- **Git**: For cloning the repository
- **OS**: Linux, macOS, or Windows (WSL recommended)

> **Note**: PyPI package is not yet published. Install from source using the methods above.

## ⚡ Quick Start

### 🎯 **Your First SAGA in 2 Minutes**

After installation, create your first distributed transaction:

```python
# my_first_saga.py
import asyncio
from fireflytx import SagaEngine, saga, saga_step

@saga("hello-world")
class HelloWorldSaga:
    @saga_step("greet", retry=3, timeout_ms=5000)
    async def greet(self, name: str) -> dict:
        print(f"👋 Hello, {name}!")
        return {"message": f"Hello, {name}!"}

async def main():
    # Create and initialize the engine
    engine = SagaEngine()
    await engine.initialize()

    # Execute the SAGA
    result = await engine.execute(
        HelloWorldSaga,
        {"name": "World"}
    )

    print(f"✅ Success: {result.is_success}")

    # Cleanup
    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python my_first_saga.py
```

Output:
```
👋 Hello, World!
✅ Success: True
```

### 🔧 **Configuration Basics**

FireflyTX uses a simple configuration hierarchy:

1. **Engine-level**: Global settings for all SAGAs and TCC transactions
2. **SAGA/TCC-level**: Settings for a specific workflow
3. **Step/Participant-level**: Settings for individual operations

#### **Quick Start: Default Configuration**

```python
from fireflytx import SagaEngine, TccEngine
from fireflytx.config import ConfigurationManager

# ✅ Method 1: Simplest setup - uses sensible defaults
saga_engine = SagaEngine()
await saga_engine.initialize()

tcc_engine = TccEngine()
tcc_engine.start()

# ✅ Method 2: Explicit default configuration
config = ConfigurationManager.get_default_config()
saga_engine = SagaEngine(config=config)
await saga_engine.initialize()

# ✅ Method 3: Production configuration helper
config = ConfigurationManager.get_production_config(
    persistence_type="redis",
    persistence_connection_string="redis://localhost:6379",
    heap_size="2g",
    max_concurrent_executions=200
)
saga_engine = SagaEngine(config=config)
await saga_engine.initialize()

# ✅ Method 4: High-performance configuration helper
config = ConfigurationManager.get_high_performance_config(
    persistence_connection_string="redis://redis-cluster:6379"
)
saga_engine = SagaEngine(config=config)
await saga_engine.initialize()
```

**Default Configuration Values:**
- Max concurrent executions: 100
- Default timeout: 30 seconds
- Thread pool size: 50
- JVM heap size: 256MB
- Persistence: In-memory (development only)
- Retry attempts: 3 with exponential backoff

**Production Configuration Values:**
- Max concurrent executions: 200
- Default timeout: 60 seconds
- Thread pool size: 100
- JVM heap size: 2GB
- Persistence: Redis with auto-checkpointing
- Retry attempts: 5 with exponential backoff
- GC: G1GC with 200ms max pause

**High-Performance Configuration Values:**
- Max concurrent executions: 500
- Default timeout: 30 seconds
- Thread pool size: 200
- JVM heap size: 4GB
- Persistence: Redis with high connection pool
- Retry attempts: 3 with exponential backoff
- GC: G1GC with 100ms max pause

#### **Production Configuration**

For production use, configure engines with `EngineConfig`:

```python
from fireflytx import SagaEngine, TccEngine, EngineConfig, PersistenceConfig, JvmConfig

# Create comprehensive configuration
config = EngineConfig(
    # Execution settings
    max_concurrent_executions=200,
    default_timeout_ms=60000,  # 60 seconds
    thread_pool_size=100,
    enable_monitoring=True,

    # Persistence configuration
    persistence=PersistenceConfig(
        type="redis",
        connection_string="redis://localhost:6379",
        auto_checkpoint=True,
        checkpoint_interval_seconds=60
    ),

    # JVM configuration
    jvm=JvmConfig(
        heap_size="1g",
        gc_algorithm="G1GC",
        max_gc_pause_ms=200,
        additional_jvm_args=[
            "-XX:+UseStringDeduplication",
            "-XX:+OptimizeStringConcat"
        ]
    )
)

# Initialize engines with configuration
saga_engine = SagaEngine(config=config)
await saga_engine.initialize()

tcc_engine = TccEngine(config=config)
tcc_engine.start()
```

#### **Configuration Hierarchy**

```python
from fireflytx import SagaEngine, saga, saga_step, compensation_step

# 1. Engine-level configuration (applies to all SAGAs)
engine = SagaEngine(
    compensation_policy="STRICT_SEQUENTIAL",
    auto_optimization_enabled=True,
    config=config  # Optional EngineConfig object
)

# 2. SAGA-level configuration (applies to all steps in this SAGA)
@saga("order-processing", layer_concurrency=10)
class OrderSaga:

    # 3. Step-level configuration (applies to this step only)
    @saga_step(
        step_id="validate",
        retry=5,              # Override engine default
        timeout_ms=5000,      # Step-specific timeout
        compensate="undo_validate"  # Compensation method
    )
    async def validate_order(self, order: dict) -> dict:
        # Your business logic here
        return {"validated": True}

    @compensation_step("validate")
    async def undo_validate(self, result: dict) -> None:
        # Compensation logic
        pass
```

#### **Environment-Based Configuration**

```python
from fireflytx import EngineConfig

# Load from environment variables
config = EngineConfig.from_env(prefix="FIREFLYTX_")

# Or from YAML file
config = EngineConfig.from_file("config/production.yaml")

# Use with engines
engine = SagaEngine(config=config)
```

**Environment Variables:**
```bash
export FIREFLYTX_MAX_CONCURRENT_EXECUTIONS=200
export FIREFLYTX_DEFAULT_TIMEOUT_MS=60000
export FIREFLYTX_THREAD_POOL_SIZE=100
export FIREFLYTX_PERSISTENCE_TYPE=redis
export FIREFLYTX_PERSISTENCE_CONNECTION_STRING=redis://localhost:6379
export FIREFLYTX_JVM_HEAP_SIZE=1g
```

See [Configuration Reference](docs/configuration.md) for complete details.

### 🐍 **Development Installation**

**For contributors and developers:**
```bash
# Clone and install in development mode
git clone https://github.com/firefly-oss/python-transactional-engine.git
cd python-transactional-engine
pip install -e .

# Build the Java bridge
python -m fireflytx.cli build

# Verify installation
python -m fireflytx.cli status
```

**Or use the install script with --dev flag:**
```bash
curl -fsSL https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh | bash -s -- --dev
```

### ⚙️ **Advanced Installation Options**

```bash
# Custom Python version
curl -fsSL https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh | bash -s -- --python python3.11

# Quiet installation
curl -fsSL https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh | bash -s -- --quiet

# Force reinstall
curl -fsSL https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh | bash -s -- --force

# Development mode with custom Python
curl -fsSL https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh | bash -s -- --dev --python python3.11

# Download and run locally
wget https://raw.githubusercontent.com/firefly-oss/python-transactional-engine/main/install.sh
chmod +x install.sh
./install.sh --help
```

### 📎 **System Requirements**

| Component | Version | Purpose | Installation |
|---|---|---|---|
| **Python** | 3.9+ | Your business logic | [python.org](https://python.org) |
| **Java** | 11+ | Transaction engine | [openjdk.org](https://openjdk.org) |
| **Redis** | 5.0+ (optional) | Distributed state | `brew install redis` |
| **Kafka** | 2.8+ (optional) | Event streaming | [kafka.apache.org](https://kafka.apache.org) |

### ✅ **Verify Installation**
```python
import fireflytx
from fireflytx import SagaEngine, saga, saga_step
print("✅ FireflyTX installed successfully!")
print(f"🔥 Version: {fireflytx.__version__}")
```

> 🔍 **Real Java Integration**: FireflyTX uses the actual lib-transactional-engine Java library, not mocks or simulations.

### 🔧 **Build Java Bridge**

After installation, build the Java bridge (happens automatically on first use, or manually):

```bash
# Check status
python -m fireflytx.cli status

# Build manually (optional)
python -m fireflytx.cli build

# Verify Java integration
python -m fireflytx.cli version
```

The Java bridge is built once and cached in `.cache/fireflytx/`. The CLI will show:
- ✅ Java version and location
- ✅ Build environment status
- ✅ JAR dependencies status
- ✅ Integration readiness

### 🤖 **Task Automation**

We use [Task](https://taskfile.dev) for project automation:

```bash
# Install Task (macOS)
brew install go-task/tap/go-task

# Or download from https://taskfile.dev

# See all available tasks
task --list

# Run tests
task test-unit        # Fast unit tests
task test-integration # Integration tests
task all-tests        # All tests

# Development workflow
task clean           # Clean build artifacts
task install-dev     # Install dev dependencies  
task format          # Format code
task lint            # Run linting
task pre-commit      # Pre-commit checks
```

## 🚀 Quick Start Guide

### 📖 **Understanding "Python Defines, Java Executes"**

FireflyTX follows a unique architecture:

| **You Write (Python)** | **Engine Handles (Java)** |
|---|---|
| Business logic with decorators | Transaction orchestration |
| Step definitions and dependencies | Retry logic and timeouts |
| Compensation methods | Automatic rollbacks |
| Configuration and events | State persistence |
| Simple async functions | Distributed execution |

**Key Concept**: You focus on **WHAT** your business logic does. The Java engine handles **HOW** it executes reliably.

### ⚙️ **How Configuration Works**

FireflyTX configuration happens in **three layers**:

#### 1️⃣ **Engine Configuration** (Python → Java)
When you create an engine, Python sends configuration to Java:

```python
from fireflytx import SagaEngine

# Python defines the configuration
engine = SagaEngine(
    compensation_policy="STRICT_SEQUENTIAL",  # ← Python defines
    auto_optimization_enabled=True,           # ← Python defines
    persistence_enabled=False                 # ← Python defines
)
# ↓ Configuration sent to Java engine via IPC
# ↓ Java engine starts with these settings
```

**What happens**:
1. Python creates configuration object
2. Configuration serialized to JSON
3. Sent to Java subprocess via IPC
4. Java engine initializes with settings
5. Python receives confirmation

#### 2️⃣ **SAGA/TCC Definition** (Python → Java)
When you define a SAGA/TCC, Python sends the structure to Java:

```python
from fireflytx import saga, saga_step

@saga("payment-processing")           # ← Python defines SAGA name
class PaymentSaga:
    @saga_step("validate", retry=3)   # ← Python defines step config
    async def validate(self, data):
        # Your business logic here
        return {"validated": True}
```

**What happens**:
1. Python decorators capture SAGA structure
2. Step metadata (name, retry, timeout, dependencies) extracted
3. SAGA definition sent to Java engine
4. Java engine registers the SAGA workflow
5. Java engine ready to orchestrate execution

#### 3️⃣ **Execution** (Java Orchestrates, Python Executes)
When you execute a SAGA, Java orchestrates but Python runs the logic:

```python
# Execute the SAGA
result = await engine.execute_by_class(PaymentSaga, {"amount": 100})
```

**What happens**:
1. **Python** → Java: "Execute PaymentSaga with this data"
2. **Java** → Determines execution order based on dependencies
3. **Java** → Python: "Execute step 'validate' with this data" (HTTP callback)
4. **Python** → Runs `validate()` method with your business logic
5. **Python** → Java: "Step completed, here's the result"
6. **Java** → Applies retry logic if needed, manages state
7. **Java** → Python: "Execute next step..." (repeat)
8. **Java** → Python: "SAGA completed successfully" (or failed with compensations)

### 🎯 **Configuration Best Practices**

#### ✅ **DO: Configure at Engine Level**
```python
# Good: Engine-level configuration
engine = SagaEngine(
    compensation_policy="STRICT_SEQUENTIAL",  # All SAGAs use this
    auto_optimization_enabled=True,           # Enable optimizations
    persistence_enabled=False                 # Disable persistence for dev
)
```

#### ✅ **DO: Configure at SAGA Level**
```python
# Good: SAGA-specific configuration
@saga("critical-payment",
      timeout_ms=30000,           # This SAGA's timeout
      max_retries=5)              # This SAGA's retry limit
class CriticalPaymentSaga:
    pass
```

#### ✅ **DO: Configure at Step Level**
```python
# Good: Step-specific configuration
@saga_step("validate",
           retry=3,                # This step's retry count
           timeout_ms=5000,        # This step's timeout
           critical=True)          # This step's criticality
async def validate(self, data):
    pass
```

#### ❌ **DON'T: Mix Configuration Concerns**
```python
# Bad: Don't configure engine settings in SAGA
@saga("payment")
class PaymentSaga:
    @saga_step("validate")
    async def validate(self, data):
        # ❌ Don't create engine here
        engine = SagaEngine()  # Wrong!
```

### 🔄 **Configuration Flow Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR PYTHON CODE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Define Configuration                                    │
│     engine = SagaEngine(...)                                │
│                          ↓                                  │
│  2. Define SAGA Structure                                   │
│     @saga("name")                                           │
│     class MySaga: ...                                       │
│                          ↓                                  │
│  3. Execute SAGA                                            │
│     result = await engine.execute_by_class(MySaga, data)    │
│                                                             │
└────────────────────────┬────────────────────────────────────┘
                         │ JSON IPC
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  JAVA ENGINE (lib-transactional-engine)     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Receive Configuration → Initialize Engine               │
│  2. Receive SAGA Definition → Register Workflow             │
│  3. Receive Execute Request → Orchestrate Steps             │
│     ├─ Manage dependencies                                  │
│     ├─ Apply retry logic                                    │
│     ├─ Handle timeouts                                      │
│     ├─ Persist state                                        │
│     └─ Trigger compensations on failure                     │
│                          ↓                                  │
│  4. Call Python for Business Logic (HTTP callbacks)         │
│                                                             │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Callbacks
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              YOUR BUSINESS LOGIC (Python Methods)           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  async def validate(self, data):                            │
│      # Your code runs here                                  │
│      return result                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 📝 **Simple Configuration Example**

```python
from fireflytx import SagaEngine, saga, saga_step

# Step 1: Configure the engine (Python → Java)
engine = SagaEngine(
    compensation_policy="STRICT_SEQUENTIAL",
    auto_optimization_enabled=True
)

# Step 2: Define your SAGA (Python → Java)
@saga("hello-world")
class HelloWorldSaga:
    @saga_step("greet")
    async def greet(self, name: str):
        return {"message": f"Hello, {name}!"}

# Step 3: Execute (Java orchestrates, Python executes)
result = await engine.execute_by_class(
    HelloWorldSaga,
    {"name": "World"}
)

print(result.output)  # {"message": "Hello, World!"}
```

**What happened**:
1. ✅ Python created engine config → Java initialized engine
2. ✅ Python defined SAGA structure → Java registered workflow
3. ✅ Python requested execution → Java orchestrated
4. ✅ Java called Python's `greet()` method → Python executed business logic
5. ✅ Python returned result → Java completed SAGA
6. ✅ Java returned final result → Python received output

## 🐚 Interactive Shell (Like PySpark)

FireflyTX includes a powerful interactive shell for development, testing, and debugging - just like PySpark!

### 🚀 **Launching the Shell**

```bash
# Method 1: Using CLI
python -m fireflytx.cli shell

# Method 2: Using Taskfile
task shell

# Method 3: Direct module
python -m fireflytx.shell
```

### 🎯 **Shell Features**

The FireflyTX shell provides:

- ✅ **Custom Prompt**: `fireflytx>>>` prompt like PySpark
- ✅ **Top-level Await**: Use `await` directly (with IPython)
- ✅ **Pre-loaded Context**: All engines, decorators, and utilities ready to use
- ✅ **Tab Completion**: Auto-complete for all FireflyTX objects
- ✅ **Command History**: Persistent history saved to `~/.fireflytx_history`
- ✅ **Syntax Highlighting**: Beautiful colored output (with IPython)
- ✅ **Developer Tools**: Inspect, benchmark, and debug SAGAs interactively

### 📖 **Shell Tutorial**

#### **1. Start the Shell**

```bash
$ python -m fireflytx.cli shell
```

You'll see:

```
  _____.__                _____.__
_/ ____\__|______   _____/ ____\  | ___.__.
\   __\|  \_  __ \_/ __ \   __\|  |<   |  |
 |  |  |  ||  | \/\  ___/|  |  |  |_\___  |
 |__|  |__||__|    \___  >__|  |____/ ____|
                       \/           \/
:: fireflytx ::                  (v2025-08)

🔥 FireflyTX Interactive Shell v1.0.0

Enterprise-grade distributed transactions for Python
"Python defines, Java executes"

Python 3.9.6 | IPython 8.x.x
Session started: 2025-10-19 14:30:00

════════════════════════════════════════════════════════════════

📚 Quick Start:
   help()               - Show all available commands
   init_engines()       - Initialize SAGA and TCC engines (async)
   status()             - Show engine and Java bridge status
   examples()           - Show example code snippets

fireflytx>>>
```

#### **2. Initialize Engines**

```python
fireflytx>>> await init_engines()
🚀 Initializing FireflyTX engines...
  📦 Creating SAGA engine...
  ✅ SAGA engine initialized
  📦 Creating TCC engine...
  ✅ TCC engine initialized
  ✅ Java bridge connected

✨ All engines initialized successfully!
   Use 'saga_engine' and 'tcc_engine' to interact with engines
```

#### **3. Check Status**

```python
fireflytx>>> status()

🔧 FireflyTX Status
════════════════════════════════════════════════════════════
Version: 1.0.0
SAGA Engine: ✅ Initialized
TCC Engine: ✅ Initialized
Java Bridge: ✅ Connected
Java Process: ✅ Running
════════════════════════════════════════════════════════════
```

#### **4. Define a SAGA Interactively**

```python
fireflytx>>> @saga("payment-processing")
...      ... class PaymentSaga:
...      ...     @saga_step("validate", retry=3)
...      ...     async def validate_payment(self, amount: float):
...      ...         print(f"Validating payment: ${amount}")
...      ...         return {"validated": True, "amount": amount}
...      ...
...      ...     @saga_step("charge", depends_on=["validate"])
...      ...     async def charge_payment(self, amount: float):
...      ...         print(f"Charging payment: ${amount}")
...      ...         return {"charged": True, "transaction_id": "tx_123"}
```

#### **5. Execute the SAGA**

```python
fireflytx>>> result = await saga_engine.execute(
...      ...     PaymentSaga,
...      ...     {"amount": 100.0}
...      ... )
Validating payment: $100.0
Charging payment: $100.0

fireflytx>>> print(f"Success: {result.is_success}")
Success: True
```

#### **6. Inspect SAGA Structure**

```python
fireflytx>>> inspect(PaymentSaga)

🔍 Inspecting SAGA: PaymentSaga
════════════════════════════════════════════════════════════
SAGA Name: payment-processing
Steps: 2

Steps:
  • validate
    Retry: 3
  • charge
    Depends on: ['validate']
════════════════════════════════════════════════════════════
```

#### **7. Benchmark Performance**

```python
fireflytx>>> await benchmark(PaymentSaga, {"amount": 50.0}, iterations=100)

⏱️ Benchmarking PaymentSaga
Iterations: 100
════════════════════════════════════════════════════════════
  Progress: 10/100
  Progress: 20/100
  ...
  Progress: 100/100

📊 Results:
  Total: 100
  Successes: 100 (100.0%)
  Failures: 0 (0.0%)

⏱️ Timing:
  Average: 45.23ms
  Min: 38.12ms
  Max: 67.89ms
  Throughput: 22.11 ops/sec
════════════════════════════════════════════════════════════
```

#### **8. View Examples**

```python
fireflytx>>> examples()

🎯 FireflyTX Code Examples
═══════════════════════════════════════════════════════════════

1️⃣ INITIALIZE ENGINES
────────────────────────────────────────────────────────────────
await init_engines()

2️⃣ DEFINE A SIMPLE SAGA
────────────────────────────────────────────────────────────────
@saga("payment-processing")
class PaymentSaga:
    @saga_step("validate", retry=3)
    async def validate_payment(self, amount: float):
        print(f"Validating payment: ${amount}")
        return {"validated": True, "amount": amount}
...
```

#### **9. Get Help**

```python
fireflytx>>> help()

🔥 FireflyTX Shell Help
═══════════════════════════════════════════════════════════════

📦 PRE-LOADED OBJECTS:
  saga_engine          - SAGA engine instance
  tcc_engine           - TCC engine instance
  java_bridge          - Java subprocess bridge

🎨 DECORATORS:
  @saga                - Define a SAGA workflow
  @saga_step           - Define a SAGA step
  @compensation_step   - Define compensation logic
  @tcc                 - Define a TCC transaction
  @tcc_participant     - Define a TCC participant

🛠️ HELPER FUNCTIONS:
  init_engines()       - Initialize engines (async)
  shutdown_engines()   - Shutdown engines (async)
  reset()              - Reset engines (shutdown + reinit) (async)
  status()             - Show current status
  java_info()          - Show Java subprocess info
  config()             - Show engine configuration
  help()               - Show this help
  examples()           - Show code examples
  clear()              - Clear screen and show banner

🔧 DEVELOPER TOOLS:
  inspect(SagaClass)   - Inspect SAGA structure
  benchmark(Saga, {})  - Benchmark SAGA execution (async)
  logs(lines=50)       - Show recent Java logs
...
```

#### **10. Shutdown and Exit**

```python
fireflytx>>> await shutdown_engines()
🛑 Shutting down FireflyTX engines...
  ✅ SAGA engine shutdown
  ✅ TCC engine shutdown

✨ All engines shutdown successfully!

fireflytx>>> exit()

👋 Goodbye! FireflyTX shell exiting...
```

### 💡 **Shell Tips & Tricks**

#### **Use IPython for Best Experience**

```bash
# Install IPython for enhanced features
pip install ipython

# Then launch shell - you'll get:
# • Top-level await (no need for run())
# • Syntax highlighting
# • Better tab completion
# • Custom fireflytx>>> prompt
```

#### **Without IPython**

If IPython is not installed, use the `run()` helper:

```python
fireflytx>>> run(init_engines())  # Instead of await
fireflytx>>> run(saga_engine.execute_by_class(MySaga, {}))
```

#### **Command History**

```python
# History is saved to ~/.fireflytx_history
# Use ↑/↓ arrows to navigate previous commands
# Search history with Ctrl+R (in IPython)
```

#### **Tab Completion**

```python
fireflytx>>> saga_<TAB>
saga_engine  saga_step  saga

fireflytx>>> saga_engine.<TAB>
execute_by_class  initialize  shutdown  ...
```

#### **Clear Screen**

```python
fireflytx>>> clear()
# Clears screen and shows banner again
```

#### **Reset Engines**

```python
fireflytx>>> await reset()
# Shuts down and reinitializes all engines
```

### 🎯 **Common Shell Workflows**

#### **Quick Testing**

```python
# Start shell
$ python -m fireflytx.cli shell

# Initialize
fireflytx>>> await init_engines()

# Define and test SAGA
fireflytx>>> @saga("test")
...      ... class TestSaga:
...      ...     @saga_step("step1")
...      ...     async def step1(self, data):
...      ...         return {"result": "ok"}

# Execute
fireflytx>>> result = await saga_engine.execute(TestSaga, {})
fireflytx>>> print(result.is_success)
True

# Done
fireflytx>>> await shutdown_engines()
fireflytx>>> exit()
```

#### **Debugging**

```python
# Start with engines initialized
fireflytx>>> await init_engines()

# Check Java bridge
fireflytx>>> java_info()

# Inspect your SAGA
fireflytx>>> inspect(MySaga)

# Run with debugging
fireflytx>>> result = await saga_engine.execute(MySaga, {"debug": True})

# Check logs
fireflytx>>> logs(100)
```

#### **Performance Testing**

```python
# Initialize
fireflytx>>> await init_engines()

# Benchmark different configurations
fireflytx>>> await benchmark(FastSaga, {}, iterations=1000)
fireflytx>>> await benchmark(SlowSaga, {}, iterations=100)

# Compare results
```

### 📚 **Shell Reference**

| Command | Description | Example |
|---------|-------------|---------|
| `help()` | Show all commands | `help()` |
| `init_engines()` | Initialize engines | `await init_engines()` |
| `shutdown_engines()` | Shutdown engines | `await shutdown_engines()` |
| `reset()` | Reset engines | `await reset()` |
| `status()` | Show status | `status()` |
| `java_info()` | Java subprocess info | `java_info()` |
| `config()` | Show configuration | `config()` |
| `examples()` | Show examples | `examples()` |
| `inspect(Saga)` | Inspect SAGA | `inspect(MySaga)` |
| `benchmark(Saga, {})` | Benchmark SAGA | `await benchmark(MySaga, {}, 100)` |
| `logs(n)` | Show logs | `logs(50)` |
| `clear()` | Clear screen | `clear()` |
| `exit()` | Exit shell | `exit()` or Ctrl+D |

---

## 📝 5-Minute Example

### 🎯 **E-Commerce Order Processing**

```python path=null start=null
import asyncio
from fireflytx import (
    SagaEngine, saga, saga_step, compensation_step, step_events,
    KafkaStepEventPublisher, RedisSagaPersistenceProvider
)

@saga("e-commerce-order")
class OrderProcessingSaga:
    """Complete order processing with automatic rollbacks."""
    
    @step_events(
        topic="order-events",
        include_timing=True,
        custom_headers={"service": "orders"}
    )
    @saga_step("validate-order", retry=3, timeout_ms=10000)
    async def validate_order(self, order_data):
        # Your validation logic
        if order_data.get("amount", 0) <= 0:
            raise ValueError("Invalid amount")
        return {"validated": True, "order_id": order_data["order_id"]}
    
    @saga_step("reserve-inventory", depends_on=["validate-order"], compensate="release_inventory")
    async def reserve_inventory(self, order_data):
        # Reserve inventory
        return {"reserved": True, "reservation_id": "res_123"}
    
    @saga_step("charge-payment", depends_on=["reserve-inventory"], compensate="refund_payment")
    async def charge_payment(self, order_data):
        # Process payment
        return {"charged": True, "transaction_id": "tx_456"}
    
    # Automatic compensation methods
    @compensation_step("reserve-inventory")
    async def release_inventory(self, reservation_data):
        print(f"🔄 Rolling back inventory reservation")
    
    @compensation_step("charge-payment")
    async def refund_payment(self, payment_data):
        print(f"💸 Refunding payment")

# Production setup with Kafka + Redis
engine = SagaEngine(
    event_publisher=KafkaStepEventPublisher("localhost:9092"),
    persistence_provider=RedisSagaPersistenceProvider()
)
await engine.initialize()

# Execute with full enterprise reliability
order_data = {
    "order_id": "ORDER-123", 
    "amount": 99.99,
    "customer_id": "CUST-456"
}

result = await engine.execute_by_class(OrderProcessingSaga, order_data)

if result.is_success:
    print(f"✅ Order processed in {result.duration_ms}ms")
else:
    print(f"❌ Order failed: {result.error}")
    print(f"🔄 Auto-compensated: {len(result.compensated_steps)} steps")
```

### 🚀 **What Just Happened?**

1. **🐍 Python**: You defined business logic with simple decorators
2. **☕ Java Engine**: Handled orchestration, retries, events, and persistence
3. **🔄 Auto-Rollback**: Failed steps automatically triggered compensations
4. **📊 Events**: Published to Kafka with timing and custom headers
5. **💾 State**: Persisted to Redis for crash recovery

**✨ Zero infrastructure code, maximum reliability!**

### Basic SAGA Example with Events

```python
import asyncio
from typing import Dict, Any
from fireflytx import (
    SagaEngine, saga, saga_step, step_events, compensation_step,
    KafkaStepEventPublisher, RedisSagaPersistenceProvider
)

@saga("payment-processing")
class PaymentProcessingSaga:
    """Payment processing SAGA with step events - Python defines, Java executes."""
    
    @step_events(
        topic="payment-validation",
        key_template="{saga_id}-validation",
        include_timing=True,
        custom_headers={"service": "payment", "operation": "validate"}
    )
    @saga_step("validate-payment", retry=3, timeout_ms=10000)
    async def validate_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payment information - Python business logic."""
        if payment_data.get("amount", 0) <= 0:
            raise ValueError("Invalid payment amount")
        
        validation_id = f"validation_{payment_data['customer_id']}"
        print(f"✅ Payment validated: {validation_id}")
        
        return {"validation_id": validation_id, "status": "validated"}
    
    @step_events(
        topic="payment-processing",
        key_template="{customer_id}-payment",
        include_result=True,
        publish_on_failure=True
    )
    @saga_step("process-payment", depends_on=["validate-payment"], 
               retry=5, compensate="refund_payment")
    async def process_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the payment - Python business logic."""
        payment_id = f"pay_{payment_data['customer_id']}_{payment_data['amount']}"
        print(f"💳 Payment processed: {payment_id}")
        
        return {"payment_id": payment_id, "status": "completed", "amount": payment_data['amount']}
    
    @compensation_step("process-payment")
    async def refund_payment(self, payment_result: Dict[str, Any]) -> None:
        """Refund the payment - Python compensation logic."""
        payment_id = payment_result.get("payment_id")
        if payment_id:
            print(f"💸 Payment refunded: {payment_id}")

# Usage with "Python defines, Java executes" architecture
async def main():
    # Create engine with event publishing and persistence (Python defines)
    engine = SagaEngine(
        event_publisher=KafkaStepEventPublisher(
            bootstrap_servers="localhost:9092",
            default_topic="saga-events"
        ),
        persistence_provider=RedisSagaPersistenceProvider(
            host="localhost",
            key_prefix="saga:"
        )
    )
    
    # Payment data
    payment_data = {
        "customer_id": "customer_123",
        "amount": 99.99,
        "payment_method": "credit_card"
    }
    
    # Execute SAGA - Java handles orchestration, events, persistence
    result = await engine.execute_by_class(
        PaymentProcessingSaga,
        input_data=payment_data
    )
    
    if result.is_success:
        print(f"✅ SAGA completed successfully in {result.duration_ms}ms!")
        print(f"   - Correlation ID: {result.correlation_id}")
        print(f"   - Steps executed: {len(result.steps)}")
    else:
        print(f"❌ SAGA failed: {result.error}")
        print(f"   - Compensated steps: {result.compensated_steps}")
    
    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📚 Complete Usage Guide

### Step 1: Define SAGA with Events

```python
from fireflytx import saga, saga_step, step_events, compensation_step

@saga("e-commerce-order", layer_concurrency=5)
class ECommerceOrderSaga:
    """Complete e-commerce order processing with step events."""
    
    @step_events(
        topic="order-validation",
        key_template="{saga_id}-{step_id}",
        include_timing=True,
        include_payload=True,
        custom_headers={"service": "validation", "priority": "high"},
        publish_on_start=True,
        publish_on_success=True,
        publish_on_failure=True,
        publish_on_retry=True
    )
    @saga_step("validate-order", retry=5, timeout_ms=10000)
    async def validate_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order - Python defines business logic."""
        # Your validation logic here
        return {"validated": True, "order_id": order_data["order_id"]}
    
    @step_events(topic="inventory-events")
    @saga_step("reserve-inventory", depends_on=["validate-order"], compensate="release_inventory")
    async def reserve_inventory(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reserve inventory - Python defines business logic."""
        # Your inventory logic here
        return {"reserved": True, "reservation_id": "res_123"}
    
    @compensation_step("reserve-inventory")
    async def release_inventory(self, reservation_data: Dict[str, Any]) -> None:
        """Release inventory - Python defines compensation logic."""
        # Your compensation logic here
        pass
```

### Step 2: Configure Engine with Providers

```python
from fireflytx import (
    SagaEngine,
    KafkaStepEventPublisher,
    RedisSagaPersistenceProvider
)

# Python defines all configuration, Java executes
engine = SagaEngine(
    # Event publishing configuration (Python defines)
    event_publisher=KafkaStepEventPublisher(
        bootstrap_servers="kafka-cluster:9092",
        default_topic="saga-events",
        key_serializer="string",
        value_serializer="json",
        acks="all",
        retries=5,
        compression_type="snappy"
    ),
    
    # Persistence configuration (Python defines)
    persistence_provider=RedisSagaPersistenceProvider(
        host="redis-cluster",
        port=6379,
        database=1,
        key_prefix="saga:",
        ttl_seconds=3600,
        max_connections=50
    ),
    
    # Engine configuration (Python defines)
    compensation_policy="STRICT_SEQUENTIAL",
    auto_optimization=True,
    thread_pool_size=20,
    max_concurrent_sagas=500
)
```

### Step 3: Execute SAGA

```python
# Register and execute - Java handles orchestration
result = await engine.execute_by_class(
    ECommerceOrderSaga,
    input_data={
        "order_id": "ORDER-12345",
        "customer_id": "CUST-456",
        "items": [{"sku": "ITEM-001", "quantity": 2}],
        "total_amount": 199.99
    },
    context={"region": "US", "currency": "USD"},
    timeout_ms=30000
)

# Java execution results mapped to Python
if result.is_success:
    print(f"Order processed in {result.duration_ms}ms")
    print(f"Steps completed: {list(result.steps.keys())}")
else:
    print(f"Order failed: {result.error}")
    print(f"Compensated: {result.compensated_steps}")
```

### Available Event Publishers

```python
# No-op publisher (for testing)
from fireflytx import NoOpStepEventPublisher
publisher = NoOpStepEventPublisher()

# Kafka publisher (for production)
from fireflytx import KafkaStepEventPublisher
publisher = KafkaStepEventPublisher(
    bootstrap_servers="kafka1:9092,kafka2:9092",
    default_topic="saga-events",
    acks="all",
    retries=10
)
```

### Available Persistence Providers

```python
# No-op provider (for testing)
from fireflytx import NoOpSagaPersistenceProvider
provider = NoOpSagaPersistenceProvider()

# Redis provider (for production)
from fireflytx import RedisSagaPersistenceProvider
provider = RedisSagaPersistenceProvider(
    host="redis-cluster",
    port=6379,
    key_prefix="saga:",
    ttl_seconds=86400
)

# Database provider (for enterprise)
from fireflytx import DatabaseSagaPersistenceProvider
provider = DatabaseSagaPersistenceProvider(
    connection_url="jdbc:postgresql://db:5432/saga_db",
    table_prefix="saga_",
    schema="transactions"
)
```

### Step Events Configuration

The `@step_events` decorator allows fine-grained control over event publishing:

```python
@step_events(
    enabled=True,                    # Enable/disable events for this step
    topic="custom-topic",            # Custom Kafka topic
    key_template="{saga_id}-{step_id}", # Event key template
    include_payload=True,            # Include step input/output
    include_context=True,            # Include SAGA context
    include_result=True,             # Include step results
    include_timing=True,             # Include execution timing
    custom_headers={                 # Custom event headers
        "service": "payment",
        "version": "v2",
        "priority": "high"
    },
    publish_on_start=True,           # Publish when step starts
    publish_on_success=True,         # Publish when step succeeds
    publish_on_failure=True,         # Publish when step fails
    publish_on_retry=False,          # Publish on retry attempts
    publish_on_compensation=True     # Publish during compensation
)
@saga_step("my-step")
async def my_step(self, data):
    return {"processed": True}
```

## 🏗️ Architecture: Python Defines, Java Executes

This library follows a clear separation of concerns:

### Python Responsibilities
- **Business Logic**: Define saga steps and compensation methods
- **Configuration**: Specify event publishing, persistence, and engine settings
- **Decorators**: Configure step behavior, events, and dependencies
- **Data Structures**: Input/output schemas and context definitions

### Java Engine Responsibilities
- **Orchestration**: Execute saga steps in correct order with dependencies
- **Event Publishing**: Publish step events to Kafka or other message brokers
- **Persistence**: Save/restore saga state to Redis, databases, or other stores
- **Transaction Management**: Handle retries, timeouts, and compensation
- **Concurrency**: Manage parallel execution and resource allocation

### Configuration Flow

```python
# 1. Python defines configuration
saga_config = JavaConfigGenerator().generate_config(
    sagas=[MySaga],
    event_publisher=KafkaStepEventPublisher(...),
    persistence_provider=RedisSagaPersistenceProvider(...)
)

# 2. Configuration sent to Java engine
engine.send_configuration(saga_config)

# 3. Java engine processes SAGA orchestration
# 4. Java calls back to Python for business logic
# 5. Java publishes events and manages persistence
# 6. Results returned to Python
```

## ⚙️ Advanced Configuration

### Engine-Level Configuration

```python
engine = SagaEngine(
    # Execution settings
    compensation_policy="STRICT_SEQUENTIAL",  # or "PARALLEL", "BEST_EFFORT"
    auto_optimization_enabled=True,
    thread_pool_size=50,
    max_concurrent_sagas=1000,
    
    # Observability
    metrics_enabled=True,
    tracing_enabled=True,
    log_level="INFO",
    
    # Security
    enable_step_validation=True,
    max_step_execution_time_ms=300000,
    
    # Resource management
    memory_limit_mb=2048,
    cleanup_interval_ms=60000
)
```

### Custom Event Publishers

```python
from fireflytx.events import StepEventPublisher
from typing import Dict, Any

class CustomWebhookEventPublisher(StepEventPublisher):
    """Custom webhook event publisher implementation."""
    
    def __init__(self, webhook_url: str, auth_token: str):
        self.webhook_url = webhook_url
        self.auth_token = auth_token
    
    async def publish(self, event):
        # Custom publishing logic
        print(f"Publishing to webhook: {event.event_type.value}")
    
    def get_publisher_config(self) -> Dict[str, Any]:
        return {
            "type": "webhook",
            "webhook_url": self.webhook_url,
            "auth_token": self.auth_token,
            "timeout_ms": 5000
        }

# Use custom publisher
engine = SagaEngine(
    event_publisher=CustomWebhookEventPublisher(
        webhook_url="https://api.example.com/events",
        auth_token="your-auth-token"
    )
)
```

### Complex SAGA Patterns

```python
@saga("complex-workflow", layer_concurrency=10)
class ComplexWorkflowSaga:
    """Demonstrates advanced SAGA patterns."""
    
    # Parallel execution branches
    @saga_step("process-a", timeout_ms=30000)
    async def process_a(self, data): pass
    
    @saga_step("process-b", timeout_ms=30000)
    async def process_b(self, data): pass
    
    # Convergence step
    @saga_step("merge-results", depends_on=["process-a", "process-b"])
    async def merge_results(self, data): pass
    
    # Conditional execution
    @saga_step("conditional-step", depends_on=["merge-results"])
    async def conditional_step(self, data):
        if data.get("condition"):
            return {"executed": True}
        else:
            return {"skipped": True}
    
    # Dynamic branching
    @saga_step("dynamic-branch", depends_on=["conditional-step"])
    async def dynamic_branch(self, data):
        # Java engine can handle dynamic step creation
        return {"next_steps": ["step-1", "step-2", "step-3"]}
```

### Monitoring and Observability

```python
import logging

# Enable comprehensive logging for observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Monitor SAGA execution through logs
logger = logging.getLogger('fireflytx')
logger.setLevel(logging.DEBUG)

# SAGA execution automatically logs:
# - SAGA start/completion
# - Step execution progress
# - Event publishing
# - Compensation actions
# - Error details
```

## 🧪 Testing

### Unit Testing SAGA Steps

```python
import pytest
from fireflytx import SagaEngine, NoOpStepEventPublisher, NoOpSagaPersistenceProvider

@pytest.mark.asyncio
async def test_order_validation():
    """Test individual saga step."""
    saga = ECommerceOrderSaga()
    
    # Test step in isolation
    result = await saga.validate_order({
        "order_id": "TEST-123",
        "customer_id": "CUST-456"
    })
    
    assert result["validated"] is True
    assert result["order_id"] == "TEST-123"

@pytest.mark.asyncio
async def test_full_saga_execution():
    """Test complete SAGA execution."""
    # Use test engine with no-op providers
    engine = SagaEngine(
        event_publisher=NoOpStepEventPublisher(),
        persistence_provider=NoOpSagaPersistenceProvider()
    )
    await engine.initialize()
    
    try:
        result = await engine.execute_by_class(
            ECommerceOrderSaga,
            input_data={"order_id": "TEST-123"},
            timeout_ms=10000
        )
        
        assert result.is_success
        assert len(result.steps) > 0
    finally:
        await engine.shutdown()
```

## 🔌 Integration Examples

### Spring Boot Integration

```python
import os
from fireflytx import (
    SagaEngine,
    KafkaStepEventPublisher,
    RedisSagaPersistenceProvider
)
from flask import Flask, request, jsonify

app = Flask(__name__)

# Initialize engine on startup
engine = SagaEngine(
    event_publisher=KafkaStepEventPublisher(
        bootstrap_servers=os.getenv("KAFKA_BROKERS"),
        default_topic="web-saga-events"
    ),
    persistence_provider=RedisSagaPersistenceProvider(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT", 6379))
    )
)

@app.route('/orders', methods=['POST'])
async def create_order():
    """REST endpoint that triggers SAGA execution."""
    order_data = request.json
    
    try:
        result = await engine.execute_by_class(
            ECommerceOrderSaga,
            input_data=order_data,
            context={"user_id": request.headers.get("User-ID")},
            timeout_ms=30000
        )
        
        if result.is_success:
            return jsonify({
                "status": "success",
                "saga_id": result.saga_id,
                "duration_ms": result.duration_ms
            }), 201
        else:
            return jsonify({
                "status": "failed",
                "error": str(result.error),
                "compensated_steps": result.compensated_steps
            }), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: saga-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: saga-service
  template:
    metadata:
      labels:
        app: saga-service
    spec:
      containers:
      - name: saga-service
        image: your-registry/saga-service:latest
        ports:
        - containerPort: 8080
        env:
        - name: KAFKA_BROKERS
          value: "kafka-cluster:9092"
        - name: REDIS_HOST
          value: "redis-cluster"
        - name: JAVA_ENGINE_JAR
          value: "/app/lib-transactional-engine.jar"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
```

### Batch Processing

```python
import asyncio
from typing import List, Dict
from fireflytx import SagaEngine, NoOpStepEventPublisher, NoOpSagaPersistenceProvider

async def process_batch_orders(orders: List[Dict]):
    """Process multiple orders concurrently."""
    engine = SagaEngine(
        event_publisher=NoOpStepEventPublisher(),
        persistence_provider=NoOpSagaPersistenceProvider()
    )
    await engine.initialize()
    
    async def process_single_order(order_data):
        return await engine.execute_by_class(
            ECommerceOrderSaga,
            input_data=order_data,
            timeout_ms=60000
        )
    
    # Process orders concurrently
    tasks = [process_single_order(order) for order in orders]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analyze results
    successful = [r for r in results if hasattr(r, 'is_success') and r.is_success]
    failed = [r for r in results if isinstance(r, Exception) or (hasattr(r, 'is_success') and not r.is_success)]
    
    print(f"Processed {len(successful)} orders successfully, {len(failed)} failed")
    
    await engine.shutdown()
    return results

# Usage
# orders = load_orders_from_database()
# results = await process_batch_orders(orders)
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Java Engine Connection Issues
```python
# Enable debug logging
import logging
logging.getLogger('fireflytx').setLevel(logging.DEBUG)

# Initialize engine and check logs for issues
engine = SagaEngine()
try:
    await engine.initialize()
    print("Engine initialized successfully")
except Exception as e:
    print(f"Engine initialization failed: {e}")
```

#### 2. Configuration Issues
```python
# Check configuration generation
from fireflytx import generate_saga_engine_config

try:
    config = generate_saga_engine_config(
        engine_name="test-engine",
        saga_classes=[MySaga],
        event_publisher=KafkaStepEventPublisher("localhost:9092")
    )
    print("Configuration generated successfully")
except Exception as e:
    print(f"Configuration error: {e}")
```

#### 3. Step Execution Timeouts
```python
# Increase timeouts for long-running steps
@saga_step("long-running-step", timeout_ms=300000)  # 5 minutes
async def long_running_step(self, data):
    # Your long-running logic here
    pass

# Or configure engine-level timeouts
engine = SagaEngine(
    # Configure via engine options if needed
)
```

#### 4. Memory Issues
```python
# Configure memory limits via Java options if needed
engine = SagaEngine()
await engine.initialize()
```

### Debugging Tips

1. **Enable comprehensive logging**:
   ```python
   logging.basicConfig(
       level=logging.DEBUG,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

2. **Monitor Java engine logs**:
   ```bash
   # View Java engine logs
   tail -f /var/log/saga-engine.log
   ```

3. **Use no-op providers for development**:
   ```python
   # Use no-op providers for debugging
   engine = SagaEngine(
       event_publisher=NoOpStepEventPublisher(),
       persistence_provider=NoOpSagaPersistenceProvider()
   )
   await engine.initialize()
   ```

4. **Monitor execution through logs**:
   ```python
   # Enable debug logging to monitor execution
   import logging
   logging.getLogger('fireflytx').setLevel(logging.DEBUG)
   ```

### Performance Optimization

```python
# Optimize for high throughput
engine = SagaEngine(
    auto_optimization_enabled=True,

    # Batch event publishing
    event_publisher=KafkaStepEventPublisher(
        batch_size=100,
        linger_ms=10,
        compression_type="lz4"
    ),
    
    # Connection pooling
    persistence_provider=RedisSagaPersistenceProvider(
        max_connections=50,
        connection_pool_timeout=5000
    )
)
```

### Basic TCC Example

```python
import asyncio
from pydantic import BaseModel
from fireflytx import TccEngine, tcc, tcc_participant, try_method, confirm_method, cancel_method

# Define Pydantic models for type safety
class DepositRequest(BaseModel):
    account_id: str
    amount: float

class CreditReservation(BaseModel):
    reserved: bool
    reservation_id: str
    amount: float

@tcc("account-deposit")
class AccountDepositTcc:
    """Simple account deposit TCC transaction with Pydantic models."""

    @tcc_participant("credit-account")
    class CreditAccountParticipant:

        @try_method
        async def try_credit(self, data: DepositRequest) -> CreditReservation:
            """Try to reserve credit for account."""
            reservation_id = f"reserve_{data.account_id}_{data.amount}"

            # Reserve account credit (example business logic)
            print(f"💰 Reserving ${data.amount} credit for account {data.account_id}")

            return CreditReservation(
                reserved=True,
                reservation_id=reservation_id,
                amount=data.amount
            )

        @confirm_method
        async def confirm_credit(self, data: DepositRequest, try_result: CreditReservation):
            """Confirm the credit to account."""
            # Access Pydantic model attributes directly
            print(f"✅ Confirmed ${try_result.amount} credit to account {data.account_id} (reservation: {try_result.reservation_id})")
            return {"confirmed": True, "final_amount": try_result.amount}

        @cancel_method
        async def cancel_credit(self, data: DepositRequest, try_result: CreditReservation):
            """Cancel the credit reservation."""
            # Access Pydantic model attributes directly
            print(f"❌ Cancelled ${try_result.amount} credit reservation for account {data.account_id} (reservation: {try_result.reservation_id})")
            return {"cancelled": True, "reservation_id": try_result.reservation_id}

# Usage
async def main():
    # Initialize the TCC engine (connects to Java lib-transactional-engine)
    engine = TccEngine()
    await engine.initialize()
    
    # Define deposit data
    deposit_data = {
        "account_id": "account_123",
        "amount": 50.0
    }
    
    # Execute the TCC (Python methods executed via Java engine)
    result = await engine.execute_by_class(AccountDepositTcc, deposit_data)
    
    if result.is_success:
        print(f"✅ TCC completed successfully!")
        print(f"   - Correlation ID: {result.correlation_id}")
        print(f"   - Confirmed: {result.is_confirmed}")
        print(f"   - Participants: {result.participants_count}")
        print(f"   - Java engine version: {result.lib_transactional_version}")
    else:
        print(f"❌ TCC failed: {result.error}")
        print(f"   - Final phase: {result.final_phase}")
        print(f"   - Cancelled: {result.is_canceled}")
    
    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📊 Topology Visualization

FireflyTX includes powerful visualization tools to understand your transaction flows:

```bash
# Visualize SAGA topology
fireflytx visualize order_saga.py OrderProcessingSaga

# Generate DOT format for Graphviz
fireflytx visualize order_saga.py OrderProcessingSaga --format=dot

# Generate Mermaid diagram
fireflytx visualize payment_tcc.py PaymentTcc --format=mermaid
```

## 🔍 Java Logging Integration

FireflyTX now streams the Java lib-transactional-engine logs into Python logging and exposes helper APIs to inspect them programmatically.

```python
import logging
from fireflytx.utils.java_subprocess_bridge import get_java_bridge

# Optional: configure Python logging
logging.basicConfig(level=logging.INFO)

bridge = get_java_bridge()
bridge.start_jvm()  # starts Java and log streaming

# Tail recent Java logs
recent = bridge.get_java_logs(count=100)
for line in recent:
    print(line)

# Follow logs in real-time via callback
bridge.follow_java_logs(lambda line, stream: print(f"FOLLOW: {line}"))

# Adjust verbosity of Java log forwarding
bridge.set_java_log_level("DEBUG")  # or logging.WARNING

# Tee Java logs to a file
bridge.enable_java_log_file("java-engine.log")

# Environment variable to set level at startup
# export FIREFLYTX_JAVA_LOG_LEVEL=DEBUG
```

> Note: A dedicated CLI command (fireflytx java-logs) may be added in a future release; for now, use the programmatic APIs above or rely on the Python logging output from the dedicated logger name "fireflytx.java".

## 📋 CLI Commands

FireflyTX provides a comprehensive CLI for development and operations:

```bash
# Engine management
fireflytx status                    # Show engine status
fireflytx test                      # Test connectivity

# Development tools  
fireflytx validate saga.py          # Validate decorators
fireflytx visualize saga.py MySaga  # Visualize topology
fireflytx list-examples             # List examples
fireflytx run-example saga-basic    # Run example

# Java integration
fireflytx jar-info                  # JAR information
fireflytx jar-build                 # Build from source
fireflytx java-logs --follow        # Monitor logs

# Configuration
fireflytx init-config config.yaml  # Generate config
```

## ⚙️ Configuration

FireflyTX provides flexible configuration options for different deployment scenarios.

### Quick Configuration Reference

```python
from fireflytx import SagaEngine, TccEngine
from fireflytx.config import ConfigurationManager

# 🚀 Development (default) - in-memory, minimal resources
config = ConfigurationManager.get_default_config()
saga_engine = SagaEngine(config=config)

# 🏭 Production - Redis persistence, optimized settings
config = ConfigurationManager.get_production_config(
    persistence_type="redis",
    persistence_connection_string="redis://localhost:6379",
    heap_size="2g",
    max_concurrent_executions=200
)
saga_engine = SagaEngine(config=config)

# ⚡ High-Performance - maximum throughput
config = ConfigurationManager.get_high_performance_config(
    persistence_connection_string="redis://redis-cluster:6379"
)
saga_engine = SagaEngine(config=config)

# 🎨 Custom - full control
from fireflytx.config import EngineConfig, PersistenceConfig, JvmConfig

config = EngineConfig(
    max_concurrent_executions=150,
    default_timeout_ms=45000,
    thread_pool_size=75,
    persistence=PersistenceConfig(
        type="postgresql",
        connection_string="postgresql://user:pass@localhost:5432/fireflytx",
        auto_checkpoint=True
    ),
    jvm=JvmConfig(
        heap_size="3g",
        gc_algorithm="G1GC",
        max_gc_pause_ms=150
    )
)
saga_engine = SagaEngine(config=config)
```

### Configuration Comparison

| Feature | Default | Production | High-Performance |
|---------|---------|------------|------------------|
| Max Concurrent | 100 | 200 | 500 |
| Timeout | 30s | 60s | 30s |
| Thread Pool | 50 | 100 | 200 |
| JVM Heap | 256m | 2g | 4g |
| Persistence | Memory | Redis | Redis (high pool) |
| Retry Attempts | 3 | 5 | 3 |
| GC Algorithm | Default | G1GC | G1GC (optimized) |

### Environment Variables

```bash
# Override any configuration via environment variables
export FIREFLYTX_MAX_CONCURRENT_EXECUTIONS=200
export FIREFLYTX_DEFAULT_TIMEOUT_MS=60000
export FIREFLYTX_THREAD_POOL_SIZE=100
export FIREFLYTX_PERSISTENCE_TYPE=redis
export FIREFLYTX_PERSISTENCE_CONNECTION_STRING=redis://localhost:6379
export FIREFLYTX_JVM_HEAP_SIZE=2g
export FIREFLYTX_JVM_GC_ALGORITHM=G1GC
```

### YAML Configuration

```yaml
# fireflytx-config.yaml
engine:
  max_concurrent_executions: 200
  default_timeout_ms: 60000
  thread_pool_size: 100
  enable_monitoring: true

retry:
  max_attempts: 5
  initial_delay_ms: 1000
  max_delay_ms: 60000
  backoff_multiplier: 2.0

persistence:
  type: redis
  connection_string: redis://localhost:6379
  auto_checkpoint: true
  checkpoint_interval_seconds: 60

jvm:
  heap_size: 2g
  gc_algorithm: G1GC
  max_gc_pause_ms: 200
  additional_jvm_args:
    - "-XX:+UseStringDeduplication"
    - "-XX:+OptimizeStringConcat"
```

**See [Configuration Reference](docs/configuration.md) for complete details and examples.**

## 🎭 Transaction Patterns

### SAGA Pattern Features

- **Step Dependencies**: Define execution order with `depends_on`
- **Automatic Compensation**: Rollback on failures with compensation steps
- **Retry Logic**: Configurable retry with exponential backoff
- **Parallel Execution**: Execute independent steps concurrently
- **Compensation Policies**: Multiple strategies (sequential, parallel, circuit breaker)
- **Type Safety**: Full Pydantic model support

### TCC Pattern Features

- **Resource Reservation**: Try phase reserves resources
- **Two-Phase Commit**: Atomic confirm/cancel operations
- **Participant Ordering**: Control execution sequence
- **Timeout Management**: Per-phase timeout configuration
- **Failure Handling**: Automatic compensation on try failures
- **Strong Consistency**: ACID properties across distributed services

## 🔧 Advanced Features

### Event System

```python
from fireflytx.events import SagaEvents

class CustomSagaEvents(SagaEvents):
    async def on_saga_started(self, saga_name: str, correlation_id: str):
        print(f"Started SAGA {saga_name}: {correlation_id}")
    
    async def on_step_completed(self, step_id: str, result: any):
        print(f"Step {step_id} completed with result: {result}")

engine = SagaEngine(events_handler=CustomSagaEvents())
```

### Custom Persistence

```python
from fireflytx.persistence import SagaPersistenceProvider

class CustomPersistenceProvider(SagaPersistenceProvider):
    async def save_saga_state(self, correlation_id: str, state: dict):
        # Custom persistence implementation
        pass

engine = SagaEngine(persistence_provider=CustomPersistenceProvider())
```

### Context Management

```python
from fireflytx import SagaContext

# Access context in steps
@saga_step("process_order")
async def process_order(self, order: OrderData, context: SagaContext) -> dict:
    # Set context variables
    context.set_variable("user_id", order.customer_id)
    context.put_header("trace_id", "abc-123")
    
    # Access context in subsequent steps
    user_id = context.get_variable("user_id")
    return {"processed_by": user_id}
```

## 🧪 Testing

**FireflyTX provides excellent testing support, allowing you to test your Python transaction logic against the real Java engine:**

```python
import pytest
import asyncio
from fireflytx import SagaEngine, TccEngine

@pytest.mark.asyncio
async def test_successful_payment_saga():
    """Test successful payment processing SAGA."""
    engine = SagaEngine()
    await engine.initialize()
    
    payment_data = {
        "customer_id": "test_customer_123",
        "amount": 50.0,
        "payment_method": "credit_card"
    }
    
    # Execute SAGA through real Java engine
    result = await engine.execute_by_class(PaymentProcessingSaga, payment_data)
    
    # Verify successful execution
    assert result.is_success
    assert result.saga_name == "payment-processing"
    assert result.engine_used is True  # Confirms Java engine was used
    assert result.lib_transactional_version is not None
    assert len(result.failed_steps) == 0
    
    await engine.shutdown()

@pytest.mark.asyncio
async def test_saga_compensation():
    """Test SAGA compensation when steps fail."""
    engine = SagaEngine()
    await engine.initialize()
    
    # Execute a SAGA designed to fail
    result = await engine.execute_by_class(FailingSaga, {"test": "data"})
    
    # Verify compensation was executed
    assert not result.is_success
    assert len(result.failed_steps) > 0
    assert len(result.compensated_steps) > 0  # Compensation executed
    
    await engine.shutdown()

@pytest.mark.asyncio
async def test_tcc_transaction():
    """Test TCC transaction execution."""
    engine = TccEngine()
    await engine.initialize()
    
    deposit_data = {
        "account_id": "test_account",
        "amount": 25.0
    }
    
    # Execute TCC through real Java engine
    result = await engine.execute_by_class(AccountDepositTcc, deposit_data)
    
    # Verify successful TCC execution
    assert result.is_success
    assert result.is_confirmed
    assert not result.is_canceled
    assert result.participants_count > 0
    
    await engine.shutdown()

@pytest.mark.asyncio
async def test_tcc_rollback():
    """Test TCC rollback when confirm fails."""
    engine = TccEngine()
    await engine.initialize()
    
    # Execute a TCC designed to fail during confirm
    result = await engine.execute_by_class(FailingTcc, {"test": "rollback"})
    
    # Verify rollback was executed
    assert not result.is_success
    assert not result.is_confirmed
    assert result.is_canceled
    
    await engine.shutdown()

# Run tests with:
# pytest tests/integration/ -v
```

**Key Testing Features:**

- **🏢 Real Engine Testing**: Tests run against actual lib-transactional-engine
- **🔄 Automatic Setup**: Engine initialization and JAR building handled automatically
- **⏱️ Async Support**: Full asyncio support with `@pytest.mark.asyncio`
- **📋 Comprehensive Results**: Test success, failure, compensation, and rollback scenarios
- **🔍 Detailed Assertions**: Verify engine integration, transaction states, and step execution

## 📚 Documentation

- [Architecture Guide](docs/architecture.md) - System design and components
- [SAGA Pattern Guide](docs/saga-pattern.md) - Detailed SAGA implementation
- [TCC Pattern Guide](docs/tcc-pattern.md) - TCC transaction details
- [Configuration Reference](docs/configuration.md) - Complete config options  
- [API Reference](docs/api-reference.md) - Full API documentation
- [Developers Guide](docs/developers-guide.md) - How the wrapper is designed and implemented
- [Project Structure](docs/project-structure.md) - Where features live and how execution flows
- [Tutorial](TUTORIAL.md) - Step-by-step getting started guide
- [Examples](fireflytx/examples/) - Working code examples

## 🔍 Troubleshooting

### Common Issues

1. **JVM Startup Failures**
   ```bash
   # Check Java installation
   fireflytx status
   
   # Test connectivity
   fireflytx test
   ```

2. **Memory Issues**
   ```yaml
   jvm:
     heap_size: 2g  # Increase heap size
   ```

3. **Connection Issues**
   ```bash
   # Check persistence backend
   fireflytx validate-config config.yaml
   ```

### Python Wrapper + Java Engine Integration

FireflyTX is designed as a **Python wrapper** that provides a seamless interface to the powerful lib-transactional-engine Java library:

**What FireflyTX Does:**
- 🐍 Provides Python decorators (`@saga`, `@tcc_participant`, etc.) for defining transactions
- 🔄 Automatically downloads and builds lib-transactional-engine JAR from GitHub
- 🌉 Manages subprocess communication bridge to Java engine
- 📋 Marshalls Python method calls to/from Java execution context
- 📈 Provides unified Python API for results and monitoring

**What lib-transactional-engine Does:**
- ⚙️ Handles the actual distributed transaction orchestration
- 💾 Manages persistence, checkpointing, and recovery
- 🔄 Provides enterprise-grade reliability and fault tolerance
- ⏱️ Implements timeout handling, retry logic, and compensation
- 📏 Ensures ACID properties across distributed operations

```bash
# Verify the wrapper's Java engine integration
fireflytx jar-info

# Test wrapper connectivity to Java engine  
fireflytx test --verbose

# Monitor both Python and Java logs
fireflytx java-logs --follow
```

**This architecture gives you:**
- 🚀 **Fast Python Development** - Write and test transaction logic in Python
- 🏢 **Enterprise Java Execution** - Run with production-grade transaction processing
- 🔧 **Zero Java Setup** - No manual JAR management or Java configuration needed
- 🌍 **Cross-Platform** - Works everywhere Python runs, including Apple Silicon

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) file for details.

## 🏢 About Firefly Software Solutions Inc

FireflyTX is developed by Firefly Software Solutions Inc, specialists in distributed systems and transaction processing.

- **Website**: https://getfirefly.io
- **GitHub**: https://github.com/firefly-oss
- **Documentation**: https://docs.getfirefly.io
- **Support**: support@getfirefly.io

---

**Build robust distributed systems with confidence using FireflyTX** 🚀