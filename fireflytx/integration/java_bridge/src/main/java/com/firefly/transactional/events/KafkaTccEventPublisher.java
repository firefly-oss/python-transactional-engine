/*
 * Copyright 2025 Firefly Software Solutions Inc
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.firefly.transactional.events;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.firefly.transactional.tcc.events.TccEventEnvelope;
import com.firefly.transactional.tcc.events.TccEventPublisher;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import reactor.core.publisher.Mono;
import reactor.kafka.sender.KafkaSender;
import reactor.kafka.sender.SenderOptions;
import reactor.kafka.sender.SenderRecord;

import java.util.HashMap;
import java.util.Map;

/**
 * Kafka implementation of TccEventPublisher.
 * 
 * Publishes TCC transaction events to Kafka using reactive Kafka sender.
 * Events are serialized to JSON and published with appropriate headers.
 */
public class KafkaTccEventPublisher implements TccEventPublisher {
    
    private static final Logger log = LoggerFactory.getLogger(KafkaTccEventPublisher.class);
    
    private final KafkaSender<String, String> kafkaSender;
    private final String topic;
    private final ObjectMapper objectMapper;
    
    public KafkaTccEventPublisher(String bootstrapServers, String topic, Map<String, Object> additionalConfig) {
        this.topic = topic;
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());
        
        // Build Kafka producer configuration
        Map<String, Object> producerProps = new HashMap<>();
        producerProps.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        producerProps.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        producerProps.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        producerProps.put(ProducerConfig.ACKS_CONFIG, "all");
        producerProps.put(ProducerConfig.RETRIES_CONFIG, 3);
        producerProps.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 1);
        producerProps.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        
        // Add any additional configuration
        if (additionalConfig != null) {
            producerProps.putAll(additionalConfig);
        }
        
        SenderOptions<String, String> senderOptions = SenderOptions.create(producerProps);
        this.kafkaSender = KafkaSender.create(senderOptions);
        
        log.info("Initialized KafkaTccEventPublisher for topic: {}", topic);
    }
    
    @Override
    public Mono<Void> publish(TccEventEnvelope event) {
        return Mono.fromCallable(() -> {
            try {
                // Serialize event to JSON
                String eventJson = objectMapper.writeValueAsString(event);

                // Use correlation ID as the key for partitioning
                String key = event.getCorrelationId();

                // Create Kafka record
                ProducerRecord<String, String> record = new ProducerRecord<>(topic, key, eventJson);

                // Add headers
                record.headers().add("event-type", "tcc-transaction".getBytes());
                record.headers().add("correlation-id", event.getCorrelationId().getBytes());
                if (event.getType() != null) {
                    record.headers().add("event-name", event.getType().getBytes());
                }
                
                return SenderRecord.create(record, null);
                
            } catch (Exception e) {
                throw new RuntimeException("Failed to serialize TCC event", e);
            }
        })
        .flatMap(senderRecord -> kafkaSender.send(Mono.just(senderRecord)).next())
        .doOnSuccess(result -> {
            if (log.isDebugEnabled()) {
                log.debug("Published TCC event to Kafka: correlationId={}, type={}",
                    event.getCorrelationId(), event.getType());
            }
        })
        .doOnError(error -> {
            log.error("Failed to publish TCC event to Kafka: correlationId={}, type={}",
                event.getCorrelationId(), event.getType(), error);
        })
        .then();
    }
    
    public void close() {
        kafkaSender.close();
    }
}

