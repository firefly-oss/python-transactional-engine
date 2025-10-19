"""
Event configuration for the transactional engine.
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

from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


class EventConfig(BaseModel):
    """
    Configuration for event publishing.

    Events are published by the Java lib-transactional-engine, not Python.
    This configuration is passed to Java via system properties.

    Attributes:
        enabled: Whether event publishing is enabled
        provider: Event provider type (memory, kafka, redis, mqtt)
        connection_string: Connection string for the event provider
        kafka_config: Kafka-specific configuration (bootstrap servers, topics, etc.)
        topic_prefix: Prefix for event topics (default: "fireflytx")
        saga_topic: Topic for SAGA step events (default: "fireflytx.saga.events")
        tcc_topic: Topic for TCC events (default: "fireflytx.tcc.events")
    """

    enabled: bool = True
    provider: str = "memory"  # memory, kafka, redis, mqtt
    connection_string: Optional[str] = None

    # Kafka-specific configuration
    kafka_config: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Topic configuration
    topic_prefix: str = "fireflytx"
    saga_topic: str = "fireflytx.saga.events"
    tcc_topic: str = "fireflytx.tcc.events"

    model_config = ConfigDict(arbitrary_types_allowed=True)
