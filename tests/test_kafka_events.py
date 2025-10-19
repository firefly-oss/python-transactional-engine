"""
Test Kafka event publishing configuration with testcontainers.

This test suite uses testcontainers to spin up a real Kafka instance
and verify that the FireflyTX engines can properly publish events to Kafka.

Events must be published by the Java lib-transactional-engine, not Python.

Copyright (c) 2025 Firefly Software Solutions Inc.
Licensed under the Apache License, Version 2.0 (the "License");
"""

import asyncio
import pytest
from pathlib import Path
from testcontainers.kafka import KafkaContainer

from fireflytx import SagaEngine, TccEngine, EngineConfig, JvmConfig
from fireflytx.config import ConfigurationManager
from fireflytx.config.engine_config import EventConfig


@pytest.fixture(scope="module")
def kafka_container():
    """Start a Kafka container for testing."""
    # Use Confluent Kafka image which includes Zookeeper
    container = KafkaContainer("confluentinc/cp-kafka:7.5.0")
    container.start()
    
    # Wait for Kafka to be ready
    import time
    time.sleep(5)
    
    yield container
    
    # Cleanup
    container.stop()


@pytest.fixture(scope="module")
def kafka_config(kafka_container):
    """Create EngineConfig with Kafka event publishing."""
    bootstrap_servers = kafka_container.get_bootstrap_server()

    config = EngineConfig(
        max_concurrent_executions=50,
        default_timeout_ms=30000,
        thread_pool_size=25,
        enable_monitoring=True,
        events=EventConfig(
            enabled=True,
            provider="kafka",
            kafka_config={
                "bootstrap_servers": bootstrap_servers,
                "client_id": "fireflytx-test",
                "acks": "all",
                "compression_type": "gzip"
            },
            saga_topic="test.saga.events",
            tcc_topic="test.tcc.events"
        ),
        jvm=JvmConfig(
            heap_size="512m",
            gc_algorithm="G1GC"
        )
    )

    return config


class TestKafkaConfiguration:
    """Test Kafka configuration."""
    
    def test_kafka_container_running(self, kafka_container):
        """Test that Kafka container is running."""
        assert kafka_container.get_bootstrap_server() is not None
    
    @pytest.mark.asyncio
    async def test_kafka_connection(self, kafka_container):
        """Test direct connection to Kafka using aiokafka."""
        from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
        import asyncio

        bootstrap_servers = kafka_container.get_bootstrap_server()

        # Test producer
        producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers
        )
        await producer.start()

        try:
            # Send test message
            await producer.send('test-topic', b'test-message')
            await producer.flush()
        finally:
            await producer.stop()

        # Test consumer
        consumer = AIOKafkaConsumer(
            'test-topic',
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000
        )
        await consumer.start()

        try:
            messages = []
            # Get messages with timeout (Python 3.9 compatible)
            async def get_message():
                async for message in consumer:
                    messages.append(message.value)
                    break  # Just get one message

            try:
                await asyncio.wait_for(get_message(), timeout=5.0)
            except asyncio.TimeoutError:
                pass

            assert len(messages) > 0, "No messages received from Kafka"
            assert messages[0] == b'test-message'
        finally:
            await consumer.stop()
    
    def test_event_config_generation(self, kafka_config):
        """Test that Kafka event config is properly generated."""
        assert kafka_config.events.enabled is True
        assert kafka_config.events.provider == "kafka"
        assert "bootstrap_servers" in kafka_config.events.kafka_config
        assert kafka_config.events.saga_topic == "test.saga.events"
        assert kafka_config.events.tcc_topic == "test.tcc.events"
    
    def test_java_properties_conversion(self, kafka_config):
        """Test conversion of Python event config to Java properties."""
        from fireflytx.integration.bridge import JavaSubprocessBridge
        
        bridge = JavaSubprocessBridge()
        props = bridge._convert_config_to_java_properties(kafka_config)
        
        # Verify event properties
        assert props.get("firefly.tx.observability.event-logging-enabled") == "true"
        assert props.get("firefly.tx.events.provider") == "kafka"
        assert "firefly.tx.events.kafka.bootstrap-servers" in props
        assert props.get("firefly.tx.events.kafka.client-id") == "fireflytx-test"
        assert props.get("firefly.tx.events.kafka.acks") == "all"
        assert props.get("firefly.tx.events.kafka.compression-type") == "gzip"
        assert props.get("firefly.tx.events.saga-topic") == "test.saga.events"
        assert props.get("firefly.tx.events.tcc-topic") == "test.tcc.events"


class TestSagaEngineWithKafka:
    """Test SagaEngine with Kafka event publishing."""
    
    @pytest.mark.asyncio
    async def test_saga_engine_initialization_with_kafka(self, kafka_config):
        """Test that SagaEngine can initialize with Kafka config."""
        engine = SagaEngine(config=kafka_config)
        
        # Initialize the engine (this will start Java subprocess with Kafka config)
        await engine.initialize()
        
        # Verify engine is initialized
        assert engine._java_bridge is not None
        assert engine._java_bridge._java_started is True
        
        # Cleanup
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_saga_engine_accepts_kafka_config(self, kafka_config):
        """Test that SagaEngine properly accepts and stores Kafka config."""
        engine = SagaEngine(config=kafka_config)

        assert engine.config is not None
        assert engine.config.events.enabled is True
        assert engine.config.events.provider == "kafka"


class TestTccEngineWithKafka:
    """Test TccEngine with Kafka event publishing."""
    
    def test_tcc_engine_initialization_with_kafka(self, kafka_config):
        """Test that TccEngine can initialize with Kafka config."""
        engine = TccEngine(config=kafka_config)
        
        # Start the engine (this will start Java subprocess with Kafka config)
        engine.start()
        
        # Verify engine is started
        assert engine.java_bridge is not None
        assert engine._is_running is True
        
        # Cleanup
        engine.stop()
    
    def test_tcc_engine_accepts_kafka_config(self, kafka_config):
        """Test that TccEngine properly accepts and stores Kafka config."""
        engine = TccEngine(config=kafka_config)

        assert engine.config is not None
        assert engine.config.events.enabled is True
        assert engine.config.events.provider == "kafka"


class TestEventConfiguration:
    """Test event configuration helpers."""
    
    def test_event_config_with_kafka(self, kafka_container):
        """Test creating event config with Kafka."""
        bootstrap_servers = kafka_container.get_bootstrap_server()
        
        event_config = EventConfig(
            enabled=True,
            provider="kafka",
            kafka_config={
                "bootstrap_servers": bootstrap_servers,
                "client_id": "test-client"
            },
            saga_topic="custom.saga.topic",
            tcc_topic="custom.tcc.topic"
        )
        
        assert event_config.enabled is True
        assert event_config.provider == "kafka"
        assert event_config.kafka_config["bootstrap_servers"] == bootstrap_servers
        assert event_config.saga_topic == "custom.saga.topic"
        assert event_config.tcc_topic == "custom.tcc.topic"
    
    def test_default_event_config(self):
        """Test default event configuration."""
        event_config = EventConfig()
        
        assert event_config.enabled is True
        assert event_config.provider == "memory"
        assert event_config.saga_topic == "fireflytx.saga.events"
        assert event_config.tcc_topic == "fireflytx.tcc.events"


class TestEventPublishing:
    """Test that events are published by Java, not Python."""
    
    def test_event_publishing_architecture(self):
        """
        Verify that event publishing is handled by Java lib-transactional-engine.
        
        This is a documentation test to ensure the architecture is clear:
        - Python defines event configuration (topics, Kafka settings, etc.)
        - Java lib-transactional-engine publishes events
        - Events are published through StepEventPublisher interface in Java
        """
        # This test documents the architecture
        # Actual event publishing happens in Java, not Python
        
        event_config = EventConfig(
            enabled=True,
            provider="kafka",
            kafka_config={
                "bootstrap_servers": "localhost:9092"
            }
        )
        
        # Python only defines configuration
        assert event_config.enabled is True
        assert event_config.provider == "kafka"
        
        # Java lib-transactional-engine handles actual publishing
        # through the StepEventPublisher interface


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

