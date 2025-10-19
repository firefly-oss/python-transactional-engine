package com.firefly.transactional;

import java.util.Map;
import java.util.List;
import java.util.HashMap;
import java.util.ArrayList;

/**
 * Result of SAGA execution, containing success status, step results,
 * and information about failures and compensations.
 */
public class SagaExecutionResult {
    
    private final String sagaName;
    private final String correlationId;
    private boolean success;
    private Map<String, Object> steps;
    private List<String> failedSteps;
    private List<String> compensatedSteps;
    private String error;
    private final long startTime;
    private long endTime;
    
    public SagaExecutionResult(String sagaName, String correlationId, boolean success,
                              Map<String, Object> steps, List<String> failedSteps,
                              List<String> compensatedSteps, String error) {
        this.sagaName = sagaName;
        this.correlationId = correlationId;
        this.success = success;
        this.steps = new HashMap<>(steps);
        this.failedSteps = new ArrayList<>(failedSteps);
        this.compensatedSteps = new ArrayList<>(compensatedSteps);
        this.error = error;
        this.startTime = System.currentTimeMillis();
        this.endTime = this.startTime;
    }
    
    public String getSagaName() {
        return sagaName;
    }
    
    public String getCorrelationId() {
        return correlationId;
    }
    
    public boolean isSuccess() {
        return success;
    }
    
    public void setSuccess(boolean success) {
        this.success = success;
        this.endTime = System.currentTimeMillis();
    }
    
    public Map<String, Object> getSteps() {
        return steps;
    }
    
    public void setSteps(Map<String, Object> steps) {
        this.steps = new HashMap<>(steps);
    }
    
    public List<String> getFailedSteps() {
        return failedSteps;
    }
    
    public void setFailedSteps(List<String> failedSteps) {
        this.failedSteps = new ArrayList<>(failedSteps);
    }
    
    public List<String> getCompensatedSteps() {
        return compensatedSteps;
    }
    
    public void setCompensatedSteps(List<String> compensatedSteps) {
        this.compensatedSteps = new ArrayList<>(compensatedSteps);
    }
    
    public String getError() {
        return error;
    }
    
    public void setError(String error) {
        this.error = error;
        this.endTime = System.currentTimeMillis();
    }
    
    public long getDurationMs() {
        return endTime - startTime;
    }
    
    /**
     * Convert the result to a Map for JSON serialization back to Python.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> result = new HashMap<>();
        result.put("saga_name", sagaName);
        result.put("correlation_id", correlationId);
        result.put("is_success", success);
        result.put("duration_ms", getDurationMs());
        result.put("steps", new HashMap<>(steps));
        result.put("failed_steps", new ArrayList<>(failedSteps));
        result.put("compensated_steps", new ArrayList<>(compensatedSteps));
        result.put("error", error);
        result.put("engine_used", true);
        result.put("lib_transactional_version", "1.0.0-SNAPSHOT");
        
        return result;
    }
    
    @Override
    public String toString() {
        return String.format("SagaExecutionResult{saga='%s', success=%s, steps=%d, failed=%d, compensated=%d, duration=%dms}",
                sagaName, success, steps.size(), failedSteps.size(), compensatedSteps.size(), getDurationMs());
    }
}