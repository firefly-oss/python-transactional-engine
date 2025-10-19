# Configuration Reference

FireflyTX provides comprehensive configuration options for engine behavior, persistence, JVM integration, and observability. This guide covers all available configuration parameters and their usage.

## Quick Start

### Default Configuration (Development)

The simplest way to get started - uses sensible defaults:

```python
from fireflytx import SagaEngine, TccEngine

# ✅ Uses default configuration
saga_engine = SagaEngine()
await saga_engine.initialize()

tcc_engine = TccEngine()
tcc_engine.start()
```

**Default Values:**
- `max_concurrent_executions`: 100
- `default_timeout_ms`: 30000 (30 seconds)
- `thread_pool_size`: 50
- `enable_monitoring`: True
- `persistence.type`: "memory" (in-memory, not for production)
- `jvm.heap_size`: "256m"
- `retry_config.max_attempts`: 3
- `retry_config.backoff_multiplier`: 2.0

### Production Configuration

For production deployments, use `EngineConfig`:

```python
from fireflytx import SagaEngine, TccEngine, EngineConfig, PersistenceConfig, JvmConfig

# Create production configuration
config = EngineConfig(
    max_concurrent_executions=200,
    default_timeout_ms=60000,
    thread_pool_size=100,
    enable_monitoring=True,

    persistence=PersistenceConfig(
        type="redis",
        connection_string="redis://prod-redis:6379",
        auto_checkpoint=True
    ),

    jvm=JvmConfig(
        heap_size="2g",
        gc_algorithm="G1GC"
    )
)

# Use with engines
saga_engine = SagaEngine(config=config)
await saga_engine.initialize()

tcc_engine = TccEngine(config=config)
tcc_engine.start()
```

## Configuration Sources

FireflyTX supports multiple configuration sources in order of precedence:

1. **Environment Variables** (highest priority)
2. **YAML Configuration Files**
3. **Python Configuration Objects**
4. **Default Values** (lowest priority)

## Engine Configuration

### EngineConfig

Core engine configuration settings:

```python
from fireflytx.config import EngineConfig, RetryConfig

config = EngineConfig(
    # Execution settings
    max_concurrent_executions=100,        # Maximum concurrent transactions
    default_timeout_ms=30000,             # Default operation timeout (ms)
    thread_pool_size=50,                  # Thread pool for async operations
    enable_monitoring=True,               # Enable metrics and monitoring
    enable_transaction_logging=True,      # Enable detailed transaction logs
    transaction_cleanup_interval_seconds=300,  # Cleanup interval

    # Retry configuration
    retry_config=RetryConfig(
        max_attempts=3,
        initial_delay_ms=1000,
        max_delay_ms=30000,
        backoff_multiplier=2.0
    )
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_concurrent_executions` | int | 100 | Maximum number of concurrent transactions |
| `default_timeout_ms` | int | 30000 | Default timeout for operations (milliseconds) |
| `enable_monitoring` | bool | True | Enable performance metrics collection |
| `thread_pool_size` | int | 50 | Size of thread pool for async operations |
| `transaction_cleanup_interval_seconds` | int | 300 | Transaction cleanup interval (seconds) |
| `enable_transaction_logging` | bool | True | Enable detailed transaction logging |

### RetryConfig

Configure retry behavior for failed operations:

```python
from fireflytx.config import RetryConfig

retry_config = RetryConfig(
    max_attempts=3,              # Maximum retry attempts
    initial_delay_ms=1000,       # Initial delay between retries
    max_delay_ms=30000,          # Maximum delay between retries
    backoff_multiplier=2.0       # Exponential backoff multiplier
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_attempts` | int | 3 | Maximum number of retry attempts |
| `initial_delay_ms` | int | 1000 | Initial delay between retries (ms) |
| `max_delay_ms` | int | 30000 | Maximum delay between retries (ms) |
| `backoff_multiplier` | float | 2.0 | Exponential backoff multiplier |

## Persistence Configuration

### PersistenceConfig

Configure transaction state persistence:

```python
from fireflytx.config import PersistenceConfig

# Memory Configuration (development only - default)
memory_config = PersistenceConfig(
    type="memory"  # No persistence, data lost on restart
)

# Redis Configuration (recommended for production)
redis_config = PersistenceConfig(
    type="redis",
    connection_string="redis://localhost:6379",
    auto_checkpoint=True,
    checkpoint_interval_seconds=60,
    max_transaction_age_hours=24,
    redis_config={
        "db": 0,
        "password": "your-password",
        "ssl": True,
        "max_connections": 50
    }
)

# PostgreSQL Configuration
postgresql_config = PersistenceConfig(
    type="postgresql",
    connection_string="postgresql://user:pass@localhost:5432/fireflytx",
    auto_checkpoint=True,
    checkpoint_interval_seconds=60,
    postgresql_config={
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30
    }
)

# File-based Configuration
file_config = PersistenceConfig(
    type="file",
    connection_string="/var/lib/fireflytx/transactions",
    auto_checkpoint=True,
    checkpoint_interval_seconds=60,
    file_config={
        "backup_enabled": True,
        "max_backup_files": 10,
        "compress": True
    }
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | str | "memory" | Persistence type: memory, redis, postgresql, file |
| `connection_string` | str | "" | Connection string for the persistence store |
| `auto_checkpoint` | bool | True | Enable automatic checkpointing |
| `checkpoint_interval_seconds` | int | 60 | Checkpoint interval (seconds) |
| `max_transaction_age_hours` | int | 24 | Maximum age before cleanup (hours) |
| `redis_config` | dict | None | Redis-specific configuration |
| `postgresql_config` | dict | None | PostgreSQL-specific configuration |
| `file_config` | dict | None | File-specific configuration |

### Environment Variables

```bash
# Persistence Configuration
export FIREFLYTX_PERSISTENCE_TYPE=redis
export FIREFLYTX_PERSISTENCE_CONNECTION_STRING=redis://localhost:6379
export FIREFLYTX_PERSISTENCE_AUTO_CHECKPOINT=true
export FIREFLYTX_PERSISTENCE_CHECKPOINT_INTERVAL_SECONDS=60
```

## JVM Configuration

### JvmConfig

Configure Java Virtual Machine integration:

```python
from fireflytx.config import JvmConfig

# Default JVM Configuration (development)
default_jvm = JvmConfig(
    heap_size="256m"  # Minimal heap for development
)

# Production JVM Configuration
production_jvm = JvmConfig(
    heap_size="2g",                       # Initial heap size
    gc_algorithm="G1GC",                  # Garbage collector algorithm
    max_gc_pause_ms=200,                  # Maximum GC pause time
    additional_jvm_args=[                 # Additional JVM arguments
        "-XX:+UseStringDeduplication",
        "-XX:+OptimizeStringConcat",
        "-Djava.awt.headless=true"
    ],
    system_properties={                   # Java system properties
        "file.encoding": "UTF-8",
        "user.timezone": "UTC"
    }
)

# High-Performance JVM Configuration
high_perf_jvm = JvmConfig(
    heap_size="4g",
    gc_algorithm="G1GC",
    max_gc_pause_ms=100,
    additional_jvm_args=[
        "-XX:+UseStringDeduplication",
        "-XX:+OptimizeStringConcat",
        "-XX:+UseCompressedOops",
        "-XX:+UseCompressedClassPointers",
        "-XX:ReservedCodeCacheSize=512m"
    ]
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `heap_size` | str | "256m" | JVM heap size (e.g., "256m", "1g", "2g") |
| `gc_algorithm` | str | None | GC algorithm: "G1GC", "ZGC", "ParallelGC" |
| `max_gc_pause_ms` | int | None | Maximum GC pause time (milliseconds) |
| `additional_jvm_args` | list | [] | Additional JVM arguments |
| `system_properties` | dict | {} | Java system properties |

### Environment Variables

```bash
# JVM Configuration
export FIREFLYTX_JVM_HEAP_SIZE=2g
export FIREFLYTX_JVM_GC_ALGORITHM=G1GC
export FIREFLYTX_JVM_MAX_GC_PAUSE_MS=200
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `heap_size` | str | "512m" | Initial heap size |
| `max_heap_size` | str | "1g" | Maximum heap size |
| `additional_jvm_args` | List[str] | [] | Additional JVM arguments |
| `jar_path` | str | Auto-detected | Path to JAR file |
| `enable_jmx` | bool | False | Enable JMX monitoring |
| `jmx_port` | int | 9999 | JMX port number |
| `debug_enabled` | bool | False | Enable remote debugging |
| `debug_port` | int | 5005 | Debug port number |
| `force_subprocess` | bool | False | Force subprocess bridge mode |

### Environment Variables

```bash
export FIREFLYTX_JVM_HEAP_SIZE=2g
export FIREFLYTX_JVM_MAX_HEAP_SIZE=4g
export FIREFLYTX_JVM_ADDITIONAL_ARGS="-XX:+UseG1GC,-XX:MaxGCPauseMillis=100"
export FIREFLYTX_FORCE_SUBPROCESS=false
export FIREFLYTX_ENABLE_JMX=true
export FIREFLYTX_JMX_PORT=9999
```

## Event Configuration

### EventConfig

Configure event system behavior and external event publishing (Kafka, Redis, etc.):

#### Basic Event Configuration

```python
from fireflytx.config import EventConfig

event_config = EventConfig(
    enabled=True,                         # Enable event system
    provider="memory",                    # Event provider: "memory", "kafka", "redis"
)
```

#### Kafka Event Publishing

FireflyTX supports publishing SAGA and TCC events to Kafka via the Java lib-transactional-engine. Events are published by the Java engine, ensuring reliability and performance.

```python
from fireflytx import EngineConfig, JvmConfig
from fireflytx.config import EventConfig

config = EngineConfig(
    max_concurrent_executions=50,
    default_timeout_ms=30000,
    events=EventConfig(
        enabled=True,
        provider="kafka",                 # Use Kafka for event publishing
        kafka_config={
            "bootstrap_servers": "localhost:9092",
            "client_id": "fireflytx-app",
            "acks": "all",                # Wait for all replicas
            "compression_type": "gzip",   # Compress messages
            "max_in_flight_requests_per_connection": 5,
            "retries": 3
        },
        saga_topic="fireflytx.saga.events",    # Topic for SAGA step events
        tcc_topic="fireflytx.tcc.events"       # Topic for TCC transaction events
    ),
    jvm=JvmConfig(
        heap_size="512m",
        gc_algorithm="G1GC"
    )
)

# Use with SagaEngine or TccEngine
from fireflytx import SagaEngine
engine = SagaEngine(config=config)
await engine.initialize()
```

**Event Types Published:**

| Event Type | Topic | Description |
|------------|-------|-------------|
| SAGA Step Events | `saga_topic` | Step started, completed, failed, compensated |
| TCC Transaction Events | `tcc_topic` | Try, confirm, cancel phase events |

**Kafka Configuration Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bootstrap_servers` | str | "localhost:9092" | Kafka broker addresses |
| `client_id` | str | "fireflytx" | Client identifier |
| `acks` | str | "all" | Acknowledgment mode ("0", "1", "all") |
| `compression_type` | str | "gzip" | Compression algorithm |
| `max_in_flight_requests_per_connection` | int | 5 | Max unacknowledged requests |
| `retries` | int | 3 | Number of retries for failed sends |

**Event Configuration Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | True | Enable event system |
| `provider` | str | "memory" | Event provider ("memory", "kafka", "redis") |
| `kafka_config` | dict | {} | Kafka-specific configuration |
| `saga_topic` | str | "fireflytx.saga.events" | Topic for SAGA events |
| `tcc_topic` | str | "fireflytx.tcc.events" | Topic for TCC events |

## Logging Configuration

Configure Java logging bridge and Python logging:

```python
from fireflytx.logging import JavaLogLevel

# Java logging configuration
java_logging_config = {
    "enabled": True,                      # Enable Java log bridge
    "level": JavaLogLevel.INFO,           # Minimum log level
    "buffer_size": 1000,                  # Log entry buffer size
    "auto_start": True,                   # Start capturing automatically
    "include_stack_traces": True,         # Include stack traces
    "format_logs": True,                  # Format logs for display
    "color_output": True                  # Enable colored output
}

# Python logging configuration
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fireflytx.log")
    ]
)
```

## Configuration Helpers

FireflyTX provides configuration helpers to quickly set up engines for different environments.

### Default Configuration (Development)

```python
from fireflytx import SagaEngine, TccEngine
from fireflytx.config import ConfigurationManager

# Get default development configuration
config = ConfigurationManager.get_default_config()

saga_engine = SagaEngine(config=config)
await saga_engine.initialize()

tcc_engine = TccEngine(config=config)
tcc_engine.start()
```

**Default Configuration Includes:**
- Max concurrent executions: 100
- Default timeout: 30 seconds
- Thread pool size: 50
- JVM heap: 256MB
- Persistence: In-memory (no persistence)
- Retry: 3 attempts with exponential backoff

### Production Configuration

```python
from fireflytx.config import ConfigurationManager

# Get production configuration with custom settings
config = ConfigurationManager.get_production_config(
    persistence_type="redis",
    persistence_connection_string="redis://prod-redis:6379",
    heap_size="2g",
    max_concurrent_executions=200
)

saga_engine = SagaEngine(config=config)
await saga_engine.initialize()
```

**Production Configuration Includes:**
- Max concurrent executions: 200 (customizable)
- Default timeout: 60 seconds
- Thread pool size: 100
- JVM heap: 2GB (customizable)
- Persistence: Redis with auto-checkpointing (customizable)
- Retry: 5 attempts with exponential backoff
- GC: G1GC with 200ms max pause
- Transaction cleanup: Every 5 minutes

### High-Performance Configuration

```python
from fireflytx.config import ConfigurationManager

# Get high-performance configuration
config = ConfigurationManager.get_high_performance_config(
    persistence_connection_string="redis://redis-cluster:6379"
)

saga_engine = SagaEngine(config=config)
await saga_engine.initialize()
```

**High-Performance Configuration Includes:**
- Max concurrent executions: 500
- Default timeout: 30 seconds
- Thread pool size: 200
- JVM heap: 4GB
- Persistence: Redis with high connection pool (200 connections)
- Retry: 3 attempts with fast backoff
- GC: G1GC with 100ms max pause
- Optimized JVM flags for throughput

## Complete Configuration Examples

### Development Configuration

Minimal configuration for local development:

```python
from fireflytx import SagaEngine, TccEngine, EngineConfig

# Use defaults - perfect for development
config = EngineConfig()

saga_engine = SagaEngine(config=config)
await saga_engine.initialize()

tcc_engine = TccEngine(config=config)
tcc_engine.start()
```

### Production Configuration

Complete production-ready configuration:

```python
from fireflytx import (
    SagaEngine, TccEngine, EngineConfig,
    PersistenceConfig, JvmConfig, RetryConfig
)

# Production configuration
config = EngineConfig(
    # Execution settings
    max_concurrent_executions=200,
    default_timeout_ms=60000,
    thread_pool_size=100,
    enable_monitoring=True,
    enable_transaction_logging=True,
    transaction_cleanup_interval_seconds=300,

    # Retry configuration
    retry_config=RetryConfig(
        max_attempts=5,
        initial_delay_ms=1000,
        max_delay_ms=60000,
        backoff_multiplier=2.0
    ),

    # Persistence configuration
    persistence=PersistenceConfig(
        type="redis",
        connection_string="redis://prod-redis:6379",
        auto_checkpoint=True,
        checkpoint_interval_seconds=60,
        max_transaction_age_hours=24,
        redis_config={
            "db": 0,
            "password": "your-secure-password",
            "ssl": True,
            "max_connections": 100
        }
    ),

    # JVM configuration
    jvm=JvmConfig(
        heap_size="2g",
        gc_algorithm="G1GC",
        max_gc_pause_ms=200,
        additional_jvm_args=[
            "-XX:+UseStringDeduplication",
            "-XX:+OptimizeStringConcat",
            "-Djava.awt.headless=true"
        ],
        system_properties={
            "file.encoding": "UTF-8",
            "user.timezone": "UTC"
        }
    )
)

# Initialize engines
saga_engine = SagaEngine(config=config)
await saga_engine.initialize()

tcc_engine = TccEngine(config=config)
tcc_engine.start()
```

### High-Performance Configuration

Optimized for high-throughput scenarios:

```python
from fireflytx import EngineConfig, PersistenceConfig, JvmConfig

config = EngineConfig(
    max_concurrent_executions=500,
    default_timeout_ms=30000,
    thread_pool_size=200,
    enable_monitoring=True,

    persistence=PersistenceConfig(
        type="redis",
        connection_string="redis://redis-cluster:6379",
        auto_checkpoint=True,
        checkpoint_interval_seconds=30,
        redis_config={
            "max_connections": 200,
            "connection_pool_timeout": 5
        }
    ),

    jvm=JvmConfig(
        heap_size="4g",
        gc_algorithm="G1GC",
        max_gc_pause_ms=100,
        additional_jvm_args=[
            "-XX:+UseStringDeduplication",
            "-XX:+OptimizeStringConcat",
            "-XX:+UseCompressedOops",
            "-XX:ReservedCodeCacheSize=512m"
        ]
    )
)

saga_engine = SagaEngine(config=config)
await saga_engine.initialize()
```

## YAML Configuration

Complete configuration file example:

```yaml
# fireflytx-config.yaml
engine:
  max_concurrent_executions: 200
  default_timeout_ms: 60000
  thread_pool_size: 100
  enable_monitoring: true
  enable_transaction_logging: true
  transaction_cleanup_interval_seconds: 300

retry:
  max_attempts: 5
  initial_delay_ms: 1000
  max_delay_ms: 60000
  backoff_multiplier: 2.0

persistence:
  type: redis
  connection_string: "redis://localhost:6379"
  auto_checkpoint: true
  checkpoint_interval_seconds: 60
  max_transaction_age_hours: 24
  redis_config:
    db: 0
    password: ${REDIS_PASSWORD}
    ssl: true
    max_connections: 100

jvm:
  heap_size: "2g"
  gc_algorithm: "G1GC"
  max_gc_pause_ms: 200
  additional_jvm_args:
    - "-XX:+UseStringDeduplication"
    - "-XX:+OptimizeStringConcat"
    - "-Djava.awt.headless=true"
  system_properties:
    file.encoding: "UTF-8"
    user.timezone: "UTC"

events:
  enable_events: true
  async_publishing: true
  event_buffer_size: 1000
  handler_timeout_ms: 5000
  retry_failed_events: true
  max_retries: 3

logging:
  level: INFO
  enable_java_logs: true
  java_log_level: INFO
  buffer_size: 1000
  color_output: true

# Development settings
development:
  debug_enabled: false
  metrics_detailed: true
  event_tracing: false
  log_sql_queries: false

# Production settings
production:
  max_concurrent_executions: 500
  heap_size: "4g"
  max_heap_size: "8g"
  connection_pool_size: 100
  enable_jmx: true
```

## Using Configuration with Engines

### SagaEngine Configuration

```python
from fireflytx import SagaEngine, EngineConfig, PersistenceConfig, JvmConfig

# Method 1: Use default configuration
saga_engine = SagaEngine()
await saga_engine.initialize()

# Method 2: Use EngineConfig object
config = EngineConfig(
    max_concurrent_executions=200,
    default_timeout_ms=60000,
    persistence=PersistenceConfig(type="redis", connection_string="redis://localhost:6379"),
    jvm=JvmConfig(heap_size="2g", gc_algorithm="G1GC")
)
saga_engine = SagaEngine(config=config)
await saga_engine.initialize()

# Method 3: Use individual parameters (backward compatible)
saga_engine = SagaEngine(
    compensation_policy="STRICT_SEQUENTIAL",
    auto_optimization_enabled=True,
    persistence_enabled=False
)
await saga_engine.initialize()

# Method 4: Mix EngineConfig with individual parameters
saga_engine = SagaEngine(
    config=config,
    compensation_policy="BEST_EFFORT",  # Overrides config
    auto_optimization_enabled=True
)
await saga_engine.initialize()
```

### TccEngine Configuration

```python
from fireflytx import TccEngine, EngineConfig, PersistenceConfig, JvmConfig

# Method 1: Use default configuration
tcc_engine = TccEngine()
tcc_engine.start()

# Method 2: Use EngineConfig object
config = EngineConfig(
    max_concurrent_executions=200,
    default_timeout_ms=60000,
    persistence=PersistenceConfig(type="redis", connection_string="redis://localhost:6379"),
    jvm=JvmConfig(heap_size="2g", gc_algorithm="G1GC")
)
tcc_engine = TccEngine(config=config)
tcc_engine.start()

# Method 3: Use individual parameters (backward compatible)
tcc_engine = TccEngine(
    timeout_ms=60000,
    enable_monitoring=True
)
tcc_engine.start()

# Method 4: Mix EngineConfig with individual parameters
tcc_engine = TccEngine(
    config=config,
    timeout_ms=90000,  # Overrides config default_timeout_ms
    enable_monitoring=True
)
tcc_engine.start()
```

### Configuration Priority

When both `config` and individual parameters are provided, individual parameters take precedence:

```python
config = EngineConfig(default_timeout_ms=30000)

# timeout_ms=60000 overrides config.default_timeout_ms=30000
tcc_engine = TccEngine(config=config, timeout_ms=60000)
```

## Loading Configuration

### From YAML File

```python
from fireflytx.config import EngineConfig
from fireflytx import SagaEngine, TccEngine
import yaml

# Load YAML configuration
with open("fireflytx-config.yaml") as f:
    config_dict = yaml.safe_load(f)

# Create EngineConfig from dictionary
config = EngineConfig(**config_dict)

# Use with engines
saga_engine = SagaEngine(config=config)
await saga_engine.initialize()

tcc_engine = TccEngine(config=config)
tcc_engine.start()
```

### From Environment Variables

```python
import os
from fireflytx import EngineConfig, PersistenceConfig, JvmConfig

# Read from environment variables
config = EngineConfig(
    max_concurrent_executions=int(os.getenv("FIREFLYTX_MAX_CONCURRENT_EXECUTIONS", "100")),
    default_timeout_ms=int(os.getenv("FIREFLYTX_DEFAULT_TIMEOUT_MS", "30000")),
    thread_pool_size=int(os.getenv("FIREFLYTX_THREAD_POOL_SIZE", "50")),

    persistence=PersistenceConfig(
        type=os.getenv("FIREFLYTX_PERSISTENCE_TYPE", "memory"),
        connection_string=os.getenv("FIREFLYTX_PERSISTENCE_CONNECTION_STRING", "")
    ),

    jvm=JvmConfig(
        heap_size=os.getenv("FIREFLYTX_JVM_HEAP_SIZE", "256m"),
        gc_algorithm=os.getenv("FIREFLYTX_JVM_GC_ALGORITHM", None)
    )
)

# Use with engines
saga_engine = SagaEngine(config=config)
await saga_engine.initialize()
```

### Environment Variables Reference

```bash
# Engine settings
export FIREFLYTX_MAX_CONCURRENT_EXECUTIONS=200
export FIREFLYTX_DEFAULT_TIMEOUT_MS=60000
export FIREFLYTX_THREAD_POOL_SIZE=100
export FIREFLYTX_ENABLE_MONITORING=true

# Persistence settings
export FIREFLYTX_PERSISTENCE_TYPE=redis
export FIREFLYTX_PERSISTENCE_CONNECTION_STRING=redis://localhost:6379
export FIREFLYTX_PERSISTENCE_AUTO_CHECKPOINT=true
export FIREFLYTX_PERSISTENCE_CHECKPOINT_INTERVAL_SECONDS=60

# JVM settings
export FIREFLYTX_JVM_HEAP_SIZE=2g
export FIREFLYTX_JVM_GC_ALGORITHM=G1GC
export FIREFLYTX_JVM_MAX_GC_PAUSE_MS=200
```

### From Dictionary

```python
config_dict = {
    "engine": {
        "max_concurrent_executions": 200,
        "default_timeout_ms": 60000
    },
    "persistence": {
        "type": "redis",
        "connection_string": "redis://localhost:6379"
    }
}

config = EngineConfig.from_dict(config_dict["engine"])
```

## Configuration Validation

FireflyTX automatically validates configuration:

```python
from fireflytx.config import EngineConfig, ConfigurationError

try:
    config = EngineConfig(
        max_concurrent_executions=-1,  # Invalid value
        default_timeout_ms=0           # Invalid value
    )
except ConfigurationError as e:
    print(f"Configuration error: {e}")

# Check for warnings
warnings = config.validate_configuration()
for warning in warnings:
    print(f"Warning: {warning}")
```

### CLI Validation

```bash
# Validate configuration file
fireflytx validate-config fireflytx-config.yaml

# Check current configuration
fireflytx config --show

# Test configuration
fireflytx config --test
```

## Environment-Specific Configurations

### Development

```yaml
engine:
  max_concurrent_executions: 10
  default_timeout_ms: 10000
  enable_metrics: false

persistence:
  type: memory
  max_entries: 1000

jvm:
  heap_size: "256m"
  debug_enabled: true
  debug_port: 5005

logging:
  level: DEBUG
  enable_java_logs: true
  java_log_level: DEBUG
```

### Testing

```yaml
engine:
  max_concurrent_executions: 5
  default_timeout_ms: 5000

persistence:
  type: memory
  eviction_policy: "lru"

jvm:
  heap_size: "128m"
  force_subprocess: true  # For CI/CD compatibility

events:
  enable_events: false  # Reduce noise in tests
```

### Production

```yaml
engine:
  max_concurrent_executions: 500
  default_timeout_ms: 30000
  circuit_breaker_enabled: true

persistence:
  type: redis
  connection_string: "${REDIS_CLUSTER_URL}"
  ssl: true
  max_connections: 100

jvm:
  heap_size: "4g"
  max_heap_size: "8g"
  additional_jvm_args:
    - "-XX:+UseG1GC"
    - "-XX:MaxGCPauseMillis=100"
    - "-XX:+UseStringDeduplication"

events:
  async_publishing: true
  dead_letter_queue_enabled: true

logging:
  level: WARN
  java_log_level: WARN
```

## Advanced Configuration

### Custom Configuration Sources

Implement custom configuration providers:

```python
from fireflytx.config import ConfigurationProvider

class DatabaseConfigProvider(ConfigurationProvider):
    """Load configuration from database."""
    
    async def load_configuration(self) -> dict:
        # Load from database
        config_data = await db.fetch_config("fireflytx")
        return config_data

# Use custom provider
provider = DatabaseConfigProvider()
config = await provider.load_configuration()
```

### Dynamic Configuration

Update configuration at runtime:

```python
# Update engine configuration
engine.update_configuration(
    max_concurrent_executions=200,
    default_timeout_ms=45000
)

# Update persistence configuration
await engine.update_persistence_config(
    connection_string="redis://new-cluster:6379"
)
```

### Configuration Encryption

Encrypt sensitive configuration values:

```python
from fireflytx.config import encrypt_config_value, decrypt_config_value

# Encrypt sensitive values
encrypted_password = encrypt_config_value("secret-password", key="config-key")

config = {
    "persistence": {
        "password": f"encrypted:{encrypted_password}"
    }
}

# Values are automatically decrypted when loaded
```

## Best Practices

### 1. Environment Separation
Use different configuration files for each environment:
- `config/development.yaml`
- `config/testing.yaml`  
- `config/staging.yaml`
- `config/production.yaml`

### 2. Secret Management
Never store secrets in configuration files:

```yaml
# ❌ Bad
persistence:
  password: "hardcoded-secret"

# ✅ Good  
persistence:
  password: ${REDIS_PASSWORD}  # Environment variable
```

### 3. Configuration Validation
Always validate configuration before deployment:

```bash
# Validate before deployment
fireflytx validate-config config/production.yaml

# Test configuration connectivity
fireflytx test-config config/production.yaml
```

### 4. Monitoring Configuration Changes
Log configuration changes for audit purposes:

```python
import logging

config_logger = logging.getLogger("fireflytx.config")

def log_config_change(old_config, new_config):
    config_logger.info(
        "Configuration updated",
        extra={
            "old_max_executions": old_config.max_concurrent_executions,
            "new_max_executions": new_config.max_concurrent_executions,
            "timestamp": datetime.now().isoformat()
        }
    )
```

## Troubleshooting

### Common Configuration Issues

1. **Invalid JVM Arguments**
   ```bash
   # Check JVM argument validity
   java -XX:+PrintFlagsFinal -version | grep MaxHeapSize
   ```

2. **Redis Connection Issues**
   ```bash
   # Test Redis connectivity
   redis-cli -h localhost -p 6379 ping
   ```

3. **File Permissions**
   ```bash
   # Check file permissions for persistence
   ls -la /var/lib/fireflytx/
   ```

### Debug Configuration Loading

```python
import logging

# Enable debug logging for configuration
logging.getLogger("fireflytx.config").setLevel(logging.DEBUG)

# Load configuration with debug output
config = load_config_from_yaml("config.yaml")
```

This configuration reference covers all aspects of FireflyTX configuration. For specific use cases, refer to the [examples directory](../fireflytx/examples/) and other documentation.