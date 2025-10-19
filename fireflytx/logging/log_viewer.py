"""
Log viewer for displaying Java logs in various formats.

Provides utilities for filtering, searching, and displaying Java library logs
with different output formats and real-time viewing capabilities.
"""

"""
Copyright (c) 2025 Firefly Software Solutions Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .java_log_bridge import JavaLogEntry, JavaLogLevel, LogFormatter


@dataclass
class LogFilter:
    """Filter configuration for log entries."""

    min_level: Optional[JavaLogLevel] = None
    max_level: Optional[JavaLogLevel] = None
    logger_pattern: Optional[str] = None
    message_pattern: Optional[str] = None
    saga_id: Optional[str] = None
    correlation_id: Optional[str] = None
    step_id: Optional[str] = None
    thread_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def matches(self, entry: JavaLogEntry) -> bool:
        """Check if a log entry matches this filter."""
        # Level filtering
        if self.min_level and self._level_to_int(entry.level) < self._level_to_int(self.min_level):
            return False
        if self.max_level and self._level_to_int(entry.level) > self._level_to_int(self.max_level):
            return False

        # Pattern matching
        if self.logger_pattern and not re.search(
            self.logger_pattern, entry.logger_name, re.IGNORECASE
        ):
            return False
        if self.message_pattern and not re.search(
            self.message_pattern, entry.message, re.IGNORECASE
        ):
            return False

        # Exact matches
        if self.saga_id and entry.saga_id != self.saga_id:
            return False
        if self.correlation_id and entry.correlation_id != self.correlation_id:
            return False
        if self.step_id and entry.step_id != self.step_id:
            return False
        if self.thread_name and entry.thread_name != self.thread_name:
            return False

        # Time filtering
        if self.start_time and entry.timestamp < self.start_time:
            return False
        if self.end_time and entry.timestamp > self.end_time:
            return False

        return True

    def _level_to_int(self, level: JavaLogLevel) -> int:
        """Convert log level to integer for comparison."""
        level_map = {
            JavaLogLevel.TRACE: 10,
            JavaLogLevel.DEBUG: 20,
            JavaLogLevel.INFO: 30,
            JavaLogLevel.WARN: 40,
            JavaLogLevel.ERROR: 50,
            JavaLogLevel.FATAL: 60,
        }
        return level_map.get(level, 30)


class LogViewer:
    """
    Viewer for Java library logs with filtering and formatting capabilities.

    Provides tools for searching, filtering, and displaying Java logs
    in various formats including real-time streaming.
    """

    def __init__(self):
        self.formatter = LogFormatter()

    def display_logs(
        self,
        logs: List[JavaLogEntry],
        filter_config: Optional[LogFilter] = None,
        format_type: str = "console",
        colorized: bool = True,
        max_entries: Optional[int] = None,
    ) -> str:
        """
        Display log entries with optional filtering and formatting.

        Args:
            logs: List of log entries to display
            filter_config: Optional filter configuration
            format_type: Display format ("console", "json", "structured")
            colorized: Whether to use colors in console output
            max_entries: Maximum number of entries to display

        Returns:
            Formatted log output as string
        """
        # Apply filtering
        filtered_logs = self._filter_logs(logs, filter_config)

        # Limit entries if specified
        if max_entries and len(filtered_logs) > max_entries:
            filtered_logs = filtered_logs[-max_entries:]

        # Format logs
        if not filtered_logs:
            return "No log entries match the specified criteria."

        lines = []

        # Add header
        lines.append(self._create_header(filtered_logs, format_type))
        lines.append("")

        # Format each entry
        for entry in filtered_logs:
            if format_type == "json":
                lines.append(self.formatter.format_json(entry))
            elif format_type == "structured":
                lines.append(self.formatter.format_structured(entry))
                lines.append("---")
            else:  # console format
                lines.append(self.formatter.format_console(entry, colorized))

        return "\\n".join(lines)

    def search_logs(
        self, logs: List[JavaLogEntry], search_term: str, search_fields: List[str] = None
    ) -> List[JavaLogEntry]:
        """
        Search log entries for a specific term.

        Args:
            logs: List of log entries to search
            search_term: Term to search for
            search_fields: Fields to search in (default: message, logger_name, exception)

        Returns:
            List of matching log entries
        """
        if search_fields is None:
            search_fields = ["message", "logger_name", "exception"]

        pattern = re.compile(search_term, re.IGNORECASE)
        results = []

        for entry in logs:
            for field in search_fields:
                value = getattr(entry, field, None)
                if value and pattern.search(str(value)):
                    results.append(entry)
                    break

        return results

    def get_log_summary(self, logs: List[JavaLogEntry]) -> Dict[str, Any]:
        """
        Generate a summary of log entries.

        Args:
            logs: List of log entries to summarize

        Returns:
            Dictionary containing summary statistics
        """
        if not logs:
            return {"total_entries": 0}

        # Count by level
        level_counts = {}
        for level in JavaLogLevel:
            level_counts[level.value] = sum(1 for log in logs if log.level == level)

        # Count by logger
        logger_counts = {}
        for entry in logs:
            logger = entry.logger_name
            logger_counts[logger] = logger_counts.get(logger, 0) + 1

        # Time range
        timestamps = [entry.timestamp for entry in logs]
        start_time = min(timestamps)
        end_time = max(timestamps)
        duration = end_time - start_time

        # Count unique SAGA IDs
        saga_ids = {entry.saga_id for entry in logs if entry.saga_id}
        correlation_ids = {entry.correlation_id for entry in logs if entry.correlation_id}

        # Error and exception counts
        error_count = sum(
            1 for entry in logs if entry.level in [JavaLogLevel.ERROR, JavaLogLevel.FATAL]
        )
        exception_count = sum(1 for entry in logs if entry.exception)

        return {
            "total_entries": len(logs),
            "level_counts": level_counts,
            "top_loggers": sorted(logger_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
            },
            "unique_sagas": len(saga_ids),
            "unique_correlations": len(correlation_ids),
            "error_count": error_count,
            "exception_count": exception_count,
            "entries_per_second": len(logs) / max(duration.total_seconds(), 1),
        }

    def create_real_time_viewer(
        self,
        log_source: Callable[[], List[JavaLogEntry]],
        filter_config: Optional[LogFilter] = None,
        refresh_interval: float = 1.0,
    ) -> "RealTimeLogViewer":
        """
        Create a real-time log viewer.

        Args:
            log_source: Function that returns current log entries
            filter_config: Optional filter configuration
            refresh_interval: Refresh interval in seconds

        Returns:
            RealTimeLogViewer instance
        """
        return RealTimeLogViewer(log_source, filter_config, refresh_interval, self)

    def export_logs(
        self,
        logs: List[JavaLogEntry],
        filename: str,
        format_type: str = "json",
        filter_config: Optional[LogFilter] = None,
    ) -> None:
        """
        Export log entries to a file.

        Args:
            logs: List of log entries to export
            filename: Output filename
            format_type: Export format ("json", "csv", "txt")
            filter_config: Optional filter configuration
        """
        filtered_logs = self._filter_logs(logs, filter_config)

        with open(filename, "w", encoding="utf-8") as f:
            if format_type == "json":
                import json

                data = [entry.to_dict() for entry in filtered_logs]
                json.dump(data, f, indent=2)
            elif format_type == "csv":
                import csv

                if filtered_logs:
                    fieldnames = filtered_logs[0].to_dict().keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for entry in filtered_logs:
                        writer.writerow(entry.to_dict())
            else:  # txt format
                for entry in filtered_logs:
                    f.write(self.formatter.format_console(entry, colorized=False))
                    f.write("\\n")

    def _filter_logs(
        self, logs: List[JavaLogEntry], filter_config: Optional[LogFilter]
    ) -> List[JavaLogEntry]:
        """Apply filtering to log entries."""
        if not filter_config:
            return logs

        return [entry for entry in logs if filter_config.matches(entry)]

    def _create_header(self, logs: List[JavaLogEntry], format_type: str) -> str:
        """Create a header for log display."""
        if not logs:
            return "No logs to display"

        summary = self.get_log_summary(logs)

        lines = []
        lines.append("Java Library Logs")
        lines.append("=" * 50)
        lines.append(f"Total Entries: {summary['total_entries']}")
        lines.append(
            f"Time Range: {summary['time_range']['start']} - {summary['time_range']['end']}"
        )
        lines.append(f"Duration: {summary['time_range']['duration_seconds']:.1f}s")
        lines.append(f"Unique SAGAs: {summary['unique_sagas']}")
        lines.append(f"Errors: {summary['error_count']}")

        # Level distribution
        level_info = []
        for level, count in summary["level_counts"].items():
            if count > 0:
                level_info.append(f"{level}: {count}")
        if level_info:
            lines.append(f"Levels: {', '.join(level_info)}")

        return "\\n".join(lines)


class RealTimeLogViewer:
    """
    Real-time log viewer that continuously displays new log entries.
    """

    def __init__(
        self,
        log_source: Callable[[], List[JavaLogEntry]],
        filter_config: Optional[LogFilter],
        refresh_interval: float,
        viewer: LogViewer,
    ):
        self.log_source = log_source
        self.filter_config = filter_config
        self.refresh_interval = refresh_interval
        self.viewer = viewer
        self.last_entry_count = 0
        self.running = False

    def start(self, max_display: int = 50) -> None:
        """Start real-time log viewing."""
        import os
        import time

        self.running = True

        try:
            while self.running:
                # Clear screen (works on most terminals)
                os.system("clear" if os.name == "posix" else "cls")

                # Get current logs
                logs = self.log_source()

                # Display recent logs
                output = self.viewer.display_logs(logs, self.filter_config, max_entries=max_display)

                print(output)
                print("\\n[Real-time viewer - Press Ctrl+C to exit]")
                print(f"Refresh interval: {self.refresh_interval}s")

                # Sleep until next refresh
                time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            print("\\nReal-time log viewer stopped.")
        finally:
            self.running = False

    def stop(self) -> None:
        """Stop real-time log viewing."""
        self.running = False
