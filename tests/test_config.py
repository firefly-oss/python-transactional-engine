#!/usr/bin/env python3
"""
Unit tests for configuration classes.
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

import pytest
import json
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from fireflytx.config.engine_config import (
    RetryConfig,
    PersistenceConfig,
    EventConfig,
    JvmConfig,
    LoggingConfig,
    EngineConfig,
    ConfigurationManager,
)


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay_ms == 1000
        assert config.max_delay_ms == 30000
        assert config.backoff_multiplier == 2.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5, initial_delay_ms=2000, max_delay_ms=60000, backoff_multiplier=1.5
        )

        assert config.max_attempts == 5
        assert config.initial_delay_ms == 2000
        assert config.max_delay_ms == 60000
        assert config.backoff_multiplier == 1.5

    def test_validation(self):
        """Test configuration validation."""
        # Valid configuration
        RetryConfig(initial_delay_ms=1000, max_delay_ms=5000)

        # Invalid: max_delay < initial_delay
        with pytest.raises(
            ValueError, match="max_delay_ms must be greater than or equal to initial_delay_ms"
        ):
            RetryConfig(initial_delay_ms=5000, max_delay_ms=1000)

        # Invalid: negative max_attempts
        with pytest.raises(ValueError):
            RetryConfig(max_attempts=0)


class TestPersistenceConfig:
    """Test PersistenceConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PersistenceConfig()

        assert config.type == "memory"
        assert config.connection_string == ""
        assert config.auto_checkpoint is True
        assert config.checkpoint_interval_seconds == 60
        assert config.max_transaction_age_hours == 24

    def test_persistence_types(self):
        """Test different persistence types."""
        # Valid types
        for ptype in ["memory", "file", "redis", "postgresql", "mongodb", "dynamodb"]:
            config = PersistenceConfig(type=ptype)
            assert config.type == ptype

        # Invalid type
        with pytest.raises(ValueError, match="Persistence type must be one of"):
            PersistenceConfig(type="invalid")

    def test_type_specific_config(self):
        """Test type-specific configuration."""
        redis_config = {"host": "localhost", "port": 6379}
        config = PersistenceConfig(type="redis", redis_config=redis_config)

        assert config.get_type_specific_config() == redis_config

        # No type-specific config
        config = PersistenceConfig(type="memory")
        assert config.get_type_specific_config() == {}


class TestEventConfig:
    """Test EventConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = EventConfig()

        assert config.enabled is True
        assert config.async_publishing is True
        assert config.buffer_size == 1000
        assert config.flush_interval_ms == 5000
        assert config.logging_enabled is True
        assert config.metrics_enabled is False
        assert config.custom_handlers == []

    def test_custom_handlers(self):
        """Test custom event handlers."""
        handlers = ["com.example.CustomHandler", "com.example.AnotherHandler"]
        config = EventConfig(custom_handlers=handlers)

        assert config.custom_handlers == handlers

    def test_external_configs(self):
        """Test external system configurations."""
        mqtt_config = {"broker": "localhost", "port": 1883}
        config = EventConfig(mqtt_config=mqtt_config)

        assert config.mqtt_config == mqtt_config


class TestJvmConfig:
    """Test JvmConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = JvmConfig()

        assert config.heap_size == "512m"
        assert config.additional_jvm_args == []
        assert config.classpath_entries == []
        assert config.system_properties == {}
        assert config.gc_algorithm == "G1GC"
        assert config.max_gc_pause_ms == 200

    def test_heap_size_validation(self):
        """Test heap size validation."""
        # Valid heap sizes
        for size in ["512m", "1G", "2g", "1024M", "512K"]:
            config = JvmConfig(heap_size=size)
            assert config.heap_size == size

        # Invalid heap sizes
        with pytest.raises(ValueError, match="heap_size must end with"):
            JvmConfig(heap_size="512")

        with pytest.raises(ValueError, match="heap_size must end with"):
            JvmConfig(heap_size="invalid")

    def test_jvm_args_generation(self):
        """Test JVM arguments generation."""
        config = JvmConfig(
            heap_size="1g",
            gc_algorithm="G1GC",
            max_gc_pause_ms=100,
            system_properties={"app.name": "test", "debug": "true"},
            additional_jvm_args=[
                "-Xdebug",
                "-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=5005",
            ],
        )

        args = config.get_jvm_args()

        assert "-Xmx1g" in args
        assert "-XX:+UseG1GC" in args
        assert "-XX:MaxGCPauseMillis=100" in args
        assert "-Dapp.name=test" in args
        assert "-Ddebug=true" in args
        assert "-Xdebug" in args
        assert "-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=5005" in args

    def test_gc_algorithms(self):
        """Test different GC algorithms."""
        # G1GC
        config = JvmConfig(gc_algorithm="G1GC")
        args = config.get_jvm_args()
        assert "-XX:+UseG1GC" in args

        # Parallel GC
        config = JvmConfig(gc_algorithm="PARALLEL")
        args = config.get_jvm_args()
        assert "-XX:+UseParallelGC" in args

        # ZGC
        config = JvmConfig(gc_algorithm="ZGC")
        args = config.get_jvm_args()
        assert "-XX:+UseZGC" in args


class TestEngineConfig:
    """Test EngineConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = EngineConfig()

        assert config.max_concurrent_executions == 100
        assert config.default_timeout_ms == 30000
        assert config.enable_monitoring is True
        assert config.thread_pool_size == 50
        assert config.transaction_cleanup_interval_seconds == 300
        assert config.enable_transaction_logging is True
        assert config.logging.level == "INFO"

        # Sub-configurations should be initialized
        assert isinstance(config.retry_config, RetryConfig)
        assert isinstance(config.persistence, PersistenceConfig)
        assert isinstance(config.events, EventConfig)
        assert isinstance(config.jvm, JvmConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_logging_config_validation(self):
        """Test logging configuration validation."""
        # Test with custom logging config
        config = EngineConfig()
        config.logging.level = "DEBUG"

        assert config.logging.level == "DEBUG"
        assert config.logging.format == "json"  # default
        assert config.logging.enable_java_logs is True  # default

    def test_custom_sub_configs(self):
        """Test custom sub-configurations."""
        retry_config = RetryConfig(max_attempts=5)
        persistence_config = PersistenceConfig(type="redis")

        config = EngineConfig(retry_config=retry_config, persistence=persistence_config)

        assert config.retry_config.max_attempts == 5
        assert config.persistence.type == "redis"

    def test_configuration_warnings(self):
        """Test configuration validation warnings."""
        # High concurrent executions
        config = EngineConfig(max_concurrent_executions=2000)
        warnings = config.validate_configuration()
        assert any("resource exhaustion" in w for w in warnings)

        # Thread pool larger than concurrent executions
        config = EngineConfig(max_concurrent_executions=50, thread_pool_size=100)
        warnings = config.validate_configuration()
        assert any("thread_pool_size is larger" in w for w in warnings)


class TestEngineConfigFileOperations:
    """Test EngineConfig file operations."""

    def test_to_file_json(self):
        """Test saving configuration to JSON file."""
        config = EngineConfig(max_concurrent_executions=200)
        config.logging.level = "DEBUG"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_path = f.name

        try:
            config.to_file(config_path, format="json")

            # Verify file exists and contains valid JSON
            assert Path(config_path).exists()

            with open(config_path) as f:
                data = json.load(f)

            assert data["max_concurrent_executions"] == 200
            assert data["logging"]["level"] == "DEBUG"

        finally:
            Path(config_path).unlink()

    def test_to_file_yaml(self):
        """Test saving configuration to YAML file."""
        config = EngineConfig(max_concurrent_executions=300)
        config.logging.level = "WARNING"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            config_path = f.name

        try:
            config.to_file(config_path, format="yaml")

            # Verify file exists and contains valid YAML
            assert Path(config_path).exists()

            with open(config_path) as f:
                data = yaml.safe_load(f)

            assert data["max_concurrent_executions"] == 300
            assert data["logging"]["level"] == "WARNING"

        finally:
            Path(config_path).unlink()

    def test_from_file_json(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "max_concurrent_executions": 150,
            "logging": {"level": "ERROR"},
            "persistence": {"type": "redis", "connection_string": "redis://localhost:6379"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            config = EngineConfig.from_file(config_path)

            assert config.max_concurrent_executions == 150
            assert config.logging.level == "ERROR"
            assert config.persistence.type == "redis"
            assert config.persistence.connection_string == "redis://localhost:6379"

        finally:
            Path(config_path).unlink()

    def test_from_file_yaml(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "max_concurrent_executions": 75,
            "logging": {"level": "DEBUG"},
            "jvm": {"heap_size": "2g", "gc_algorithm": "ZGC"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = EngineConfig.from_file(config_path)

            assert config.max_concurrent_executions == 75
            assert config.logging.level == "DEBUG"
            assert config.jvm.heap_size == "2g"
            assert config.jvm.gc_algorithm == "ZGC"

        finally:
            Path(config_path).unlink()

    def test_from_file_nonexistent(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            EngineConfig.from_file("/path/that/does/not/exist.json")

    def test_from_file_invalid_json(self):
        """Test loading from invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            config_path = f.name

        try:
            with pytest.raises(ValueError, match="Failed to parse configuration file"):
                EngineConfig.from_file(config_path)
        finally:
            Path(config_path).unlink()


class TestEngineConfigEnvironment:
    """Test EngineConfig environment variable loading."""

    def test_from_env_basic(self):
        """Test loading basic configuration from environment variables."""
        env_vars = {
            "PYTRANSACTIONAL_MAX_CONCURRENT_EXECUTIONS": "250",
            "PYTRANSACTIONAL_DEFAULT_TIMEOUT_MS": "45000",
            "PYTRANSACTIONAL_ENABLE_MONITORING": "false",
        }

        with patch.dict(os.environ, env_vars):
            config = EngineConfig.from_env()

            assert config.max_concurrent_executions == 250
            assert config.default_timeout_ms == 45000
            assert config.enable_monitoring is False

    def test_from_env_nested(self):
        """Test loading nested configuration from environment variables."""
        env_vars = {
            "PYTRANSACTIONAL_PERSISTENCE_TYPE": "postgresql",
            "PYTRANSACTIONAL_PERSISTENCE_CONNECTION_STRING": "postgresql://user:pass@localhost/db",
            "PYTRANSACTIONAL_JVM_HEAP_SIZE": "4g",
        }

        with patch.dict(os.environ, env_vars):
            config = EngineConfig.from_env()

            assert config.persistence.type == "postgresql"
            assert config.persistence.connection_string == "postgresql://user:pass@localhost/db"
            assert config.jvm.heap_size == "4g"

    def test_from_env_custom_prefix(self):
        """Test loading with custom environment variable prefix."""
        env_vars = {"CUSTOM_MAX_CONCURRENT_EXECUTIONS": "500"}

        with patch.dict(os.environ, env_vars):
            config = EngineConfig.from_env(prefix="CUSTOM_")

            assert config.max_concurrent_executions == 500

    def test_from_env_invalid_values(self):
        """Test handling of invalid environment variable values."""
        env_vars = {"PYTRANSACTIONAL_MAX_CONCURRENT_EXECUTIONS": "not_a_number"}

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError, match="Invalid value for"):
                EngineConfig.from_env()


class TestConfigurationManager:
    """Test ConfigurationManager utility class."""

    def test_create_default_config_file(self):
        """Test creating default configuration file."""
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as f:
            config_path = f.name

        try:
            ConfigurationManager.create_default_config_file(config_path)

            # Verify file exists
            assert Path(config_path).exists()

            # Verify it contains valid configuration
            config = EngineConfig.from_file(config_path)
            assert config.max_concurrent_executions == 100  # Default value

        finally:
            Path(config_path).unlink()

    def test_merge_configs_basic(self):
        """Test basic configuration merging."""
        config1 = EngineConfig(max_concurrent_executions=100)
        config2 = EngineConfig(max_concurrent_executions=200)

        merged = ConfigurationManager.merge_configs(config1, config2)

        # config2 should override config1
        assert merged.max_concurrent_executions == 200
        # Other values should remain default
        assert merged.default_timeout_ms == 30000

    def test_merge_configs_nested(self):
        """Test merging nested configurations."""
        config1 = EngineConfig(persistence=PersistenceConfig(type="memory", auto_checkpoint=True))
        config2 = EngineConfig(
            persistence=PersistenceConfig(type="redis", connection_string="redis://localhost")
        )

        merged = ConfigurationManager.merge_configs(config1, config2)

        # Nested values should be merged properly
        assert merged.persistence.type == "redis"  # Overridden
        assert merged.persistence.connection_string == "redis://localhost"  # New
        # Note: auto_checkpoint will be the default from config2, not preserved from config1
        # This is expected behavior for Pydantic model merging

    def test_merge_configs_empty(self):
        """Test merging with no configurations."""
        merged = ConfigurationManager.merge_configs()

        # Should return default configuration
        assert merged.max_concurrent_executions == 100

    def test_load_config_file_only(self):
        """Test loading configuration from file only."""
        config_data = {
            "max_concurrent_executions": 300,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            config = ConfigurationManager.load_config(config_file=config_path, use_env=False)

            assert config.max_concurrent_executions == 300

        finally:
            Path(config_path).unlink()

    def test_load_config_env_only(self):
        """Test loading configuration from environment only."""
        env_vars = {
            "PYTRANSACTIONAL_MAX_CONCURRENT_EXECUTIONS": "400",
        }

        with patch.dict(os.environ, env_vars):
            config = ConfigurationManager.load_config(config_file=None, use_env=True)

            assert config.max_concurrent_executions == 400

    def test_load_config_precedence(self):
        """Test configuration precedence (env overrides file)."""
        # Create config file
        config_data = {"max_concurrent_executions": 100, "thread_pool_size": 25}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        # Set environment variables that override some values
        env_vars = {
            "PYTRANSACTIONAL_MAX_CONCURRENT_EXECUTIONS": "500",
            # thread_pool_size not set in env, should use file value
        }

        try:
            with patch.dict(os.environ, env_vars):
                config = ConfigurationManager.load_config(config_file=config_path, use_env=True)

                # Environment should override file
                assert config.max_concurrent_executions == 500
                # File values should be preserved where no env override
                assert config.thread_pool_size == 25

        finally:
            Path(config_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
