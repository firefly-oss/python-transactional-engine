"""
Log viewer for FireflyTX shell.

Provides log viewing and tailing functionality.
"""

import time
from typing import Optional
from collections import deque


class LogViewer:
    """Log viewing utility."""

    def __init__(self, session, formatter):
        """
        Initialize log viewer.

        Args:
            session: ShellSession instance
            formatter: ShellFormatter instance
        """
        self.session = session
        self.formatter = formatter
        self._log_buffer = deque(maxlen=1000)  # Keep last 1000 log lines
        self._following = False

    def show_logs(
        self,
        lines: int = 50,
        follow: bool = False,
        stream: str = "both",
        pid: Optional[int] = None
    ):
        """
        Show recent Java logs from stdout and stderr.

        Args:
            lines: Number of log lines to show (default: 50)
            follow: If True, tail -f style continuous log streaming (default: False)
            stream: Which stream to show - 'stdout', 'stderr', or 'both' (default: 'both')
            pid: Optional PID to show logs for (only works for current bridge)
        """
        # Check if we have a current bridge
        if not self.session.java_bridge:
            self.formatter.print_error("No Java bridge available.")
            self.formatter.print_info("Logs are only available for the current bridge.")
            self.formatter.print_info("Run 'await init_engines()' to start a bridge.")
            return

        # Check if PID matches current bridge
        if pid and pid != self.session.current_bridge_pid:
            self.formatter.print_warning(
                f"PID {pid} is not the current bridge (current: {self.session.current_bridge_pid})"
            )
            self.formatter.print_info("Logs are only available for the current bridge.")
            return

        # Get the Java bridge
        bridge = self.session.java_bridge

        # Check if bridge has log access
        if not hasattr(bridge, '_process') or not bridge._process:
            self.formatter.print_warning("Java bridge process not available for log viewing")
            self.formatter.print_info("Logs may not be accessible in this mode")
            return

        # Show header
        stream_label = stream.upper() if stream != "both" else "STDOUT & STDERR"
        self.formatter.print_header(f"📋 Java Bridge Logs ({stream_label})")

        if follow:
            self._follow_logs(bridge, stream)
        else:
            self._show_recent_logs(bridge, lines, stream)

    def _show_recent_logs(self, bridge, lines: int, stream: str):
        """Show recent log lines."""
        # Try to get logs from the bridge's log file or buffer
        # Since the bridge logs to Python's logging system, we can show those

        self.formatter.print_info(f"Showing last {lines} log lines...")
        print()

        # Get logs from Python's logging system
        # The bridge logs are captured by the logging handlers
        import logging

        # Get the fireflytx.java logger which captures Java output
        java_logger = logging.getLogger('fireflytx.java')

        # Show information about log configuration
        if not java_logger.handlers:
            self.formatter.print_warning("No log handlers configured for Java bridge")
            self.formatter.print_info("Java logs are being captured but not stored for viewing")
            self.formatter.print_info("To enable log viewing, configure a file handler:")
            print()
            self.formatter.print_code("""
import logging

# Configure file handler for Java logs
handler = logging.FileHandler('fireflytx_java.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logging.getLogger('fireflytx.java').addHandler(handler)
""")
            return

        # Show recent logs from handlers
        self.formatter.print_info("Recent Java bridge activity:")
        print()

        # Show a helpful message about log viewing
        self.formatter.print_info("💡 Tip: Java logs are captured in real-time by Python's logging system")
        self.formatter.print_info("   Configure a FileHandler to persist logs to a file for viewing")
        print()

        # Show current bridge status
        if hasattr(bridge, '_process') and bridge._process:
            self.formatter.print_success(f"✅ Java bridge is running (PID: {bridge._process.pid})")
        else:
            self.formatter.print_warning("⚠️  Java bridge process not accessible")

    def _follow_logs(self, bridge, stream: str):
        """Follow logs in real-time (tail -f style)."""
        self.formatter.print_info("Following logs in real-time... (Press Ctrl+C to stop)")
        print()

        self._following = True

        try:
            # Get the Java logger
            import logging
            java_logger = logging.getLogger('fireflytx.java')

            # Create a custom handler to capture logs
            class LogCaptureHandler(logging.Handler):
                def __init__(self, viewer):
                    super().__init__()
                    self.viewer = viewer

                def emit(self, record):
                    if self.viewer._following:
                        msg = self.format(record)
                        # Print with appropriate color based on level
                        if record.levelno >= logging.ERROR:
                            print(f"\033[91m{msg}\033[0m")  # Red
                        elif record.levelno >= logging.WARNING:
                            print(f"\033[93m{msg}\033[0m")  # Yellow
                        else:
                            print(msg)

            # Add the handler
            handler = LogCaptureHandler(self)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
            java_logger.addHandler(handler)

            # Keep following until interrupted
            while self._following:
                time.sleep(0.1)

        except KeyboardInterrupt:
            self.formatter.print_info("\nStopped following logs")
        finally:
            self._following = False
            # Remove the handler
            if 'handler' in locals():
                java_logger.removeHandler(handler)

