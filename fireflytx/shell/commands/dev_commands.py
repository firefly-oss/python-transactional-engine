"""
Developer commands for FireflyTX shell.

Provides inspection, visualization, and debugging tools.
"""

import asyncio
import inspect
import time
from typing import TYPE_CHECKING, Any, Dict, Optional
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

if TYPE_CHECKING:
    from ..core.shell import FireflyTXShell


class DevCommands:
    """Developer tool commands."""

    def __init__(self, shell: "FireflyTXShell"):
        """
        Initialize developer commands.

        Args:
            shell: FireflyTXShell instance
        """
        self.shell = shell
        self.formatter = shell.formatter

    def inspect_saga(self, saga_class):
        """
        Inspect a SAGA class and show its structure.

        Args:
            saga_class: The SAGA class to inspect
        """
        self.formatter.print_header(f"🔍 Inspecting SAGA: {saga_class.__name__}")

        # Check if it's a SAGA class
        if not hasattr(saga_class, '_saga_config'):
            self.formatter.print_error("Not a SAGA class. Use @saga decorator.")
            return

        saga_config = saga_class._saga_config

        # Create tree structure
        tree = Tree(f"[bold cyan]SAGA: {saga_class.__name__}[/bold cyan]")

        # Add metadata
        meta_branch = tree.add("[yellow]Metadata[/yellow]")
        meta_branch.add(f"Name: {saga_config.name}")
        meta_branch.add(f"Layer Concurrency: {saga_config.layer_concurrency}")

        # Find all steps
        steps_branch = tree.add("[green]Steps[/green]")
        for step_id, step_config in saga_config.steps.items():
            step_node = steps_branch.add(f"[cyan]{step_id}[/cyan]")
            step_node.add(f"Retry: {step_config.retry}")
            step_node.add(f"Timeout: {step_config.timeout_ms}ms")
            step_node.add(f"Backoff: {step_config.backoff_ms}ms")

            if step_config.depends_on:
                deps = ", ".join(step_config.depends_on)
                step_node.add(f"Depends on: {deps}")

            # Check for compensation
            if step_config.compensate:
                step_node.add(f"[red]Compensation: {step_config.compensate}[/red]")
                step_node.add(f"[red]Compensation Critical: {step_config.compensation_critical}[/red]")

        # Show compensation methods
        if saga_config.compensation_methods:
            comp_branch = tree.add("[red]Compensation Methods[/red]")
            for step_id, comp_method in saga_config.compensation_methods.items():
                comp_branch.add(f"{step_id} → {comp_method}")

        self.formatter.console.print(tree)

        # Show source code preview
        try:
            source = inspect.getsource(saga_class)
            syntax = Syntax(source, "python", theme="solarized-dark", line_numbers=True)
            panel = Panel(syntax, title="[bold]Source Code[/bold]", border_style="blue")
            self.formatter.console.print(panel)
        except Exception as e:
            self.formatter.print_warning(f"Could not retrieve source: {e}")

    def inspect_tcc(self, tcc_class):
        """
        Inspect a TCC class and show its structure.

        Args:
            tcc_class: The TCC class to inspect
        """
        self.formatter.print_header(f"🔍 Inspecting TCC: {tcc_class.__name__}")

        # Check if it's a TCC class
        if not hasattr(tcc_class, '_tcc_config'):
            self.formatter.print_error("Not a TCC class. Use @tcc decorator.")
            return

        tcc_config = tcc_class._tcc_config

        # Create tree structure
        tree = Tree(f"[bold cyan]TCC: {tcc_class.__name__}[/bold cyan]")

        # Add metadata
        meta_branch = tree.add("[yellow]Metadata[/yellow]")
        meta_branch.add(f"Name: {tcc_config.name}")
        meta_branch.add(f"Timeout: {tcc_config.timeout_ms}ms")

        # Find all participants
        participants_branch = tree.add("[green]Participants[/green]")
        for participant_id, participant_config in tcc_config.participants.items():
            part_node = participants_branch.add(f"[cyan]{participant_id}[/cyan]")
            part_node.add(f"Order: {participant_config.order}")
            part_node.add(f"Timeout: {participant_config.timeout_ms}ms")

            # Show try/confirm/cancel methods
            if participant_config.try_method:
                part_node.add(f"[green]Try: {participant_config.try_method}[/green]")
            if participant_config.confirm_method:
                part_node.add(f"[blue]Confirm: {participant_config.confirm_method}[/blue]")
            if participant_config.cancel_method:
                part_node.add(f"[red]Cancel: {participant_config.cancel_method}[/red]")

        self.formatter.console.print(tree)

        # Show source code preview
        try:
            source = inspect.getsource(tcc_class)
            syntax = Syntax(source, "python", theme="solarized-dark", line_numbers=True)
            panel = Panel(syntax, title="[bold]Source Code[/bold]", border_style="blue")
            self.formatter.console.print(panel)
        except Exception as e:
            self.formatter.print_warning(f"Could not retrieve source: {e}")

    def visualize(self, workflow_class, output_format: str = "ascii"):
        """
        Visualize a SAGA or TCC workflow.

        Args:
            workflow_class: The workflow class to visualize
            output_format: Output format (ascii, mermaid, dot)
        """
        self.formatter.print_header(f"📊 Visualizing: {workflow_class.__name__}")

        # Determine workflow type
        is_saga = hasattr(workflow_class, '_saga_config')
        is_tcc = hasattr(workflow_class, '_tcc_config')

        if is_saga:
            self.visualize_saga(workflow_class, output_format)
        elif is_tcc:
            self.visualize_tcc(workflow_class, output_format)
        else:
            self.formatter.print_error("Not a SAGA or TCC class. Use @saga or @tcc decorator.")

    def visualize_saga(self, saga_class, output_format: str = "ascii"):
        """
        Visualize a SAGA workflow.

        Args:
            saga_class: The SAGA class to visualize
            output_format: Output format (ascii, mermaid, dot)
        """
        try:
            from fireflytx.visualization import SagaVisualizer, OutputFormat

            # Map format string to enum
            format_map = {
                "ascii": OutputFormat.ASCII,
                "mermaid": OutputFormat.MERMAID,
                "dot": OutputFormat.DOT,
            }

            fmt = format_map.get(output_format.lower(), OutputFormat.ASCII)

            visualizer = SagaVisualizer()
            output = visualizer.visualize_saga(saga_class, fmt)

            if fmt == OutputFormat.ASCII:
                self.formatter.console.print(output)
            else:
                syntax = Syntax(output, "mermaid" if fmt == OutputFormat.MERMAID else "dot",
                              theme="solarized-dark", line_numbers=True)
                panel = Panel(syntax, title=f"[bold]{output_format.upper()} Diagram[/bold]",
                            border_style="cyan")
                self.formatter.console.print(panel)

        except Exception as e:
            self.formatter.print_error(f"Visualization failed: {e}")
            import traceback
            traceback.print_exc()

    def visualize_tcc(self, tcc_class, output_format: str = "ascii"):
        """
        Visualize a TCC workflow.

        Args:
            tcc_class: The TCC class to visualize
            output_format: Output format (ascii, mermaid, dot)
        """
        try:
            from fireflytx.visualization import TccVisualizer, OutputFormat

            # Map format string to enum
            format_map = {
                "ascii": OutputFormat.ASCII,
                "mermaid": OutputFormat.MERMAID,
                "dot": OutputFormat.DOT,
            }

            fmt = format_map.get(output_format.lower(), OutputFormat.ASCII)

            visualizer = TccVisualizer()
            output = visualizer.visualize_tcc(tcc_class, fmt)

            if fmt == OutputFormat.ASCII:
                self.formatter.console.print(output)
            else:
                syntax = Syntax(output, "mermaid" if fmt == OutputFormat.MERMAID else "dot",
                              theme="solarized-dark", line_numbers=True)
                panel = Panel(syntax, title=f"[bold]{output_format.upper()} Diagram[/bold]",
                            border_style="cyan")
                self.formatter.console.print(panel)

        except Exception as e:
            self.formatter.print_error(f"Visualization failed: {e}")
            import traceback
            traceback.print_exc()

    async def benchmark(self, workflow_class, inputs: Dict[str, Any], iterations: int = 100):
        """
        Benchmark a SAGA or TCC workflow execution.

        Args:
            workflow_class: The workflow class to benchmark
            inputs: Input data for the workflow
            iterations: Number of iterations to run
        """
        self.formatter.print_header(f"⚡ Benchmarking: {workflow_class.__name__}")
        self.formatter.print_info(f"Running {iterations} iterations...")

        # Determine workflow type
        is_saga = hasattr(workflow_class, '_fireflytx_saga_metadata')
        is_tcc = hasattr(workflow_class, '_fireflytx_tcc_metadata')

        if not (is_saga or is_tcc):
            self.formatter.print_error("Not a SAGA or TCC class.")
            return

        # Check if engines are initialized
        if not self.shell.session.saga_engine and not self.shell.session.tcc_engine:
            self.formatter.print_error("Engines not initialized. Run 'await init_engines()' first.")
            return

        # Run benchmark
        times = []
        errors = 0

        try:
            for i in range(iterations):
                start = time.perf_counter()

                try:
                    if is_saga:
                        engine = self.shell.session.saga_engine
                        result = await engine.execute(workflow_class, inputs)
                    else:
                        engine = self.shell.session.tcc_engine
                        result = await engine.execute(workflow_class, inputs)

                    elapsed = time.perf_counter() - start
                    times.append(elapsed)

                except Exception as e:
                    errors += 1
                    elapsed = time.perf_counter() - start
                    times.append(elapsed)

                # Progress indicator
                if (i + 1) % 10 == 0:
                    self.formatter.print_info(f"Progress: {i + 1}/{iterations}")

        except KeyboardInterrupt:
            self.formatter.print_warning("Benchmark interrupted!")

        # Calculate statistics
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            # Create results table
            table = Table(title="Benchmark Results", show_header=True, header_style="bold cyan")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Total Iterations", str(len(times)))
            table.add_row("Successful", str(len(times) - errors))
            table.add_row("Failed", str(errors))
            table.add_row("Average Time", f"{avg_time*1000:.2f} ms")
            table.add_row("Min Time", f"{min_time*1000:.2f} ms")
            table.add_row("Max Time", f"{max_time*1000:.2f} ms")
            table.add_row("Throughput", f"{len(times)/sum(times):.2f} ops/sec")

            self.formatter.console.print(table)
        else:
            self.formatter.print_error("No successful iterations!")

    def show_logs(self, lines: int = 50, follow: bool = False, stream: str = "both", pid: Optional[int] = None):
        """
        Show Java bridge logs.

        Args:
            lines: Number of lines to show
            follow: Follow mode (tail -f style)
            stream: Which stream to show (stdout, stderr, both)
            pid: Specific PID to show logs for
        """
        self.formatter.print_header("📋 Java Bridge Logs")

        # Determine which bridge to use
        bridge = None

        if pid:
            # Check if it's the current bridge
            if self.shell.session.java_bridge and hasattr(self.shell.session.java_bridge, '_java_process'):
                if self.shell.session.java_bridge._java_process and self.shell.session.java_bridge._java_process.pid == pid:
                    bridge = self.shell.session.java_bridge
                else:
                    self.formatter.print_error(f"PID {pid} is not the current bridge. Logs only available for current bridge.")
                    return
            else:
                self.formatter.print_error("No active bridge. Initialize engines first.")
                return
        else:
            # Use current bridge
            if self.shell.session.java_bridge:
                bridge = self.shell.session.java_bridge
            else:
                self.formatter.print_error("No active bridge. Initialize engines first.")
                return

        # Show logs
        try:
            if follow:
                self.formatter.print_info("Following logs (Ctrl+C to stop)...")
                self.formatter.print_warning("Follow mode not yet implemented. Showing last lines instead.")

            # Use the bridge's get_java_logs() method
            if hasattr(bridge, 'get_java_logs'):
                log_lines = bridge.get_java_logs(count=lines)

                if not log_lines:
                    self.formatter.print_warning("No logs available yet. The Java bridge may still be starting up.")
                    return

                self.formatter.print_info(f"\n📜 Last {len(log_lines)} log lines:")
                self.formatter.console.print("")

                for log_line in log_lines:
                    # Color code based on log level
                    if "[STDERR]" in log_line or "ERROR" in log_line or "Exception" in log_line:
                        self.formatter.console.print(f"[red]{log_line}[/red]")
                    elif "WARN" in log_line:
                        self.formatter.console.print(f"[yellow]{log_line}[/yellow]")
                    elif "INFO" in log_line:
                        self.formatter.console.print(f"[cyan]{log_line}[/cyan]")
                    else:
                        self.formatter.console.print(log_line)

                self.formatter.console.print("")
                self.formatter.print_info(f"💡 Showing logs from bridge PID: {bridge._java_process.pid if hasattr(bridge, '_java_process') and bridge._java_process else 'unknown'}")
            else:
                self.formatter.print_warning("Log retrieval not available for this bridge.")

        except Exception as e:
            self.formatter.print_error(f"Failed to read logs: {e}")
            import traceback
            traceback.print_exc()

