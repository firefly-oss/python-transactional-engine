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

import com.firefly.transactional.saga.events.StepEventPublisher;
import com.firefly.transactional.tcc.events.TccEventPublisher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

import java.util.HashMap;
import java.util.Map;

/**
 * Spring configuration for event publishers.
 * 
 * This configuration creates Kafka event publishers when the event provider is set to "kafka"
 * in the Python configuration (passed via system properties).
 * 
 * Configuration is read from system properties set by Python:
 * - firefly.tx.events.provider=kafka
 * - firefly.tx.events.kafka.bootstrap-servers=localhost:9092
 * - firefly.tx.events.saga-topic=fireflytx.saga.events
 * - firefly.tx.events.tcc-topic=fireflytx.tcc.events
 */
@Configuration
public class EventPublisherConfiguration {
    
    private static final Logger log = LoggerFactory.getLogger(EventPublisherConfiguration.class);
    
    /**
     * Create a Kafka step event publisher when Kafka is configured.
     */
    @Bean
    @ConditionalOnProperty(name = "firefly.tx.events.provider", havingValue = "kafka")
    public StepEventPublisher kafkaStepEventPublisher(Environment env) {
        String bootstrapServers = env.getProperty("firefly.tx.events.kafka.bootstrap-servers", "localhost:9092");
        String topic = env.getProperty("firefly.tx.events.saga-topic", "fireflytx.saga.events");
        
        log.info("Creating KafkaStepEventPublisher with bootstrapServers={}, topic={}", bootstrapServers, topic);
        
        // Build additional Kafka config from environment
        Map<String, Object> additionalConfig = new HashMap<>();
        
        // Check for additional Kafka properties
        String acks = env.getProperty("firefly.tx.events.kafka.acks");
        if (acks != null) {
            additionalConfig.put("acks", acks);
        }
        
        String retries = env.getProperty("firefly.tx.events.kafka.retries");
        if (retries != null) {
            additionalConfig.put("retries", Integer.parseInt(retries));
        }
        
        String compressionType = env.getProperty("firefly.tx.events.kafka.compression-type");
        if (compressionType != null) {
            additionalConfig.put("compression.type", compressionType);
        }
        
        String batchSize = env.getProperty("firefly.tx.events.kafka.batch-size");
        if (batchSize != null) {
            additionalConfig.put("batch.size", Integer.parseInt(batchSize));
        }
        
        String lingerMs = env.getProperty("firefly.tx.events.kafka.linger-ms");
        if (lingerMs != null) {
            additionalConfig.put("linger.ms", Integer.parseInt(lingerMs));
        }
        
        return new KafkaStepEventPublisher(bootstrapServers, topic, additionalConfig);
    }
    
    /**
     * Create a Kafka TCC event publisher when Kafka is configured.
     */
    @Bean
    @ConditionalOnProperty(name = "firefly.tx.events.provider", havingValue = "kafka")
    public TccEventPublisher kafkaTccEventPublisher(Environment env) {
        String bootstrapServers = env.getProperty("firefly.tx.events.kafka.bootstrap-servers", "localhost:9092");
        String topic = env.getProperty("firefly.tx.events.tcc-topic", "fireflytx.tcc.events");
        
        log.info("Creating KafkaTccEventPublisher with bootstrapServers={}, topic={}", bootstrapServers, topic);
        
        // Build additional Kafka config from environment
        Map<String, Object> additionalConfig = new HashMap<>();
        
        // Check for additional Kafka properties
        String acks = env.getProperty("firefly.tx.events.kafka.acks");
        if (acks != null) {
            additionalConfig.put("acks", acks);
        }
        
        String retries = env.getProperty("firefly.tx.events.kafka.retries");
        if (retries != null) {
            additionalConfig.put("retries", Integer.parseInt(retries));
        }
        
        String compressionType = env.getProperty("firefly.tx.events.kafka.compression-type");
        if (compressionType != null) {
            additionalConfig.put("compression.type", compressionType);
        }
        
        String batchSize = env.getProperty("firefly.tx.events.kafka.batch-size");
        if (batchSize != null) {
            additionalConfig.put("batch.size", Integer.parseInt(batchSize));
        }
        
        String lingerMs = env.getProperty("firefly.tx.events.kafka.linger-ms");
        if (lingerMs != null) {
            additionalConfig.put("linger.ms", Integer.parseInt(lingerMs));
        }
        
        return new KafkaTccEventPublisher(bootstrapServers, topic, additionalConfig);
    }
}

