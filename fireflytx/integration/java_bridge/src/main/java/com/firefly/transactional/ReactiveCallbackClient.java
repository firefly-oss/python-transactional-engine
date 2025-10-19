package com.firefly.transactional;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import io.netty.handler.timeout.WriteTimeoutHandler;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import reactor.netty.http.client.HttpClient;
import reactor.netty.resources.ConnectionProvider;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Reactive HTTP client for making callbacks to Python with connection pooling.
 * 
 * This class uses Spring WebClient with Reactor Netty for non-blocking, reactive
 * HTTP callbacks to Python methods. Connection pooling is handled by Reactor Netty's
 * ConnectionProvider.
 * 
 * Connection Pool Configuration:
 * - Max connections: 500
 * - Pending acquire max count: 1000
 * - Max idle time: 30 seconds
 * - Max life time: 60 seconds
 * - Connection timeout: 5 seconds
 * - Response timeout: 30 seconds
 */
public class ReactiveCallbackClient {
    
    private final WebClient webClient;
    private final ConnectionProvider connectionProvider;
    private final ObjectMapper objectMapper;
    
    /**
     * Create reactive callback client with default connection pool settings.
     */
    public ReactiveCallbackClient() {
        this(500, 1000);
    }
    
    /**
     * Create reactive callback client with custom connection pool settings.
     * 
     * @param maxConnections Maximum connections in the pool
     * @param pendingAcquireMaxCount Maximum pending requests waiting for a connection
     */
    public ReactiveCallbackClient(int maxConnections, int pendingAcquireMaxCount) {
        // Create connection provider with pooling
        this.connectionProvider = ConnectionProvider.builder("python-callback-pool")
                .maxConnections(maxConnections)
                .pendingAcquireMaxCount(pendingAcquireMaxCount)
                .maxIdleTime(Duration.ofSeconds(30))      // Close idle connections after 30s
                .maxLifeTime(Duration.ofSeconds(60))      // Close connections after 60s
                .evictInBackground(Duration.ofSeconds(10)) // Evict idle connections every 10s
                .build();
        
        // Create HTTP client with connection pooling and timeouts
        HttpClient httpClient = HttpClient.create(connectionProvider)
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 5000)  // 5 second connect timeout
                .responseTimeout(Duration.ofSeconds(30))              // 30 second response timeout
                .doOnConnected(conn -> conn
                        .addHandlerLast(new ReadTimeoutHandler(30, TimeUnit.SECONDS))
                        .addHandlerLast(new WriteTimeoutHandler(5, TimeUnit.SECONDS)));
        
        // Create WebClient with connection pooling
        this.webClient = WebClient.builder()
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .build();
        
        this.objectMapper = new ObjectMapper();
        
        System.out.println("Reactive Callback Client initialized with connection pool: " +
                "maxConnections=" + maxConnections + ", pendingAcquireMaxCount=" + pendingAcquireMaxCount);
    }
    
    /**
     * Execute HTTP callback to Python method (blocking wrapper for reactive call).
     * 
     * @param callbackUrl The callback URL
     * @param methodType The method type (step, compensation, etc.)
     * @param methodName The Python method name
     * @param stepId The step ID
     * @param inputData Input data for the method
     * @param contextData Context data
     * @return Response from Python method
     */
    public Map<String, Object> executeCallback(
            String callbackUrl,
            String methodType,
            String methodName,
            String stepId,
            Map<String, Object> inputData,
            Map<String, Object> contextData) {
        
        return executeCallbackReactive(callbackUrl, methodType, methodName, stepId, inputData, contextData)
                .block(Duration.ofSeconds(35)); // Block with timeout slightly longer than response timeout
    }
    
    /**
     * Execute HTTP callback to Python method (reactive).
     * 
     * @param callbackUrl The callback URL
     * @param methodType The method type (step, compensation, etc.)
     * @param methodName The Python method name
     * @param stepId The step ID
     * @param inputData Input data for the method
     * @param contextData Context data
     * @return Mono of response from Python method
     */
    public Mono<Map<String, Object>> executeCallbackReactive(
            String callbackUrl,
            String methodType,
            String methodName,
            String stepId,
            Map<String, Object> inputData,
            Map<String, Object> contextData) {
        
        // Prepare callback request
        Map<String, Object> callbackRequest = new HashMap<>();
        callbackRequest.put("method_type", methodType);
        callbackRequest.put("method_name", methodName);
        callbackRequest.put("step_id", stepId);
        callbackRequest.put("input_data", inputData);
        callbackRequest.put("context_data", contextData);
        
        // Make reactive HTTP POST request
        return webClient.post()
                .uri(callbackUrl)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(callbackRequest)
                .retrieve()
                .bodyToMono(Map.class)
                .map(map -> (Map<String, Object>) map)
                .onErrorResume(error -> {
                    // Handle errors gracefully
                    Map<String, Object> errorResult = new HashMap<>();
                    errorResult.put("success", false);
                    errorResult.put("error", error.getMessage());
                    return Mono.just(errorResult);
                });
    }
    
    /**
     * Execute TCC callback to Python method (blocking wrapper for reactive call).
     * 
     * @param callbackUrl The callback URL
     * @param phase The TCC phase (TRY, CONFIRM, CANCEL)
     * @param participantId The participant ID
     * @param methodName The Python method name
     * @param inputData Input data for the method
     * @param contextData Context data
     * @return Response from Python method
     */
    public Map<String, Object> executeTccCallback(
            String callbackUrl,
            String phase,
            String participantId,
            String methodName,
            Map<String, Object> inputData,
            Map<String, Object> contextData) {
        
        return executeTccCallbackReactive(callbackUrl, phase, participantId, methodName, inputData, contextData)
                .block(Duration.ofSeconds(35)); // Block with timeout slightly longer than response timeout
    }
    
    /**
     * Execute TCC callback to Python method (reactive).
     * 
     * @param callbackUrl The callback URL
     * @param phase The TCC phase (TRY, CONFIRM, CANCEL)
     * @param participantId The participant ID
     * @param methodName The Python method name
     * @param inputData Input data for the method
     * @param contextData Context data
     * @return Mono of response from Python method
     */
    public Mono<Map<String, Object>> executeTccCallbackReactive(
            String callbackUrl,
            String phase,
            String participantId,
            String methodName,
            Map<String, Object> inputData,
            Map<String, Object> contextData) {
        
        // Prepare callback request
        Map<String, Object> callbackRequest = new HashMap<>();
        callbackRequest.put("phase", phase);
        callbackRequest.put("participant_id", participantId);
        callbackRequest.put("method_name", methodName);
        callbackRequest.put("input_data", inputData);
        callbackRequest.put("context_data", contextData);
        
        // Make reactive HTTP POST request
        return webClient.post()
                .uri(callbackUrl)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(callbackRequest)
                .retrieve()
                .bodyToMono(Map.class)
                .map(map -> (Map<String, Object>) map)
                .onErrorResume(error -> {
                    // Handle errors gracefully
                    Map<String, Object> errorResult = new HashMap<>();
                    errorResult.put("success", false);
                    errorResult.put("error", error.getMessage());
                    return Mono.just(errorResult);
                });
    }
    
    /**
     * Get connection pool statistics.
     * 
     * @return Map containing pool statistics
     */
    public Map<String, Object> getPoolStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("provider", connectionProvider.toString());
        return stats;
    }
    
    /**
     * Dispose the connection provider and release all connections.
     */
    public void dispose() {
        if (connectionProvider != null) {
            connectionProvider.dispose();
            System.out.println("Reactive Callback Client disposed");
        }
    }
}

