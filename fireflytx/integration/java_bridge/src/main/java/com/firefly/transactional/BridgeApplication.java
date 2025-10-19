package com.firefly.transactional;

import com.firefly.transactional.shared.config.TransactionalEnginePropertiesCompatibility;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;

/**
 * Spring Boot application for the Java subprocess bridge.
 *
 * This application initializes a Spring context that includes:
 * - lib-transactional-engine auto-configuration (SagaEngine, TccEngine, etc.)
 * - Event publisher auto-configuration (Kafka publishers if configured)
 * - Persistence auto-configuration (Redis if configured)
 *
 * The bridge receives configuration from Python via system properties (-D flags)
 * and uses Spring Boot's auto-configuration to wire everything together.
 *
 * IMPORTANT: This is a REACTIVE application using WebFlux, NOT Spring MVC.
 * The web server is disabled - we only need the reactive infrastructure.
 */
@SpringBootApplication
@ComponentScan(
    basePackages = "com.firefly.transactional",
    excludeFilters = @ComponentScan.Filter(
        type = FilterType.ASSIGNABLE_TYPE,
        classes = TransactionalEnginePropertiesCompatibility.class
    )
)
public class BridgeApplication {

    private static ApplicationContext applicationContext;
    private static JavaSubprocessBridge bridge;

    public static void main(String[] args) {
        if (args.length != 1) {
            System.err.println("Usage: BridgeApplication <temp_dir>");
            System.exit(1);
        }

        String tempDir = args[0];

        // Initialize Spring Boot application (REACTIVE, NO WEB SERVER)
        SpringApplication app = new SpringApplication(BridgeApplication.class);
        app.setWebApplicationType(WebApplicationType.NONE);  // Disable web server
        applicationContext = app.run(args);

        // Create and start the bridge
        bridge = new JavaSubprocessBridge(tempDir, applicationContext);

        System.out.println("Java subprocess bridge started in: " + tempDir);
        System.out.flush();

        // Start request processing loop
        bridge.startProcessing();
    }

    public static ApplicationContext getApplicationContext() {
        return applicationContext;
    }
}

