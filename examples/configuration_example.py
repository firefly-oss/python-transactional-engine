#!/usr/bin/env python3
"""
Configuration Example: How to Configure FireflyTX Engines

This example demonstrates different ways to configure SagaEngine and TccEngine
for various deployment scenarios.

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0 (the "License");
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from fireflytx import SagaEngine, TccEngine
from fireflytx.config import (
    ConfigurationManager,
    EngineConfig,
    PersistenceConfig,
    JvmConfig,
    RetryConfig,
)


def example_1_default_configuration():
    """Example 1: Using default configuration (development)."""
    print("\n" + "=" * 70)
    print("Example 1: Default Configuration (Development)")
    print("=" * 70)

    # Method 1: Implicit defaults
    saga_engine = SagaEngine()
    print("✅ SagaEngine created with implicit defaults")

    # Method 2: Explicit default configuration
    config = ConfigurationManager.get_default_config()
    saga_engine = SagaEngine(config=config)
    print("✅ SagaEngine created with explicit default config")

    print(f"\nDefault Configuration:")
    print(f"  - Max concurrent executions: {config.max_concurrent_executions}")
    print(f"  - Default timeout: {config.default_timeout_ms}ms")
    print(f"  - Thread pool size: {config.thread_pool_size}")
    print(f"  - JVM heap size: {config.jvm.heap_size}")
    print(f"  - Persistence type: {config.persistence.type}")
    print(f"  - Retry attempts: {config.retry_config.max_attempts}")


def example_2_production_configuration():
    """Example 2: Using production configuration."""
    print("\n" + "=" * 70)
    print("Example 2: Production Configuration")
    print("=" * 70)

    # Get production configuration with custom settings
    config = ConfigurationManager.get_production_config(
        persistence_type="redis",
        persistence_connection_string="redis://prod-redis:6379",
        heap_size="2g",
        max_concurrent_executions=200,
    )

    saga_engine = SagaEngine(config=config)
    print("✅ SagaEngine created with production config")

    tcc_engine = TccEngine(config=config)
    print("✅ TccEngine created with production config")

    print(f"\nProduction Configuration:")
    print(f"  - Max concurrent executions: {config.max_concurrent_executions}")
    print(f"  - Default timeout: {config.default_timeout_ms}ms")
    print(f"  - Thread pool size: {config.thread_pool_size}")
    print(f"  - JVM heap size: {config.jvm.heap_size}")
    print(f"  - GC algorithm: {config.jvm.gc_algorithm}")
    print(f"  - Persistence type: {config.persistence.type}")
    print(f"  - Auto checkpoint: {config.persistence.auto_checkpoint}")
    print(f"  - Retry attempts: {config.retry_config.max_attempts}")


def example_3_high_performance_configuration():
    """Example 3: Using high-performance configuration."""
    print("\n" + "=" * 70)
    print("Example 3: High-Performance Configuration")
    print("=" * 70)

    # Get high-performance configuration
    config = ConfigurationManager.get_high_performance_config(
        persistence_connection_string="redis://redis-cluster:6379"
    )

    saga_engine = SagaEngine(config=config)
    print("✅ SagaEngine created with high-performance config")

    print(f"\nHigh-Performance Configuration:")
    print(f"  - Max concurrent executions: {config.max_concurrent_executions}")
    print(f"  - Default timeout: {config.default_timeout_ms}ms")
    print(f"  - Thread pool size: {config.thread_pool_size}")
    print(f"  - JVM heap size: {config.jvm.heap_size}")
    print(f"  - GC algorithm: {config.jvm.gc_algorithm}")
    print(f"  - Max GC pause: {config.jvm.max_gc_pause_ms}ms")
    print(f"  - Checkpoint interval: {config.persistence.checkpoint_interval_seconds}s")


def example_4_custom_configuration():
    """Example 4: Creating custom configuration."""
    print("\n" + "=" * 70)
    print("Example 4: Custom Configuration")
    print("=" * 70)

    # Create completely custom configuration
    config = EngineConfig(
        # Execution settings
        max_concurrent_executions=150,
        default_timeout_ms=45000,
        thread_pool_size=75,
        enable_monitoring=True,
        enable_transaction_logging=True,
        transaction_cleanup_interval_seconds=600,
        # Retry configuration
        retry_config=RetryConfig(
            max_attempts=4,
            initial_delay_ms=2000,
            max_delay_ms=45000,
            backoff_multiplier=1.5,
        ),
        # Persistence configuration
        persistence=PersistenceConfig(
            type="postgresql",
            connection_string="postgresql://user:pass@localhost:5432/fireflytx",
            auto_checkpoint=True,
            checkpoint_interval_seconds=90,
            max_transaction_age_hours=48,
            postgresql_config={
                "pool_size": 30,
                "max_overflow": 15,
                "pool_timeout": 45,
            },
        ),
        # JVM configuration
        jvm=JvmConfig(
            heap_size="3g",
            gc_algorithm="G1GC",
            max_gc_pause_ms=150,
            additional_jvm_args=[
                "-XX:+UseStringDeduplication",
                "-XX:+OptimizeStringConcat",
                "-XX:+UseCompressedOops",
            ],
            system_properties={
                "file.encoding": "UTF-8",
                "user.timezone": "America/New_York",
            },
        ),
    )

    saga_engine = SagaEngine(config=config)
    print("✅ SagaEngine created with custom config")

    print(f"\nCustom Configuration:")
    print(f"  - Max concurrent executions: {config.max_concurrent_executions}")
    print(f"  - Default timeout: {config.default_timeout_ms}ms")
    print(f"  - Thread pool size: {config.thread_pool_size}")
    print(f"  - JVM heap size: {config.jvm.heap_size}")
    print(f"  - Persistence type: {config.persistence.type}")
    print(f"  - Checkpoint interval: {config.persistence.checkpoint_interval_seconds}s")
    print(f"  - Retry backoff multiplier: {config.retry_config.backoff_multiplier}")


def example_5_environment_based_configuration():
    """Example 5: Loading configuration from environment variables."""
    print("\n" + "=" * 70)
    print("Example 5: Environment-Based Configuration")
    print("=" * 70)

    import os

    # Set environment variables (in production, these would be set externally)
    os.environ["FIREFLYTX_MAX_CONCURRENT_EXECUTIONS"] = "250"
    os.environ["FIREFLYTX_DEFAULT_TIMEOUT_MS"] = "50000"
    os.environ["FIREFLYTX_THREAD_POOL_SIZE"] = "120"
    os.environ["FIREFLYTX_PERSISTENCE_TYPE"] = "redis"
    os.environ["FIREFLYTX_PERSISTENCE_CONNECTION_STRING"] = "redis://env-redis:6379"
    os.environ["FIREFLYTX_JVM_HEAP_SIZE"] = "3g"

    # Create configuration from environment variables
    config = EngineConfig(
        max_concurrent_executions=int(
            os.getenv("FIREFLYTX_MAX_CONCURRENT_EXECUTIONS", "100")
        ),
        default_timeout_ms=int(os.getenv("FIREFLYTX_DEFAULT_TIMEOUT_MS", "30000")),
        thread_pool_size=int(os.getenv("FIREFLYTX_THREAD_POOL_SIZE", "50")),
        persistence=PersistenceConfig(
            type=os.getenv("FIREFLYTX_PERSISTENCE_TYPE", "memory"),
            connection_string=os.getenv("FIREFLYTX_PERSISTENCE_CONNECTION_STRING", ""),
        ),
        jvm=JvmConfig(heap_size=os.getenv("FIREFLYTX_JVM_HEAP_SIZE", "256m")),
    )

    saga_engine = SagaEngine(config=config)
    print("✅ SagaEngine created with environment-based config")

    print(f"\nEnvironment-Based Configuration:")
    print(f"  - Max concurrent executions: {config.max_concurrent_executions}")
    print(f"  - Default timeout: {config.default_timeout_ms}ms")
    print(f"  - Thread pool size: {config.thread_pool_size}")
    print(f"  - JVM heap size: {config.jvm.heap_size}")
    print(f"  - Persistence type: {config.persistence.type}")
    print(f"  - Persistence connection: {config.persistence.connection_string}")


def example_6_mixed_configuration():
    """Example 6: Mixing EngineConfig with individual parameters."""
    print("\n" + "=" * 70)
    print("Example 6: Mixed Configuration (Config + Individual Parameters)")
    print("=" * 70)

    # Start with production config
    config = ConfigurationManager.get_production_config()

    # Override specific settings with individual parameters
    saga_engine = SagaEngine(
        config=config,
        compensation_policy="BEST_EFFORT",  # Override default
        auto_optimization_enabled=True,
    )
    print("✅ SagaEngine created with mixed configuration")

    tcc_engine = TccEngine(
        config=config,
        timeout_ms=90000,  # Override config.default_timeout_ms
        enable_monitoring=True,
    )
    print("✅ TccEngine created with mixed configuration")

    print(f"\nMixed Configuration:")
    print(f"  - Base config: Production")
    print(f"  - SagaEngine compensation_policy: BEST_EFFORT (overridden)")
    print(f"  - TccEngine timeout_ms: 90000 (overridden)")
    print(f"  - Other settings from production config")


def main():
    """Run all configuration examples."""
    print("\n" + "=" * 70)
    print("FireflyTX Configuration Examples")
    print("=" * 70)
    print("\nThis example demonstrates different ways to configure engines:")
    print("  1. Default configuration (development)")
    print("  2. Production configuration")
    print("  3. High-performance configuration")
    print("  4. Custom configuration")
    print("  5. Environment-based configuration")
    print("  6. Mixed configuration")

    # Run all examples
    example_1_default_configuration()
    example_2_production_configuration()
    example_3_high_performance_configuration()
    example_4_custom_configuration()
    example_5_environment_based_configuration()
    example_6_mixed_configuration()

    print("\n" + "=" * 70)
    print("✅ All configuration examples completed successfully!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  • Use default config for development (in-memory, minimal resources)")
    print("  • Use production config for production (Redis, optimized settings)")
    print("  • Use high-performance config for high-throughput scenarios")
    print("  • Create custom configs for specific requirements")
    print("  • Use environment variables for deployment flexibility")
    print("  • Mix configs with individual parameters for fine-tuning")
    print("\nSee docs/configuration.md for complete configuration reference.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

