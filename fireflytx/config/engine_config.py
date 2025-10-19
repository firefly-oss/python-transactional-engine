#!/usr/bin/env python3
"""
Configuration classes for the Python Transactional Engine.

Provides configuration management for engines, persistence, events, and JVM settings.
"""

"""
Copyright (c) 2025 Firefly Software Solutions Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_attempts: int = Field(default=3, ge=1, description="Maximum number of retry attempts")
    initial_delay_ms: int = Field(
        default=1000, ge=0, description="Initial delay between retries in milliseconds"
    )
    max_delay_ms: int = Field(
        default=30000, ge=0, description="Maximum delay between retries in milliseconds"
    )
    backoff_multiplier: float = Field(
        default=2.0, ge=1.0, description="Exponential backoff multiplier"
    )

    @field_validator("max_delay_ms")
    @classmethod
    def max_delay_must_be_greater_than_initial(cls, v, info):
        if "initial_delay_ms" in info.data and v < info.data["initial_delay_ms"]:
            raise ValueError("max_delay_ms must be greater than or equal to initial_delay_ms")
        return v


class PersistenceConfig(BaseModel):
    """Configuration for transaction persistence."""

    type: str = Field(
        default="memory", description="Persistence type: memory, file, redis, postgresql"
    )
    connection_string: str = Field(
        default="", description="Connection string for the persistence store"
    )
    auto_checkpoint: bool = Field(default=True, description="Enable automatic checkpointing")
    checkpoint_interval_seconds: int = Field(
        default=60, ge=1, description="Checkpoint interval in seconds"
    )
    max_transaction_age_hours: int = Field(
        default=24, ge=1, description="Maximum age of transactions before cleanup"
    )

    # Type-specific configurations
    redis_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Redis-specific configuration"
    )
    postgresql_config: Optional[Dict[str, Any]] = Field(
        default=None, description="PostgreSQL-specific configuration"
    )
    file_config: Optional[Dict[str, Any]] = Field(
        default=None, description="File-specific configuration"
    )

    @field_validator("type")
    @classmethod
    def validate_persistence_type(cls, v):
        valid_types = {"memory", "file", "redis", "postgresql", "mongodb", "dynamodb"}
        if v not in valid_types:
            raise ValueError(f"Persistence type must be one of: {valid_types}")
        return v

    def get_type_specific_config(self) -> Dict[str, Any]:
        """Get configuration specific to the persistence type."""
        if self.type == "redis" and self.redis_config:
            return self.redis_config
        elif self.type == "postgresql" and self.postgresql_config:
            return self.postgresql_config
        elif self.type == "file" and self.file_config:
            return self.file_config
        return {}


class LoggingConfig(BaseModel):
    """Configuration for FireflyTX logging system."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="json", description="Log format: json or text")
    enable_java_logs: bool = Field(default=True, description="Enable Java log capturing")
    java_log_level: str = Field(default="INFO", description="Java logging level")
    output_file: Optional[str] = Field(default=None, description="Log output file path")
    max_file_size_mb: int = Field(default=100, ge=1, description="Maximum log file size in MB")
    backup_count: int = Field(default=5, ge=1, description="Number of backup log files to keep")

    # Advanced logging options
    include_thread_info: bool = Field(
        default=True, description="Include thread information in logs"
    )
    include_module_info: bool = Field(
        default=True, description="Include module/function information in logs"
    )
    correlation_id_header: str = Field(
        default="X-Correlation-ID", description="Header name for correlation ID"
    )

    @field_validator("level", "java_log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = {"TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "FATAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        valid_formats = {"json", "text"}
        if v.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of: {valid_formats}")
        return v.lower()


class EventConfig(BaseModel):
    """
    Configuration for event publishing and handling.

    Events are published by the Java lib-transactional-engine, not Python.
    This configuration is passed to Java via system properties.
    """

    enabled: bool = Field(default=True, description="Enable event publishing")
    provider: str = Field(default="memory", description="Event provider type (memory, kafka, redis, mqtt)")
    async_publishing: bool = Field(default=True, description="Publish events asynchronously")
    buffer_size: int = Field(default=1000, ge=1, description="Event buffer size")
    flush_interval_ms: int = Field(
        default=5000, ge=100, description="Event buffer flush interval in milliseconds"
    )

    # Event handler configurations
    logging_enabled: bool = Field(default=True, description="Enable logging event handler")
    metrics_enabled: bool = Field(default=False, description="Enable metrics collection")
    custom_handlers: List[str] = Field(
        default_factory=list, description="Custom event handler class names"
    )

    # External system configurations
    mqtt_config: Optional[Dict[str, Any]] = Field(
        default=None, description="MQTT event publishing configuration"
    )

    # Kafka-specific configuration
    kafka_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Kafka-specific configuration"
    )

    # Topic configuration
    topic_prefix: str = Field(default="fireflytx", description="Prefix for event topics")
    saga_topic: str = Field(default="fireflytx.saga.events", description="Topic for SAGA step events")
    tcc_topic: str = Field(default="fireflytx.tcc.events", description="Topic for TCC events")
    kafka_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Kafka event publishing configuration"
    )
    webhook_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Webhook event publishing configuration"
    )


class JvmConfig(BaseModel):
    """Configuration for JVM startup and management."""

    heap_size: str = Field(default="512m", description="JVM heap size (e.g., '512m', '2g')")
    additional_jvm_args: List[str] = Field(
        default_factory=list, description="Additional JVM arguments"
    )
    classpath_entries: List[str] = Field(
        default_factory=list, description="Additional classpath entries"
    )
    system_properties: Dict[str, str] = Field(
        default_factory=dict, description="JVM system properties"
    )

    # Performance tuning - Garbage Collection
    gc_algorithm: Optional[str] = Field(
        default="G1GC",
        description="Garbage collection algorithm (G1GC, ZGC, ParallelGC, SerialGC)"
    )
    max_gc_pause_ms: Optional[int] = Field(
        default=200, ge=10, description="Maximum GC pause time in milliseconds (G1GC only)"
    )

    # G1GC specific tuning
    g1_heap_region_size: Optional[str] = Field(
        default=None,
        description="G1 heap region size (e.g., '4m', '8m', '16m'). Auto-calculated if not set."
    )
    initiating_heap_occupancy_percent: Optional[int] = Field(
        default=45,
        ge=0,
        le=100,
        description="Heap occupancy % to start concurrent GC cycle (G1GC)"
    )

    # ZGC specific tuning (for low-latency workloads)
    zgc_enabled: bool = Field(
        default=False,
        description="Enable ZGC (low-latency garbage collector, requires Java 15+)"
    )

    # GC logging and monitoring
    enable_gc_logging: bool = Field(
        default=False,
        description="Enable detailed GC logging for monitoring and tuning"
    )
    gc_log_file: Optional[str] = Field(
        default=None,
        description="Path to GC log file. If None, logs to stdout."
    )

    # Thread configuration
    parallel_gc_threads: Optional[int] = Field(
        default=None,
        description="Number of parallel GC threads. Auto-calculated if not set."
    )
    concurrent_gc_threads: Optional[int] = Field(
        default=None,
        description="Number of concurrent GC threads. Auto-calculated if not set."
    )

    # Memory management
    max_metaspace_size: Optional[str] = Field(
        default="256m",
        description="Maximum metaspace size (e.g., '256m', '512m')"
    )
    compressed_oops: bool = Field(
        default=True,
        description="Use compressed object pointers (reduces memory footprint)"
    )

    @field_validator("heap_size")
    @classmethod
    def validate_heap_size(cls, v):
        if not v or not any(v.endswith(suffix) for suffix in ["k", "K", "m", "M", "g", "G"]):
            raise ValueError('heap_size must end with k/K, m/M, or g/G (e.g., "512m", "2g")')
        return v

    def get_jvm_args(self) -> List[str]:
        """Generate JVM arguments list."""
        args = [f"-Xmx{self.heap_size}"]

        if self.gc_algorithm:
            if self.gc_algorithm.upper() == "G1GC":
                args.extend(["-XX:+UseG1GC"])
                if self.max_gc_pause_ms:
                    args.append(f"-XX:MaxGCPauseMillis={self.max_gc_pause_ms}")
            elif self.gc_algorithm.upper() == "PARALLEL":
                args.extend(["-XX:+UseParallelGC"])
            elif self.gc_algorithm.upper() == "ZGC":
                args.extend(["-XX:+UseZGC"])

        # Add system properties
        for key, value in self.system_properties.items():
            args.append(f"-D{key}={value}")

        # Add additional arguments
        args.extend(self.additional_jvm_args)

        return args


class EngineConfig(BaseModel):
    """Main configuration class for the transactional engine."""

    # Engine settings
    max_concurrent_executions: int = Field(
        default=100, ge=1, description="Maximum concurrent transaction executions"
    )
    default_timeout_ms: int = Field(
        default=30000, ge=1000, description="Default transaction timeout in milliseconds"
    )
    enable_monitoring: bool = Field(
        default=True, description="Enable transaction monitoring and metrics"
    )

    # Sub-configurations
    retry_config: RetryConfig = Field(
        default_factory=RetryConfig, description="Retry configuration"
    )
    persistence: PersistenceConfig = Field(
        default_factory=PersistenceConfig, description="Persistence configuration"
    )
    events: EventConfig = Field(default_factory=EventConfig, description="Event configuration")
    jvm: JvmConfig = Field(default_factory=JvmConfig, description="JVM configuration")
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )

    # Advanced settings
    thread_pool_size: int = Field(
        default=50, ge=1, description="Thread pool size for transaction execution"
    )
    transaction_cleanup_interval_seconds: int = Field(
        default=300, ge=60, description="Transaction cleanup interval"
    )
    enable_transaction_logging: bool = Field(
        default=True, description="Enable detailed transaction logging"
    )

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "EngineConfig":
        """Load configuration from a JSON or YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        content = path.read_text(encoding="utf-8")

        try:
            if path.suffix.lower() in [".yml", ".yaml"]:
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"Failed to parse configuration file: {e}")

        return cls(**data)

    @classmethod
    def from_env(cls, prefix: str = "PYTRANSACTIONAL_") -> "EngineConfig":
        """Load configuration from environment variables.

        Note: This returns a config with only explicitly set environment variables,
        all other values will be the model defaults.
        """
        config_data = {}

        # Simple environment variable mapping
        env_mappings = {
            f"{prefix}MAX_CONCURRENT_EXECUTIONS": ("max_concurrent_executions", int),
            f"{prefix}DEFAULT_TIMEOUT_MS": ("default_timeout_ms", int),
            f"{prefix}ENABLE_MONITORING": ("enable_monitoring", lambda x: x.lower() == "true"),
            f"{prefix}THREAD_POOL_SIZE": ("thread_pool_size", int),
            f"{prefix}LOG_LEVEL": ("logging.level", str),
            f"{prefix}LOG_FORMAT": ("logging.format", str),
            f"{prefix}ENABLE_JAVA_LOGS": (
                "logging.enable_java_logs",
                lambda x: x.lower() == "true",
            ),
            f"{prefix}PERSISTENCE_TYPE": ("persistence.type", str),
            f"{prefix}PERSISTENCE_CONNECTION_STRING": ("persistence.connection_string", str),
            f"{prefix}JVM_HEAP_SIZE": ("jvm.heap_size", str),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    converted_value = converter(value)
                    # Handle nested keys
                    if "." in config_key:
                        parts = config_key.split(".")
                        current = config_data
                        for part in parts[:-1]:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = converted_value
                    else:
                        config_data[config_key] = converted_value
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid value for {env_var}: {value} ({e})")

        return cls(**config_data)

    def to_file(self, config_path: Union[str, Path], format: str = "auto") -> None:
        """Save configuration to a file."""
        path = Path(config_path)

        if format == "auto":
            format = "yaml" if path.suffix.lower() in [".yml", ".yaml"] else "json"

        data = self.model_dump()

        if format == "yaml":
            content = yaml.dump(data, default_flow_style=False, sort_keys=False, indent=2)
        else:
            content = json.dumps(data, indent=2)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def validate_configuration(self) -> List[str]:
        """Validate the configuration and return any warnings."""
        warnings = []

        # Performance warnings
        if self.max_concurrent_executions > 1000:
            warnings.append("High max_concurrent_executions may cause resource exhaustion")

        if self.thread_pool_size > self.max_concurrent_executions:
            warnings.append("thread_pool_size is larger than max_concurrent_executions")

        # Persistence warnings
        if self.persistence.type == "memory" and self.enable_monitoring:
            warnings.append(
                "Memory persistence with monitoring may cause memory leaks in long-running applications"
            )

        if self.persistence.auto_checkpoint and self.persistence.type == "memory":
            warnings.append("auto_checkpoint is enabled but persistence type is memory")

        # Event warnings
        if self.events.enabled and self.events.buffer_size < 100:
            warnings.append(
                "Small event buffer size may cause frequent flushes and performance issues"
            )

        # JVM warnings
        try:
            heap_num = int(self.jvm.heap_size[:-1])
            heap_unit = self.jvm.heap_size[-1].upper()
            heap_mb = heap_num * (1024 if heap_unit == "G" else 1 if heap_unit == "M" else 0.001)

            if heap_mb < 256:
                warnings.append("JVM heap size may be too small for production use")
            elif heap_mb > 8192:
                warnings.append("Very large JVM heap size may cause long GC pauses")
        except (ValueError, IndexError):
            warnings.append("Invalid JVM heap size format")

        return warnings


class ConfigurationManager:
    """Utility class for managing configurations."""

    @staticmethod
    def create_default_config_file(path: Union[str, Path], format: str = "yaml") -> None:
        """Create a default configuration file."""
        config = EngineConfig()
        config.to_file(path, format)

    @staticmethod
    def merge_configs(*configs: EngineConfig) -> EngineConfig:
        """Merge multiple configurations, with later configs taking precedence."""
        if not configs:
            return EngineConfig()

        merged_data = configs[0].model_dump()

        for config in configs[1:]:
            config_data = config.model_dump()
            merged_data = ConfigurationManager._deep_merge(merged_data, config_data)

        return EngineConfig(**merged_data)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigurationManager._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def load_config(
        config_file: Optional[Union[str, Path]] = None,
        env_prefix: str = "PYTRANSACTIONAL_",
        use_env: bool = True,
    ) -> EngineConfig:
        """Load configuration from file and/or environment variables."""

        # Start with base configuration (file or defaults)
        if config_file:
            try:
                base_config = EngineConfig.from_file(config_file)
            except FileNotFoundError:
                base_config = EngineConfig()  # File doesn't exist, use defaults
        else:
            base_config = EngineConfig()

        # Apply environment variable overrides if requested
        if use_env:
            # Get only the environment variables that are actually set
            env_overrides = ConfigurationManager._get_env_overrides(env_prefix)
            if env_overrides:
                # Merge environment overrides into base config
                base_data = base_config.model_dump()
                merged_data = ConfigurationManager._deep_merge(base_data, env_overrides)
                return EngineConfig(**merged_data)

        return base_config

    @staticmethod
    def _get_env_overrides(prefix: str = "PYTRANSACTIONAL_") -> Dict[str, Any]:
        """Get only the environment variable overrides that are actually set."""
        config_data = {}

        # Simple environment variable mapping
        env_mappings = {
            f"{prefix}MAX_CONCURRENT_EXECUTIONS": ("max_concurrent_executions", int),
            f"{prefix}DEFAULT_TIMEOUT_MS": ("default_timeout_ms", int),
            f"{prefix}ENABLE_MONITORING": ("enable_monitoring", lambda x: x.lower() == "true"),
            f"{prefix}THREAD_POOL_SIZE": ("thread_pool_size", int),
            f"{prefix}LOG_LEVEL": ("logging.level", str),
            f"{prefix}LOG_FORMAT": ("logging.format", str),
            f"{prefix}ENABLE_JAVA_LOGS": (
                "logging.enable_java_logs",
                lambda x: x.lower() == "true",
            ),
            f"{prefix}PERSISTENCE_TYPE": ("persistence.type", str),
            f"{prefix}PERSISTENCE_CONNECTION_STRING": ("persistence.connection_string", str),
            f"{prefix}JVM_HEAP_SIZE": ("jvm.heap_size", str),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    converted_value = converter(value)
                    # Handle nested keys
                    if "." in config_key:
                        parts = config_key.split(".")
                        current = config_data
                        for part in parts[:-1]:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = converted_value
                    else:
                        config_data[config_key] = converted_value
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid value for {env_var}: {value} ({e})")

        return config_data

    @staticmethod
    def get_default_config() -> EngineConfig:
        """
        Get the default configuration for development.

        This configuration uses:
        - In-memory persistence (no data persistence)
        - Minimal JVM heap (256m)
        - Moderate concurrency (100 concurrent executions)
        - Standard timeouts (30 seconds)

        Returns:
            EngineConfig: Default development configuration
        """
        return EngineConfig()

    @staticmethod
    def get_production_config(
        persistence_type: str = "redis",
        persistence_connection_string: str = "redis://localhost:6379",
        heap_size: str = "2g",
        max_concurrent_executions: int = 200,
    ) -> EngineConfig:
        """
        Get a production-ready configuration.

        This configuration uses:
        - Redis persistence (or specified type)
        - 2GB JVM heap (or specified size)
        - High concurrency (200 concurrent executions)
        - Extended timeouts (60 seconds)
        - G1GC garbage collector
        - Auto-checkpointing enabled

        Args:
            persistence_type: Type of persistence ("redis", "postgresql", "file")
            persistence_connection_string: Connection string for persistence
            heap_size: JVM heap size (e.g., "2g", "4g")
            max_concurrent_executions: Maximum concurrent transactions

        Returns:
            EngineConfig: Production configuration
        """
        return EngineConfig(
            max_concurrent_executions=max_concurrent_executions,
            default_timeout_ms=60000,
            thread_pool_size=100,
            enable_monitoring=True,
            enable_transaction_logging=True,
            transaction_cleanup_interval_seconds=300,
            retry_config=RetryConfig(
                max_attempts=5,
                initial_delay_ms=1000,
                max_delay_ms=60000,
                backoff_multiplier=2.0,
            ),
            persistence=PersistenceConfig(
                type=persistence_type,
                connection_string=persistence_connection_string,
                auto_checkpoint=True,
                checkpoint_interval_seconds=60,
                max_transaction_age_hours=24,
            ),
            jvm=JvmConfig(
                heap_size=heap_size,
                gc_algorithm="G1GC",
                max_gc_pause_ms=200,
                initiating_heap_occupancy_percent=45,
                max_metaspace_size="256m",
                compressed_oops=True,
                enable_gc_logging=False,
                additional_jvm_args=[
                    "-XX:+UseStringDeduplication",
                    "-XX:+OptimizeStringConcat",
                    "-Djava.awt.headless=true",
                ],
                system_properties={
                    "file.encoding": "UTF-8",
                    "user.timezone": "UTC",
                },
            ),
        )

    @staticmethod
    def get_high_performance_config(
        persistence_connection_string: str = "redis://localhost:6379",
    ) -> EngineConfig:
        """
        Get a high-performance configuration optimized for throughput.

        This configuration uses:
        - Redis persistence with high connection pool
        - 4GB JVM heap
        - Very high concurrency (500 concurrent executions)
        - Optimized GC settings
        - Large thread pool

        Args:
            persistence_connection_string: Redis connection string

        Returns:
            EngineConfig: High-performance configuration
        """
        return EngineConfig(
            max_concurrent_executions=500,
            default_timeout_ms=30000,
            thread_pool_size=200,
            enable_monitoring=True,
            enable_transaction_logging=True,
            transaction_cleanup_interval_seconds=300,
            retry_config=RetryConfig(
                max_attempts=3,
                initial_delay_ms=500,
                max_delay_ms=30000,
                backoff_multiplier=2.0,
            ),
            persistence=PersistenceConfig(
                type="redis",
                connection_string=persistence_connection_string,
                auto_checkpoint=True,
                checkpoint_interval_seconds=30,
                max_transaction_age_hours=12,
                redis_config={
                    "max_connections": 200,
                    "connection_pool_timeout": 5,
                },
            ),
            jvm=JvmConfig(
                heap_size="4g",
                gc_algorithm="G1GC",
                max_gc_pause_ms=100,
                g1_heap_region_size="8m",
                initiating_heap_occupancy_percent=40,
                parallel_gc_threads=8,
                concurrent_gc_threads=2,
                max_metaspace_size="512m",
                compressed_oops=True,
                enable_gc_logging=False,
                additional_jvm_args=[
                    "-XX:+UseStringDeduplication",
                    "-XX:+OptimizeStringConcat",
                    "-XX:ReservedCodeCacheSize=512m",
                ],
                system_properties={
                    "file.encoding": "UTF-8",
                    "user.timezone": "UTC",
                },
            ),
        )

    @staticmethod
    def get_low_latency_config(
        persistence_connection_string: str = "redis://localhost:6379",
        heap_size: str = "8g",
    ) -> EngineConfig:
        """
        Get a low-latency configuration optimized for minimal GC pauses.

        This configuration uses:
        - ZGC (Z Garbage Collector) for ultra-low latency
        - 8GB JVM heap (ZGC works best with larger heaps)
        - High concurrency (300 concurrent executions)
        - Minimal GC pause times (<10ms)
        - Optimized for latency-sensitive workloads

        Note: Requires Java 15+ for ZGC

        Args:
            persistence_connection_string: Redis connection string
            heap_size: JVM heap size (e.g., "8g", "16g"). ZGC works best with 8GB+

        Returns:
            EngineConfig: Low-latency configuration with ZGC
        """
        return EngineConfig(
            max_concurrent_executions=300,
            default_timeout_ms=30000,
            thread_pool_size=150,
            enable_monitoring=True,
            enable_transaction_logging=True,
            transaction_cleanup_interval_seconds=300,
            retry_config=RetryConfig(
                max_attempts=3,
                initial_delay_ms=500,
                max_delay_ms=30000,
                backoff_multiplier=2.0,
            ),
            persistence=PersistenceConfig(
                type="redis",
                connection_string=persistence_connection_string,
                auto_checkpoint=True,
                checkpoint_interval_seconds=60,
                max_transaction_age_hours=24,
                redis_config={
                    "max_connections": 150,
                    "connection_pool_timeout": 5,
                },
            ),
            jvm=JvmConfig(
                heap_size=heap_size,
                gc_algorithm="ZGC",
                zgc_enabled=True,
                max_metaspace_size="512m",
                compressed_oops=True,
                enable_gc_logging=False,
                additional_jvm_args=[
                    "-XX:+UseStringDeduplication",
                    "-XX:+OptimizeStringConcat",
                    "-XX:ReservedCodeCacheSize=512m",
                ],
                system_properties={
                    "file.encoding": "UTF-8",
                    "user.timezone": "UTC",
                },
            ),
        )

