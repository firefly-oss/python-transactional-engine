# 🔥 FireflyTX Examples

```
  _____.__                _____.__
_/ ____\__|______   _____/ ____\  | ___.__.
\   __\|  \_  __ \_/ __ \   __\|  |<   |  |
 |  |  |  ||  | \/\  ___/|  |  |  |_\___  |
 |__|  |__||__|    \___  >__|  |____/ ____|
                       \/           \/
:: fireflytx ::                  (v2025-08)
```

**Enterprise-grade distributed transactions for Python**
*"Python defines, Java executes"*

---

This directory contains comprehensive, production-ready examples demonstrating how to use FireflyTX to build reliable distributed transactions using the SAGA and TCC patterns.

## 🎯 What You'll Learn

- ✅ How to define SAGA and TCC workflows in Python
- ✅ How the Java `lib-transactional-engine` orchestrates execution
- ✅ How to handle failures with automatic compensation
- ✅ How to configure retries, timeouts, and dependencies
- ✅ How to integrate with real systems (Kafka, Redis, databases)
- ✅ How to test and debug distributed transactions

## 🚀 Quick Start

### Prerequisites

```bash
# 1. Install FireflyTX from source (PyPI not yet published)
git clone https://github.com/firefly-oss/python-transactional-engine.git
cd python-transactional-engine

# 2. Run installation script
./install.sh

# 3. Build Java bridge (required for examples to work)
python -m fireflytx.cli build

# 4. Verify installation
python -m fireflytx.cli status
```

### Run Your First Example

```bash
# Run the basic SAGA example
python examples/saga_basic.py
```

**Expected Output:**
```
🚀 Initializing SAGA engine (connecting to Java subprocess)...
✅ SAGA engine initialized and connected to Java

Processing order: ORD-001
📦 Executing SAGA via Java lib-transactional-engine...
🎉 Order ORD-001 completed successfully!
```

## 📚 Examples Catalog

### 🌟 Beginner Examples

#### 1. [`saga_basic.py`](saga_basic.py) - **START HERE**
**What it demonstrates:**
- Basic SAGA pattern with 3 steps (inventory, payment, shipping)
- Automatic compensation on failure
- Real Java engine integration
- Success and failure scenarios

**Key Concepts:**
- `@saga` decorator to define workflows
- `@saga_step` for individual steps
- `@compensation_step` for rollback logic
- `SagaEngine.execute_saga_class()` for execution

**Run it:**
```bash
python examples/saga_basic.py
```

**What happens:**
1. Python defines the SAGA structure using decorators
2. Java `lib-transactional-engine` receives the configuration
3. Java orchestrates execution, calling back to Python methods
4. On failure, Java automatically triggers compensation

---

#### 2. [`tcc_basic.py`](tcc_basic.py) - TCC Pattern Basics
**What it demonstrates:**
- TCC (Try-Confirm-Cancel) two-phase commit pattern
- Strong consistency guarantees
- Try, Confirm, and Cancel phases
- Real Java engine integration

**Key Concepts:**
- `@tcc` decorator for TCC workflows
- `@tcc_participant` for participants
- Three-phase execution model
- Automatic rollback on failure

**Run it:**
```bash
python examples/tcc_basic.py
```

---

### 🏢 Intermediate Examples

#### 3. [`complete_integration_example.py`](complete_integration_example.py)
**⭐ RECOMMENDED FOR PRODUCTION LEARNING**

**What it demonstrates:**
- Complete end-to-end integration
- Event publishing to Kafka
- State persistence to Redis
- Custom event configuration
- Error handling patterns
- Monitoring and observability

**Key Concepts:**
- Engine configuration
- Event publishers
- Persistence backends
- Custom event topics and headers
- Correlation IDs

**Run it:**
```bash
python examples/complete_integration_example.py
```

---

#### 4. [`order_saga_comprehensive.py`](order_saga_comprehensive.py)
**What it demonstrates:**
- Real-world e-commerce order processing
- Complex step dependencies
- Multiple compensation strategies
- Idempotency handling
- Timeout configuration

**Key Concepts:**
- Step dependencies (`depends_on`)
- Retry policies
- Timeout configuration
- Idempotent operations
- Business logic patterns

**Run it:**
```bash
python examples/order_saga_comprehensive.py
```

---

### 🔧 Advanced Examples

#### 5. [`events_and_persistence_example.py`](events_and_persistence_example.py)
**What it demonstrates:**
- Advanced event publishing patterns
- Multiple persistence backends
- Custom serialization
- Event filtering and routing
- State recovery

**Key Concepts:**
- Kafka integration
- Redis persistence
- Event schemas
- State snapshots
- Recovery mechanisms

**Run it:**
```bash
python examples/events_and_persistence_example.py
```

---

#### 6. [`demo_json_logging.py`](demo_json_logging.py)
**What it demonstrates:**
- Structured logging with JSON
- Python and Java log integration
- Correlation IDs across services
- Log levels and filtering
- Debugging distributed transactions

**Key Concepts:**
- JSON log formatting
- Log correlation
- Java bridge logging
- Debugging techniques

**Run it:**
```bash
python examples/demo_json_logging.py
```

---

## 📖 Learning Path

We recommend following this sequence for the best learning experience:

### 🎓 Level 1: Foundations (30 minutes)
1. **[`saga_basic.py`](saga_basic.py)** - Understand SAGA basics
   - What is a SAGA?
   - How to define steps
   - How compensation works
   - Success and failure flows

2. **[`tcc_basic.py`](tcc_basic.py)** - Understand TCC basics
   - What is TCC?
   - Try-Confirm-Cancel phases
   - When to use TCC vs SAGA

### 🎓 Level 2: Integration (1 hour)
3. **[`complete_integration_example.py`](complete_integration_example.py)** - Full system understanding
   - How Python and Java communicate
   - How configuration flows
   - How events are published
   - How state is persisted

### 🎓 Level 3: Production Patterns (1 hour)
4. **[`order_saga_comprehensive.py`](order_saga_comprehensive.py)** - Real-world patterns
   - Complex workflows
   - Error handling
   - Idempotency
   - Timeouts and retries

5. **[`events_and_persistence_example.py`](events_and_persistence_example.py)** - Advanced configuration
   - Kafka integration
   - Redis persistence
   - Event routing
   - State recovery

### 🎓 Level 4: Operations (30 minutes)
6. **[`demo_json_logging.py`](demo_json_logging.py)** - Observability
   - Structured logging
   - Debugging techniques
   - Monitoring patterns

---

## 🏃‍♂️ Running Examples

### Method 1: Run Individual Examples
```bash
# From project root directory
python examples/saga_basic.py
python examples/tcc_basic.py
python examples/complete_integration_example.py
```

### Method 2: Use the Taskfile
```bash
# If you have Task installed
task run-example EXAMPLE=saga_basic
task run-example EXAMPLE=tcc_basic
```

### Method 3: Run All Examples
```bash
# Run all examples sequentially
for example in examples/*.py; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running: $example"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    python "$example"
    echo ""
done
```

### Method 4: Interactive Shell
```bash
# Start the FireflyTX shell (like PySpark)
python -m fireflytx.cli shell

# Or with Task
task shell
```

Then in the shell:
```python
# Initialize engines
await init_engines()

# Define and run a SAGA interactively
@saga("test-saga")
class TestSaga:
    @saga_step("step1")
    async def step1(self, data):
        return {"result": "success"}

result = await saga_engine.execute_saga_class(TestSaga, {})
print(result)

# Shutdown
await shutdown_engines()
```

---

## 🏗️ Architecture: "Python Defines, Java Executes"

All examples demonstrate this core architectural principle:

```
┌─────────────────────────────────────┐
│         PYTHON LAYER                │
│  (Define Structure & Logic)         │
├─────────────────────────────────────┤
│ 1. Define SAGA/TCC with decorators  │
│    @saga("order-processing")        │
│    @saga_step("reserve-inventory")  │
│                                     │
│ 2. Implement business logic         │
│    async def reserve_inventory():   │
│        # Your code here             │
│                                     │
│ 3. Configure events & persistence   │
│    EngineConfig(...)                │
└─────────────────────────────────────┘
              ↓
    JSON Configuration & HTTP Callbacks
              ↓
┌─────────────────────────────────────┐
│         JAVA LAYER                  │
│  (lib-transactional-engine)         │
├─────────────────────────────────────┤
│ 1. Receives SAGA/TCC definition     │
│ 2. Orchestrates execution flow      │
│ 3. Manages step dependencies        │
│ 4. Handles retries & timeouts       │
│ 5. Executes compensation on failure │
│ 6. Publishes events to Kafka        │
│ 7. Persists state to Redis          │
│ 8. Calls back to Python methods     │
└─────────────────────────────────────┘
```

### Why This Architecture?

✅ **Best of Both Worlds:**
- Python: Easy to write, test, and maintain business logic
- Java: Battle-tested transaction orchestration and reliability

✅ **Separation of Concerns:**
- Python focuses on "what" (business logic)
- Java focuses on "how" (orchestration, retries, compensation)

✅ **Production-Ready:**
- Java engine handles all the hard distributed systems problems
- Python developers write simple, clean code

---

## 🔍 How Examples Work

### Step-by-Step Execution Flow

Let's trace what happens when you run `saga_basic.py`:

#### 1. **Python Defines the SAGA**
```python
@saga("order-fulfillment")
class OrderFulfillmentSaga:
    @saga_step("reserve-inventory", retry=3)
    async def reserve_inventory(self, order):
        # Your business logic
        return {"reserved": True}
```

#### 2. **Engine Initialization**
```python
saga_engine = SagaEngine()
await saga_engine.initialize()
```
- Python starts Java subprocess
- Loads `lib-transactional-engine.jar`
- Establishes IPC communication

#### 3. **SAGA Execution**
```python
result = await saga_engine.execute_saga_class(
    OrderFulfillmentSaga,
    {"order_id": "ORD-001"}
)
```
- Python sends SAGA definition to Java (JSON)
- Java creates execution plan
- Java calls back to Python methods via HTTP
- Python executes business logic
- Java handles retries, timeouts, compensation

#### 4. **Result Handling**
```python
if result.is_success:
    print("Success!")
else:
    print(f"Failed: {result.error}")
    print(f"Compensated: {result.compensated}")
```

---

## 🧪 Verifying Java Integration

All examples use the **real** Java `lib-transactional-engine`. Here's how to verify:

### Check Java Bridge Status
```bash
python -m fireflytx.cli status
```

Expected output:
```
FireflyTX v2025-08
Python 3.x.x
Task x.x.x

Java Bridge Status:
✅ JAR built: /path/to/.cache/fireflytx/deps/lib-transactional-engine.jar
✅ Java subprocess: Ready
```

### Test Java Integration
```bash
python -m fireflytx.cli test
```

### View Java Logs
When running examples, you'll see Java logs like:
```
[Java] INFO: Starting SAGA execution: order-fulfillment
[Java] INFO: Executing step: reserve-inventory
[Java] INFO: Step completed successfully
```

This confirms the Java engine is actually running!

---

## 🐛 Troubleshooting

### Example Fails to Start

**Problem:** `Java bridge not initialized`

**Solution:**
```bash
# Build the Java bridge
python -m fireflytx.cli build

# Verify it worked
python -m fireflytx.cli status
```

---

### Java Subprocess Errors

**Problem:** `Failed to start Java subprocess`

**Solution:**
```bash
# Check Java is installed
java -version

# Should show Java 11 or higher
# If not, install Java:
# macOS: brew install openjdk@11
# Ubuntu: sudo apt install openjdk-11-jdk
```

---

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'fireflytx'`

**Solution:**
```bash
# Install from source
pip install -e .

# Or run the install script
./install.sh
```

---

### Examples Don't Show Java Logs

**Problem:** Can't see what Java is doing

**Solution:**
```bash
# Run with Java logging enabled
python examples/saga_basic.py --log-level DEBUG

# Or use the JSON logging example
python examples/demo_json_logging.py
```

---

## 🤝 Contributing Examples

Want to add your own example? Great! Follow these guidelines:

### Example Template

```python
#!/usr/bin/env python3
"""
Brief description of what this example demonstrates.

Key Concepts:
- Concept 1
- Concept 2
- Concept 3

Usage:
    python examples/your_example.py
"""

import asyncio
from fireflytx import SagaEngine, saga, saga_step

@saga("your-saga-name")
class YourSaga:
    @saga_step("step1")
    async def step1(self, data):
        # Your logic here
        return {"result": "success"}

async def main():
    # Initialize engine
    engine = SagaEngine()
    await engine.initialize()

    try:
        # Execute SAGA
        result = await engine.execute_saga_class(YourSaga, {})
        print(f"Result: {result}")
    finally:
        # Always shutdown
        await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### Checklist

- [ ] Clear docstring explaining what it demonstrates
- [ ] Uses real Java engine (no mocking)
- [ ] Includes error handling
- [ ] Properly shuts down engine
- [ ] Added to this README with description
- [ ] Tested and working
- [ ] Follows naming convention: `{pattern}_{topic}.py`

---

## 📚 Additional Resources

### Documentation
- 📖 [Main README](../README.md) - Project overview and installation
- 🏗️ [Architecture Guide](../docs/architecture.md) - Deep dive into system design
- 📘 [SAGA Pattern](../docs/saga-pattern.md) - SAGA pattern details
- 📗 [TCC Pattern](../docs/tcc-pattern.md) - TCC pattern details
- 🔧 [API Reference](../docs/api-reference.md) - Complete API documentation

### Tools
- 🐚 [Interactive Shell](../fireflytx/shell.py) - PySpark-like REPL
- 🧪 [Testing Guide](../tests/README.md) - How to test your SAGAs
- ⚙️ [Taskfile](../Taskfile.yml) - Development tasks

### Community
- 🌐 Website: https://getfirefly.io
- 💬 Issues: https://github.com/firefly-oss/python-transactional-engine/issues
- 📚 Docs: https://github.com/firefly-oss/python-transactional-engine

---

## 💡 Tips for Success

1. **Start Simple:** Begin with `saga_basic.py` before moving to complex examples
2. **Use the Shell:** The interactive shell is great for experimentation
3. **Check Java Logs:** They show what's really happening under the hood
4. **Test Failures:** Understanding compensation is key to distributed transactions
5. **Read the Docs:** The architecture guide explains the "why" behind the design

---

**Happy coding with FireflyTX! 🔥**

*Questions? Open an issue on GitHub or check the documentation.*