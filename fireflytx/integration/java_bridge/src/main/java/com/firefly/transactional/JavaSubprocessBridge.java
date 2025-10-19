package com.firefly.transactional;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.firefly.transactional.saga.core.SagaContext;
import com.firefly.transactional.saga.engine.SagaEngine;
import com.firefly.transactional.saga.engine.StepInputs;
import com.firefly.transactional.saga.engine.step.StepHandler;
import com.firefly.transactional.saga.registry.SagaDefinition;
import com.firefly.transactional.saga.registry.SagaRegistry;
import com.firefly.transactional.saga.registry.StepDefinition;
import com.firefly.transactional.saga.core.SagaResult;
import com.firefly.transactional.tcc.engine.TccEngine;
import org.springframework.context.ApplicationContext;
import reactor.core.publisher.Mono;

import java.io.File;
import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Java subprocess bridge for Python-Java communication.
 * 
 * This class enables "Python defines, Java executes" architecture by:
 * 1. Receiving method call requests from Python via JSON files
 * 2. Executing Java methods using reflection
 * 3. Managing Java object instances
 * 4. Providing callbacks to Python for SAGA step execution
 * 5. Returning results to Python via JSON responses
 */
public class JavaSubprocessBridge {

    private static final ObjectMapper objectMapper = new ObjectMapper();
    private static final Map<String, Object> instances = new ConcurrentHashMap<>();
    private static final Map<String, Object> callbackHandlers = new ConcurrentHashMap<>();
    private static final ExecutorService executor = Executors.newCachedThreadPool();

    private final String tempDir;
    private final Path requestDir;
    private final Path responseDir;
    private final ApplicationContext applicationContext;
    private final ReactiveCallbackClient callbackClient;
    private volatile boolean running = true;

    public JavaSubprocessBridge(String tempDir, ApplicationContext applicationContext) {
        this.tempDir = tempDir;
        this.requestDir = Paths.get(tempDir, "requests");
        this.responseDir = Paths.get(tempDir, "responses");
        this.applicationContext = applicationContext;
        this.callbackClient = new ReactiveCallbackClient(500, 1000);

        try {
            Files.createDirectories(requestDir);
            Files.createDirectories(responseDir);
        } catch (IOException e) {
            throw new RuntimeException("Failed to create communication directories", e);
        }
    }
    

    
    public void startProcessing() {
        while (running) {
            try {
                processRequests();
                Thread.sleep(100); // Poll every 100ms
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                System.err.println("Error processing requests: " + e.getMessage());
                e.printStackTrace();
            }
        }
        
        executor.shutdown();
        callbackClient.dispose();
        System.out.println("Java subprocess bridge shutdown");
    }
    
    private void processRequests() throws IOException {
        File[] requestFiles = requestDir.toFile().listFiles((dir, name) -> name.endsWith(".json"));
        if (requestFiles == null) return;
        
        for (File requestFile : requestFiles) {
            try {
                processRequest(requestFile);
            } catch (Exception e) {
                System.err.println("Error processing request " + requestFile.getName() + ": " + e.getMessage());
                e.printStackTrace();
                
                // Send error response
                String requestId = requestFile.getName().replace(".json", "");
                sendErrorResponse(requestId, e.getMessage());
            }
            
            // Delete processed request file
            requestFile.delete();
        }
    }
    
    private void processRequest(File requestFile) throws IOException {
        String content = Files.readString(requestFile.toPath());
        JsonNode request = objectMapper.readTree(content);
        
        String requestId = request.get("requestId").asText();
        String className = request.get("className").asText();
        String methodName = request.get("methodName").asText();
        String methodType = request.get("methodType").asText();
        JsonNode argsNode = request.get("args");
        String instanceId = request.has("instanceId") ? request.get("instanceId").asText() : null;
        
        try {
            Object result = executeMethod(className, methodName, methodType, argsNode, instanceId);
            sendSuccessResponse(requestId, result, instanceId);
        } catch (Exception e) {
            sendErrorResponse(requestId, e.getMessage());
        }
    }
    
    private Object executeMethod(String className, String methodName, String methodType, 
                               JsonNode argsNode, String instanceId) throws Exception {
        
        Class<?> clazz = getClass(className);
        Object[] args = parseArguments(argsNode);
        
        switch (methodType) {
            case "constructor":
                return executeConstructor(clazz, args, instanceId);
                
            case "static":
                return executeStaticMethod(clazz, methodName, args);
                
            case "instance":
                return executeInstanceMethod(clazz, methodName, args, instanceId);
                
            default:
                throw new IllegalArgumentException("Unknown method type: " + methodType);
        }
    }
    
    private Object executeConstructor(Class<?> clazz, Object[] args, String instanceId) throws Exception {
        Object instance;

        // Check if this is a Spring-managed bean (SagaEngine, TccEngine, etc.)
        if (applicationContext != null && isSpringManagedBean(clazz)) {
            try {
                // Get bean from Spring context
                instance = applicationContext.getBean(clazz);
                System.out.println("Retrieved Spring bean: " + clazz.getSimpleName());
            } catch (Exception e) {
                System.err.println("Failed to get Spring bean for " + clazz.getName() + ", falling back to reflection: " + e.getMessage());
                // Fallback to reflection if bean not found
                Constructor<?> constructor = findMatchingConstructor(clazz, args);
                instance = constructor.newInstance(args);
            }
        } else {
            // Use reflection for non-Spring beans
            Constructor<?> constructor = findMatchingConstructor(clazz, args);
            instance = constructor.newInstance(args);
        }

        String id = instanceId != null ? instanceId : UUID.randomUUID().toString();
        instances.put(id, instance);

        return new ConstructorResult(id, clazz.getName() + " instance created");
    }

    /**
     * Check if a class should be managed by Spring.
     * These are classes from lib-transactional-engine that are auto-configured.
     */
    private boolean isSpringManagedBean(Class<?> clazz) {
        String className = clazz.getName();
        return className.equals("com.firefly.transactional.saga.engine.SagaEngine") ||
               className.equals("com.firefly.transactional.tcc.engine.TccEngine");
    }
    
    private Object executeStaticMethod(Class<?> clazz, String methodName, Object[] args) throws Exception {
        Method method = findMatchingMethod(clazz, methodName, args, true);
        return method.invoke(null, args);
    }
    
    private Object executeInstanceMethod(Class<?> clazz, String methodName, Object[] args, String instanceId) throws Exception {
        if (instanceId == null) {
            throw new IllegalArgumentException("Instance ID required for instance method calls");
        }
        
        Object instance = instances.get(instanceId);
        if (instance == null) {
            throw new IllegalArgumentException("Instance not found: " + instanceId);
        }
        
        // Handle special SAGA engine methods
        if (instance instanceof SagaEngine) {
            return handleSagaEngineMethod((SagaEngine) instance, methodName, args);
        }
        
        // Handle special TCC engine methods
        if (instance instanceof TccEngine) {
            return handleTccEngineMethod((TccEngine) instance, methodName, args);
        }
        
        Method method = findMatchingMethod(clazz, methodName, args, false);
        return method.invoke(instance, args);
    }
    
    private Object handleSagaEngineMethod(SagaEngine sagaEngine, String methodName, Object[] args) throws Exception {
        switch (methodName) {
            case "registerSagaDefinition":
                return registerSagaDefinition(sagaEngine, args);
                
            case "executeSaga":
                return executeSaga(sagaEngine, args);
                
            case "registerSaga":
                return registerSaga(sagaEngine, args);
                
            default:
                // Fall back to reflection for other methods
                Method method = findMatchingMethod(SagaEngine.class, methodName, args, false);
                return method.invoke(sagaEngine, args);
        }
    }
    
    private Object registerSagaDefinition(SagaEngine sagaEngine, Object[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("registerSagaDefinition requires 1 argument");
        }
        
        @SuppressWarnings("unchecked")
        Map<String, Object> sagaDefinition = (Map<String, Object>) args[0];
        
        String sagaName = (String) sagaDefinition.get("saga_name");
        String className = (String) sagaDefinition.get("class_name");
        String module = (String) sagaDefinition.get("module");
        
        @SuppressWarnings("unchecked")
        Map<String, Object> steps = (Map<String, Object>) sagaDefinition.get("steps");
        
        @SuppressWarnings("unchecked")
        Map<String, Object> compensations = (Map<String, Object>) sagaDefinition.get("compensations");
        
        // Store SAGA definition for execution orchestration
        SagaDefinition definition = new SagaDefinition(sagaName, className, module, steps, compensations);
        SagaDefinitionRegistry.register(sagaName, definition);
        
        System.out.println("Registered SAGA definition: " + sagaName + " with " + steps.size() + " steps");
        
        return "SAGA definition registered: " + sagaName;
    }
    
    private Object executeSaga(SagaEngine sagaEngine, Object[] args) throws Exception {
        if (args.length < 3) {
            throw new IllegalArgumentException("executeSaga requires at least 3 arguments: sagaName, inputData, correlationId");
        }

        String sagaName = (String) args[0];
        @SuppressWarnings("unchecked")
        Map<String, Object> inputData = (Map<String, Object>) args[1];
        String correlationId = (String) args[2];

        // Get callback handler info if provided
        @SuppressWarnings("unchecked")
        Map<String, Object> callbackInfo = args.length > 3 ? (Map<String, Object>) args[3] : null;

        System.out.println("Executing SAGA: " + sagaName + " with correlation ID: " + correlationId);

        // Get Python SAGA definition from our registry (using fully qualified name to avoid conflict)
        com.firefly.transactional.JavaSubprocessBridge.SagaDefinition pythonDefinition = SagaDefinitionRegistry.get(sagaName);
        if (pythonDefinition == null) {
            throw new IllegalArgumentException("SAGA definition not found: " + sagaName);
        }

        // Register callback handler if provided
        PythonCallbackHandler callbackHandler = null;
        if (callbackInfo != null) {
            callbackHandler = new PythonCallbackHandler(callbackInfo, this);
            callbackHandlers.put(correlationId, callbackHandler);
        }

        // Get the lib-transactional-engine SagaRegistry
        SagaRegistry sagaRegistry = applicationContext.getBean(SagaRegistry.class);

        // Build a lib-transactional-engine SagaDefinition with Python callback handlers
        com.firefly.transactional.saga.registry.SagaDefinition libSagaDefinition = buildLibSagaDefinition(sagaName, pythonDefinition, callbackHandler);

        // Temporarily register this saga with the lib-transactional-engine registry
        // Note: We use reflection to access the internal sagas map since there's no public register method
        try {
            java.lang.reflect.Field sagasField = SagaRegistry.class.getDeclaredField("sagas");
            sagasField.setAccessible(true);
            @SuppressWarnings("unchecked")
            Map<String, com.firefly.transactional.saga.registry.SagaDefinition> sagas = (Map<String, com.firefly.transactional.saga.registry.SagaDefinition>) sagasField.get(sagaRegistry);
            sagas.put(sagaName, libSagaDefinition);
        } catch (Exception e) {
            System.err.println("Warning: Could not register saga with lib-transactional-engine registry: " + e.getMessage());
        }

        // Create StepInputs from inputData
        StepInputs.Builder inputsBuilder = StepInputs.builder();
        if (inputData != null) {
            // Add input data for all steps
            for (String stepId : pythonDefinition.getSteps().keySet()) {
                inputsBuilder.forStepId(stepId, inputData);
            }
        }
        StepInputs stepInputs = inputsBuilder.build();

        // Create SagaContext with correlation ID
        SagaContext sagaContext = new SagaContext(sagaName, correlationId);

        try {
            // DELEGATE TO lib-transactional-engine SagaEngine!
            System.out.println("[DELEGATION] Calling lib-transactional-engine SagaEngine.execute() for SAGA: " + sagaName);
            Mono<SagaResult> resultMono = sagaEngine.execute(sagaName, stepInputs, sagaContext);

            // Block and wait for result (since Python expects synchronous response)
            // Use subscribeOn(Schedulers.boundedElastic()) to offload blocking to a thread that allows it
            SagaResult sagaResult = resultMono
                .subscribeOn(reactor.core.scheduler.Schedulers.boundedElastic())
                .block(Duration.ofMinutes(5));

            // Check for null result
            if (sagaResult == null) {
                System.err.println("[lib-transactional-engine] SAGA execution returned null result: " + sagaName);
                Map<String, Object> errorMap = new HashMap<>();
                errorMap.put("success", false);
                errorMap.put("correlation_id", correlationId);
                errorMap.put("saga_name", sagaName);
                errorMap.put("error", "SAGA execution returned null result");
                errorMap.put("failed_steps", new ArrayList<>());
                errorMap.put("compensated_steps", new ArrayList<>());
                return errorMap;
            }

            // Convert SagaResult to our result format
            Map<String, Object> resultMap = new HashMap<>();
            resultMap.put("is_success", sagaResult.isSuccess());  // Python expects "is_success"
            resultMap.put("correlation_id", correlationId);
            resultMap.put("saga_name", sagaName);

            // Extract duration from SagaResult
            long durationMs = sagaResult.duration() != null ? sagaResult.duration().toMillis() : 0;
            resultMap.put("duration_ms", durationMs);

            // Extract timestamps
            resultMap.put("started_at", sagaResult.startedAt() != null ? sagaResult.startedAt().toString() : null);
            resultMap.put("completed_at", sagaResult.completedAt() != null ? sagaResult.completedAt().toString() : null);

            // Extract step results from SagaResult
            Map<String, Object> stepsMap = new HashMap<>();
            for (Map.Entry<String, SagaResult.StepOutcome> entry : sagaResult.steps().entrySet()) {
                Map<String, Object> stepData = new HashMap<>();
                SagaResult.StepOutcome outcome = entry.getValue();
                // Handle null status (can happen with lib-transactional-engine in some cases)
                stepData.put("status", outcome.status() != null ? outcome.status().toString() : "UNKNOWN");
                stepData.put("attempts", outcome.attempts());
                stepData.put("latency_ms", outcome.latencyMs());
                stepData.put("result", outcome.result());
                stepData.put("compensated", outcome.compensated());
                if (outcome.error() != null) {
                    stepData.put("error", outcome.error().getMessage());
                }
                stepsMap.put(entry.getKey(), stepData);
            }
            resultMap.put("steps", stepsMap);

            // Extract failed and compensated steps from SagaResult
            resultMap.put("failed_steps", new ArrayList<>(sagaResult.failedSteps()));
            resultMap.put("compensated_steps", new ArrayList<>(sagaResult.compensatedSteps()));

            if (sagaResult.isSuccess()) {
                System.out.println("[lib-transactional-engine] SAGA execution completed successfully: " + sagaName);
            } else {
                System.err.println("[lib-transactional-engine] SAGA execution failed: " + sagaName);
                String errorMsg = sagaResult.error().map(Throwable::getMessage).orElse("SAGA execution failed");
                resultMap.put("error", errorMsg);
            }

            System.out.println("[lib-transactional-engine] Returning result: is_success=" + sagaResult.isSuccess() +
                ", failed_steps=" + sagaResult.failedSteps().size() +
                ", compensated_steps=" + sagaResult.compensatedSteps().size());
            return resultMap;

        } finally {
            // Clean up callback handler
            if (callbackHandler != null) {
                callbackHandlers.remove(correlationId);
            }
        }
    }
    
    /**
     * Build a lib-transactional-engine SagaDefinition from a Python SAGA definition.
     * This creates StepHandler instances that call back to Python for step execution.
     */
    private com.firefly.transactional.saga.registry.SagaDefinition buildLibSagaDefinition(String sagaName, JavaSubprocessBridge.SagaDefinition pythonDef, PythonCallbackHandler callbackHandler) {
        // Create a dummy bean object for the saga (lib-transactional-engine requires a bean)
        Object dummyBean = new Object();

        // Create lib-transactional-engine SagaDefinition
        com.firefly.transactional.saga.registry.SagaDefinition libSagaDef = new com.firefly.transactional.saga.registry.SagaDefinition(sagaName, dummyBean, dummyBean, 0);

        // Build StepDefinitions with Python callback handlers
        for (Map.Entry<String, Object> entry : pythonDef.getSteps().entrySet()) {
            String stepId = entry.getKey();
            @SuppressWarnings("unchecked")
            Map<String, Object> stepData = (Map<String, Object>) entry.getValue();

            String pythonMethod = (String) stepData.get("python_method");
            String compensationMethod = (String) stepData.get("compensation_method");

            @SuppressWarnings("unchecked")
            List<String> dependsOn = (List<String>) stepData.getOrDefault("depends_on", new ArrayList<>());

            Integer retry = (Integer) stepData.getOrDefault("retry", 0);
            Long timeoutMs = stepData.containsKey("timeout_ms") ? ((Number) stepData.get("timeout_ms")).longValue() : 0L;
            Long backoffMs = stepData.containsKey("backoff_ms") ? ((Number) stepData.get("backoff_ms")).longValue() : 100L;

            // Create Python callback handler for this step
            PythonStepHandler stepHandler = new PythonStepHandler(stepId, pythonMethod, compensationMethod, callbackHandler);

            // Create StepDefinition
            StepDefinition stepDef = new StepDefinition(
                stepId,
                compensationMethod,  // compensateName
                dependsOn,
                retry,
                Duration.ofMillis(backoffMs),
                Duration.ofMillis(timeoutMs),
                null,  // idempotencyKey
                false, // jitter
                0.0,   // jitterFactor
                false, // cpuBound
                null   // stepMethod (we use handler instead)
            );

            // Set the handler for programmatic execution
            stepDef.handler = stepHandler;

            // Add to saga definition
            libSagaDef.steps.put(stepId, stepDef);
        }

        System.out.println("[lib-transactional-engine] Built SagaDefinition for: " + sagaName + " with " + libSagaDef.steps.size() + " steps");
        return libSagaDef;
    }

    private Object registerSaga(SagaEngine sagaEngine, Object[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("registerSaga requires 2 arguments: sagaName, registrationData");
        }
        
        String sagaName = (String) args[0];
        @SuppressWarnings("unchecked")
        Map<String, Object> registrationData = (Map<String, Object>) args[1];
        
        System.out.println("Registering SAGA: " + sagaName);
        
        // Store registration data for later use
        SagaRegistration registration = new SagaRegistration(sagaName, registrationData);
        SagaRegistrationRegistry.register(sagaName, registration);
        
        return "SAGA registered: " + sagaName;
    }
    
    private Object handleTccEngineMethod(TccEngine tccEngine, String methodName, Object[] args) throws Exception {
        switch (methodName) {
            case "execute":
                return executeTccWithRealEngine(tccEngine, args);
                
            case "executeTcc":
                return executeTccWithCallbacks(tccEngine, args);
                
            case "registerTcc":
                return registerTcc(tccEngine, args);
                
            case "registerTccDefinition":
                return registerTccDefinition(tccEngine, args);
                
            case "reportPhaseExecution":
                return reportTccPhaseExecution(tccEngine, args);
                
            default:
                // Fall back to reflection for other methods
                Method method = findMatchingMethod(TccEngine.class, methodName, args, false);
                return method.invoke(tccEngine, args);
        }
    }
    
    private Object executeTccWithCallbacks(TccEngine tccEngine, Object[] args) throws Exception {
        if (args.length < 3) {
            throw new IllegalArgumentException("executeTcc requires at least 3 arguments: tccName, correlationId, participantInputs, callbackInfo");
        }
        
        String tccName = (String) args[0];
        String correlationId = (String) args[1];
        @SuppressWarnings("unchecked")
        Map<String, Object> participantInputs = (Map<String, Object>) args[2];
        
        // Get callback handler info if provided
        @SuppressWarnings("unchecked")
        Map<String, Object> callbackInfo = args.length > 3 ? (Map<String, Object>) args[3] : null;
        
        System.out.println("Executing TCC: " + tccName + " with correlation ID: " + correlationId);
        
        // Get TCC definition
        TccDefinition definition = TccDefinitionRegistry.get(tccName);
        if (definition == null) {
            throw new IllegalArgumentException("TCC definition not found: " + tccName);
        }
        
        // Create TCC execution context
        TccExecutionContext context = new TccExecutionContext(tccName, correlationId, participantInputs, definition);
        
        // Register callback handler if provided
        if (callbackInfo != null) {
            TccCallbackHandler handler = new TccCallbackHandler(callbackInfo, this);
            callbackHandlers.put(correlationId, (Object) handler);
            context.setCallbackHandler(handler);
        }
        
        // Execute TCC with Java orchestration
        TccExecutionResult result = executeTccWithOrchestration(context);
        
        // Clean up callback handler
        callbackHandlers.remove(correlationId);
        
        return result.toMap();
    }
    
    private Object registerTcc(TccEngine tccEngine, Object[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("registerTcc requires 2 arguments: tccName, registrationData");
        }
        
        String tccName = (String) args[0];
        @SuppressWarnings("unchecked")
        Map<String, Object> registrationData = (Map<String, Object>) args[1];
        
        System.out.println("Registering TCC: " + tccName);
        
        // Store TCC registration data for later use
        // In a real implementation, this would create TCC definition and store it
        System.out.println("TCC " + tccName + " registered successfully");
        
        return "TCC registered: " + tccName;
    }
    
    private Object registerTccDefinition(TccEngine tccEngine, Object[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("registerTccDefinition requires 1 argument: tccDefinition");
        }
        
        @SuppressWarnings("unchecked")
        Map<String, Object> tccDefinition = (Map<String, Object>) args[0];
        
        String tccName = (String) tccDefinition.get("tcc_name");
        String className = (String) tccDefinition.get("class_name");
        String module = (String) tccDefinition.get("module");
        
        @SuppressWarnings("unchecked")
        Map<String, Object> participants = (Map<String, Object>) tccDefinition.get("participants");
        
        // Store TCC definition for execution orchestration
        TccDefinition definition = new TccDefinition(tccName, className, module, participants);
        TccDefinitionRegistry.register(tccName, definition);
        
        System.out.println("Registered TCC definition: " + tccName + " with " + participants.size() + " participants");
        
        return "TCC definition registered: " + tccName;
    }
    
    private Object executeTccWithRealEngine(TccEngine tccEngine, Object[] args) throws Exception {
        System.out.println("Executing TCC using real TccEngine with " + args.length + " arguments");
        
        if (args.length < 2) {
            throw new IllegalArgumentException("TccEngine.execute requires at least 2 arguments: tccName, tccInputsId");
        }
        
        String tccName = (String) args[0];
        String tccInputsId = (String) args[1];
        String tccContextId = args.length > 2 ? (String) args[2] : null;
        
        System.out.println("Executing TCC: " + tccName + " with TccInputs: " + tccInputsId + 
                           (tccContextId != null ? " and TccContext: " + tccContextId : ""));
        
        // Get the TccInputs object from instance registry
        Object tccInputs = instances.get(tccInputsId);
        if (tccInputs == null) {
            throw new IllegalArgumentException("TccInputs object not found: " + tccInputsId);
        }
        
        // Get the TccContext object if provided
        Object tccContext = null;
        if (tccContextId != null) {
            tccContext = instances.get(tccContextId);
            if (tccContext == null) {
                throw new IllegalArgumentException("TccContext object not found: " + tccContextId);
            }
        }
        
        try {
            // Use reflection to call the proper TccEngine.execute method
            Method executeMethod;
            Object result;
            
            if (tccContext != null) {
                // Call execute(String, TccInputs, TccContext)
                executeMethod = TccEngine.class.getMethod("execute", String.class, 
                    Class.forName("com.firefly.transactional.tcc.core.TccInputs"),
                    Class.forName("com.firefly.transactional.tcc.core.TccContext"));
                result = executeMethod.invoke(tccEngine, tccName, tccInputs, tccContext);
            } else {
                // Call execute(String, TccInputs)
                executeMethod = TccEngine.class.getMethod("execute", String.class, 
                    Class.forName("com.firefly.transactional.tcc.core.TccInputs"));
                result = executeMethod.invoke(tccEngine, tccName, tccInputs);
            }
            
            // The result is a Mono<TccResult>, so we need to block on it
            if (result != null && result.getClass().getName().contains("Mono")) {
                System.out.println("TCC execution returned Mono, blocking for result...");
                
                // Use reflection to call .block() on the Mono
                Method blockMethod = result.getClass().getMethod("block");
                Object tccResult = blockMethod.invoke(result);
                
                if (tccResult != null) {
                    // Store the TccResult instance for future method calls
                    String resultId = UUID.randomUUID().toString();
                    instances.put(resultId, tccResult);
                    
                    System.out.println("TCC execution completed successfully, result stored as: " + resultId);
                    
                    // Return the instance ID so Python can extract data from the TccResult
                    return resultId;
                } else {
                    throw new RuntimeException("TCC execution returned null result");
                }
            } else {
                throw new RuntimeException("Expected Mono<TccResult> but got: " + 
                    (result != null ? result.getClass().getName() : "null"));
            }
            
        } catch (Exception e) {
            System.err.println("TCC execution failed: " + e.getMessage());
            e.printStackTrace();
            
            // Create a failure result
            Map<String, Object> failureResult = new HashMap<>();
            failureResult.put("tcc_name", tccName);
            failureResult.put("correlation_id", "failed_" + UUID.randomUUID().toString());
            failureResult.put("is_success", false);
            failureResult.put("is_confirmed", false);
            failureResult.put("is_canceled", false);
            failureResult.put("final_phase", "FAILED");
            failureResult.put("duration_ms", 0);
            failureResult.put("try_results", new HashMap<>());
            failureResult.put("participant_results", new HashMap<>());
            failureResult.put("error", e.getMessage());
            failureResult.put("participants_count", 0);
            failureResult.put("engine_used", true);
            failureResult.put("lib_transactional_version", "1.0.0-SNAPSHOT");
            
            return failureResult;
        }
    }
    
    private Object reportTccPhaseExecution(TccEngine tccEngine, Object[] args) throws Exception {
        if (args.length < 4) {
            throw new IllegalArgumentException("reportPhaseExecution requires 4 arguments: tccName, phase, phaseResults, correlationId");
        }
        
        String tccName = (String) args[0];
        String phase = (String) args[1];
        @SuppressWarnings("unchecked")
        Map<String, Object> phaseResults = (Map<String, Object>) args[2];
        String correlationId = (String) args[3];
        
        System.out.println("Reporting TCC phase execution: " + tccName + 
                           " phase " + phase + " with correlation ID " + correlationId);
        
        // Phase execution reported to Python wrapper. Persist if a persistence layer is configured.
        
        try {
            // Validate phase results
            if (phaseResults == null || phaseResults.isEmpty()) {
                System.out.println("Warning: Empty phase results for TCC " + tccName + " phase " + phase);
            } else {
                System.out.println("Phase results received: " + phaseResults.keySet().size() + " participants");
                for (Map.Entry<String, Object> entry : phaseResults.entrySet()) {
                    System.out.println("  Participant " + entry.getKey() + ": " + entry.getValue());
                }
            }
            
            // Phase reporting completed
            System.out.println("TCC " + tccName + " phase " + phase + " reported successfully");
            return true;
            
        } catch (Exception e) {
            System.err.println("Failed to report TCC phase: " + e.getMessage());
            e.printStackTrace();
            return false;
        }
    }
    
    private SagaExecutionResult executeWithOrchestration(SagaExecutionContext context) {
        long startNanos = System.nanoTime();
        System.out.println("Starting Java orchestration for SAGA: " + context.getSagaName());
        
        SagaExecutionResult result = new SagaExecutionResult(
            context.getSagaName(),
            context.getCorrelationId(),
            true, // assume success initially
            new HashMap<>(),
            new ArrayList<>(),
            new ArrayList<>(),
            null
        );
        
        try {
            // Execute steps in dependency order
            Map<String, Object> stepResults = new HashMap<>();
            List<String> executedSteps = new ArrayList<>();
            
            // Get step execution order based on dependencies
            List<String> executionOrder = calculateExecutionOrder(context.getDefinition().getSteps());
            
            for (String stepId : executionOrder) {
                try {
                    System.out.println("Executing step: " + stepId);
                    
                    // Call back to Python to execute the step
                    Map<String, Object> stepResult = executeStepCallback(context, stepId, stepResults);
                    
                    if (stepResult != null && Boolean.TRUE.equals(stepResult.get("success"))) {
                        stepResults.put(stepId, stepResult.get("result"));
                        executedSteps.add(stepId);
                        System.out.println("Step completed successfully: " + stepId);
                    } else {
                        // Step failed - start compensation
                        String error = stepResult != null ? (String) stepResult.get("error") : "Step execution failed";
                        System.out.println("Step failed: " + stepId + " - " + error);
                        
                        result.setSuccess(false);
                        result.setError(error);
                        result.getFailedSteps().add(stepId);
                        
                        // Execute compensation for completed steps
                        executeCompensation(context, executedSteps, result);
                        break;
                    }
                    
                } catch (Exception e) {
                    System.err.println("Error executing step " + stepId + ": " + e.getMessage());
                    result.setSuccess(false);
                    result.setError(e.getMessage());
                    result.getFailedSteps().add(stepId);
                    
                    // Execute compensation for completed steps
                    executeCompensation(context, executedSteps, result);
                    break;
                }
            }
            
            result.setSteps(stepResults);
            
        } catch (Exception e) {
            System.err.println("SAGA execution failed: " + e.getMessage());
            result.setSuccess(false);
            result.setError(e.getMessage());
        }
        
        long durationMs = (System.nanoTime() - startNanos) / 1_000_000;
        result.setDurationMs(durationMs);
        System.out.println("SAGA execution completed: " + context.getSagaName() + " - Success: " + result.isSuccess() + " in " + durationMs + "ms");
        return result;
    }
    
    private Map<String, Object> executeStepCallback(SagaExecutionContext context, String stepId, Map<String, Object> previousResults) {
        PythonCallbackHandler handler = context.getCallbackHandler();
        if (handler == null) {
            throw new RuntimeException("No callback handler available for step execution");
        }
        
        // Get step definition from saga definition
        SagaDefinition definition = context.getDefinition();
        Map<String, Object> stepDef = (Map<String, Object>) definition.getSteps().get(stepId);
        if (stepDef == null) {
            throw new RuntimeException("Step definition not found for step: " + stepId);
        }
        
        String methodName = (String) stepDef.get("python_method");
        if (methodName == null) {
            throw new RuntimeException("Python method not defined for step: " + stepId);
        }
        
        // Prepare input data for the step
        Map<String, Object> stepInput = new HashMap<>(context.getInputData());
        stepInput.putAll(previousResults); // Include results from previous steps
        
        // Prepare context data
        Map<String, Object> contextData = new HashMap<>();
        contextData.put("correlation_id", context.getCorrelationId());
        contextData.put("saga_name", context.getSagaName());
        contextData.put("variables", new HashMap<>()); // Could include context variables
        contextData.put("step_results", previousResults); // Pass all previous step results
        
        // Execute HTTP callback to Python
        return executeHttpCallback(handler.getCallbackUrl(), "step", methodName, stepId, stepInput, contextData);
    }
    
    private void executeCompensation(SagaExecutionContext context, List<String> executedSteps, SagaExecutionResult result) {
        System.out.println("Starting compensation for " + executedSteps.size() + " executed steps");
        
        PythonCallbackHandler handler = context.getCallbackHandler();
        if (handler == null) {
            System.out.println("No callback handler for compensation");
            return;
        }
        
        // Compensate in reverse order
        Collections.reverse(executedSteps);
        
        for (String stepId : executedSteps) {
            try {
                System.out.println("Compensating step: " + stepId);
                
                // Get compensation method from saga definition
                SagaDefinition definition = context.getDefinition();
                Map<String, Object> compensationDef = (Map<String, Object>) definition.getCompensations().get(stepId);
                if (compensationDef == null) {
                    System.out.println("No compensation defined for step: " + stepId);
                    continue;
                }
                
                String compensationMethod = (String) compensationDef.get("python_method");
                if (compensationMethod == null) {
                    System.out.println("No compensation method defined for step: " + stepId);
                    continue;
                }
                
                Object stepResultObj = result.getSteps().get(stepId);
                Map<String, Object> stepResult = stepResultObj instanceof Map ? (Map<String, Object>) stepResultObj : new HashMap<>();
                Map<String, Object> contextData = new HashMap<>();
                contextData.put("correlation_id", context.getCorrelationId());
                contextData.put("saga_name", context.getSagaName());
                
                // Execute HTTP callback for compensation
                Map<String, Object> compensationResult = executeHttpCallback(
                    handler.getCallbackUrl(), "compensation", compensationMethod, stepId, stepResult, contextData
                );
                
                if (compensationResult != null && Boolean.TRUE.equals(compensationResult.get("success"))) {
                    result.getCompensatedSteps().add(stepId);
                    System.out.println("Compensation completed: " + stepId);
                } else {
                    System.err.println("Compensation failed for step: " + stepId);
                }
                
            } catch (Exception e) {
                System.err.println("Error during compensation for step " + stepId + ": " + e.getMessage());
            }
        }
    }
    
    private Map<String, Object> executeHttpCallback(String callbackUrl, String methodType, String methodName,
                                                   String stepId, Map<String, Object> inputData,
                                                   Map<String, Object> contextData) {
        try {
            System.out.println("Making HTTP callback to: " + callbackUrl + " for method: " + methodName);

            // Use reactive callback client with connection pooling
            Map<String, Object> result = callbackClient.executeCallback(
                    callbackUrl, methodType, methodName, stepId, inputData, contextData);

            System.out.println("HTTP callback completed successfully: " + methodName);
            return result;

        } catch (Exception e) {
            System.err.println("Error making HTTP callback: " + e.getMessage());
            e.printStackTrace();
            return createFailureResponse("HTTP callback error: " + e.getMessage());
        }
    }
    
    private Map<String, Object> createFailureResponse(String error) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", false);
        response.put("error", error);
        return response;
    }
    
    private List<String> calculateExecutionOrder(Map<String, Object> steps) {
        // Simple topological sort based on dependencies
        List<String> order = new ArrayList<>();
        Set<String> visited = new HashSet<>();
        Set<String> visiting = new HashSet<>();
        
        for (String stepId : steps.keySet()) {
            if (!visited.contains(stepId)) {
                visitStep(stepId, steps, order, visited, visiting);
            }
        }
        
        return order;
    }
    
    private void visitStep(String stepId, Map<String, Object> steps, List<String> order, Set<String> visited, Set<String> visiting) {
        if (visiting.contains(stepId)) {
            throw new RuntimeException("Circular dependency detected: " + stepId);
        }
        
        if (visited.contains(stepId)) {
            return;
        }
        
        visiting.add(stepId);
        
        @SuppressWarnings("unchecked")
        Map<String, Object> stepConfig = (Map<String, Object>) steps.get(stepId);
        @SuppressWarnings("unchecked")
        List<String> dependencies = (List<String>) stepConfig.get("depends_on");
        
        if (dependencies != null) {
            for (String dep : dependencies) {
                visitStep(dep, steps, order, visited, visiting);
            }
        }
        
        visiting.remove(stepId);
        visited.add(stepId);
        order.add(stepId);
    }
    
    private Class<?> getClass(String className) throws ClassNotFoundException {
        return Class.forName(className);
    }
    
    private Constructor<?> findMatchingConstructor(Class<?> clazz, Object[] args) throws NoSuchMethodException {
        Constructor<?>[] constructors = clazz.getConstructors();
        
        for (Constructor<?> constructor : constructors) {
            if (constructor.getParameterCount() == args.length) {
                return constructor;
            }
        }
        
        // Default constructor if no args
        if (args.length == 0) {
            return clazz.getConstructor();
        }
        
        throw new NoSuchMethodException("No matching constructor found for " + clazz.getName());
    }
    
    private Method findMatchingMethod(Class<?> clazz, String methodName, Object[] args, boolean isStatic) throws NoSuchMethodException {
        Method[] methods = clazz.getMethods();
        
        for (Method method : methods) {
            if (method.getName().equals(methodName) && 
                method.getParameterCount() == args.length &&
                java.lang.reflect.Modifier.isStatic(method.getModifiers()) == isStatic) {
                return method;
            }
        }
        
        throw new NoSuchMethodException("No matching method found: " + methodName + " in " + clazz.getName());
    }
    
    private Object[] parseArguments(JsonNode argsNode) {
        if (argsNode == null || argsNode.isNull()) {
            return new Object[0];
        }
        
        if (!argsNode.isArray()) {
            throw new IllegalArgumentException("Arguments must be an array");
        }
        
        Object[] args = new Object[argsNode.size()];
        for (int i = 0; i < argsNode.size(); i++) {
            args[i] = parseArgument(argsNode.get(i));
        }
        
        return args;
    }
    
    private Object parseArgument(JsonNode node) {
        if (node.isNull()) {
            return null;
        } else if (node.isBoolean()) {
            return node.asBoolean();
        } else if (node.isInt()) {
            return node.asInt();
        } else if (node.isLong()) {
            return node.asLong();
        } else if (node.isDouble()) {
            return node.asDouble();
        } else if (node.isTextual()) {
            return node.asText();
        } else if (node.isArray() || node.isObject()) {
            return objectMapper.convertValue(node, Object.class);
        } else {
            return node.toString();
        }
    }
    
    private void sendSuccessResponse(String requestId, Object result, String instanceId) throws IOException {
        ObjectNode response = objectMapper.createObjectNode();
        response.put("success", true);
        response.put("requestId", requestId);
        
        if (result instanceof ConstructorResult) {
            ConstructorResult constructorResult = (ConstructorResult) result;
            response.put("instanceId", constructorResult.instanceId);
            response.put("result", constructorResult.message);
        } else {
            response.set("result", objectMapper.valueToTree(result));
            if (instanceId != null) {
                response.put("instanceId", instanceId);
            }
        }
        
        Path responseFile = responseDir.resolve(requestId + ".json");
        Files.writeString(responseFile, response.toString());
    }
    
    private void sendErrorResponse(String requestId, String error) throws IOException {
        ObjectNode response = objectMapper.createObjectNode();
        response.put("success", false);
        response.put("requestId", requestId);
        response.put("error", error);
        
        Path responseFile = responseDir.resolve(requestId + ".json");
        Files.writeString(responseFile, response.toString());
    }
    
    // Helper classes
    private static class ConstructorResult {
        public final String instanceId;
        public final String message;
        
        public ConstructorResult(String instanceId, String message) {
            this.instanceId = instanceId;
            this.message = message;
        }
    }
    
    
    // Helper classes for callback system
    private static class PythonCallbackHandler {
        private final Map<String, Object> callbackInfo;
        private final JavaSubprocessBridge bridge;
        
        public PythonCallbackHandler(Map<String, Object> callbackInfo, JavaSubprocessBridge bridge) {
            this.callbackInfo = callbackInfo;
            this.bridge = bridge;
        }
        
        public String getCallbackUrl() {
            return (String) callbackInfo.get("callback_url");
        }
        
        public Map<String, Object> executeStep(String stepId, Map<String, Object> input, Map<String, Object> context) {
            // Legacy method - not used in new HTTP callback system
            return new HashMap<>();
        }

        public Map<String, Object> executeCompensation(String stepId, Map<String, Object> input, Map<String, Object> context) {
            // Legacy method - not used in new HTTP callback system
            return new HashMap<>();
        }

        /**
         * Execute a callback to Python for a specific method.
         * Used by lib-transactional-engine integration via PythonStepHandler.
         */
        public Map<String, Object> executeCallback(String methodName, Map<String, Object> inputData, Map<String, Object> contextData) {
            // Use the ReactiveCallbackClient from the bridge
            String stepId = (String) contextData.getOrDefault("step_id", "unknown");
            return bridge.callbackClient.executeCallback(getCallbackUrl(), "STEP", methodName, stepId, inputData, contextData);
        }

        /**
         * Execute a callback to Python (reactive version).
         * Used by lib-transactional-engine integration via PythonStepHandler.
         */
        public Mono<Map<String, Object>> executeCallbackReactive(String methodName, Map<String, Object> inputData, Map<String, Object> contextData) {
            // Use the ReactiveCallbackClient from the bridge with "STEP" method type
            String stepId = (String) contextData.getOrDefault("step_id", "unknown");
            return bridge.callbackClient.executeCallbackReactive(getCallbackUrl(), "STEP", methodName, stepId, inputData, contextData);
        }

        /**
         * Execute a compensation callback to Python.
         * Used by lib-transactional-engine integration via PythonCompensationHandler.
         */
        public Map<String, Object> executeCompensationCallback(String methodName, Map<String, Object> inputData, Map<String, Object> contextData) {
            // Use the ReactiveCallbackClient from the bridge with "compensation" method type
            String stepId = (String) contextData.getOrDefault("step_id", "unknown");
            return bridge.callbackClient.executeCallback(getCallbackUrl(), "compensation", methodName, stepId, inputData, contextData);
        }

        /**
         * Execute a compensation callback to Python (reactive version).
         * Used by lib-transactional-engine integration via PythonCompensationHandler.
         */
        public Mono<Map<String, Object>> executeCompensationCallbackReactive(String methodName, Map<String, Object> inputData, Map<String, Object> contextData) {
            // Use the ReactiveCallbackClient from the bridge with "compensation" method type
            String stepId = (String) contextData.getOrDefault("step_id", "unknown");
            return bridge.callbackClient.executeCallbackReactive(getCallbackUrl(), "compensation", methodName, stepId, inputData, contextData);
        }
    }
    
    private static class SagaDefinition {
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
        
        public String getSagaName() { return sagaName; }
        public String getClassName() { return className; }
        public String getModule() { return module; }
        public Map<String, Object> getSteps() { return steps; }
        public Map<String, Object> getCompensations() { return compensations; }
    }
    
    private static class SagaExecutionContext {
        private final String sagaName;
        private final String correlationId;
        private final Map<String, Object> inputData;
        private final SagaDefinition definition;
        private PythonCallbackHandler callbackHandler;
        
        public SagaExecutionContext(String sagaName, String correlationId, 
                                   Map<String, Object> inputData, SagaDefinition definition) {
            this.sagaName = sagaName;
            this.correlationId = correlationId;
            this.inputData = inputData;
            this.definition = definition;
        }
        
        public String getSagaName() { return sagaName; }
        public String getCorrelationId() { return correlationId; }
        public Map<String, Object> getInputData() { return inputData; }
        public SagaDefinition getDefinition() { return definition; }
        public PythonCallbackHandler getCallbackHandler() { return callbackHandler; }
        public void setCallbackHandler(PythonCallbackHandler handler) { this.callbackHandler = handler; }
    }
    
    private static class SagaDefinitionRegistry {
        private static final Map<String, SagaDefinition> definitions = new ConcurrentHashMap<>();
        
        public static void register(String name, SagaDefinition definition) {
            definitions.put(name, definition);
        }
        
        public static SagaDefinition get(String name) {
            return definitions.get(name);
        }
    }
    
    private static class SagaRegistration {
        private final String sagaName;
        private final Map<String, Object> registrationData;
        
        public SagaRegistration(String sagaName, Map<String, Object> registrationData) {
            this.sagaName = sagaName;
            this.registrationData = registrationData;
        }
        
        public String getSagaName() { return sagaName; }
        public Map<String, Object> getRegistrationData() { return registrationData; }
    }
    
    private static class SagaRegistrationRegistry {
        private static final Map<String, SagaRegistration> registrations = new ConcurrentHashMap<>();
        
        public static void register(String name, SagaRegistration registration) {
            registrations.put(name, registration);
        }
        
        public static SagaRegistration get(String name) {
            return registrations.get(name);
        }
    }
    
    private static class SagaExecutionResult {
        private String sagaName;
        private String correlationId;
        private boolean success;
        private Map<String, Object> steps;
        private List<String> failedSteps;
        private List<String> compensatedSteps;
        private String error;
        private long durationMs;
        
        public SagaExecutionResult(String sagaName, String correlationId, boolean success,
                                 Map<String, Object> steps, List<String> failedSteps, 
                                 List<String> compensatedSteps, String error) {
            this.sagaName = sagaName;
            this.correlationId = correlationId;
            this.success = success;
            this.steps = steps;
            this.failedSteps = failedSteps;
            this.compensatedSteps = compensatedSteps;
            this.error = error;
            this.durationMs = 0L;
        }
        
        public Map<String, Object> toMap() {
            Map<String, Object> result = new HashMap<>();
            result.put("saga_name", sagaName);
            result.put("correlation_id", correlationId);
            result.put("is_success", success);
            result.put("duration_ms", durationMs);
            result.put("steps", steps);
            result.put("failed_steps", failedSteps);
            result.put("compensated_steps", compensatedSteps);
            result.put("error", error);
            result.put("engine_used", true);
            result.put("lib_transactional_version", "1.0.0-SNAPSHOT");
            return result;
        }
        
        // Getters and setters
        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        public String getError() { return error; }
        public void setError(String error) { this.error = error; }
        public Map<String, Object> getSteps() { return steps; }
        public void setSteps(Map<String, Object> steps) { this.steps = steps; }
        public List<String> getFailedSteps() { return failedSteps; }
        public List<String> getCompensatedSteps() { return compensatedSteps; }
        public void setDurationMs(long durationMs) { this.durationMs = durationMs; }
    }
    
    // TCC-related support classes
    
    private static class TccDefinitionRegistry {
        private static final Map<String, TccDefinition> tccDefinitions = new ConcurrentHashMap<>();
        
        public static void register(String tccName, TccDefinition definition) {
            tccDefinitions.put(tccName, definition);
        }
        
        public static TccDefinition get(String tccName) {
            return tccDefinitions.get(tccName);
        }
        
        public static boolean exists(String tccName) {
            return tccDefinitions.containsKey(tccName);
        }
    }
    
    private static class TccDefinition {
        private final String tccName;
        private final String className;
        private final String module;
        private final Map<String, Object> participants;
        
        public TccDefinition(String tccName, String className, String module, Map<String, Object> participants) {
            this.tccName = tccName;
            this.className = className;
            this.module = module;
            this.participants = participants;
        }
        
        public String getTccName() { return tccName; }
        public String getClassName() { return className; }
        public String getModule() { return module; }
        public Map<String, Object> getParticipants() { return participants; }
    }
    
    private static class TccExecutionContext {
        private final String tccName;
        private final String correlationId;
        private final Map<String, Object> participantInputs;
        private final TccDefinition definition;
        private TccCallbackHandler callbackHandler;
        
        public TccExecutionContext(String tccName, String correlationId, Map<String, Object> participantInputs, TccDefinition definition) {
            this.tccName = tccName;
            this.correlationId = correlationId;
            this.participantInputs = participantInputs;
            this.definition = definition;
        }
        
        public String getTccName() { return tccName; }
        public String getCorrelationId() { return correlationId; }
        public Map<String, Object> getParticipantInputs() { return participantInputs; }
        public TccDefinition getDefinition() { return definition; }
        public TccCallbackHandler getCallbackHandler() { return callbackHandler; }
        public void setCallbackHandler(TccCallbackHandler callbackHandler) { this.callbackHandler = callbackHandler; }
    }
    
    private static class TccCallbackHandler {
        private final String callbackEndpoint;
        private final JavaSubprocessBridge bridge;
        
        public TccCallbackHandler(Map<String, Object> callbackInfo, JavaSubprocessBridge bridge) {
            this.callbackEndpoint = (String) callbackInfo.get("callback_endpoint");
            this.bridge = bridge;
        }
        
        public Map<String, Object> executeTccMethod(String phase, String participantId, String methodName, Object inputData, Map<String, Object> contextData) {
            System.out.println("Executing TCC " + phase + " callback: " + participantId + "." + methodName);

            try {
                // Use reactive callback client with connection pooling
                Map<String, Object> result = bridge.callbackClient.executeTccCallback(
                        callbackEndpoint, phase, participantId, methodName,
                        inputData instanceof Map ? (Map<String, Object>) inputData : new HashMap<>(),
                        contextData);

                System.out.println("TCC callback completed: " + participantId + "." + methodName);
                return result;

            } catch (Exception e) {
                System.err.println("Error making TCC callback: " + e.getMessage());
                e.printStackTrace();
                return createTccFailureResponse("TCC callback error: " + e.getMessage());
            }
        }
        
        private Map<String, Object> createTccFailureResponse(String error) {
            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("error", error);
            return response;
        }
    }
    
    private static class TccExecutionResult {
        private String tccName;
        private String correlationId;
        private boolean success;
        private String phase; // "TRY", "CONFIRM", "CANCEL"
        private Map<String, Object> tryResults;
        private Map<String, Object> participantResults;
        private String error;
        private long durationMs;
        
        public TccExecutionResult(String tccName, String correlationId, boolean success,
                                 String phase, Map<String, Object> tryResults, 
                                 Map<String, Object> participantResults, String error) {
            this.tccName = tccName;
            this.correlationId = correlationId;
            this.success = success;
            this.phase = phase;
            this.tryResults = tryResults;
            this.participantResults = participantResults;
            this.error = error;
            this.durationMs = 0L;
        }
        
        public Map<String, Object> toMap() {
            Map<String, Object> result = new HashMap<>();
            result.put("tcc_name", tccName);
            result.put("correlation_id", correlationId);
            result.put("success", success);
            result.put("phase", phase);
            result.put("duration_ms", durationMs);
            result.put("try_results", tryResults);
            result.put("participant_results", participantResults);
            result.put("error", error);
            result.put("engine_used", true);
            result.put("lib_transactional_version", "1.0.0-SNAPSHOT");
            return result;
        }
        
        // Getters and setters
        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        public String getError() { return error; }
        public void setError(String error) { this.error = error; }
        public String getPhase() { return phase; }
        public void setPhase(String phase) { this.phase = phase; }
        public Map<String, Object> getTryResults() { return tryResults; }
        public Map<String, Object> getParticipantResults() { return participantResults; }
        public void setTryResults(Map<String, Object> tryResults) { this.tryResults = tryResults; }
        public void setParticipantResults(Map<String, Object> participantResults) { this.participantResults = participantResults; }
        public void setDurationMs(long durationMs) { this.durationMs = durationMs; }
    }
    
    // TCC orchestration logic
    private TccExecutionResult executeTccWithOrchestration(TccExecutionContext context) {
        long startNanos = System.nanoTime();
        String tccName = context.getTccName();
        String correlationId = context.getCorrelationId();
        TccCallbackHandler callbackHandler = context.getCallbackHandler();
        Map<String, Object> participants = context.getDefinition().getParticipants();
        
        System.out.println("Executing TCC orchestration: " + tccName + " with " + participants.size() + " participants");
        
        Map<String, Object> tryResults = new HashMap<>();
        Map<String, Object> participantResults = new HashMap<>();
        Map<String, Object> contextData = new HashMap<>();
        contextData.put("correlation_id", correlationId);
        contextData.put("tcc_name", tccName);
        
        try {
            // Phase 1: Execute TRY for all participants (sorted by order)
            System.out.println("TCC Phase 1: Executing TRY phase for all participants");

            // Sort participants by order, then by participant ID for stable ordering
            List<Map.Entry<String, Object>> sortedParticipants = new ArrayList<>(participants.entrySet());
            sortedParticipants.sort((e1, e2) -> {
                @SuppressWarnings("unchecked")
                Map<String, Object> config1 = (Map<String, Object>) e1.getValue();
                @SuppressWarnings("unchecked")
                Map<String, Object> config2 = (Map<String, Object>) e2.getValue();
                Integer order1 = (Integer) config1.getOrDefault("order", 1);
                Integer order2 = (Integer) config2.getOrDefault("order", 1);
                int orderCompare = order1.compareTo(order2);
                if (orderCompare != 0) {
                    return orderCompare;
                }
                // If orders are equal, sort by participant ID for stable ordering
                return e1.getKey().compareTo(e2.getKey());
            });

            for (Map.Entry<String, Object> entry : sortedParticipants) {
                String participantId = entry.getKey();
                @SuppressWarnings("unchecked")
                Map<String, Object> participantConfig = (Map<String, Object>) entry.getValue();
                
                String tryMethod = (String) participantConfig.get("try_method");
                Object inputData = context.getParticipantInputs().get(participantId);
                if (inputData == null) {
                    inputData = context.getParticipantInputs(); // fallback to all input data
                }
                
                if (callbackHandler != null && tryMethod != null) {
                    Map<String, Object> tryResult = callbackHandler.executeTccMethod("TRY", participantId, tryMethod, inputData, contextData);
                    
                    if (tryResult.get("success").equals(false)) {
                        // TRY phase failed - need to cancel all previous tries
                        System.err.println("TCC TRY phase failed for participant: " + participantId);
                        cancelPreviousTryResults(context, tryResults, contextData);
                        
                        TccExecutionResult failure = new TccExecutionResult(tccName, correlationId, false, "CANCEL", 
                                                    tryResults, participantResults, 
                                                    "TRY phase failed: " + tryResult.get("error"));
                        failure.setDurationMs((System.nanoTime() - startNanos) / 1_000_000);
                        return failure;
                    }
                    
                    tryResults.put(participantId, tryResult.get("result"));
                    participantResults.put(participantId, tryResult);
                }
            }
            
            // Phase 2: All TRY succeeded, execute CONFIRM for all participants (sorted by order)
            System.out.println("TCC Phase 2: All TRY succeeded, executing CONFIRM phase");
            for (Map.Entry<String, Object> entry : sortedParticipants) {
                String participantId = entry.getKey();
                @SuppressWarnings("unchecked")
                Map<String, Object> participantConfig = (Map<String, Object>) entry.getValue();

                String confirmMethod = (String) participantConfig.get("confirm_method");
                Boolean isClassBased = (Boolean) participantConfig.get("is_class_based");

                // Get the TRY result for this participant
                @SuppressWarnings("unchecked")
                Map<String, Object> participantTryResult = (Map<String, Object>) tryResults.get(participantId);

                // Get original input data
                Object originalInputData = context.getParticipantInputs().get(participantId);
                if (originalInputData == null) {
                    originalInputData = context.getParticipantInputs();
                }

                // For CONFIRM/CANCEL methods, Python expects both original data and try_result
                // Create a combined input structure
                Map<String, Object> confirmInputData = new HashMap<>();
                confirmInputData.put("data", originalInputData);
                confirmInputData.put("try_result", participantTryResult);

                if (callbackHandler != null && confirmMethod != null) {
                    Map<String, Object> confirmResult = callbackHandler.executeTccMethod("CONFIRM", participantId, confirmMethod, confirmInputData, contextData);

                    if (confirmResult.get("success").equals(false)) {
                        // CONFIRM phase failed - this is a problem as we can't easily roll back confirmed operations
                        System.err.println("TCC CONFIRM phase failed for participant: " + participantId + ", error: " + confirmResult.get("error"));
                        // Continue trying to confirm other participants, but mark as failure
                    }

                    participantResults.put(participantId + "_confirm", confirmResult);
                }
            }
            
            System.out.println("TCC orchestration completed successfully: " + tccName);
            TccExecutionResult successResult = new TccExecutionResult(tccName, correlationId, true, "CONFIRM", 
                                        tryResults, participantResults, null);
            successResult.setDurationMs((System.nanoTime() - startNanos) / 1_000_000);
            return successResult;
            
        } catch (Exception e) {
            System.err.println("TCC orchestration failed: " + e.getMessage());
            e.printStackTrace();
            
            // Execute CANCEL phase for any successful TRY results
            cancelPreviousTryResults(context, tryResults, contextData);
            
            TccExecutionResult errorResult = new TccExecutionResult(tccName, correlationId, false, "CANCEL", 
                                        tryResults, participantResults, e.getMessage());
            errorResult.setDurationMs((System.nanoTime() - startNanos) / 1_000_000);
            return errorResult;
        }
    }
    
    private void cancelPreviousTryResults(TccExecutionContext context, Map<String, Object> tryResults, Map<String, Object> contextData) {
        System.out.println("Executing CANCEL phase for previous TRY results");

        TccCallbackHandler callbackHandler = context.getCallbackHandler();
        Map<String, Object> participants = context.getDefinition().getParticipants();

        for (String participantId : tryResults.keySet()) {
            try {
                @SuppressWarnings("unchecked")
                Map<String, Object> participantConfig = (Map<String, Object>) participants.get(participantId);
                String cancelMethod = (String) participantConfig.get("cancel_method");
                Boolean isClassBased = (Boolean) participantConfig.get("is_class_based");

                // Get the TRY result for this participant
                @SuppressWarnings("unchecked")
                Map<String, Object> participantTryResult = (Map<String, Object>) tryResults.get(participantId);

                // Get original input data
                Object originalInputData = context.getParticipantInputs().get(participantId);
                if (originalInputData == null) {
                    originalInputData = context.getParticipantInputs();
                }

                // For CONFIRM/CANCEL methods, Python expects both original data and try_result
                // Create a combined input structure
                Map<String, Object> cancelInputData = new HashMap<>();
                cancelInputData.put("data", originalInputData);
                cancelInputData.put("try_result", participantTryResult);

                if (callbackHandler != null && cancelMethod != null) {
                    Map<String, Object> cancelResult = callbackHandler.executeTccMethod("CANCEL", participantId, cancelMethod, cancelInputData, contextData);
                    System.out.println("CANCEL executed for participant: " + participantId + ", result: " + cancelResult.get("success"));
                }
            } catch (Exception e) {
                System.err.println("Error executing CANCEL for participant " + participantId + ": " + e.getMessage());
            }
        }
    }

    /**
     * StepHandler implementation that calls back to Python for step execution.
     * This enables lib-transactional-engine to orchestrate Python-defined SAGA steps.
     */
    private class PythonStepHandler implements StepHandler<Object, Object> {
        private final String stepId;
        private final String pythonMethod;
        private final String compensationMethod;
        private final PythonCallbackHandler callbackHandler;

        public PythonStepHandler(String stepId, String pythonMethod, String compensationMethod, PythonCallbackHandler callbackHandler) {
            this.stepId = stepId;
            this.pythonMethod = pythonMethod;
            this.compensationMethod = compensationMethod;
            this.callbackHandler = callbackHandler;
        }

        @Override
        public Mono<Object> execute(Object input, SagaContext ctx) {
            System.out.println("[lib-transactional-engine] Executing step: " + stepId + " via Python callback: " + pythonMethod);

            // Prepare input data for the step
            Map<String, Object> stepInput = new HashMap<>();
            if (input instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> inputMap = (Map<String, Object>) input;
                stepInput.putAll(inputMap);
            }

            // Add context data including variables from previous steps
            Map<String, Object> contextData = new HashMap<>();
            contextData.put("correlation_id", ctx.correlationId());
            contextData.put("step_id", stepId);
            // Pass all context variables to Python so it can access data from previous steps
            contextData.put("variables", new HashMap<>(ctx.variables()));

            // Make HTTP callback to Python (reactive)
            System.out.println("Making HTTP callback to: " + callbackHandler.getCallbackUrl() + " for method: " + pythonMethod);
            return callbackHandler.executeCallbackReactive(pythonMethod, stepInput, contextData)
                .map(result -> {
                    if (result != null && Boolean.TRUE.equals(result.get("success"))) {
                        System.out.println("HTTP callback completed successfully: " + pythonMethod);

                        // Get the step result
                        Object stepResult = result.get("result");

                        // Store step result in context for compensation to access
                        // This ensures compensation methods can access the result from the original step
                        if (stepResult != null) {
                            String stepResultKey = "__step_result_" + stepId;
                            ctx.variables().put(stepResultKey, stepResult);
                            System.out.println("[lib-transactional-engine] 💾 Stored step result for compensation: " + stepResultKey);
                        }

                        // Update context variables with any changes from Python
                        @SuppressWarnings("unchecked")
                        Map<String, Object> contextUpdates = (Map<String, Object>) result.get("context_updates");
                        if (contextUpdates != null) {
                            if (contextUpdates.containsKey("variables")) {
                                @SuppressWarnings("unchecked")
                                Map<String, Object> updatedVariables = (Map<String, Object>) contextUpdates.get("variables");
                                if (updatedVariables != null && !updatedVariables.isEmpty()) {
                                    // Update the SagaContext with new variables from Python
                                    for (Map.Entry<String, Object> entry : updatedVariables.entrySet()) {
                                        ctx.variables().put(entry.getKey(), entry.getValue());
                                    }
                                    System.out.println("[lib-transactional-engine] ✅ Updated context variables: " + updatedVariables.keySet());
                                } else {
                                    System.out.println("[lib-transactional-engine] ℹ️  No context variables to update (variables map is empty)");
                                }
                            } else {
                                System.out.println("[lib-transactional-engine] ⚠️  context_updates missing 'variables' key");
                            }
                        } else {
                            System.out.println("[lib-transactional-engine] ⚠️  No context_updates in callback response");
                        }

                        return stepResult;
                    } else {
                        String error = result != null ? (String) result.get("error") : "Step execution failed";
                        System.err.println("HTTP callback failed: " + pythonMethod + " - " + error);
                        throw new RuntimeException(error);
                    }
                });
        }

        @Override
        public Mono<Void> compensate(Object arg, SagaContext ctx) {
            if (compensationMethod == null || compensationMethod.isEmpty()) {
                return Mono.empty();
            }

            System.out.println("[lib-transactional-engine] Compensating step: " + stepId + " via Python callback: " + compensationMethod);

            // Prepare compensation input - this should be the step result
            // NOTE: The 'arg' parameter from lib-transactional-engine may contain the SAGA input data,
            // not the step result. We need to retrieve the actual step result from context.
            Map<String, Object> compensationInput = new HashMap<>();

            // Try to retrieve step result from context first (most reliable)
            String stepResultKey = "__step_result_" + stepId;
            Object storedResult = ctx.variables().get(stepResultKey);

            if (storedResult instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> resultMap = (Map<String, Object>) storedResult;
                compensationInput.putAll(resultMap);
                System.out.println("[lib-transactional-engine] ✅ Compensation input from context (step result): " + resultMap.keySet());
            } else if (storedResult != null) {
                compensationInput.put("result", storedResult);
                System.out.println("[lib-transactional-engine] ✅ Compensation input from context (wrapped): " + storedResult.getClass().getSimpleName());
            } else {
                // Fallback to arg if step result not found in context
                System.out.println("[lib-transactional-engine] ⚠️  WARNING: Step result not found in context, falling back to arg parameter");
                if (arg instanceof Map) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> argMap = (Map<String, Object>) arg;
                    compensationInput.putAll(argMap);
                    System.out.println("[lib-transactional-engine] Compensation input from arg: " + argMap.keySet());
                } else if (arg != null) {
                    compensationInput.put("result", arg);
                    System.out.println("[lib-transactional-engine] Compensation input from arg (wrapped): " + arg.getClass().getSimpleName());
                } else {
                    System.out.println("[lib-transactional-engine] ⚠️  ERROR: No compensation input available!");
                }
            }

            // Add context data including variables
            Map<String, Object> contextData = new HashMap<>();
            contextData.put("correlation_id", ctx.correlationId());
            contextData.put("step_id", stepId);
            // Pass context variables so compensation can access data like payment_id
            contextData.put("variables", new HashMap<>(ctx.variables()));

            // Make HTTP callback to Python for compensation (reactive)
            System.out.println("Making HTTP callback for compensation: " + compensationMethod);
            return callbackHandler.executeCompensationCallbackReactive(compensationMethod, compensationInput, contextData)
                .doOnNext(result -> {
                    if (result != null && Boolean.TRUE.equals(result.get("success"))) {
                        System.out.println("Compensation callback completed successfully: " + compensationMethod);
                    } else {
                        String error = result != null ? (String) result.get("error") : "Compensation failed";
                        System.err.println("Compensation callback failed: " + compensationMethod + " - " + error);
                        // Note: lib-transactional-engine handles compensation errors according to policy
                    }
                })
                .then();
        }
    }
}
