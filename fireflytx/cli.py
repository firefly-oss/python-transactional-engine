#!/usr/bin/env python3
"""
Command-line interface for the Python Transactional Engine.

Provides utilities for managing the engine, running tests, and debugging.

Copyright 2025 Firefly Software Solutions Inc
Licensed under the Apache License, Version 2.0
https://github.com/firefly-oss/python-transactional-engine
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from fireflytx import SagaEngine, TccEngine, __version__
from fireflytx.config.engine_config import EngineConfig
from fireflytx.logging import (
    JavaLogLevel,
    LogFilter,
    LogViewer,
    get_java_log_bridge,
    setup_fireflytx_logging,
)

# JVM management handled by Java subprocess bridge
from fireflytx.integration.jar_builder import JarBuilder, check_build_environment
from fireflytx.visualization import OutputFormat, SagaVisualizer, TccVisualizer


def print_firefly_banner() -> None:
    """Print the Firefly ASCII art banner."""
    banner = r"""
  _____.__                _____.__
_/ ____\__|______   _____/ ____\  | ___.__.
\   __\|  \_  __ \_/ __ \   __\|  |<   |  |
 |  |  |  ||  | \/\  ___/|  |  |  |_\___  |
 |__|  |__||__|    \___  >__|  |____/ ____|
                       \/           \/
:: fireflytx ::                  (v2025-08)
                                                 
Python Wrapper for Firefly Transactional Engine    

Copyright © 2025 Firefly Software Solutions Inc
Licensed under Apache License 2.0
    
🌐 Website: https://getfirefly.io
📚 Docs: https://github.com/firefly-oss/python-transactional-engine
💬 Issues: https://github.com/firefly-oss/python-transactional-engine/issues
    """
    print(banner)


def print_copyright_info() -> None:
    """Print copyright and license information."""
    info = """
Firefly Transactional Engine Python Wrapper
Copyright © 2025 Firefly Software Solutions Inc

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Website: https://getfirefly.io
Repository: https://github.com/firefly-oss/python-transactional-engine
    """
    print(info)


def setup_logging(
    level: str = "INFO", format_type: str = "json", enable_java_logs: bool = True
) -> None:
    """Configure logging for CLI with JSON support."""
    from fireflytx.config.engine_config import EngineConfig, LoggingConfig

    # Create logging configuration
    logging_config = LoggingConfig(
        level=level.upper(), format=format_type, enable_java_logs=enable_java_logs
    )

    # Create minimal engine config with logging settings
    config = EngineConfig(logging=logging_config)

    # Setup FireflyTX logging system
    setup_fireflytx_logging(config)


def create_sample_config(output_path: str) -> None:
    """Create a sample configuration file."""
    config = {
        "engine": {
            "max_concurrent_executions": 50,
            "default_timeout_ms": 30000,
            "retry_config": {
                "max_attempts": 3,
                "initial_delay_ms": 1000,
                "max_delay_ms": 10000,
                "backoff_multiplier": 2.0,
            },
        },
        "persistence": {
            "type": "file",
            "connection_string": "./transactional_state",
            "auto_checkpoint": True,
            "checkpoint_interval_seconds": 60,
        },
        "jvm": {
            "heap_size": "512m",
            "additional_jvm_args": ["-XX:+UseG1GC", "-XX:MaxGCPauseMillis=200"],
        },
        "logging": {
            "level": "INFO",
            "format": "json",
            "enable_java_logs": True,
            "java_log_level": "INFO",
            "output_file": None,
            "max_file_size_mb": 100,
            "backup_count": 5,
            "include_thread_info": True,
            "include_module_info": True,
        },
    }

    Path(output_path).write_text(json.dumps(config, indent=2))
    print(f"Sample configuration written to {output_path}")


async def test_engine_connectivity() -> None:
    """Test engine connectivity and basic functionality."""
    print("Testing Java/JVM connectivity...")

    try:
        # JVM is managed by Java subprocess bridge
        print("✓ JVM managed by Java subprocess bridge")

        # Test SAGA engine initialization
        print("Testing SAGA engine...")
        saga_engine = SagaEngine()
        await saga_engine.initialize()
        print("✓ SAGA engine initialized")

        # Test TCC engine initialization
        print("Testing TCC engine...")
        tcc_engine = TccEngine()
        await tcc_engine.initialize()
        print("✓ TCC engine initialized")

        # Clean up
        await saga_engine.shutdown()
        await tcc_engine.shutdown()

        print("\n✅ All connectivity tests passed!")

    except Exception as e:
        print(f"\n❌ Connectivity test failed: {e}")
        sys.exit(1)


async def validate_decorators(module_path: str) -> None:
    """Validate SAGA/TCC decorators in a Python module."""
    print(f"Validating decorators in {module_path}...")

    try:
        # Import the module
        import importlib.util

        spec = importlib.util.spec_from_file_location("user_module", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {module_path}")

        user_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_module)

        # Scan for decorated classes
        from fireflytx.decorators.saga import get_saga_metadata, is_saga_class
        from fireflytx.decorators.tcc import get_tcc_metadata, is_tcc_class

        saga_classes = []
        tcc_classes = []

        for name in dir(user_module):
            obj = getattr(user_module, name)
            if hasattr(obj, "__class__") and hasattr(obj.__class__, "__name__"):
                if is_saga_class(obj.__class__):
                    saga_classes.append((name, obj.__class__))
                elif is_tcc_class(obj.__class__):
                    tcc_classes.append((name, obj.__class__))

        # Report findings
        if saga_classes:
            print(f"\n📋 Found {len(saga_classes)} SAGA class(es):")
            for name, cls in saga_classes:
                metadata = get_saga_metadata(cls)
                print(f"  - {name}: saga_name='{metadata.saga_name}'")

                # Validate steps
                steps = metadata.get_step_methods()
                if steps:
                    print(f"    Steps: {', '.join(steps.keys())}")
                else:
                    print("    ⚠️  No steps found")

        if tcc_classes:
            print(f"\n🔄 Found {len(tcc_classes)} TCC class(es):")
            for name, cls in tcc_classes:
                metadata = get_tcc_metadata(cls)
                print(f"  - {name}: tcc_name='{metadata.tcc_name}'")

                # Validate participants
                participants = metadata.get_participants()
                if participants:
                    print(f"    Participants: {', '.join(participants.keys())}")
                else:
                    print("    ⚠️  No participants found")

        if not saga_classes and not tcc_classes:
            print("⚠️  No SAGA or TCC classes found in module")

        print("\n✅ Validation completed")

    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        sys.exit(1)


def show_engine_status() -> None:
    """Show current engine status and configuration."""
    print_firefly_banner()


    print("\n🔧 Engine Status")
    print("=" * 20)
    print(f"Version: {__version__}")
    print("JVM Status: ⭕ Managed by subprocess bridge")

    # Show configuration if available
    try:
        config = EngineConfig()
        print("\nEngine Configuration:")
        print(f"  Max Concurrent: {config.max_concurrent_executions}")
        print(f"  Default Timeout: {config.default_timeout_ms}ms")

        if hasattr(config, "persistence") and config.persistence:
            print(f"  Persistence: {config.persistence.type}")
            print(f"  Connection: {config.persistence.connection_string}")
    except Exception:
        print("No configuration loaded")


def list_examples() -> None:
    """List available example files."""
    examples_dir = Path(__file__).parent / "examples"

    print("📚 Available Examples:")
    print("=" * 25)

    if examples_dir.exists():
        for example_file in sorted(examples_dir.glob("*.py")):
            print(f"  • {example_file.name}")

            # Try to extract description from docstring
            try:
                with open(example_file) as f:
                    content = f.read()
                    if '"""' in content:
                        start = content.find('"""') + 3
                        end = content.find('"""', start)
                        if end > start:
                            docstring = content[start:end].strip()
                            first_line = docstring.split("\n")[0].strip()
                            if first_line:
                                print(f"    {first_line}")
            except Exception:
                pass
    else:
        print("  No examples directory found")


def build_jar(force_rebuild: bool = False) -> None:
    """Build the JAR from GitHub sources."""
    print("🔨 Building lib-transactional-engine JAR from GitHub...")
    print("=" * 55)

    try:
        # Check build environment
        print("Checking build environment...")
        if not check_build_environment():
            print("❌ Build environment check failed")
            sys.exit(1)

        print("✅ Build environment ready")

        # Build/get the JAR
        builder = JarBuilder()
        jar_path = builder.get_jar_path(force_rebuild=force_rebuild)

        print(f"\n✅ JAR ready at: {jar_path}")
        print(f"Size: {jar_path.stat().st_size // 1024} KB")

    except Exception as e:
        print(f"\n❌ JAR build failed: {e}")
        sys.exit(1)


def clear_jar_cache() -> None:
    """Clear the JAR build cache."""
    print("🧹 Clearing JAR build cache...")

    try:
        builder = JarBuilder()
        builder.clear_cache()
        print("✅ JAR build cache cleared")

    except Exception as e:
        print(f"❌ Failed to clear cache: {e}")
        sys.exit(1)


def show_jar_info() -> None:
    """Show JAR information."""
    print("📦 JAR Information")
    print("=" * 20)

    try:
        builder = JarBuilder()
        cached_jar = builder._get_cached_jar_path()

        print(f"Repository: {builder.repo_url}")
        print(f"Branch: {builder.branch}")
        print(f"Cache directory: {builder.build_cache_dir}")

        if cached_jar.exists():
            print(f"\nCached JAR: {cached_jar}")
            print(f"Size: {cached_jar.stat().st_size // 1024} KB")
            print(f"Modified: {cached_jar.stat().st_mtime}")
            print("Status: ✅ Available")
        else:
            print(f"\nCached JAR: {cached_jar}")
            print("Status: ❌ Not built")

        # Check build prerequisites
        print("\nBuild Prerequisites:")
        prereqs = builder.check_prerequisites()
        for name, available in prereqs.items():
            status = "✅" if available else "❌"
            print(f"  {name}: {status}")
            if name == "java_version" and available:
                print(f"    Version: {prereqs.get('java_version', 'Unknown')}")

    except Exception as e:
        print(f"❌ Failed to get JAR info: {e}")
        sys.exit(1)


def run_example(example_name: str) -> None:
    """Run a specific example."""
    examples_dir = Path(__file__).parent / "examples"
    example_path = examples_dir / f"{example_name}.py"

    if not example_path.exists():
        example_path = examples_dir / example_name
        if not example_path.exists():
            print(f"❌ Example '{example_name}' not found")
            print("Use 'fireflytx list-examples' to see available examples")
            sys.exit(1)

    print(f"🚀 Running example: {example_path.name}")
    print("-" * 40)

    # Run the example
    import subprocess

    result = subprocess.run([sys.executable, str(example_path)], capture_output=False, text=True)

    if result.returncode != 0:
        print(f"\n❌ Example failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    else:
        print("\n✅ Example completed successfully")


def visualize_topology(module_path: str, class_name: str, format_type: str = "ascii") -> None:
    """Visualize SAGA or TCC topology."""
    print(f"Visualizing topology for {class_name} in {module_path}...")

    try:
        # Import the module
        import importlib.util

        spec = importlib.util.spec_from_file_location("user_module", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {module_path}")

        user_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_module)

        # Get the class
        if not hasattr(user_module, class_name):
            raise AttributeError(f"Class '{class_name}' not found in module")

        target_class = getattr(user_module, class_name)

        # Determine if it's SAGA or TCC
        output_format = OutputFormat(format_type.lower())

        if hasattr(target_class, "_saga_config"):
            visualizer = SagaVisualizer()
            result = visualizer.visualize_saga(target_class, output_format)
            print("\n🎯 SAGA Topology:")
            print(result)

            # Also show summary
            topology = visualizer.analyze_saga_class(target_class)
            print("\n📊 SAGA Summary:")
            print(f"  Steps: {len(topology.steps)}")
            print(f"  Dependencies: {sum(len(step.dependencies) for step in topology.steps)}")
            print(
                f"  Compensations: {sum(1 for step in topology.steps if step.compensation_method)}"
            )

            # Validate topology
            issues = visualizer.validate_topology(topology)
            if issues:
                print("\n⚠️  Topology Issues:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("\n✅ Topology validation passed")

        elif hasattr(target_class, "_tcc_config"):
            visualizer = TccVisualizer()
            result = visualizer.visualize_tcc(target_class, output_format)
            print("\n🔄 TCC Topology:")
            print(result)

            # Also show summary and phase diagram
            topology = visualizer.analyze_tcc_class(target_class)
            print("\n📊 TCC Summary:")
            print(f"  Participants: {len(topology.participants)}")
            print(f"  Execution Order: {', '.join(topology.execution_order)}")

            phase_diagram = visualizer.get_phase_diagram(topology)
            print("\n📋 Phase Flow:")
            print(phase_diagram)

            # Validate topology
            issues = visualizer.validate_topology(topology)
            if issues:
                print("\n⚠️  Topology Issues:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("\n✅ Topology validation passed")

        else:
            raise ValueError(f"Class '{class_name}' is not decorated with @saga or @tcc")

    except Exception as e:
        print(f"❌ Failed to visualize topology: {e}")
        sys.exit(1)


def show_java_logs(count: int = 50, level: str = "INFO", follow: bool = False) -> None:
    """Show Java library logs."""
    bridge = get_java_log_bridge()
    viewer = LogViewer()

    if not bridge.enabled:
        print("Java log bridge is disabled. Enable it first with 'fireflytx java-logs --enable'")
        return

    try:
        min_level = JavaLogLevel(level.upper())
        filter_config = LogFilter(min_level=min_level)

        if follow:
            print("📺 Real-time Java log viewer (Press Ctrl+C to exit)")
            print(f"Minimum level: {level}")
            print("=" * 50)

            real_time_viewer = viewer.create_real_time_viewer(
                log_source=lambda: bridge.get_recent_logs(count),
                filter_config=filter_config,
                refresh_interval=1.0,
            )
            real_time_viewer.start(max_display=count)
        else:
            logs = bridge.get_recent_logs(count)
            output = viewer.display_logs(logs, filter_config, max_entries=count)
            print(output)

    except Exception as e:
        print(f"❌ Failed to show logs: {e}")
        sys.exit(1)


def configure_java_logging(enable: bool = None, level: str = None) -> None:
    """Configure Java logging bridge."""
    bridge = get_java_log_bridge()

    if enable is not None:
        if enable:
            bridge.enable()
            bridge.start_capturing()
            print("✅ Java log bridge enabled")
        else:
            bridge.disable()
            bridge.stop_capturing()
            print("❌ Java log bridge disabled")

    if level is not None:
        try:
            java_level = JavaLogLevel(level.upper())
            bridge.set_min_level(java_level)
            print(f"📊 Java log level set to {level.upper()}")
        except ValueError:
            print(f"❌ Invalid log level: {level}")
            print(f"Valid levels: {', '.join([l.value for l in JavaLogLevel])}")
            sys.exit(1)

    # Show current status
    stats = bridge.get_statistics()
    print("\n📈 Java Logging Status:")
    print(f"  Enabled: {'✅' if stats['enabled'] else '❌'}")
    print(f"  Minimum Level: {stats['min_level']}")
    print(f"  Total Entries: {stats['total_entries_captured']}")
    print(f"  Buffer Size: {stats['buffer_size']}/{stats['max_buffer_size']}")

    if stats["entries_by_level"]:
        print("  Level Distribution:")
        for level, count in stats["entries_by_level"].items():
            if count > 0:
                print(f"    {level}: {count}")


def main() -> None:
    """Main CLI entry point."""
    # Always show the banner first
    print_firefly_banner()

    parser = argparse.ArgumentParser(
        description="Firefly Python Transactional Engine - Distributed Transaction Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fireflytx status                           # Show engine status
  fireflytx test                             # Test connectivity
  fireflytx init-config config.json         # Create sample config
  fireflytx validate saga.py                # Validate decorators
  fireflytx list-examples                   # List example files
  fireflytx run-example saga-basic          # Run example
  fireflytx jar-info                         # Show JAR information
  fireflytx jar-build                       # Build JAR from GitHub
  fireflytx jar-build --force               # Force rebuild JAR
  fireflytx jar-clear-cache                 # Clear JAR cache
  fireflytx visualize saga.py MySaga        # Visualize SAGA topology
  fireflytx visualize tcc.py MyTcc --format=dot  # Generate DOT format
  fireflytx java-logs --level=DEBUG         # Show Java debug logs
  fireflytx java-logs --follow              # Follow logs in real-time
  fireflytx java-logs --enable              # Enable Java logging
        """,
    )

    parser.add_argument("--version", action="version", version=f"fireflytx {__version__}")

    parser.add_argument(
        "--copyright", action="store_true", help="Show copyright and license information"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )

    parser.add_argument(
        "--log-format", choices=["json", "text"], default="json", help="Set log output format"
    )

    parser.add_argument("--no-java-logs", action="store_true", help="Disable Java log capturing")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Shell command
    shell_parser = subparsers.add_parser("shell", help="Start interactive FireflyTX shell")
    shell_parser.add_argument(
        "--no-auto-init",
        action="store_true",
        help="Don't automatically initialize engines on startup",
    )

    # Status command
    subparsers.add_parser("status", help="Show engine status")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test engine connectivity")

    # Init config command
    init_parser = subparsers.add_parser("init-config", help="Create sample configuration file")
    init_parser.add_argument("output", help="Output configuration file path")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate SAGA/TCC decorators")
    validate_parser.add_argument("module", help="Python module to validate")

    # Examples commands
    subparsers.add_parser("list-examples", help="List available examples")

    run_example_parser = subparsers.add_parser("run-example", help="Run an example")
    run_example_parser.add_argument("example", help="Example name to run")

    # JAR management commands
    jar_info_parser = subparsers.add_parser("jar-info", help="Show JAR information")

    jar_build_parser = subparsers.add_parser("jar-build", help="Build JAR from GitHub sources", aliases=["build"])
    jar_build_parser.add_argument(
        "--force", action="store_true", help="Force rebuild even if cached"
    )

    jar_cache_parser = subparsers.add_parser("jar-clear-cache", help="Clear JAR build cache")

    # Topology visualization commands
    visualize_parser = subparsers.add_parser("visualize", help="Visualize SAGA/TCC topology")
    visualize_parser.add_argument("module", help="Python module containing the class")
    visualize_parser.add_argument("class_name", help="Name of the SAGA/TCC class")
    visualize_parser.add_argument(
        "--format",
        choices=["ascii", "dot", "mermaid", "json"],
        default="ascii",
        help="Output format",
    )

    # Java logging commands
    java_logs_parser = subparsers.add_parser("java-logs", help="Show Java library logs")
    java_logs_parser.add_argument(
        "--count", type=int, default=50, help="Number of log entries to show"
    )
    java_logs_parser.add_argument(
        "--level",
        choices=["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"],
        default="INFO",
        help="Minimum log level",
    )
    java_logs_parser.add_argument("--follow", action="store_true", help="Follow logs in real-time")
    java_logs_parser.add_argument("--enable", action="store_true", help="Enable Java log bridge")
    java_logs_parser.add_argument("--disable", action="store_true", help="Disable Java log bridge")

    # Parse arguments
    args = parser.parse_args()

    # Handle special flags
    if args.copyright:
        print_copyright_info()
        return

    # Setup logging with new options
    setup_logging(
        level=args.log_level, format_type=args.log_format, enable_java_logs=not args.no_java_logs
    )

    # Handle commands
    if args.command == "shell":
        from fireflytx.shell import FireflyTXShell
        shell = FireflyTXShell(auto_init=not args.no_auto_init)
        shell.run()

    elif args.command == "status":
        show_engine_status()

    elif args.command == "test":
        asyncio.run(test_engine_connectivity())

    elif args.command == "init-config":
        create_sample_config(args.output)

    elif args.command == "validate":
        asyncio.run(validate_decorators(args.module))

    elif args.command == "list-examples":
        list_examples()

    elif args.command == "run-example":
        run_example(args.example)

    elif args.command == "jar-info":
        show_jar_info()

    elif args.command in ("jar-build", "build"):
        build_jar(force_rebuild=args.force)

    elif args.command == "jar-clear-cache":
        clear_jar_cache()

    elif args.command == "visualize":
        visualize_topology(args.module, args.class_name, args.format)

    elif args.command == "java-logs":
        if args.enable and args.disable:
            print("❌ Cannot specify both --enable and --disable")
            sys.exit(1)

        if args.enable:
            configure_java_logging(enable=True)
        elif args.disable:
            configure_java_logging(enable=False)
        else:
            show_java_logs(args.count, args.level, args.follow)

    elif args.command is None:
        parser.print_help()
        sys.exit(1)

    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
