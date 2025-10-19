"""
Java integration via subprocess instead of JPype1.

This approach bypasses the JPype1 compatibility issues with Java 21
by running Java as a separate process and communicating via JSON.
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
import logging
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Union

from .jar_builder import check_build_environment, get_jar_path

logger = logging.getLogger(__name__)


@dataclass
class JavaClassCallRequest:
    """Request to call a Java method."""

    class_name: str
    method_name: str
    method_type: str  # "static" or "instance" or "constructor"
    args: List[Any]
    instance_id: Optional[str] = None


@dataclass
class JavaClassCallResponse:
    """Response from a Java method call."""

    success: bool
    result: Any = None
    error: Optional[str] = None
    instance_id: Optional[str] = None


class JavaSubprocessBridge:
    """
    Java integration bridge using subprocess communication.

    This provides the same interface as JVMManager but uses subprocess
    communication instead of JPype1 to bypass compatibility issues.
    """

    def __init__(self):
        self._java_process: Optional[subprocess.Popen] = None
        self._java_started = False
        self._temp_dir = None
        self._request_counter = 0
        self._jar_path = None
        self._package_dir = Path(__file__).parent  # integration/ directory
        # Java log streaming state
        from collections import deque
        self._java_log_buffer = deque(maxlen=2000)  # ring buffer of recent lines
        self._java_log_followers = []  # callbacks(line: str, stream: str)
        self._java_stdout_thread = None
        self._java_stderr_thread = None
        self._java_log_file = None  # Optional file handle for teeing logs
        # Dedicated logger for Java output
        self._java_logger = logging.getLogger("fireflytx.java")
        # Honor env var for log level
        import os
        lvl = os.getenv("FIREFLYTX_JAVA_LOG_LEVEL")
        if lvl:
            try:
                self._java_logger.setLevel(getattr(logging, lvl.upper()))
            except Exception:
                self._java_logger.setLevel(logging.INFO)
        else:
            self._java_logger.setLevel(logging.INFO)

    def _convert_config_to_java_properties(self, config) -> dict:
        """
        Convert Python EngineConfig to Java Spring Boot properties.

        Maps Python configuration to firefly.tx.* properties that the
        Java lib-transactional-engine expects.

        Args:
            config: EngineConfig object or JvmConfig object

        Returns:
            Dictionary of Java system properties
        """
        props = {}

        if config is None:
            return props

        # Check if this is a full EngineConfig or just JvmConfig
        from fireflytx.config.engine_config import EngineConfig

        if isinstance(config, EngineConfig):
            # Engine-level configuration
            if hasattr(config, 'max_concurrent_executions'):
                props['firefly.tx.max-concurrent-transactions'] = str(config.max_concurrent_executions)

            if hasattr(config, 'default_timeout_ms'):
                # Convert milliseconds to ISO-8601 duration format (PT30S for 30 seconds)
                timeout_seconds = config.default_timeout_ms / 1000
                props['firefly.tx.default-timeout'] = f'PT{int(timeout_seconds)}S'

            # Persistence configuration
            if hasattr(config, 'persistence') and config.persistence:
                pers = config.persistence

                # Enable persistence if not memory type
                if hasattr(pers, 'type') and pers.type != 'memory':
                    props['firefly.tx.persistence.enabled'] = 'true'
                    props['firefly.tx.persistence.provider'] = pers.type

                    # Redis-specific configuration
                    if pers.type == 'redis' and hasattr(pers, 'connection_string'):
                        # Parse Redis connection string
                        conn_str = pers.connection_string
                        if conn_str:
                            # Simple parsing: redis://host:port or redis://host:port/db
                            import re
                            match = re.match(r'redis://([^:]+):(\d+)(?:/(\d+))?', conn_str)
                            if match:
                                host, port, db = match.groups()
                                props['firefly.tx.persistence.redis.host'] = host
                                props['firefly.tx.persistence.redis.port'] = port
                                if db:
                                    props['firefly.tx.persistence.redis.database'] = db
                            else:
                                # Fallback: assume it's just host:port
                                if ':' in conn_str:
                                    host, port = conn_str.replace('redis://', '').split(':')
                                    props['firefly.tx.persistence.redis.host'] = host
                                    props['firefly.tx.persistence.redis.port'] = port

                    # Redis config dict
                    if hasattr(pers, 'redis_config') and pers.redis_config:
                        redis_cfg = pers.redis_config
                        if 'password' in redis_cfg:
                            props['firefly.tx.persistence.redis.password'] = redis_cfg['password']
                        if 'db' in redis_cfg:
                            props['firefly.tx.persistence.redis.database'] = str(redis_cfg['db'])
                        if 'max_connections' in redis_cfg:
                            # Note: This might need to be mapped to Spring Redis pool config
                            pass

                    # Auto-checkpoint configuration
                    if hasattr(pers, 'auto_checkpoint'):
                        props['firefly.tx.persistence.auto-recovery-enabled'] = str(pers.auto_checkpoint).lower()

                    # Cleanup and retention
                    if hasattr(pers, 'checkpoint_interval_seconds'):
                        props['firefly.tx.persistence.cleanup-interval'] = f'PT{pers.checkpoint_interval_seconds}S'

                    if hasattr(pers, 'max_transaction_age_hours'):
                        props['firefly.tx.persistence.max-transaction-age'] = f'PT{pers.max_transaction_age_hours}H'
                else:
                    # Memory persistence (disabled)
                    props['firefly.tx.persistence.enabled'] = 'false'
                    props['firefly.tx.persistence.provider'] = 'in-memory'

            # Observability configuration
            if hasattr(config, 'enable_monitoring'):
                props['firefly.tx.observability.metrics-enabled'] = str(config.enable_monitoring).lower()

            # Event configuration
            if hasattr(config, 'events') and config.events:
                evt = config.events
                if hasattr(evt, 'enabled'):
                    props['firefly.tx.observability.event-logging-enabled'] = str(evt.enabled).lower()

                # Event provider configuration
                if hasattr(evt, 'provider') and evt.provider:
                    props['firefly.tx.events.provider'] = evt.provider

                # Kafka-specific configuration
                if hasattr(evt, 'provider') and evt.provider == 'kafka':
                    if hasattr(evt, 'kafka_config') and evt.kafka_config:
                        kafka_cfg = evt.kafka_config
                        if 'bootstrap_servers' in kafka_cfg:
                            props['firefly.tx.events.kafka.bootstrap-servers'] = kafka_cfg['bootstrap_servers']
                        if 'client_id' in kafka_cfg:
                            props['firefly.tx.events.kafka.client-id'] = kafka_cfg['client_id']
                        if 'acks' in kafka_cfg:
                            props['firefly.tx.events.kafka.acks'] = str(kafka_cfg['acks'])
                        if 'compression_type' in kafka_cfg:
                            props['firefly.tx.events.kafka.compression-type'] = kafka_cfg['compression_type']
                        if 'retries' in kafka_cfg:
                            props['firefly.tx.events.kafka.retries'] = str(kafka_cfg['retries'])
                        if 'batch_size' in kafka_cfg:
                            props['firefly.tx.events.kafka.batch-size'] = str(kafka_cfg['batch_size'])
                        if 'linger_ms' in kafka_cfg:
                            props['firefly.tx.events.kafka.linger-ms'] = str(kafka_cfg['linger_ms'])

                    # Topic configuration
                    if hasattr(evt, 'saga_topic'):
                        props['firefly.tx.events.saga-topic'] = evt.saga_topic
                    if hasattr(evt, 'tcc_topic'):
                        props['firefly.tx.events.tcc-topic'] = evt.tcc_topic

        return props

    def _validate_configuration(self, config) -> None:
        """
        Validate that external dependencies (Redis, Kafka, etc.) are available
        when configured.

        Args:
            config: EngineConfig object

        Raises:
            RuntimeError: If a configured dependency is not available
        """
        if config is None:
            return

        from fireflytx.config.engine_config import EngineConfig

        if not isinstance(config, EngineConfig):
            return

        # Validate Redis persistence if configured
        if hasattr(config, 'persistence') and config.persistence:
            pers = config.persistence
            if hasattr(pers, 'type') and pers.type == 'redis':
                if hasattr(pers, 'connection_string') and pers.connection_string:
                    # Try to connect to Redis to validate it's available
                    try:
                        import socket
                        import re

                        conn_str = pers.connection_string
                        match = re.match(r'redis://([^:]+):(\d+)', conn_str)
                        if match:
                            host, port = match.groups()
                            port = int(port)

                            # Try to connect with a short timeout
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(2.0)
                            try:
                                result = sock.connect_ex((host, port))
                                if result != 0:
                                    logger.warning(
                                        f"Redis persistence configured but Redis is not available at {host}:{port}. "
                                        f"The engine will fail to start if Redis is required."
                                    )
                            finally:
                                sock.close()
                    except Exception as e:
                        logger.warning(f"Could not validate Redis connection: {e}")

    def start_jvm(self, config=None, **kwargs) -> None:
        """Start the Java subprocess with the given configuration."""
        if self._java_started:
            logger.debug("Java subprocess already started")
            return

        try:
            # Validate configuration before starting
            self._validate_configuration(config)
            # Get classpath from config
            classpath = []
            if config and hasattr(config, "classpath_entries"):
                classpath.extend(config.classpath_entries)

            # Add default JAR if not provided - build from GitHub sources
            if not classpath:
                try:
                    # Check build environment first
                    if not check_build_environment():
                        raise RuntimeError(
                            "Build environment not ready. Please install Git and Java."
                        )

                    # Get/build the JAR from GitHub sources
                    jar_path = get_jar_path()
                    classpath.append(str(jar_path))
                    logger.info(f"Using JAR built from GitHub: {jar_path}")
                except Exception as e:
                    logger.error(f"Failed to build JAR from GitHub: {e}")
                    # No fallback JAR available - must build from GitHub
                    raise RuntimeError(
                        f"Failed to build JAR from GitHub and no fallback available: {e}"
                    )

            # Add all runtime dependencies (optional - lib-transactional-engine is self-contained)
            deps_dir = self._package_dir / "deps"
            if deps_dir.exists():
                dep_jars = list(deps_dir.glob("*.jar"))
                for dep_jar in dep_jars:
                    classpath.append(str(dep_jar))
                logger.info(f"Added {len(dep_jars)} runtime dependencies to classpath")
            else:
                logger.debug("No deps directory - using self-contained lib-transactional-engine JAR")

            if not classpath:
                raise RuntimeError("No JAR files found in classpath")

            self._jar_path = classpath[0]  # Store primary JAR path

            # Create temporary directory for communication
            self._temp_dir = tempfile.mkdtemp(prefix="java_bridge_")

            # Add our Java bridge JAR to classpath
            bridge_jar = self._package_dir / "java_bridge" / "java-subprocess-bridge.jar"
            if bridge_jar.exists():
                classpath.insert(0, str(bridge_jar))
                logger.info(f"Added Java subprocess bridge: {bridge_jar}")
            else:
                # Build the bridge JAR if it doesn't exist
                logger.info("Building Java subprocess bridge...")
                build_script = self._package_dir / "java_bridge" / "build.sh"
                if build_script.exists():
                    result = subprocess.run(
                        ["bash", str(build_script)],
                        capture_output=True,
                        text=True,
                        cwd=str(build_script.parent),
                    )
                    if result.returncode == 0:
                        logger.info("Java bridge built successfully")
                        classpath.insert(0, str(bridge_jar))
                    else:
                        logger.error(f"Failed to build Java bridge: {result.stderr}")
                        raise RuntimeError(f"Java bridge build failed: {result.stderr}")
                else:
                    raise RuntimeError(
                        f"Java bridge not found and build script missing: {build_script}"
                    )

            # Build Java command with configuration
            java_args = ["java", "-cp", ":".join(classpath)]

            # Add JVM configuration if provided
            if config and hasattr(config, "heap_size"):
                java_args.append(f"-Xmx{config.heap_size}")
                logger.debug(f"Using configured heap size: {config.heap_size}")
            else:
                java_args.append("-Xmx256m")  # Default heap size

            # Add additional JVM arguments from config
            if config and hasattr(config, "additional_jvm_args"):
                java_args.extend(config.additional_jvm_args)
                logger.debug(f"Added {len(config.additional_jvm_args)} additional JVM args")

            # Add system properties from config
            if config and hasattr(config, "system_properties"):
                for key, value in config.system_properties.items():
                    java_args.append(f"-D{key}={value}")
                logger.debug(f"Added {len(config.system_properties)} system properties")

            # Add engine configuration as Java system properties
            # This allows the Java lib-transactional-engine to receive Python configuration
            engine_props = self._convert_config_to_java_properties(config)
            for key, value in engine_props.items():
                java_args.append(f"-D{key}={value}")
            if engine_props:
                logger.debug(f"Added {len(engine_props)} engine configuration properties")

            # Add GC configuration if specified
            if config and hasattr(config, "gc_algorithm") and config.gc_algorithm:
                # Check if ZGC is explicitly enabled
                if hasattr(config, "zgc_enabled") and config.zgc_enabled:
                    java_args.append("-XX:+UseZGC")
                    logger.debug("Using ZGC (low-latency garbage collector)")
                elif config.gc_algorithm == "G1GC":
                    java_args.append("-XX:+UseG1GC")
                    logger.debug("Using G1GC garbage collector")

                    # G1GC specific tuning
                    if hasattr(config, "max_gc_pause_ms") and config.max_gc_pause_ms:
                        java_args.append(f"-XX:MaxGCPauseMillis={config.max_gc_pause_ms}")
                        logger.debug(f"G1GC max pause time: {config.max_gc_pause_ms}ms")

                    if hasattr(config, "g1_heap_region_size") and config.g1_heap_region_size:
                        java_args.append(f"-XX:G1HeapRegionSize={config.g1_heap_region_size}")
                        logger.debug(f"G1 heap region size: {config.g1_heap_region_size}")

                    if hasattr(config, "initiating_heap_occupancy_percent") and config.initiating_heap_occupancy_percent:
                        java_args.append(f"-XX:InitiatingHeapOccupancyPercent={config.initiating_heap_occupancy_percent}")
                        logger.debug(f"G1 IHOP: {config.initiating_heap_occupancy_percent}%")

                elif config.gc_algorithm == "ZGC":
                    java_args.append("-XX:+UseZGC")
                    logger.debug("Using ZGC garbage collector")
                elif config.gc_algorithm == "ParallelGC":
                    java_args.append("-XX:+UseParallelGC")
                    logger.debug("Using ParallelGC garbage collector")
                elif config.gc_algorithm == "SerialGC":
                    java_args.append("-XX:+UseSerialGC")
                    logger.debug("Using SerialGC garbage collector")

                # Thread configuration
                if hasattr(config, "parallel_gc_threads") and config.parallel_gc_threads:
                    java_args.append(f"-XX:ParallelGCThreads={config.parallel_gc_threads}")
                    logger.debug(f"Parallel GC threads: {config.parallel_gc_threads}")

                if hasattr(config, "concurrent_gc_threads") and config.concurrent_gc_threads:
                    java_args.append(f"-XX:ConcGCThreads={config.concurrent_gc_threads}")
                    logger.debug(f"Concurrent GC threads: {config.concurrent_gc_threads}")

                # Memory management
                if hasattr(config, "max_metaspace_size") and config.max_metaspace_size:
                    java_args.append(f"-XX:MaxMetaspaceSize={config.max_metaspace_size}")
                    logger.debug(f"Max metaspace size: {config.max_metaspace_size}")

                if hasattr(config, "compressed_oops") and not config.compressed_oops:
                    java_args.append("-XX:-UseCompressedOops")
                    logger.debug("Compressed OOPs disabled")

                # GC logging
                if hasattr(config, "enable_gc_logging") and config.enable_gc_logging:
                    if hasattr(config, "gc_log_file") and config.gc_log_file:
                        java_args.append(f"-Xlog:gc*:file={config.gc_log_file}:time,uptime,level,tags")
                        logger.debug(f"GC logging enabled to file: {config.gc_log_file}")
                    else:
                        java_args.append("-Xlog:gc*:stdout:time,uptime,level,tags")
                        logger.debug("GC logging enabled to stdout")

            # Always add headless mode
            java_args.append("-Djava.awt.headless=true")

            # Add main class and temp directory
            java_args.extend([
                "com.firefly.transactional.BridgeApplication",  # Spring Boot application
                self._temp_dir,
            ])

            logger.info(f"Starting Java subprocess: {' '.join(java_args)}")

            # Start Java subprocess for integration
            try:
                self._java_process = subprocess.Popen(
                    java_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line buffered
                )

                # Wait briefly for startup
                time.sleep(1.0)

                # Check if process started successfully
                if self._java_process.poll() is not None:
                    stdout, stderr = self._java_process.communicate()
                    raise RuntimeError(
                        f"Java process exited immediately. stdout: {stdout}, stderr: {stderr}"
                    )

                self._java_started = True
                logger.info("Java subprocess bridge started successfully")
                # Start Java log readers to stream engine logs to Python
                self._start_log_readers()
            except Exception as e:
                logger.error(f"Failed to start Java process: {e}")
                raise RuntimeError(f"Java subprocess failed: {e}") from e

        except Exception as e:
            logger.error(f"Failed to start Java subprocess: {e}")
            raise RuntimeError(f"Java subprocess initialization failed: {e}") from e

        # Initialize subprocess communication after process starts
        self._initialize_communication()

    def _initialize_communication(self):
        """Initialize communication directories and metadata after Java process starts."""
        try:
            # Create request/response directories for communication
            request_dir = Path(self._temp_dir) / "requests"
            response_dir = Path(self._temp_dir) / "responses"
            request_dir.mkdir(parents=True, exist_ok=True)
            response_dir.mkdir(parents=True, exist_ok=True)

            # Store known class names for method calls
            self._known_classes = {
                "com.firefly.transactional.saga.engine.SagaEngine",
                "com.firefly.transactional.saga.engine.SagaExecutionOrchestrator",
                "com.firefly.transactional.tcc.engine.TccEngine",
                "com.firefly.transactional.tcc.engine.TccExecutionOrchestrator",
            }

            # Get and log lib-transactional-engine version
            lib_version = self._get_lib_transactional_version()
            if lib_version:
                logger.info(f"🔧 lib-transactional-engine loaded: {lib_version}")
            else:
                logger.info("🔧 lib-transactional-engine loaded: version unknown")

            logger.info("Java subprocess communication initialized")

        except Exception as e:
            logger.error(f"Failed to initialize communication: {e}")
            raise RuntimeError(f"Communication initialization failed: {e}") from e

    def get_lib_transactional_version(self) -> Optional[str]:
        """Get the lib-transactional-engine version information."""
        return self._get_lib_transactional_version()

    def get_available_methods(self, class_name: str) -> List[str]:
        """Get available methods for a Java class."""
        if not self._java_started:
            return []

        try:
            request = JavaClassCallRequest(
                class_name=class_name, method_name="__introspect__", method_type="static", args=[]
            )

            response = self.call_java_method(request)
            if response.success and isinstance(response.result, list):
                return response.result
            return []
        except Exception:
            return []

    def _get_lib_transactional_version(self) -> Optional[str]:
        """Extract version information from the lib-transactional-engine JAR manifest if possible."""
        try:
            if getattr(self, "_jar_path", None):
                from zipfile import ZipFile
                with ZipFile(self._jar_path, 'r') as jar:
                    # Try common manifest location
                    manifest_path = 'META-INF/MANIFEST.MF'
                    if manifest_path in jar.namelist():
                        with jar.open(manifest_path) as mf:
                            content = mf.read().decode('utf-8', errors='ignore')
                            impl_version = None
                            impl_title = None
                            for line in content.splitlines():
                                if line.startswith('Implementation-Version:'):
                                    impl_version = line.split(':', 1)[1].strip()
                                elif line.startswith('Implementation-Title:'):
                                    impl_title = line.split(':', 1)[1].strip()
                            if impl_version:
                                # Optionally include title if available
                                return impl_version if not impl_title else f"{impl_title} {impl_version}"
                # Fallback: derive from filename
                jar_name = Path(self._jar_path).name
                # Example: lib-transactional-engine-1.2.3.jar
                if '-' in jar_name and jar_name.endswith('.jar'):
                    parts = jar_name[:-4].split('-')
                    # take the last token as version if it looks like one
                    if len(parts) >= 2:
                        candidate = parts[-1]
                        return candidate
            # Default fallback
            return "1.0.0-SNAPSHOT"
        except Exception:
            return "1.0.0-SNAPSHOT"

    def is_jvm_started(self) -> bool:
        """Check if the Java subprocess is started."""
        return self._java_started

    def get_java_class(self, class_name: str) -> "JavaClassProxy":
        """Get a proxy for a Java class."""
        if not self._java_started:
            raise RuntimeError("Java subprocess not started. Call start_jvm() first.")

        return JavaClassProxy(self, class_name)

    # ----------------------- Java log streaming APIs -----------------------
    def _start_log_readers(self) -> None:
        """Start background threads to read Java stdout/stderr and forward to Python logger."""
        import threading
        if not self._java_process:
            return
        if self._java_stdout_thread and self._java_stdout_thread.is_alive():
            return  # already running

        self._java_stdout_thread = threading.Thread(
            target=self._log_reader, args=("STDOUT", self._java_process.stdout), daemon=True
        )
        self._java_stderr_thread = threading.Thread(
            target=self._log_reader, args=("STDERR", self._java_process.stderr), daemon=True
        )
        self._java_stdout_thread.start()
        self._java_stderr_thread.start()

    def _log_reader(self, stream_name: str, pipe) -> None:
        """Continuously read a pipe and dispatch lines to logger, buffer, and followers."""
        try:
            for raw_line in iter(pipe.readline, ''):
                line = raw_line.rstrip('\n')
                if not line:
                    continue
                # Format entry
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                formatted = f"[{timestamp}] [JAVA][{stream_name}] {line}"
                # Store in ring buffer
                try:
                    self._java_log_buffer.append((stream_name, formatted))
                except Exception:
                    pass
                # Tee to file if configured
                try:
                    if self._java_log_file:
                        self._java_log_file.write(formatted + "\n")
                        self._java_log_file.flush()
                except Exception:
                    pass
                # Emit to Python logger
                if stream_name == "STDERR":
                    # Use ERROR if looks like an exception, else WARNING
                    level = logging.ERROR if ("Exception" in line or "ERROR" in line) else logging.WARNING
                else:
                    level = logging.INFO
                try:
                    self._java_logger.log(level, formatted)
                except Exception:
                    logger.log(level, formatted)
                # Notify followers
                for cb in list(self._java_log_followers):
                    try:
                        cb(formatted, stream_name)
                    except Exception:
                        # Remove failing callbacks silently
                        try:
                            self._java_log_followers.remove(cb)
                        except Exception:
                            pass
        except Exception as e:
            try:
                self._java_logger.debug(f"Java log reader stopped for {stream_name}: {e}")
            except Exception:
                pass

    def set_java_log_level(self, level: Union[int, str]) -> None:
        """Set the Python logger level for Java output (e.g., logging.INFO or 'DEBUG')."""
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        self._java_logger.setLevel(level)

    def get_java_logs(self, count: int = 100) -> List[str]:
        """Return the last N Java log lines (formatted)."""
        try:
            return [entry[1] for entry in list(self._java_log_buffer)[-count:]]
        except Exception:
            return []

    def follow_java_logs(self, callback) -> None:
        """Register a callback(line: str, stream: str) to receive new Java log lines."""
        if callable(callback):
            self._java_log_followers.append(callback)

    def enable_java_log_file(self, file_path: str) -> None:
        """Enable teeing Java logs to a file."""
        try:
            if self._java_log_file:
                try:
                    self._java_log_file.flush()
                    self._java_log_file.close()
                except Exception:
                    pass
            self._java_log_file = open(file_path, 'a', encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to open Java log file '{file_path}': {e}")
            self._java_log_file = None

    def disable_java_log_file(self) -> None:
        """Disable log file teeing for Java logs."""
        if self._java_log_file:
            try:
                self._java_log_file.flush()
                self._java_log_file.close()
            except Exception:
                pass
            self._java_log_file = None

    @property
    def temp_dir(self) -> Optional[str]:
        """Get the temporary directory used for Java bridge communication."""
        return self._temp_dir

    @property
    def process(self):
        """Get the Java subprocess."""
        return self._java_process

    def shutdown(self) -> None:
        """Shutdown the Java subprocess."""
        self.shutdown_jvm()

    def shutdown_jvm(self) -> None:
        """Shutdown the Java subprocess."""
        if self._java_started:
            try:
                # Stop log readers first
                try:
                    if self._java_log_file:
                        try:
                            self._java_log_file.flush()
                            self._java_log_file.close()
                        except Exception:
                            pass
                        self._java_log_file = None
                except AttributeError:
                    # Log streaming not initialized
                    pass

                if self._java_process and self._java_process.poll() is None:
                    self._java_process.terminate()
                    self._java_process.wait(timeout=5)
                self._java_started = False

                # Join reader threads
                for th in (getattr(self, "_java_stdout_thread", None), getattr(self, "_java_stderr_thread", None)):
                    if th and th.is_alive():
                        try:
                            th.join(timeout=1.0)
                        except Exception:
                            pass
                logger.info("Java subprocess shutdown successfully")
            except Exception as e:
                logger.error(f"Error shutting down Java subprocess: {e}")
        else:
            logger.debug("Java subprocess was not started")

    def call_java_method(self, request: JavaClassCallRequest) -> JavaClassCallResponse:
        """Call a Java method using subprocess integration."""
        if not self._java_started:
            raise RuntimeError("Java subprocess not started")

        return self._call_java_method(request)

    def _call_java_method(self, request: JavaClassCallRequest) -> JavaClassCallResponse:
        """Call Java methods using JSON file communication."""

        logger.debug(
            f"🔄 [IPC] Python → Java: {request.class_name}.{request.method_name}({request.method_type})"
        )

        try:
            # Generate unique request ID
            request_id = str(uuid.uuid4())

            # Prepare request data
            request_data = {
                "requestId": request_id,
                "className": request.class_name,
                "methodName": request.method_name,
                "methodType": request.method_type,
                "args": request.args,
            }

            if request.instance_id:
                request_data["instanceId"] = request.instance_id

            # Write request to JSON file
            request_file = Path(self._temp_dir) / "requests" / f"{request_id}.json"
            logger.debug(f"📤 [IPC] Writing request to: {request_file.name}")
            with open(request_file, "w") as f:
                json.dump(request_data, f)

            # Wait for response
            response_file = Path(self._temp_dir) / "responses" / f"{request_id}.json"
            logger.debug(f"⏳ [IPC] Waiting for response: {response_file.name}")
            response_data = self._wait_for_response(response_file, timeout=30)

            if response_data["success"]:
                logger.debug(f"✅ [IPC] Java → Python: Success")
                return JavaClassCallResponse(
                    success=True,
                    result=response_data.get("result"),
                    instance_id=response_data.get("instanceId"),
                )
            else:
                logger.error(f"❌ [IPC] Java → Python: Error - {response_data.get('error')}")
                return JavaClassCallResponse(
                    success=False, error=response_data.get("error", "Unknown Java error")
                )

        except Exception as e:
            logger.error(f"❌ [IPC] Method call failed: {e}")
            return JavaClassCallResponse(success=False, error=str(e))

    def _wait_for_response(self, response_file: Path, timeout: int = 30) -> dict:
        """Wait for Java response file to be created."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if response_file.exists():
                try:
                    with open(response_file) as f:
                        response_data = json.load(f)

                    # Clean up response file
                    response_file.unlink()
                    return response_data

                except (OSError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to read response file: {e}")
                    time.sleep(0.1)
                    continue

            time.sleep(0.1)  # Poll every 100ms

        raise TimeoutError(f"Java response timeout after {timeout}s")

    # TCC specific methods

    def executeTcc(
        self, tcc_name: str, correlation_id: str, tcc_inputs: dict, callback_info: dict = None
    ) -> dict:
        """Execute a TCC transaction with callback support."""
        try:
            logger.info(f"Executing TCC: {tcc_name} with correlation ID: {correlation_id}")

            # Create TCC engine instance
            tcc_engine_request = JavaClassCallRequest(
                class_name="com.firefly.transactional.tcc.engine.TccEngine",
                method_name="__constructor__",
                method_type="constructor",
                args=[],
            )

            tcc_engine_response = self.call_java_method(tcc_engine_request)
            if not tcc_engine_response.success:
                raise RuntimeError(f"Failed to create TCC engine: {tcc_engine_response.error}")

            engine_instance_id = tcc_engine_response.instance_id

            # Execute TCC with callbacks
            execute_request = JavaClassCallRequest(
                class_name="com.firefly.transactional.tcc.engine.TccEngine",
                method_name="executeTcc",
                method_type="instance",
                instance_id=engine_instance_id,
                args=[tcc_name, correlation_id, tcc_inputs, callback_info],
            )

            execute_response = self.call_java_method(execute_request)
            if execute_response.success:
                return execute_response.result
            else:
                raise RuntimeError(f"TCC execution failed: {execute_response.error}")

        except Exception as e:
            logger.error(f"TCC execution error: {e}")
            return {
                "tcc_name": tcc_name,
                "correlation_id": correlation_id,
                "success": False,
                "error": str(e),
                "phase": "FAILED",
                "participant_results": {},
            }

    def registerTccDefinition(self, tcc_definition: dict) -> str:
        """Register a TCC definition with the Java bridge."""
        try:
            logger.info(f"Registering TCC definition: {tcc_definition.get('tcc_name')}")

            # Create TCC engine instance
            tcc_engine_request = JavaClassCallRequest(
                class_name="com.firefly.transactional.tcc.engine.TccEngine",
                method_name="__constructor__",
                method_type="constructor",
                args=[],
            )

            tcc_engine_response = self.call_java_method(tcc_engine_request)
            if not tcc_engine_response.success:
                raise RuntimeError(f"Failed to create TCC engine: {tcc_engine_response.error}")

            engine_instance_id = tcc_engine_response.instance_id

            # Register TCC definition
            register_request = JavaClassCallRequest(
                class_name="com.firefly.transactional.tcc.engine.TccEngine",
                method_name="registerTccDefinition",
                method_type="instance",
                instance_id=engine_instance_id,
                args=[tcc_definition],
            )

            register_response = self.call_java_method(register_request)
            if register_response.success:
                logger.info(f"TCC definition registered: {tcc_definition.get('tcc_name')}")
                return register_response.result
            else:
                raise RuntimeError(f"TCC registration failed: {register_response.error}")

        except Exception as e:
            logger.error(f"TCC registration error: {e}")
            raise RuntimeError(f"Failed to register TCC definition: {e}") from e


class JavaClassProxy:
    """Proxy for a Java class that communicates via subprocess."""

    def __init__(self, bridge: JavaSubprocessBridge, class_name: str):
        self._bridge = bridge
        self._class_name = class_name
        self._instance_id = None

        # Add common nested classes for SagaEngine
        if "SagaEngine" in class_name:
            self.CompensationPolicy = JavaNestedClassProxy(
                bridge, f"{class_name}$CompensationPolicy"
            )

    def __call__(self, *args, **kwargs):
        """Constructor call."""
        request = JavaClassCallRequest(
            class_name=self._class_name,
            method_name="__constructor__",
            method_type="constructor",
            args=list(args),
        )

        response = self._bridge.call_java_method(request)
        if response.success:
            # Create a new instance proxy
            instance = JavaInstanceProxy(self._bridge, self._class_name, response.instance_id)
            return instance
        else:
            raise RuntimeError(f"Failed to create {self._class_name}: {response.error}")

    def __getattr__(self, name):
        """Access static methods and fields."""
        if name == "valueOf":  # Handle common static method

            def value_of(*args, **kwargs):
                request = JavaClassCallRequest(
                    class_name=self._class_name,
                    method_name="valueOf",
                    method_type="static",
                    args=list(args),
                )
                response = self._bridge.call_java_method(request)
                if response.success:
                    return JavaInstanceProxy(
                        self._bridge, self._class_name, response.instance_id or str(uuid.uuid4())
                    )
                else:
                    raise RuntimeError(f"Java method call failed: {response.error}")

            return value_of

        def static_method(*args, **kwargs):
            request = JavaClassCallRequest(
                class_name=self._class_name, method_name=name, method_type="static", args=list(args)
            )
            response = self._bridge.call_java_method(request)
            if response.success:
                if response.instance_id:  # If it returns an instance
                    return JavaInstanceProxy(self._bridge, self._class_name, response.instance_id)
                return response.result
            else:
                raise RuntimeError(f"Java method call failed: {response.error}")

        return static_method


class JavaNestedClassProxy:
    """Proxy for nested Java classes (like enums)."""

    def __init__(self, bridge: JavaSubprocessBridge, class_name: str):
        self._bridge = bridge
        self._class_name = class_name

    def valueOf(self, value: str):
        """Handle enum valueOf calls."""
        request = JavaClassCallRequest(
            class_name=self._class_name, method_name="valueOf", method_type="static", args=[value]
        )
        response = self._bridge.call_java_method(request)
        if response.success:
            return JavaInstanceProxy(
                self._bridge, self._class_name, response.instance_id or str(uuid.uuid4())
            )
        else:
            raise RuntimeError(f"valueOf call failed: {response.error}")


class JavaInstanceProxy:
    """Proxy for a Java instance that communicates via subprocess."""

    def __init__(self, bridge: JavaSubprocessBridge, class_name: str, instance_id: str):
        self._bridge = bridge
        self._class_name = class_name
        self._instance_id = instance_id

    def __getattr__(self, name):
        """Access instance methods."""

        def instance_method(*args, **kwargs):
            request = JavaClassCallRequest(
                class_name=self._class_name,
                method_name=name,
                method_type="instance",
                args=list(args),
                instance_id=self._instance_id,
            )
            response = self._bridge.call_java_method(request)
            if response.success:
                return response.result
            else:
                raise RuntimeError(f"Java method call failed: {response.error}")

        return instance_method


# Global bridge instance
_java_bridge = JavaSubprocessBridge()


def get_java_bridge() -> JavaSubprocessBridge:
    """Get the global Java subprocess bridge."""
    return _java_bridge
