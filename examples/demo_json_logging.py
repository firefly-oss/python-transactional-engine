#!/usr/bin/env python3
"""
Demonstration script for FireflyTX JSON logging system.

Shows how Python and Java logs are formatted with proper prefixes:
- fireflytx::bridge::log for Python components
- fireflytx::lib-transactional-engine::log for Java components

Run with: python demo_json_logging.py
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

import asyncio
import logging
import time
from fireflytx.config.engine_config import EngineConfig, LoggingConfig
from fireflytx.logging import setup_fireflytx_logging, get_fireflytx_logger, get_logging_manager


async def demo_saga_execution():
    """Simulate SAGA execution with logging."""
    saga_logger = get_fireflytx_logger("saga")
    
    saga_logger.info("Starting SAGA execution", extra={
        'saga_id': 'saga-12345',
        'correlation_id': 'corr-67890',
        'transaction_type': 'payment_processing'
    })
    
    # Simulate step execution
    for step_num in range(1, 4):
        saga_logger.info(f"Executing step {step_num}", extra={
            'saga_id': 'saga-12345',
            'step_id': f'step-{step_num}',
            'correlation_id': 'corr-67890'
        })
        
        # Simulate processing time
        await asyncio.sleep(0.2)
        
        if step_num == 2:
            # Simulate a warning
            saga_logger.warning("Step 2 encountered minor issue", extra={
                'saga_id': 'saga-12345',
                'step_id': f'step-{step_num}',
                'correlation_id': 'corr-67890',
                'retry_count': 1
            })
    
    saga_logger.info("SAGA execution completed successfully", extra={
        'saga_id': 'saga-12345',
        'correlation_id': 'corr-67890',
        'total_steps': 3,
        'execution_time_ms': 600
    })


async def demo_tcc_execution():
    """Simulate TCC execution with logging."""
    tcc_logger = get_fireflytx_logger("tcc")
    
    tcc_logger.info("Starting TCC transaction", extra={
        'transaction_id': 'tcc-54321',
        'correlation_id': 'corr-11111',
        'participants': ['service-a', 'service-b', 'service-c']
    })
    
    # Try phase
    for participant in ['service-a', 'service-b', 'service-c']:
        tcc_logger.info(f"Try phase - {participant}", extra={
            'transaction_id': 'tcc-54321',
            'participant': participant,
            'phase': 'try',
            'correlation_id': 'corr-11111'
        })
        await asyncio.sleep(0.1)
    
    # Confirm phase
    for participant in ['service-a', 'service-b', 'service-c']:
        tcc_logger.info(f"Confirm phase - {participant}", extra={
            'transaction_id': 'tcc-54321',
            'participant': participant,
            'phase': 'confirm',
            'correlation_id': 'corr-11111'
        })
        await asyncio.sleep(0.1)
    
    tcc_logger.info("TCC transaction committed", extra={
        'transaction_id': 'tcc-54321',
        'correlation_id': 'corr-11111',
        'participants_confirmed': 3
    })


def demo_java_logs():
    """Simulate Java log entries."""
    logging_manager = get_logging_manager()
    
    if logging_manager.java_bridge:
        # Start the Java log bridge to generate sample logs
        logging_manager.java_bridge.start_capturing()
        
        # Wait for some Java logs to be generated
        time.sleep(2)
        
        print("\n" + "="*60)
        print("RECENT JAVA LOG ENTRIES (last 10):")
        print("="*60)
        
        recent_logs = logging_manager.get_java_logs(count=10)
        for log_entry in recent_logs:
            print(f"Java Log Entry: {log_entry.timestamp} [{log_entry.level.value}] "
                  f"{log_entry.logger_name}: {log_entry.message}")
            if log_entry.saga_id:
                print(f"  - SAGA ID: {log_entry.saga_id}")
            if log_entry.correlation_id:
                print(f"  - Correlation ID: {log_entry.correlation_id}")
        
        logging_manager.java_bridge.stop_capturing()


def demo_different_log_levels():
    """Demonstrate different log levels with JSON formatting."""
    demo_logger = get_fireflytx_logger("demo")
    
    print("\n" + "="*60)
    print("DEMONSTRATING DIFFERENT LOG LEVELS:")
    print("="*60)
    
    # Different log levels
    demo_logger.debug("Debug message for troubleshooting", extra={
        'component': 'persistence',
        'operation': 'checkpoint'
    })
    
    demo_logger.info("System operation completed", extra={
        'component': 'engine',
        'operation': 'transaction_commit',
        'duration_ms': 150
    })
    
    demo_logger.warning("Resource usage is high", extra={
        'component': 'jvm',
        'heap_usage_percent': 85,
        'gc_count': 5
    })
    
    demo_logger.error("Transaction failed", extra={
        'component': 'saga',
        'error_code': 'TIMEOUT',
        'saga_id': 'saga-99999',
        'retry_count': 3
    })


async def main():
    """Main demonstration function."""
    print("FireflyTX JSON Logging Demonstration")
    print("=" * 50)
    print()
    
    # Setup logging with JSON format
    logging_config = LoggingConfig(
        level="INFO",
        format="json",
        enable_java_logs=True,
        java_log_level="INFO",
        include_thread_info=True,
        include_module_info=True
    )
    
    config = EngineConfig(logging=logging_config)
    setup_fireflytx_logging(config)
    
    # Get a logger to demonstrate the setup
    setup_logger = get_fireflytx_logger("setup")
    setup_logger.info("FireflyTX JSON logging system initialized", extra={
        'log_format': 'json',
        'java_logs_enabled': True,
        'demonstration': True
    })
    
    print("\n" + "="*60)
    print("PYTHON LOG ENTRIES (with fireflytx::bridge::log prefix):")
    print("="*60)
    
    # Demonstrate different components
    await demo_saga_execution()
    print()
    
    await demo_tcc_execution()
    print()
    
    demo_different_log_levels()
    
    # Demonstrate Java logging
    demo_java_logs()
    
    # Final message
    completion_logger = get_fireflytx_logger("demo")
    completion_logger.info("JSON logging demonstration completed", extra={
        'total_demos': 4,
        'formats_shown': ['saga_logs', 'tcc_logs', 'level_demos', 'java_logs']
    })
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nKey features demonstrated:")
    print("✓ JSON-formatted logs with fireflytx::bridge::log prefix")
    print("✓ Java logs with fireflytx::lib-transactional-engine::log prefix")
    print("✓ Structured logging with extra fields (saga_id, correlation_id, etc.)")
    print("✓ Different log levels (DEBUG, INFO, WARNING, ERROR)")
    print("✓ Component-specific loggers (saga, tcc, engine, etc.)")
    print("✓ Thread and module information inclusion")
    print("✓ Configurable Java log integration")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()