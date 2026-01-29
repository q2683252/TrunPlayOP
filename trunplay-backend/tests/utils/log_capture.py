"""
Log Capture utility for testing.

Captures structured logs during tests and provides assertion methods.
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime


class CaptureHandler(logging.Handler):
    """Custom logging handler that captures log records."""

    def __init__(self, records: List[Dict[str, Any]]):
        super().__init__()
        self.records = records

    def emit(self, record: logging.LogRecord):
        """Capture a log record."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "context": getattr(record, "context", {}),
            "trace_id": getattr(record, "trace_id", None),
            "file": record.filename,
            "line": record.lineno,
            "func": record.funcName,
        }

        # Capture exception info if present
        if record.exc_info:
            log_entry["exception"] = self.format(record)

        self.records.append(log_entry)


class LogCapture:
    """
    Captures logs during test execution and provides assertion methods.

    Usage:
        def test_something(log_capture):
            # ... do something that logs
            log_capture.assert_logged("INFO", "Operation completed")
            log_capture.assert_not_logged("ERROR", "failed")
    """

    def __init__(self):
        self.records: List[Dict[str, Any]] = []
        self._handler: Optional[CaptureHandler] = None
        self._original_handlers: Dict[str, List[logging.Handler]] = {}

    def start(self, logger_name: Optional[str] = None):
        """Start capturing logs."""
        self._handler = CaptureHandler(self.records)
        self._handler.setLevel(logging.DEBUG)

        # Get the target logger
        logger = logging.getLogger(logger_name)

        # Store original handlers
        self._original_handlers[logger_name or "root"] = list(logger.handlers)

        # Add our capture handler
        logger.addHandler(self._handler)

        # Ensure logger level allows all messages
        if logger.level > logging.DEBUG:
            logger.setLevel(logging.DEBUG)

    def stop(self):
        """Stop capturing logs."""
        if self._handler:
            for logger_name in self._original_handlers:
                logger = logging.getLogger(logger_name if logger_name != "root" else None)
                logger.removeHandler(self._handler)
            self._handler = None

    def assert_logged(
        self,
        level: str,
        message_contains: str,
        context_match: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assert that a specific log was recorded.

        Args:
            level: Log level (INFO, ERROR, etc.)
            message_contains: Substring that should be in the message
            context_match: Optional dict of context values to match

        Returns:
            The matching log record

        Raises:
            AssertionError: If no matching log is found
        """
        for record in self.records:
            if record["level"] != level:
                continue
            if message_contains not in record["message"]:
                continue
            if context_match is not None:
                ctx = record.get("context", {})
                if not all(ctx.get(k) == v for k, v in context_match.items()):
                    continue
            return record

        # Build helpful error message
        error_msg = f"Expected log not found: level={level}, message contains '{message_contains}'"
        if context_match:
            error_msg += f", context={context_match}"
        error_msg += f"\n\nCaptured logs ({len(self.records)} total):\n{self.dump()}"

        raise AssertionError(error_msg)

    def assert_not_logged(self, level: str, message_contains: str):
        """
        Assert that a specific log was NOT recorded.

        Args:
            level: Log level (INFO, ERROR, etc.)
            message_contains: Substring that should NOT be in any message

        Raises:
            AssertionError: If a matching log is found
        """
        for record in self.records:
            if record["level"] == level and message_contains in record["message"]:
                raise AssertionError(
                    f"Unexpected log found: level={level}, message='{record['message']}'"
                )

    def assert_logged_count(self, level: str, expected_count: int):
        """Assert the number of logs at a specific level."""
        actual_count = len([r for r in self.records if r["level"] == level])
        if actual_count != expected_count:
            raise AssertionError(
                f"Expected {expected_count} {level} logs, found {actual_count}"
            )

    def get_by_level(self, level: str) -> List[Dict[str, Any]]:
        """Get all logs at a specific level."""
        return [r for r in self.records if r["level"] == level]

    def get_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all logs with a specific trace ID."""
        return [r for r in self.records if r.get("trace_id") == trace_id]

    def get_by_logger(self, logger_name: str) -> List[Dict[str, Any]]:
        """Get all logs from a specific logger."""
        return [r for r in self.records if r["logger"] == logger_name]

    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all ERROR level logs."""
        return self.get_by_level("ERROR")

    def get_warnings(self) -> List[Dict[str, Any]]:
        """Get all WARNING level logs."""
        return self.get_by_level("WARNING")

    def has_errors(self) -> bool:
        """Check if any ERROR logs were captured."""
        return len(self.get_errors()) > 0

    def has_warnings(self) -> bool:
        """Check if any WARNING logs were captured."""
        return len(self.get_warnings()) > 0

    def dump(self, pretty: bool = True) -> str:
        """Dump all captured logs as a string."""
        if pretty:
            lines = []
            for r in self.records:
                line = f"[{r['timestamp']}] {r['level']:7} {r['logger']}: {r['message']}"
                if r.get("context"):
                    line += f" | context={r['context']}"
                lines.append(line)
            return "\n".join(lines)
        else:
            return "\n".join(json.dumps(r, ensure_ascii=False) for r in self.records)

    def dump_json(self) -> str:
        """Dump all captured logs as JSON."""
        return json.dumps(self.records, indent=2, ensure_ascii=False)

    def clear(self):
        """Clear all captured logs."""
        self.records.clear()

    def __len__(self) -> int:
        """Return the number of captured logs."""
        return len(self.records)

    def __iter__(self):
        """Iterate over captured logs."""
        return iter(self.records)

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
