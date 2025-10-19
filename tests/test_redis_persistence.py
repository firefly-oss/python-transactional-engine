"""
Test Redis persistence configuration with testcontainers.

This test suite uses testcontainers to spin up a real Redis instance
and verify that the FireflyTX engines can properly connect and use it
for persistence.

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0 (the "License");
"""

import asyncio
import pytest
from pathlib import Path
from testcontainers.redis import RedisContainer

from fireflytx import SagaEngine, TccEngine, EngineConfig, PersistenceConfig, JvmConfig
from fireflytx.config import ConfigurationManager


@pytest.fixture(scope="module")
def redis_container():
    """Start a Redis container for testing."""
    container = RedisContainer("redis:7-alpine")
    container.start()
    
    # Wait for Redis to be ready
    import time
    time.sleep(2)
    
    yield container
    
    # Cleanup
    container.stop()


@pytest.fixture(scope="module")
def redis_config(redis_container):
    """Create EngineConfig with Redis persistence."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    connection_string = f"redis://{host}:{port}"

    config = EngineConfig(
        max_concurrent_executions=50,
        default_timeout_ms=30000,
        thread_pool_size=25,
        enable_monitoring=True,
        persistence=PersistenceConfig(
            type="redis",
            connection_string=connection_string,
            auto_checkpoint=True,
            checkpoint_interval_seconds=30,
            redis_config={
                "db": 0,
                "max_connections": 10
            }
        ),
        jvm=JvmConfig(
            heap_size="512m",
            gc_algorithm="G1GC"
        )
    )

    return config


class TestRedisConfiguration:
    """Test Redis configuration and connection."""
    
    def test_redis_container_running(self, redis_container):
        """Test that Redis container is running."""
        assert redis_container.get_container_host_ip() is not None
        assert redis_container.get_exposed_port(6379) is not None
    
    def test_redis_connection(self, redis_container):
        """Test direct connection to Redis."""
        import redis
        
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        
        client = redis.Redis(host=host, port=port, decode_responses=True)
        
        # Test basic operations
        client.set("test_key", "test_value")
        assert client.get("test_key") == "test_value"
        client.delete("test_key")
    
    def test_config_generation(self, redis_config):
        """Test that Redis config is properly generated."""
        assert redis_config.persistence.type == "redis"
        assert "redis://" in redis_config.persistence.connection_string
        assert redis_config.persistence.auto_checkpoint is True
    
    def test_java_properties_conversion(self, redis_config):
        """Test conversion of Python config to Java properties."""
        from fireflytx.integration.bridge import JavaSubprocessBridge
        
        bridge = JavaSubprocessBridge()
        props = bridge._convert_config_to_java_properties(redis_config)
        
        # Verify persistence properties
        assert props.get("firefly.tx.persistence.enabled") == "true"
        assert props.get("firefly.tx.persistence.provider") == "redis"
        assert "firefly.tx.persistence.redis.host" in props
        assert "firefly.tx.persistence.redis.port" in props
        
        # Verify other properties
        assert props.get("firefly.tx.max-concurrent-transactions") == "50"
        assert "PT30S" in props.get("firefly.tx.default-timeout", "")


class TestSagaEngineWithRedis:
    """Test SagaEngine with Redis persistence."""
    
    @pytest.mark.asyncio
    async def test_saga_engine_initialization_with_redis(self, redis_config):
        """Test that SagaEngine can initialize with Redis config."""
        engine = SagaEngine(config=redis_config)
        
        # Initialize the engine (this will start Java subprocess with Redis config)
        await engine.initialize()
        
        # Verify engine is initialized
        assert engine._java_bridge is not None
        assert engine._java_bridge._java_started is True
        
        # Cleanup
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_saga_engine_accepts_redis_config(self, redis_config):
        """Test that SagaEngine properly accepts and stores Redis config."""
        engine = SagaEngine(config=redis_config)
        
        assert engine.config is not None
        assert engine.config.persistence.type == "redis"
        assert "redis://" in engine.config.persistence.connection_string


class TestTccEngineWithRedis:
    """Test TccEngine with Redis persistence."""
    
    def test_tcc_engine_initialization_with_redis(self, redis_config):
        """Test that TccEngine can initialize with Redis config."""
        engine = TccEngine(config=redis_config)

        # Start the engine (this will start Java subprocess with Redis config)
        engine.start()

        # Verify engine is started - TccEngine stores bridge in java_bridge attribute
        assert engine.java_bridge is not None
        assert engine._is_running is True

        # Cleanup
        engine.stop()
    
    def test_tcc_engine_accepts_redis_config(self, redis_config):
        """Test that TccEngine properly accepts and stores Redis config."""
        engine = TccEngine(config=redis_config)
        
        assert engine.config is not None
        assert engine.config.persistence.type == "redis"
        assert "redis://" in engine.config.persistence.connection_string


class TestRedisValidation:
    """Test Redis connection validation."""
    
    def test_validation_with_available_redis(self, redis_config):
        """Test validation passes when Redis is available."""
        from fireflytx.integration.bridge import JavaSubprocessBridge
        
        bridge = JavaSubprocessBridge()
        
        # This should not raise an exception
        bridge._validate_configuration(redis_config)
    
    def test_validation_with_unavailable_redis(self, caplog):
        """Test validation warns when Redis is unavailable."""
        import logging

        config = EngineConfig(
            persistence=PersistenceConfig(
                type="redis",
                connection_string="redis://localhost:9999"  # Invalid port
            )
        )

        from fireflytx.integration.bridge import JavaSubprocessBridge

        bridge = JavaSubprocessBridge()

        # Capture log warnings
        with caplog.at_level(logging.WARNING):
            # This should log a warning but not raise
            bridge._validate_configuration(config)

            # Verify warning was logged
            assert any("Redis" in record.message for record in caplog.records)


class TestConfigurationHelpers:
    """Test configuration helper methods with Redis."""
    
    def test_production_config_with_redis(self, redis_container):
        """Test production config helper with Redis."""
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        connection_string = f"redis://{host}:{port}"
        
        config = ConfigurationManager.get_production_config(
            persistence_type="redis",
            persistence_connection_string=connection_string,
            heap_size="512m",
            max_concurrent_executions=100
        )
        
        assert config.persistence.type == "redis"
        assert config.persistence.connection_string == connection_string
        assert config.max_concurrent_executions == 100
    
    def test_high_performance_config_with_redis(self, redis_container):
        """Test high-performance config helper with Redis."""
        host = redis_container.get_container_host_ip()
        port = redis_container.get_exposed_port(6379)
        connection_string = f"redis://{host}:{port}"
        
        config = ConfigurationManager.get_high_performance_config(
            persistence_connection_string=connection_string
        )
        
        # Override to use Redis instead of default
        config.persistence.type = "redis"
        config.persistence.connection_string = connection_string
        
        assert config.max_concurrent_executions == 500
        assert config.jvm.heap_size == "4g"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

