#!/usr/bin/env python3
"""
FireflyTX - Python Wrapper for lib-transactional-engine

Enterprise-grade Python wrapper for the real lib-transactional-engine Java library,
enabling genuine SAGA and TCC distributed transaction patterns in Python applications.

Key Features:
- Real lib-transactional-engine integration via subprocess bridge
- SAGA pattern support with automatic compensation
- TCC (Try-Confirm-Cancel) pattern support for strong consistency
- Reactive programming with full asyncio integration
- Enterprise-grade reliability and observability
- Type-safe APIs with comprehensive Pydantic model validation
- No mocks or simulations - genuine transaction processing

Usage:
    from fireflytx import SagaEngine, TccEngine
    from fireflytx.decorators import saga, saga_step

    @saga("payment-processing")
    class PaymentSaga:

        @saga_step("validate")
        async def validate_payment(self, order_id: str) -> PaymentResult:
            # Implementation
            pass

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

__version__ = "1.0.0"
__author__ = "Firefly Software Solutions Inc"
__license__ = "Apache 2.0"

# Auto-install dependencies if needed
from .utils.dependency_installer import install_dependencies_if_needed

install_dependencies_if_needed()

# Core engine imports
from .internal.engine import SagaEngine, TccEngine

# Configuration generation
from .config import generate_saga_engine_config

# Configuration
from .config.engine_config import (
    EngineConfig,
    PersistenceConfig,
    JvmConfig,
    RetryConfig,
    LoggingConfig,
    ConfigurationManager,
)
from .config.event_config import EventConfig

# Core types
from .core.saga_context import SagaContext
from .core.saga_result import SagaResult
from .core.step_inputs import StepInputs
from .core.tcc_context import TccContext
from .core.tcc_inputs import TccInputs
from .core.tcc_result import TccResult

# Decorators
from .decorators.saga import compensation_step, saga, saga_step, step_events
from .decorators.tcc import cancel_method, confirm_method, tcc, tcc_participant, try_method

# Events and observability - using implementations from events module
from .events import (
    EventType,
    KafkaStepEventPublisher,
    NoOpStepEventPublisher,
    StepEvent,
    StepEventPublisher,
)

# Persistence - using implementations from persistence module
from .persistence import (
    DatabaseSagaPersistenceProvider,
    NoOpSagaPersistenceProvider,
    RedisSagaPersistenceProvider,
    SagaPersistenceProvider,
)

# Integration layer (Java bridge, callbacks, type conversion)
from .integration import JavaSubprocessBridge, TypeConverter

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Core engines
    "SagaEngine",
    "TccEngine",
    # Core types
    "SagaContext",
    "SagaResult",
    "TccContext",
    "TccResult",
    "StepInputs",
    "TccInputs",
    # Decorators
    "saga",
    "saga_step",
    "compensation_step",
    "step_events",
    "tcc",
    "tcc_participant",
    "try_method",
    "confirm_method",
    "cancel_method",
    # Configuration
    "EngineConfig",
    "PersistenceConfig",
    "JvmConfig",
    "RetryConfig",
    "LoggingConfig",
    "ConfigurationManager",
    "EventConfig",
    # Events
    "EventType",
    "StepEvent",
    "StepEventPublisher",
    "NoOpStepEventPublisher",
    "KafkaStepEventPublisher",
    # Persistence
    "SagaPersistenceProvider",
    "NoOpSagaPersistenceProvider",
    "RedisSagaPersistenceProvider",
    "DatabaseSagaPersistenceProvider",
    # Configuration
    "generate_saga_engine_config",
    # Utilities
    "TypeConverter",
    "JavaSubprocessBridge",
]
