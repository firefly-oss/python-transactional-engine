# API Reference

Complete API reference for FireflyTX components, classes, and functions.

## Core Components

### SagaEngine

The main engine for executing SAGA transactions.

```python
class SagaEngine:
    def __init__(
        self,
        compensation_policy: str = CompensationPolicy.STRICT_SEQUENTIAL,
        auto_optimization_enabled: bool = True,
        persistence_enabled: bool = False,
        config: Optional[Any] = None,
        event_publisher: Optional[Any] = None,
        persistence_provider: Optional[Any] = None,
    ) -> None
    async def initialize(self) -> None
    async def execute(self, saga_name: str, input_data: Dict[str, Any]) -> SagaResult
    async def execute_by_class(
        self,
        saga_class: type,
        step_inputs: Union[Dict[str, Any], StepInputs],
        context: Optional[SagaContext] = None,
    ) -> SagaResult
    async def register_saga(self, saga_class: type, saga_name: Optional[str] = None) -> None
    async def shutdown(self) -> None
    def is_initialized(self) -> bool
```

**Methods:**

#### `__init__(...)`
Initialize the SAGA engine with optional configuration.

**Parameters:**
- `compensation_policy` (str, optional): Policy for handling compensations. Default: `CompensationPolicy.STRICT_SEQUENTIAL`
- `auto_optimization_enabled` (bool, optional): Enable automatic optimizations. Default: `True`
- `persistence_enabled` (bool, optional): Enable saga persistence. Default: `False`
- `config` (Any, optional): Optional transactional engine configuration
- `event_publisher` (Any, optional): Optional event publisher implementation
- `persistence_provider` (Any, optional): Optional persistence provider implementation

**Example:**
```python
from fireflytx import SagaEngine
from fireflytx.core.compensation_policy import CompensationPolicy

engine = SagaEngine(
    compensation_policy=CompensationPolicy.STRICT_SEQUENTIAL,
    persistence_enabled=True
)
```

#### `initialize()`
Initialize the engine and establish connections to the Java subprocess.

This method starts the subprocess bridge and creates a Java SagaEngine instance. The SagaEngine internally creates the orchestrator and all necessary components for transaction execution.

**Returns:** None

**Raises:**
- `RuntimeError`: If initialization fails

**Example:**
```python
engine = SagaEngine()
await engine.initialize()
```

#### `execute(saga_name, input_data)`
Execute a SAGA transaction by name (compatibility method for tests).

**Parameters:**
- `saga_name` (str): Name of the SAGA to execute
- `input_data` (Dict[str, Any]): Input data for SAGA steps

**Returns:** `SagaResult` - Execution result

**Raises:**
- `RuntimeError`: If engine not initialized

**Example:**
```python
result = await engine.execute("payment-saga", {"amount": 100.0})
```

#### `execute_by_class(saga_class, step_inputs, context=None)`
Execute a SAGA by Python class with pure Java orchestration.

**Parameters:**
- `saga_class` (type): Python class decorated with `@saga`
- `step_inputs` (Union[Dict[str, Any], StepInputs]): Inputs for saga steps
- `context` (Optional[SagaContext]): Optional saga context

**Returns:** `SagaResult` - Execution result containing results from Java engine

**Example:**
```python
@saga("payment-processing")
class PaymentSaga:
    @saga_step("validate")
    async def validate_payment(self, amount: float):
        return {"validated": True}

result = await engine.execute_by_class(PaymentSaga, {"amount": 100.0})
```

#### `register_saga(saga_class, saga_name=None)`
Register a Python saga class with the lib-transactional-engine.

**Parameters:**
- `saga_class` (type): Python class decorated with `@saga`
- `saga_name` (Optional[str]): Optional name override

**Raises:**
- `RuntimeError`: If engine not initialized
- `ValueError`: If class missing `@saga` decorator

#### `shutdown()`
Gracefully shutdown the engine and cleanup resources.

**Example:**
```python
await engine.shutdown()
```

#### `is_initialized()`
Check if the engine is initialized.

**Returns:** `bool` - True if initialized, False otherwise

### TccEngine

The main engine for executing TCC transactions.

```python
class TccEngine:
    def __init__(self, java_bridge: Optional[JavaSubprocessBridge] = None) -> None
    def start(self) -> None
    def execute(
        self,
        tcc_class: Type,
        input_data: dict = None,
        correlation_id: str = None
    ) -> TccResult
    def stop(self) -> None
    def is_running(self) -> bool
```

**Methods:**

#### `__init__(java_bridge=None)`
Initialize the TCC engine.

**Parameters:**
- `java_bridge` (Optional[JavaSubprocessBridge]): Optional Java bridge instance. If not provided, a new one is created.

**Example:**
```python
from fireflytx import TccEngine

engine = TccEngine()
```

#### `start()`
Start the TCC engine.

This method starts the Java subprocess bridge.

**Example:**
```python
engine = TccEngine()
engine.start()
```

#### `execute(tcc_class, input_data=None, correlation_id=None)`
Execute a TCC transaction with Python-defined participants via Java subprocess bridge.

**Parameters:**
- `tcc_class` (Type): The TCC transaction class decorated with `@tcc`
- `input_data` (dict, optional): Input data for TCC participants
- `correlation_id` (str, optional): Unique identifier for this transaction instance

**Returns:** `TccResult` - Execution outcome with phase details

**Raises:**
- `RuntimeError`: If engine is not running
- `ValueError`: If class is not decorated with `@tcc`

**Example:**
```python
@tcc("payment-processing")
class PaymentTcc:
    @tcc_participant("payment")
    class PaymentParticipant:
        @try_method
        async def try_payment(self, amount: float):
            return {"reserved": True}

        @confirm_method
        async def confirm_payment(self, reservation):
            pass

        @cancel_method
        async def cancel_payment(self, reservation):
            pass

result = engine.execute(PaymentTcc, {"amount": 100.0})
```

#### `stop()`
Stop the TCC engine and cleanup resources.

**Example:**
```python
engine.stop()
```

#### `is_running()`
Check if the engine is running.

**Returns:** `bool` - True if running, False otherwise

## Decorators

### SAGA Decorators

#### `@saga(name, layer_concurrency=5)`

Mark a class as a SAGA transaction.

**Parameters:**
- `name` (str): SAGA name (required)
- `layer_concurrency` (int, optional): Maximum concurrency within execution layers. Default: `5`

**Example:**
```python
from fireflytx.decorators.saga import saga

@saga("order-processing", layer_concurrency=10)
class OrderSaga:
    pass
```

#### `@saga_step(step_id, **kwargs)`

Mark a method as a SAGA step.

**Parameters:**
- `step_id` (str): Unique identifier for the step (required)
- `depends_on` (Union[str, List[str]], optional): Step IDs this step depends on
- `retry` (int, optional): Number of retry attempts. Default: `3`
- `backoff_ms` (int, optional): Backoff time between retries in milliseconds. Default: `1000`
- `timeout_ms` (int, optional): Step timeout in milliseconds. Default: `30000`
- `jitter` (bool, optional): Enable jitter in retry backoff. Default: `True`
- `jitter_factor` (float, optional): Jitter factor for backoff randomization. Default: `0.3`
- `cpu_bound` (bool, optional): Whether this is a CPU-bound operation. Default: `False`
- `idempotency_key` (Optional[str], optional): Key for idempotent execution
- `compensate` (Optional[str], optional): Name of the compensation method
- `compensation_retry` (int, optional): Number of compensation retry attempts. Default: `3`
- `compensation_timeout_ms` (int, optional): Compensation timeout in milliseconds. Default: `10000`
- `compensation_critical` (bool, optional): Whether compensation failure is critical. Default: `False`

**Example:**
```python
from fireflytx.decorators.saga import saga_step

@saga_step(
    "process_payment",
    depends_on=["validate_order"],
    compensate="refund_payment",
    retry=5,
    timeout_ms=10000,
    backoff_ms=2000
)
async def process_payment(self, order: dict) -> dict:
    # Process payment logic
    return {"transaction_id": "tx_123"}
```

#### `@compensation_step(for_step_id)`

Mark a method as a compensation step.

**Parameters:**
- `for_step_id` (str): The step ID this method compensates for (required)

**Example:**
```python
from fireflytx.decorators.saga import compensation_step

@compensation_step("process_payment")
async def refund_payment(self, payment_result: dict) -> None:
    # Refund logic
    pass
```

#### `@step_events(**kwargs)`

Configure event publishing for a SAGA step. This decorator should be applied before `@saga_step`.

**Parameters:**
- `enabled` (bool, optional): Whether event publishing is enabled. Default: `True`
- `topic` (Optional[str], optional): Custom topic for step events
- `key_template` (Optional[str], optional): Template for event keys (e.g., `"{saga_id}-{step_id}"`)
- `include_payload` (bool, optional): Include step payload in events. Default: `True`
- `include_context` (bool, optional): Include SAGA context in events. Default: `True`
- `include_result` (bool, optional): Include step results in events. Default: `True`
- `include_timing` (bool, optional): Include timing information in events. Default: `True`
- `custom_headers` (Optional[Dict[str, str]], optional): Custom headers to add to events
- `publish_on_start` (bool, optional): Publish event when step starts. Default: `True`
- `publish_on_success` (bool, optional): Publish event when step succeeds. Default: `True`
- `publish_on_failure` (bool, optional): Publish event when step fails. Default: `True`
- `publish_on_retry` (bool, optional): Publish event on step retry. Default: `False`
- `publish_on_compensation` (bool, optional): Publish event during compensation. Default: `True`

**Example:**
```python
from fireflytx.decorators.saga import step_events, saga_step

@step_events(
    topic="payment-events",
    key_template="{saga_id}-payment",
    publish_on_retry=True
)
@saga_step("process_payment")
async def process_payment(self, order_id: str) -> dict:
    # Implementation
    pass
```

#### `@compensation_step(step_id)`

Mark a method as a compensation step.

**Parameters:**
- `step_id` (str): Step to compensate

**Example:**
```python
@compensation_step("process_payment")
async def refund_payment(self, result: PaymentResult) -> None:
    pass
```

### TCC Decorators

#### `@tcc(name, **kwargs)`

Mark a class as a TCC transaction.

**Parameters:**
- `name` (str): TCC name
- `timeout_ms` (int, optional): Global timeout

#### `@tcc_participant(participant_id, **kwargs)`

Mark a nested class as a TCC participant.

**Parameters:**
- `participant_id` (str): Unique participant identifier
- `order` (int, optional): Execution order

#### `@try_method(**kwargs)`

Mark a method as a TCC try method.

**Parameters:**
- `timeout_ms` (int, optional): Method timeout
- `retry` (int, optional): Retry attempts
- `backoff_ms` (int, optional): Retry backoff

#### `@confirm_method(**kwargs)`

Mark a method as a TCC confirm method.

#### `@cancel_method(**kwargs)`

Mark a method as a TCC cancel method.

## Core Data Types

### SagaResult

Result of SAGA execution.

```python
@dataclass
class SagaResult:
    saga_name: str
    correlation_id: str
    is_success: bool
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: int
    steps_completed: int
    steps_total: int
    compensation_steps: int
    error_message: Optional[str]
    step_results: Dict[str, Any]
    context_variables: Dict[str, Any]
```

**Properties:**

- `saga_name`: Name of executed SAGA
- `correlation_id`: Unique execution identifier
- `is_success`: Whether execution succeeded
- `start_time`: Execution start time
- `end_time`: Execution end time
- `duration_ms`: Total execution time in milliseconds
- `steps_completed`: Number of completed steps
- `steps_total`: Total number of steps
- `compensation_steps`: Number of compensation steps executed
- `error_message`: Error message if failed
- `step_results`: Results from individual steps
- `context_variables`: SAGA context variables

### TccResult

Result of TCC execution.

```python
@dataclass
class TccResult:
    tcc_name: str
    transaction_id: str
    is_success: bool
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: int
    participants_completed: int
    participants_total: int
    phase_reached: str  # "try", "confirm", "cancel"
    cancelled_participants: int
    error_message: Optional[str]
    participant_results: Dict[str, Any]
    context_variables: Dict[str, Any]
```

### SagaContext

Execution context for SAGA transactions.

```python
class SagaContext:
    def __init__(self, correlation_id: str) -> None
    def set_variable(self, key: str, value: Any) -> None
    def get_variable(self, key: str, default: Any = None) -> Any
    def put_header(self, key: str, value: str) -> None
    def get_header(self, key: str, default: str = None) -> Optional[str]
    def get_all_variables(self) -> Dict[str, Any]
    def get_all_headers(self) -> Dict[str, str]
```

**Methods:**

#### `set_variable(key, value)`
Store a variable in the context.

#### `get_variable(key, default=None)`
Retrieve a variable from the context.

#### `put_header(key, value)`
Set a header value.

#### `get_header(key, default=None)`
Get a header value.

### TccContext

Execution context for TCC transactions.

```python
class TccContext:
    def __init__(self, transaction_id: str) -> None
    def set_variable(self, key: str, value: Any) -> None
    def get_variable(self, key: str, default: Any = None) -> Any
    def put_header(self, key: str, value: str) -> None
    def get_header(self, key: str, default: str = None) -> Optional[str]
    def get_participant_result(self, participant_id: str) -> Optional[Any]
    def set_participant_result(self, participant_id: str, result: Any) -> None
```

## Configuration

### EngineConfig

Main engine configuration.

```python
@dataclass
class EngineConfig:
    max_concurrent_executions: int = 50
    default_timeout_ms: int = 30000
    enable_metrics: bool = True
    enable_events: bool = True
    thread_pool_size: int = 10
    connection_pool_size: int = 20
    retry_policy: str = "exponential_backoff"
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 30000
    
    def validate_configuration(self) -> List[str]
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'EngineConfig'
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'EngineConfig'
```

### PersistenceConfig

Persistence configuration.

```python
@dataclass
class PersistenceConfig:
    type: str = "memory"  # "memory", "file", "redis"
    connection_string: Optional[str] = None
    file_path: Optional[str] = None
    auto_checkpoint: bool = True
    checkpoint_interval_ms: int = 10000
    max_entries: int = 10000
    eviction_policy: str = "lru"
    
    def validate(self) -> List[str]
```

### EventConfig

Event system configuration.

```python
@dataclass
class EventConfig:
    enable_events: bool = True
    async_publishing: bool = True
    event_buffer_size: int = 1000
    max_event_handlers: int = 10
    handler_timeout_ms: int = 5000
    dead_letter_queue_enabled: bool = True
    retry_failed_events: bool = True
    max_retries: int = 3
    event_persistence_enabled: bool = False
```

## Events System

### SagaEvents

Base class for SAGA event handlers.

```python
class SagaEvents:
    async def on_saga_started(self, saga_name: str, correlation_id: str) -> None
    async def on_saga_completed(self, saga_name: str, correlation_id: str, success: bool, duration_ms: int) -> None
    async def on_step_started(self, step_id: str, correlation_id: str) -> None
    async def on_step_completed(self, step_id: str, correlation_id: str, result: Any, duration_ms: int) -> None
    async def on_step_failed(self, step_id: str, correlation_id: str, error: Exception) -> None
    async def on_compensation_started(self, step_id: str, correlation_id: str) -> None
    async def on_compensation_completed(self, step_id: str, correlation_id: str, duration_ms: int) -> None
    async def on_compensation_failed(self, step_id: str, correlation_id: str, error: Exception) -> None
```

### TccEvents

Base class for TCC event handlers.

```python
class TccEvents:
    async def on_tcc_started(self, tcc_name: str, transaction_id: str) -> None
    async def on_tcc_completed(self, tcc_name: str, transaction_id: str, success: bool, duration_ms: int) -> None
    async def on_try_phase_started(self, participants: List[str], transaction_id: str) -> None
    async def on_try_phase_completed(self, participants: List[str], transaction_id: str, duration_ms: int) -> None
    async def on_participant_try_started(self, participant_id: str, transaction_id: str) -> None
    async def on_participant_try_completed(self, participant_id: str, transaction_id: str, result: Any, duration_ms: int) -> None
    async def on_participant_try_failed(self, participant_id: str, transaction_id: str, error: Exception) -> None
    async def on_confirm_phase_started(self, participants: List[str], transaction_id: str) -> None
    async def on_cancel_phase_started(self, participants: List[str], transaction_id: str, reason: str) -> None
```

## Visualization

### SagaVisualizer

SAGA topology visualization.

```python
class SagaVisualizer:
    def __init__(self) -> None
    def analyze_saga_class(self, saga_class: type) -> SagaTopologyGraph
    def visualize_saga(self, saga_class: type, format: OutputFormat = OutputFormat.ASCII) -> str
    def validate_topology(self, topology: SagaTopologyGraph) -> List[str]
    def generate_execution_plan(self, topology: SagaTopologyGraph) -> List[List[str]]
```

#### `analyze_saga_class(saga_class)`
Analyze a SAGA class and extract topology information.

**Parameters:**
- `saga_class` (type): Class decorated with @saga

**Returns:** `SagaTopologyGraph` - Topology information

#### `visualize_saga(saga_class, format)`
Generate visual representation of SAGA topology.

**Parameters:**
- `saga_class` (type): SAGA class to visualize
- `format` (OutputFormat): Output format (ASCII, DOT, MERMAID, JSON)

**Returns:** str - Formatted visualization

### TccVisualizer

TCC topology visualization.

```python
class TccVisualizer:
    def __init__(self) -> None
    def analyze_tcc_class(self, tcc_class: type) -> TccTopologyGraph
    def visualize_tcc(self, tcc_class: type, format: OutputFormat = OutputFormat.ASCII) -> str
    def get_phase_diagram(self, topology: TccTopologyGraph) -> str
    def validate_topology(self, topology: TccTopologyGraph) -> List[str]
```

### OutputFormat

Enumeration of output formats.

```python
class OutputFormat(Enum):
    ASCII = "ascii"
    DOT = "dot"
    MERMAID = "mermaid"
    JSON = "json"
```

## Java Integration

### JVMManager

Java Virtual Machine lifecycle management.

```python
class JVMManager:
    def __init__(self) -> None
    def start_jvm(self, config: Optional[JvmConfig] = None) -> None
    def is_jvm_started(self) -> bool
    def get_java_class(self, class_name: str) -> Any
    def shutdown(self) -> None
    def get_jvm_info(self) -> Dict[str, Any]
```

#### `start_jvm(config)`
Start the Java Virtual Machine.

**Parameters:**
- `config` (JvmConfig, optional): JVM configuration

**Raises:**
- `JvmStartupError`: If JVM startup fails

#### `is_jvm_started()`
Check if JVM is running.

**Returns:** bool - True if JVM is started

#### `get_java_class(class_name)`
Load and return a Java class.

**Parameters:**
- `class_name` (str): Fully qualified Java class name

**Returns:** Java class object

### get_jvm_manager()

Get the singleton JVM manager instance.

```python
def get_jvm_manager() -> JVMManager:
    """Get the global JVM manager instance."""
```

## Logging

### JavaLogBridge

Bridge for capturing Java library logs.

```python
class JavaLogBridge:
    def __init__(self) -> None
    def enable(self) -> None
    def disable(self) -> None
    def start_capturing(self) -> None
    def stop_capturing(self) -> None
    def set_level(self, level: JavaLogLevel) -> None
    def get_recent_logs(self, count: int = 100) -> List[JavaLogEntry]
    def get_statistics(self) -> Dict[str, Any]
    def clear_buffer(self) -> None
```

#### `enable()`
Enable the Java log bridge.

#### `start_capturing()`
Start capturing Java logs.

#### `get_recent_logs(count)`
Get recent log entries.

**Parameters:**
- `count` (int): Number of entries to retrieve

**Returns:** List[JavaLogEntry] - Recent log entries

### JavaLogLevel

Log level enumeration.

```python
class JavaLogLevel(Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
```

### JavaLogEntry

Individual log entry.

```python
@dataclass
class JavaLogEntry:
    timestamp: datetime
    level: JavaLogLevel
    logger_name: str
    message: str
    thread_name: str
    exception: Optional[str] = None
```

### get_java_log_bridge()

Get the Java log bridge instance.

```python
def get_java_log_bridge() -> JavaLogBridge:
    """Get the global Java log bridge instance."""
```

## Utilities

### Helpers

Common utility functions.

```python
def generate_correlation_id() -> str:
    """Generate a unique correlation ID."""

def format_duration(duration_ms: int) -> str:
    """Format duration in milliseconds to human readable format."""

def is_async_function(func: Callable) -> bool:
    """Check if a function is async."""

def extract_type_hints(func: Callable) -> Dict[str, Any]:
    """Extract type hints from function signature."""
```

### Type Conversion

Type conversion utilities for Java-Python interop.

```python
def python_to_java(value: Any) -> Any:
    """Convert Python value to Java equivalent."""

def java_to_python(value: Any) -> Any:
    """Convert Java value to Python equivalent."""

def serialize_for_java(obj: Any) -> str:
    """Serialize Python object for Java consumption."""

def deserialize_from_java(json_str: str) -> Any:
    """Deserialize object from Java JSON representation."""
```

## Exceptions

### Base Exceptions

```python
class FireflyTXError(Exception):
    """Base exception for FireflyTX."""

class EngineError(FireflyTXError):
    """Base exception for engine-related errors."""

class ConfigurationError(FireflyTXError):
    """Configuration validation error."""
```

### SAGA Exceptions

```python
class SagaError(EngineError):
    """Base SAGA exception."""

class SagaExecutionError(SagaError):
    """SAGA execution failed."""

class SagaTimeoutError(SagaError):
    """SAGA execution timeout."""

class SagaStepError(SagaError):
    """SAGA step execution error."""

class CompensationError(SagaError):
    """Compensation execution error."""
```

### TCC Exceptions

```python
class TccError(EngineError):
    """Base TCC exception."""

class TccExecutionError(TccError):
    """TCC execution failed."""

class TccTryFailedException(TccError):
    """TCC try phase failed."""

class TccConfirmFailedException(TccError):
    """TCC confirm phase failed."""

class TccCancelFailedException(TccError):
    """TCC cancel phase failed."""

class TccTimeoutError(TccError):
    """TCC operation timeout."""
```

### JVM Exceptions

```python
class JvmError(FireflyTXError):
    """Base JVM exception."""

class JvmStartupError(JvmError):
    """JVM startup failed."""

class JvmNotAvailableError(JvmError):
    """JVM not available."""

class JavaClassNotFoundError(JvmError):
    """Java class not found."""
```

## CLI Reference

### Command Structure

```bash
fireflytx [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGS]
```

### Global Options

- `--config FILE`: Configuration file path
- `--verbose`: Enable verbose output
- `--quiet`: Suppress output
- `--help`: Show help message

### Commands

#### `status`
Show engine and system status.

```bash
fireflytx status [--json]
```

#### `test`
Test system connectivity and configuration.

```bash
fireflytx test [--timeout SECONDS]
```

#### `validate`
Validate SAGA/TCC definitions.

```bash
fireflytx validate FILE [--class CLASS_NAME] [--strict]
```

#### `visualize`
Generate topology visualizations.

```bash
fireflytx visualize FILE CLASS_NAME [--format FORMAT] [--output FILE]
```

#### `java-logs`
Manage Java logging.

```bash
fireflytx java-logs [--level LEVEL] [--count COUNT] [--follow] [--enable] [--disable]
```

#### `jar-info`
Show JAR file information.

```bash
fireflytx jar-info [--build-info] [--verify]
```

#### `run-example`
Run built-in examples.

```bash
fireflytx run-example EXAMPLE_NAME [--args ARGS]
```

#### `init-config`
Generate configuration files.

```bash
fireflytx init-config [OUTPUT_FILE] [--template TEMPLATE]
```

For detailed usage of each command, use:
```bash
fireflytx COMMAND --help
```

This API reference covers all public interfaces in FireflyTX. For implementation examples, see the [SAGA Pattern Guide](saga-pattern.md) and [TCC Pattern Guide](tcc-pattern.md).