"""Unit tests for the logger module."""

from __future__ import annotations

import xmltvfr.utils.logger as logger


def _reset() -> None:
    """Reset all module-level state to defaults before each test."""
    logger._level = "none"
    logger._debug_folder = "var/logs"
    logger._last_log = ""
    logger._log_file = {}


def test_log_none_level(capsys):
    _reset()
    logger.set_log_level("none")
    logger.log("should not appear")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_log_debug_level(capsys):
    _reset()
    logger.set_log_level("debug")
    logger.log("hello debug")
    captured = capsys.readouterr()
    assert "hello debug" in captured.out


def test_set_log_level():
    _reset()
    logger.set_log_level("info")
    assert logger.get_log_level() == "info"


def test_add_channel_entry():
    _reset()
    logger.add_channel_entry("guide.json", "TF1.fr", "2025-01-01")
    entry = logger._log_file["guide.json"]["channels"]["2025-01-01"]["TF1.fr"]
    assert entry["success"] is False
    assert entry["provider"] is None
    assert entry["cache"] is False
    assert entry["failed_providers"] == []


def test_has_channel_successful_provider():
    _reset()
    assert logger.has_channel_successful_provider("guide.json", "TF1.fr", "2025-01-01") is False
    logger.set_channel_successful_provider("guide.json", "TF1.fr", "2025-01-01", "MyProvider")
    assert logger.has_channel_successful_provider("guide.json", "TF1.fr", "2025-01-01") is True


def test_add_channel_failed_provider():
    _reset()
    logger.add_channel_failed_provider("guide.json", "TF1.fr", "2025-01-01", "BadProvider")
    entry = logger._log_file["guide.json"]["channels"]["2025-01-01"]["TF1.fr"]
    assert "BadProvider" in entry["failed_providers"]
    assert logger._log_file["guide.json"]["failed_providers"]["BadProvider"] is True


def test_get_last_log():
    _reset()
    logger.set_log_level("info")
    logger.log("last message")
    assert logger.get_last_log() == "last message"
