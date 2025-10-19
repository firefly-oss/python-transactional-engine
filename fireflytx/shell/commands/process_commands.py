"""
Process management commands for FireflyTX shell.

Handles Java bridge process management, monitoring, and log viewing.
"""

import os
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Optional, List, Dict, Any

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

if TYPE_CHECKING:
    from ..core.shell import FireflyTXShell


class ProcessCommands:
    """Process management commands."""
    
    def __init__(self, shell: "FireflyTXShell"):
        """
        Initialize process commands.
        
        Args:
            shell: FireflyTXShell instance
        """
        self.shell = shell
        self.session = shell.session
        self.formatter = shell.formatter
    
    def list_java_bridges(self) -> List[Dict[str, Any]]:
        """
        List all running Java bridge processes on the system.
        
        Returns:
            List of bridge information dictionaries
        """
        if not PSUTIL_AVAILABLE:
            self.formatter.print_error("psutil not available. Install with: pip install psutil")
            return []
        
        bridges = []
        temp_base = tempfile.gettempdir()
        
        # Find all Java processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'memory_info']):
            try:
                if proc.info['name'] and 'java' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('fireflytx' in str(arg).lower() or 'BridgeApplication' in str(arg) for arg in cmdline):
                        # This is a FireflyTX Java bridge

                        # Extract temp directory from command line
                        # The temp_dir is passed as the last argument to BridgeApplication
                        temp_dir = None
                        for i, arg in enumerate(cmdline):
                            if 'BridgeApplication' in str(arg) and i + 1 < len(cmdline):
                                # Next argument is the temp_dir
                                temp_dir = cmdline[i + 1]
                                break
                        
                        # Calculate uptime
                        create_time = proc.info.get('create_time', 0)
                        uptime_seconds = time.time() - create_time
                        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
                        
                        # Get memory usage
                        memory_info = proc.info.get('memory_info')
                        memory_mb = memory_info.rss / (1024 * 1024) if memory_info else 0
                        
                        # Determine connection status
                        lib_version = "unknown"
                        connection_status = "External"
                        is_current = False
                        
                        if temp_dir and self.session.java_bridge:
                            is_current = temp_dir == self.session.java_bridge._temp_dir
                        
                        # If this is the current bridge, get lib version
                        if is_current and self.session.java_bridge:
                            try:
                                lib_version = self.session.java_bridge.get_lib_transactional_version() or "unknown"
                            except:
                                lib_version = "unknown"
                        
                        if is_current:
                            connection_status = "Current"
                        elif self.session.has_connected_bridge and proc.info['pid'] == self.session.connected_bridge_pid:
                            connection_status = "Connected"
                        
                        bridges.append({
                            'pid': proc.info['pid'],
                            'temp_dir': temp_dir or "unknown",
                            'uptime': uptime_str,
                            'uptime_seconds': uptime_seconds,
                            'memory_mb': memory_mb,
                            'lib_version': lib_version,
                            'connection_status': connection_status,
                            'is_current': is_current
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if not bridges:
            self.formatter.print_info("No Java bridge processes found")
            return []
        
        # Sort by uptime (oldest first)
        bridges.sort(key=lambda x: x['uptime_seconds'], reverse=True)
        
        # Format as table
        rows = []
        for bridge in bridges:
            rows.append([
                str(bridge['pid']),
                bridge['connection_status'],
                bridge['uptime'],
                f"{bridge['memory_mb']:.1f} MB",
                bridge['lib_version'],
                bridge['temp_dir'][:40] + "..." if len(bridge['temp_dir']) > 40 else bridge['temp_dir'],
            ])
        
        self.formatter.print_table(
            "🌉 Running Java Bridge Processes",
            ["PID", "Status", "Uptime", "Memory", "Lib Version", "Temp Dir"],
            rows,
            show_lines=True,
        )
        
        # Show helpful tips
        if bridges:
            self.formatter.print_info("Use 'connect_bridge(pid)' to connect to a bridge")
            self.formatter.print_info("Use 'java_info(pid)' to view detailed information")
            self.formatter.print_info("Use 'kill_bridge(pid)' to terminate a bridge")
        
        return bridges
    
    def connect_to_bridge(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        Connect to an existing Java bridge process.
        
        Args:
            pid: Process ID of the bridge
            
        Returns:
            Bridge information dictionary or None
        """
        if not PSUTIL_AVAILABLE:
            self.formatter.print_error("psutil not available. Install with: pip install psutil")
            return None
        
        try:
            proc = psutil.Process(pid)
            
            # Verify it's a Java process
            if 'java' not in proc.name().lower():
                self.formatter.print_error(f"PID {pid} is not a Java process")
                return None
            
            # Extract temp directory
            cmdline = proc.cmdline()
            temp_dir = None
            for i, arg in enumerate(cmdline):
                if 'BridgeApplication' in str(arg) and i + 1 < len(cmdline):
                    # Next argument is the temp_dir
                    temp_dir = cmdline[i + 1]
                    break
            
            # Calculate uptime
            create_time = proc.create_time()
            uptime_seconds = time.time() - create_time
            uptime_str = str(timedelta(seconds=int(uptime_seconds)))
            
            # Get memory usage
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            # Store connection info
            bridge_info = {
                'pid': pid,
                'temp_dir': temp_dir,
                'uptime': uptime_str,
                'memory_mb': memory_mb,
            }
            
            self.session.set_connected_bridge(bridge_info)
            
            # Display connection info
            info_data = {
                "PID": str(pid),
                "Temp Dir": temp_dir or "unknown",
                "Status": "✅ Running" if proc.is_running() else "⭕ Not running",
                "Uptime": uptime_str,
                "Memory": f"{memory_mb:.1f} MB",
            }
            
            rows = [[k, v] for k, v in info_data.items()]
            self.formatter.print_table(
                "🔗 Connected to Java Bridge",
                ["Property", "Value"],
                rows,
            )
            
            self.formatter.print_info("Connected! You can now use:")
            self.formatter.print_info("  • java_info() - Show detailed bridge information")
            self.formatter.print_info("  • java_info(pid) - Show info for any bridge PID")
            self.formatter.print_warning("Note: Logs are only available for the current bridge")
            self.formatter.print_info("  • To view logs, start your own bridge with 'await init_engines()'")
            
            return bridge_info
            
        except psutil.NoSuchProcess:
            self.formatter.print_error(f"No process found with PID {pid}")
            return None
        except psutil.AccessDenied:
            self.formatter.print_error(f"Access denied to process {pid}")
            return None
        except Exception as e:
            self.formatter.print_error(f"Error connecting to bridge: {e}")
            return None

    def show_java_info(self, pid: Optional[int] = None):
        """
        Show Java subprocess information.

        Args:
            pid: Optional PID to show info for
        """
        if not PSUTIL_AVAILABLE:
            self.formatter.print_error("psutil not available. Install with: pip install psutil")
            return

        # Determine which bridge to show info for
        target_pid = None
        target_bridge = None
        is_current = False

        if pid:
            # Show info for specific PID
            target_pid = pid
        elif self.session.java_bridge and self.session.current_bridge_pid:
            # Use current bridge
            target_pid = self.session.current_bridge_pid
            target_bridge = self.session.java_bridge
            is_current = True
        elif self.session.has_connected_bridge:
            # Use connected bridge
            target_pid = self.session.connected_bridge_pid
        else:
            self.formatter.print_error("No Java bridge available.")
            self.formatter.print_info("Run 'await init_engines()' to start a new bridge")
            self.formatter.print_info("Or use 'connect_bridge(pid)' to connect to an existing bridge")
            self.formatter.print_info("Or use 'list_bridges()' to see all running bridges")
            return

        try:
            proc = psutil.Process(target_pid)

            # Get process info
            create_time = proc.create_time()
            uptime_seconds = time.time() - create_time
            uptime_str = str(timedelta(seconds=int(uptime_seconds)))

            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            cpu_percent = proc.cpu_percent(interval=0.1)

            # Get temp directory
            temp_dir = None
            cmdline = proc.cmdline()
            for i, arg in enumerate(cmdline):
                if 'BridgeApplication' in str(arg) and i + 1 < len(cmdline):
                    # Next argument is the temp_dir
                    temp_dir = cmdline[i + 1]
                    break

            # Build info data
            info_data = {
                "PID": str(target_pid),
                "Status": "✅ Running" if proc.is_running() else "⭕ Not running",
                "Connection": "Current Bridge" if is_current else "Connected Bridge" if self.session.has_connected_bridge else "External",
                "Uptime": uptime_str,
                "Memory": f"{memory_mb:.1f} MB",
                "CPU": f"{cpu_percent:.1f}%",
                "Temp Dir": temp_dir or "unknown",
            }

            # Show JAR path if available from current bridge
            if target_bridge and target_bridge._jar_path:
                info_data["JAR Path"] = str(target_bridge._jar_path)

            # Try to get lib version if this is current bridge
            if target_bridge:
                try:
                    lib_version = target_bridge.get_lib_transactional_version()
                    if lib_version:
                        info_data["Lib Version"] = lib_version
                except:
                    pass

            # Format as table
            rows = [[k, v] for k, v in info_data.items()]
            self.formatter.print_table(
                "☕ Java Subprocess Information",
                ["Property", "Value"],
                rows,
            )

        except psutil.NoSuchProcess:
            self.formatter.print_error(f"No process found with PID {target_pid}")
        except psutil.AccessDenied:
            self.formatter.print_error(f"Access denied to process {target_pid}")
        except Exception as e:
            self.formatter.print_error(f"Error getting Java info: {e}")

    def kill_bridge_process(self, pid: int, force: bool = False) -> bool:
        """
        Terminate a Java bridge process.

        Args:
            pid: Process ID to kill
            force: If True, use SIGKILL instead of SIGTERM

        Returns:
            True if successful, False otherwise
        """
        if not PSUTIL_AVAILABLE:
            self.formatter.print_error("psutil not available. Install with: pip install psutil")
            return False

        try:
            proc = psutil.Process(pid)

            # Verify it's a Java process
            if 'java' not in proc.name().lower():
                self.formatter.print_error(f"PID {pid} is not a Java process")
                return False

            # Warn if trying to kill current bridge
            if self.session.current_bridge_pid == pid:
                self.formatter.print_warning(
                    "This is your current bridge! Consider using 'await shutdown_engines()' instead"
                )
                confirm = input("Are you sure you want to kill it? (yes/no): ").strip().lower()
                if confirm != 'yes':
                    self.formatter.print_info("Cancelled")
                    return False

            # Terminate the process
            if force:
                self.formatter.print_warning(f"Force killing Java bridge (PID {pid})...")
                proc.kill()  # SIGKILL
            else:
                self.formatter.print_info(f"Terminating Java bridge (PID {pid})...")
                proc.terminate()  # SIGTERM

            # Wait for process to exit
            try:
                proc.wait(timeout=5)
                self.formatter.print_success(f"Java bridge (PID {pid}) terminated successfully")

                # Clear connected bridge if it was the one we killed
                if self.session.connected_bridge_pid == pid:
                    self.session.clear_connected_bridge()

                return True
            except psutil.TimeoutExpired:
                self.formatter.print_warning("Process did not exit within 5 seconds")
                if not force:
                    self.formatter.print_info("Try kill_bridge(pid, force=True) to force kill")
                return False

        except psutil.NoSuchProcess:
            self.formatter.print_error(f"No process found with PID {pid}")
            return False
        except psutil.AccessDenied:
            self.formatter.print_error(f"Access denied to process {pid}")
            return False
        except Exception as e:
            self.formatter.print_error(f"Error killing process: {e}")
            return False

    def kill_bridge(self, pid: int = None, force: bool = False):
        """
        Kill a specific Java bridge process.

        Args:
            pid: Process ID to kill. If None, shows list of bridges to choose from.
            force: If True, use SIGKILL instead of SIGTERM

        Examples:
            kill_bridge(12345)           # Kill bridge with PID 12345
            kill_bridge(12345, force=True)  # Force kill bridge
            kill_bridge()                # Show list of bridges to kill
        """
        if pid is None:
            # Show list of bridges
            self.formatter.print_info("Available Java bridges:")
            self.list_java_bridges()
            self.formatter.print_info("\nUsage: kill_bridge(pid) or kill_bridge(pid, force=True)")
            return

        # Kill the specified bridge
        self.kill_bridge_process(pid, force=force)

    def kill_all_bridges(self, force: bool = False, skip_current: bool = False):
        """
        Kill all Java bridge processes.

        Args:
            force: If True, use SIGKILL instead of SIGTERM
            skip_current: If True, skip the current bridge without asking

        Examples:
            kill_all_bridges()                    # Kill all bridges (asks for confirmation on current)
            kill_all_bridges(force=True)          # Force kill all bridges
            kill_all_bridges(skip_current=True)   # Kill all except current bridge
        """
        if not PSUTIL_AVAILABLE:
            self.formatter.print_error("psutil not available. Install with: pip install psutil")
            return

        try:
            # Find all Java bridge processes
            bridges = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'java' in proc.info['name'].lower():
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline and any('BridgeApplication' in str(arg) for arg in cmdline):
                            bridges.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not bridges:
                self.formatter.print_info("No Java bridge processes found")
                return

            # Show what we found
            self.formatter.print_info(f"Found {len(bridges)} Java bridge process(es)")

            # Separate current bridge from others
            current_pid = self.session.current_bridge_pid
            other_bridges = [pid for pid in bridges if pid != current_pid]

            # Kill other bridges first
            killed_count = 0
            failed_count = 0

            for pid in other_bridges:
                self.formatter.print_info(f"Killing bridge PID {pid}...")
                if self.kill_bridge_process(pid, force=force):
                    killed_count += 1
                else:
                    failed_count += 1

            # Handle current bridge
            if current_pid in bridges:
                if skip_current:
                    self.formatter.print_info(f"Skipping current bridge (PID {current_pid})")
                else:
                    self.formatter.print_warning(f"\nBridge PID {current_pid} is your CURRENT bridge!")
                    self.formatter.print_warning("Killing it will terminate your engines and Java connection.")
                    confirm = input("Do you want to kill the current bridge? (yes/no): ").strip().lower()
                    if confirm == 'yes':
                        if self.kill_bridge_process(current_pid, force=force):
                            killed_count += 1
                        else:
                            failed_count += 1
                    else:
                        self.formatter.print_info("Skipped current bridge")

            # Summary
            self.formatter.print_success(f"\n✅ Killed {killed_count} bridge(s)")
            if failed_count > 0:
                self.formatter.print_warning(f"⚠️  Failed to kill {failed_count} bridge(s)")

        except Exception as e:
            self.formatter.print_error(f"Error killing bridges: {e}")

