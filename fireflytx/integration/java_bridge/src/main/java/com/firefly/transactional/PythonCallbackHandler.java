package com.firefly.transactional;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Handles callbacks from Java to Python for SAGA step and compensation execution using HTTP.
 *
 * This implementation uses the callback URL provided by Python to POST JSON payloads
 * for step and compensation method execution. It removes previous simulated behavior.
 */
public class PythonCallbackHandler {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    private final Map<String, Object> callbackInfo;
    private final JavaSubprocessBridge bridge;
    private final String callbackUrl;

    public PythonCallbackHandler(Map<String, Object> callbackInfo, JavaSubprocessBridge bridge) {
        this.callbackInfo = callbackInfo;
        this.bridge = bridge;
        // Prefer keys used by Python side
        String url = (String) callbackInfo.get("callback_url");
        if (url == null) {
            url = (String) callbackInfo.get("callback_endpoint");
        }
        if (url == null) {
            url = (String) callbackInfo.get("endpoint");
        }
        if (url == null) {
            throw new IllegalArgumentException("Missing callback URL in callbackInfo");
        }
        this.callbackUrl = url;
    }

    public String getCallbackUrl() {
        return this.callbackUrl;
    }

    /**
     * Direct invocation methods are not used by the current orchestration flow.
     * JavaSubprocessBridge performs the HTTP callback with method metadata.
     * These methods are kept for compatibility but will raise if called directly.
     */
    public Map<String, Object> executeStep(String stepId, Map<String, Object> inputData, Map<String, Object> contextData) {
        throw new IllegalStateException("Direct executeStep is not supported; use bridge HTTP callback.");
    }

    public Map<String, Object> executeCompensation(String stepId, Object stepResult, Map<String, Object> contextData) {
        throw new IllegalStateException("Direct executeCompensation is not supported; use bridge HTTP callback.");
    }

    /**
     * Execute a callback to Python for a specific method.
     * Used by lib-transactional-engine integration.
     */
    public Map<String, Object> executeCallback(String methodName, Map<String, Object> inputData, Map<String, Object> contextData) {
        try {
            return postJson("STEP", methodName, (String) contextData.get("step_id"), inputData, contextData);
        } catch (Exception e) {
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", e.getMessage());
            return error;
        }
    }

    // Optional helper if needed in the future
    private Map<String, Object> postJson(String methodType, String methodName, String stepId,
                                         Map<String, Object> inputData, Map<String, Object> contextData) throws Exception {
        Map<String, Object> payload = new HashMap<>();
        payload.put("method_type", methodType);
        payload.put("method_name", methodName);
        payload.put("step_id", stepId);
        payload.put("input_data", inputData);
        payload.put("context_data", contextData);

        String json = objectMapper.writeValueAsString(payload);

        URL url = new URL(this.callbackUrl);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setDoOutput(true);

        try (OutputStream os = conn.getOutputStream()) {
            os.write(json.getBytes(StandardCharsets.UTF_8));
        }

        int code = conn.getResponseCode();
        if (code == 200) {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) sb.append(line);
                @SuppressWarnings("unchecked")
                Map<String, Object> result = objectMapper.readValue(sb.toString(), Map.class);
                return result;
            }
        } else {
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", "HTTP " + code);
            return error;
        }
    }

    public String getCallbackType() {
        return (String) callbackInfo.get("callback_type");
    }

    public String getHandlerId() {
        return String.valueOf(callbackInfo.get("handler_id"));
    }

    public String getClassName() {
        return (String) callbackInfo.get("class_name");
    }
}