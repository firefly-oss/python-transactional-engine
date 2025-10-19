package com.firefly.transactional;

import java.util.Map;
import java.util.List;
import java.util.HashMap;
import java.util.ArrayList;

/**
 * Execution context for a SAGA, containing all necessary information
 * for Java orchestration of Python-defined SAGAs.
 */
public class SagaExecutionContext {
    
    private final String sagaName;
    private final String correlationId;
    private final Map<String, Object> inputData;
    private final SagaDefinition definition;
    private PythonCallbackHandler callbackHandler;
    private final Map<String, Object> contextVariables;
    
    public SagaExecutionContext(String sagaName, String correlationId, 
                               Map<String, Object> inputData, SagaDefinition definition) {
        this.sagaName = sagaName;
        this.correlationId = correlationId;
        this.inputData = new HashMap<>(inputData);
        this.definition = definition;
        this.contextVariables = new HashMap<>();
    }
    
    public String getSagaName() {
        return sagaName;
    }
    
    public String getCorrelationId() {
        return correlationId;
    }
    
    public Map<String, Object> getInputData() {
        return inputData;
    }
    
    public SagaDefinition getDefinition() {
        return definition;
    }
    
    public PythonCallbackHandler getCallbackHandler() {
        return callbackHandler;
    }
    
    public void setCallbackHandler(PythonCallbackHandler callbackHandler) {
        this.callbackHandler = callbackHandler;
    }
    
    public Map<String, Object> getContextVariables() {
        return contextVariables;
    }
    
    public void setContextVariable(String key, Object value) {
        contextVariables.put(key, value);
    }
    
    public Object getContextVariable(String key) {
        return contextVariables.get(key);
    }
    
    @Override
    public String toString() {
        return String.format("SagaExecutionContext{saga='%s', correlation='%s', hasCallback=%s}",
                sagaName, correlationId, callbackHandler != null);
    }
}
