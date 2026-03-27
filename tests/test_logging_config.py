"""Tests for mcp_assistant.logging_config."""

from __future__ import annotations

import json
import logging
import sys
from unittest.mock import patch

import pytest

from mcp_assistant.logging_config import JsonFormatter, log_operation, setup_logging


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_pkg_logger() -> None:
    """Remove all handlers from the mcp_assistant logger between tests."""
    pkg = logging.getLogger("mcp_assistant")
    pkg.handlers.clear()


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    def setup_method(self):
        _reset_pkg_logger()

    def teardown_method(self):
        _reset_pkg_logger()

    def test_adds_stderr_handler(self):
        setup_logging()
        pkg = logging.getLogger("mcp_assistant")
        assert any(
            isinstance(h, logging.StreamHandler) and h.stream is sys.stderr
            for h in pkg.handlers
        )

    def test_default_level_is_info(self):
        with patch.dict("os.environ", {"LOG_LEVEL": "INFO"}, clear=False):
            setup_logging()
        pkg = logging.getLogger("mcp_assistant")
        assert pkg.level == logging.INFO

    def test_log_level_env_var_debug(self):
        _reset_pkg_logger()
        with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}, clear=False):
            # Re-import constants to pick up env override
            import importlib
            import mcp_assistant.logging_config as lc
            importlib.reload(lc)
            lc.setup_logging()
        pkg = logging.getLogger("mcp_assistant")
        assert pkg.level == logging.DEBUG
        # Restore
        import mcp_assistant.logging_config as lc2
        importlib.reload(lc2)

    def test_does_not_add_duplicate_handlers(self):
        setup_logging()
        setup_logging()
        pkg = logging.getLogger("mcp_assistant")
        assert len(pkg.handlers) == 1

    def test_propagate_is_false(self):
        setup_logging()
        pkg = logging.getLogger("mcp_assistant")
        assert pkg.propagate is False

    def test_json_format_uses_json_formatter(self):
        _reset_pkg_logger()
        with patch.dict("os.environ", {"LOG_FORMAT": "json"}, clear=False):
            import importlib
            import mcp_assistant.logging_config as lc
            importlib.reload(lc)
            lc.setup_logging()
        pkg = logging.getLogger("mcp_assistant")
        assert any(isinstance(h.formatter, lc.JsonFormatter) for h in pkg.handlers)
        import mcp_assistant.logging_config as lc2
        importlib.reload(lc2)

    def test_fastmcp_logger_quietened(self):
        setup_logging()
        fmcp = logging.getLogger("fastmcp")
        assert fmcp.level == logging.WARNING


# ---------------------------------------------------------------------------
# JsonFormatter
# ---------------------------------------------------------------------------


class TestJsonFormatter:
    def _make_record(self, msg: str, level: int = logging.INFO) -> logging.LogRecord:
        return logging.LogRecord(
            name="test.module",
            level=level,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )

    def test_output_is_valid_json(self):
        fmt = JsonFormatter()
        record = self._make_record("hello world")
        output = fmt.format(record)
        parsed = json.loads(output)
        assert parsed["msg"] == "hello world"
        assert parsed["level"] == "INFO"
        assert parsed["module"] == "test.module"
        assert "ts" in parsed

    def test_exception_included(self):
        fmt = JsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        output = fmt.format(record)
        parsed = json.loads(output)
        assert "exc" in parsed
        assert "ValueError" in parsed["exc"]


# ---------------------------------------------------------------------------
# log_operation
# ---------------------------------------------------------------------------


class TestLogOperation:
    """
    These tests do NOT call setup_logging() — log_operation is a pure helper
    that uses whatever logger is passed in.  We rely on caplog's default root
    handler (propagation must be True, i.e. no setup_logging side-effects).
    """

    def setup_method(self):
        # Make sure mcp_assistant logger has no handlers / propagate=True
        # so that caplog's root handler can intercept records.
        pkg = logging.getLogger("mcp_assistant")
        pkg.handlers.clear()
        pkg.propagate = True

    def teardown_method(self):
        _reset_pkg_logger()

    def _msg(self, record: logging.LogRecord) -> str:
        return record.getMessage()

    def test_logs_start_and_end_on_success(self, caplog):
        test_logger = logging.getLogger("mcp_assistant.test")
        with caplog.at_level(logging.INFO, logger="mcp_assistant"):
            with log_operation(test_logger, "my_op", feature="foo"):
                pass

        messages = [self._msg(r) for r in caplog.records]
        assert any("start op=my_op" in m and "feature=foo" in m for m in messages)
        assert any(
            "end op=my_op" in m and "status=ok" in m and "duration=" in m and "feature=foo" in m
            for m in messages
        )

    def test_logs_error_and_reraises(self, caplog):
        test_logger = logging.getLogger("mcp_assistant.test")
        with caplog.at_level(logging.ERROR, logger="mcp_assistant"):
            with pytest.raises(RuntimeError, match="oops"):
                with log_operation(test_logger, "failing_op", key="val"):
                    raise RuntimeError("oops")

        messages = [self._msg(r) for r in caplog.records]
        assert any(
            "end op=failing_op" in m and "status=error" in m and "oops" in m for m in messages
        )

    def test_duration_is_non_negative(self, caplog):
        import re

        test_logger = logging.getLogger("mcp_assistant.test")
        with caplog.at_level(logging.INFO, logger="mcp_assistant"):
            with log_operation(test_logger, "timed_op"):
                pass

        end_msg = next(
            self._msg(r) for r in caplog.records if "end op=timed_op" in self._msg(r)
        )
        match = re.search(r"duration=(\d+)ms", end_msg)
        assert match is not None
        assert int(match.group(1)) >= 0
