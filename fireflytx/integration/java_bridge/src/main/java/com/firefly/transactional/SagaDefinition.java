package com.firefly.transactional;

import java.util.Map;

/**
 * Represents a SAGA definition with steps, compensations, and metadata.
 * This is used to store Python SAGA definitions for Java orchestration.
 */
public class SagaDefinition {
    
    private final String sagaName;
    private final String className;
    private final String module;
    private final Map<String, Object> steps;
    private final Map<String, Object> compensations;
    
    public SagaDefinition(String sagaName, String className, String module, 
                         Map<String, Object> steps, Map<String, Object> compensations) {
        this.sagaName = sagaName;
        this.className = className;
        this.module = module;
        this.steps = steps;
        this.compensations = compensations;
    }
    
    public String getSagaName() {
        return sagaName;
    }
    
    public String getClassName() {
        return className;
    }
    
    public String getModule() {
        return module;
    }
    
    public Map<String, Object> getSteps() {
        return steps;
    }
    
    public Map<String, Object> getCompensations() {
        return compensations;
    }
    
    @Override
    public String toString() {
        return String.format("SagaDefinition{name='%s', class='%s', steps=%d, compensations=%d}",
                sagaName, className, steps.size(), compensations.size());
    }
}

/**
 * Registry for storing SAGA definitions.
 */
class SagaDefinitionRegistry {
    
    private static final Map<String, SagaDefinition> definitions = new java.util.concurrent.ConcurrentHashMap<>();
    
    public static void register(String sagaName, SagaDefinition definition) {
        definitions.put(sagaName, definition);
    }
    
    public static SagaDefinition get(String sagaName) {
        return definitions.get(sagaName);
    }
    
    public static boolean exists(String sagaName) {
        return definitions.containsKey(sagaName);
    }
    
    public static void remove(String sagaName) {
        definitions.remove(sagaName);
    }
    
    public static void clear() {
        definitions.clear();
    }
}

/**
 * Represents a SAGA registration for simpler cases.
 */
class SagaRegistration {
    
    private final String sagaName;
    private final Map<String, Object> registrationData;
    
    public SagaRegistration(String sagaName, Map<String, Object> registrationData) {
        this.sagaName = sagaName;
        this.registrationData = registrationData;
    }
    
    public String getSagaName() {
        return sagaName;
    }
    
    public Map<String, Object> getRegistrationData() {
        return registrationData;
    }
}

/**
 * Registry for SAGA registrations.
 */
class SagaRegistrationRegistry {
    
    private static final Map<String, SagaRegistration> registrations = new java.util.concurrent.ConcurrentHashMap<>();
    
    public static void register(String sagaName, SagaRegistration registration) {
        registrations.put(sagaName, registration);
    }
    
    public static SagaRegistration get(String sagaName) {
        return registrations.get(sagaName);
    }
    
    public static boolean exists(String sagaName) {
        return registrations.containsKey(sagaName);
    }
    
    public static void remove(String sagaName) {
        registrations.remove(sagaName);
    }
    
    public static void clear() {
        registrations.clear();
    }
}