"""
Engine management commands for FireflyTX shell.

Handles initialization, shutdown, and status of SAGA and TCC engines.
"""

import traceback
from typing import TYPE_CHECKING

from fireflytx import SagaEngine, TccEngine
from fireflytx.integration.bridge import JavaSubprocessBridge

if TYPE_CHECKING:
    from ..core.shell import FireflyTXShell


class EngineCommands:
    """Engine management commands."""
    
    def __init__(self, shell: "FireflyTXShell"):
        """
        Initialize engine commands.
        
        Args:
            shell: FireflyTXShell instance
        """
        self.shell = shell
        self.session = shell.session
        self.context = shell.context
        self.formatter = shell.formatter
    
    async def init_engines(self):
        """Initialize SAGA and TCC engines."""
        if self.session.is_initialized:
            self.formatter.print_warning(
                "Engines already initialized. Use 'reset()' to reinitialize."
            )
            return
        
        self.formatter.print_info("Initializing FireflyTX engines...")
        
        try:
            # Create shared Java bridge
            self.formatter.print_info("Creating shared Java bridge...")
            self.session.java_bridge = JavaSubprocessBridge()
            self.formatter.print_success("Java bridge created")
            
            # Initialize SAGA engine with shared bridge
            self.formatter.print_info("Creating SAGA engine...")
            self.session.saga_engine = SagaEngine(java_bridge=self.session.java_bridge)
            await self.session.saga_engine.initialize()
            self.formatter.print_success("SAGA engine initialized")
            
            # Initialize TCC engine with shared bridge (uses start() not initialize())
            self.formatter.print_info("Creating TCC engine...")
            self.session.tcc_engine = TccEngine(java_bridge=self.session.java_bridge)
            self.session.tcc_engine.start()
            self.formatter.print_success("TCC engine initialized")
            
            # Mark as initialized
            self.session.mark_initialized()
            
            # Update context namespace
            self.context.update_engines()
            
            self.formatter.print_success("All engines initialized successfully!")
            self.formatter.print_info(
                "Use 'saga_engine' and 'tcc_engine' to interact with engines"
            )
            self.formatter.print_info("Try: examples() to see code examples")
            
        except Exception as e:
            self.formatter.print_error(f"Failed to initialize engines: {e}")
            traceback.print_exc()
            raise
    
    async def shutdown_engines(self):
        """Shutdown SAGA and TCC engines."""
        if not self.session.is_initialized:
            self.formatter.print_warning("Engines not initialized")
            return
        
        self.formatter.print_info("Shutting down FireflyTX engines...")
        
        try:
            # Shutdown SAGA engine
            if self.session.saga_engine:
                self.formatter.print_info("Shutting down SAGA engine...")
                await self.session.saga_engine.shutdown()
                self.session.saga_engine = None
                self.formatter.print_success("SAGA engine shutdown")
            
            # Shutdown TCC engine
            if self.session.tcc_engine:
                self.formatter.print_info("Shutting down TCC engine...")
                self.session.tcc_engine.stop()
                self.session.tcc_engine = None
                self.formatter.print_success("TCC engine shutdown")
            
            # Shutdown Java bridge
            if self.session.java_bridge:
                self.formatter.print_info("Shutting down Java bridge...")
                self.session.java_bridge.shutdown()
                self.session.java_bridge = None
                self.formatter.print_success("Java bridge shutdown")
            
            # Mark as uninitialized
            self.session.mark_uninitialized()
            
            # Update context namespace
            self.context.update_engines()
            
            self.formatter.print_success("All engines shutdown successfully")
            
        except Exception as e:
            self.formatter.print_error(f"Error during shutdown: {e}")
            traceback.print_exc()
    
    async def reset_engines(self):
        """Reset engines by shutting down and reinitializing."""
        self.formatter.print_info("Resetting engines...")
        self.session.mark_uninitialized()
        await self.shutdown_engines()
        await self.init_engines()
    
    def show_status(self):
        """Show current status of engines and Java bridge."""
        from fireflytx import __version__
        
        status_data = {
            "Version": __version__,
            "SAGA Engine": "✅ Initialized" if self.session.saga_engine else "⭕ Not initialized",
            "TCC Engine": "✅ Initialized" if self.session.tcc_engine else "⭕ Not initialized",
        }
        
        # Show current bridge status
        if self.session.java_bridge:
            status_data["Java Bridge"] = "✅ Connected (Current)"
            if self.session.current_bridge_pid:
                status_data["  └─ PID"] = str(self.session.current_bridge_pid)
        else:
            status_data["Java Bridge"] = "⭕ Not connected"
        
        # Show connected bridge status
        if self.session.has_connected_bridge:
            status_data["Connected Bridge"] = "🔗 Connected (External)"
            status_data["  └─ PID"] = str(self.session.connected_bridge_pid)
        
        # Show session info
        uptime_mins = int(self.session.uptime / 60)
        status_data["Session Uptime"] = f"{uptime_mins} minutes"
        status_data["Commands Executed"] = str(self.session.execution_count)
        
        # Format as table
        rows = [[k, v] for k, v in status_data.items()]
        self.formatter.print_table(
            "🔧 FireflyTX Status",
            ["Property", "Value"],
            rows,
        )
    
    def show_config(self):
        """Show current engine configuration."""
        config_data = {}

        if self.session.saga_engine:
            saga_config = {}
            saga_config["Initialized"] = "✅"

            # Extract configuration from SAGA engine
            if hasattr(self.session.saga_engine, 'config') and self.session.saga_engine.config:
                config = self.session.saga_engine.config
                saga_config["Max Concurrent"] = getattr(config, 'max_concurrent_executions', 'N/A')
                saga_config["Default Timeout"] = f"{getattr(config, 'default_timeout_ms', 'N/A')}ms"
                saga_config["Monitoring"] = "✅" if getattr(config, 'enable_monitoring', False) else "⭕"

                # Persistence config
                if hasattr(config, 'persistence') and config.persistence:
                    saga_config["Persistence Type"] = config.persistence.type
                    if config.persistence.type != "memory":
                        saga_config["Persistence Connection"] = config.persistence.connection_string or "N/A"

                # JVM config
                if hasattr(config, 'jvm') and config.jvm:
                    saga_config["JVM Heap"] = config.jvm.heap_size
                    saga_config["GC Algorithm"] = config.jvm.gc_algorithm

                # Retry config
                if hasattr(config, 'retry_config') and config.retry_config:
                    saga_config["Retry Attempts"] = config.retry_config.max_attempts
                    saga_config["Retry Backoff"] = f"{config.retry_config.initial_backoff_ms}ms"

            config_data["SAGA Engine"] = saga_config
        else:
            config_data["SAGA Engine"] = {"Initialized": "⭕"}

        if self.session.tcc_engine:
            tcc_config = {}
            tcc_config["Initialized"] = "✅"

            # Extract configuration from TCC engine
            if hasattr(self.session.tcc_engine, 'config') and self.session.tcc_engine.config:
                config = self.session.tcc_engine.config
                tcc_config["Max Concurrent"] = getattr(config, 'max_concurrent_executions', 'N/A')
                tcc_config["Default Timeout"] = f"{getattr(config, 'default_timeout_ms', 'N/A')}ms"
                tcc_config["Monitoring"] = "✅" if getattr(config, 'enable_monitoring', False) else "⭕"

                # Persistence config
                if hasattr(config, 'persistence') and config.persistence:
                    tcc_config["Persistence Type"] = config.persistence.type
                    if config.persistence.type != "memory":
                        tcc_config["Persistence Connection"] = config.persistence.connection_string or "N/A"

                # JVM config
                if hasattr(config, 'jvm') and config.jvm:
                    tcc_config["JVM Heap"] = config.jvm.heap_size
                    tcc_config["GC Algorithm"] = config.jvm.gc_algorithm
            else:
                # Fallback to direct attributes
                tcc_config["Timeout"] = f"{getattr(self.session.tcc_engine, 'timeout_ms', 'N/A')}ms"
                tcc_config["Monitoring"] = "✅" if getattr(self.session.tcc_engine, 'enable_monitoring', False) else "⭕"

            config_data["TCC Engine"] = tcc_config
        else:
            config_data["TCC Engine"] = {"Initialized": "⭕"}

        self.formatter.print_tree("⚙️ Engine Configuration", config_data)

