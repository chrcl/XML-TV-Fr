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


# ---------------------------------------------------------------------------
# update_line
# ---------------------------------------------------------------------------


def test_update_line(capsys):
    _reset()
    logger.set_log_level("info")
    logger.update_line("hello")
    captured = capsys.readouterr()
    assert "\r" in captured.out
    _reset()


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------


def test_save_debug_level(tmp_path):
    _reset()
    logger.set_log_folder(str(tmp_path))
    logger.set_log_level("debug")
    logger.add_channel_entry("guide.json", "TF1.fr", "2025-01-01")
    logger.save()
    json_files = list(tmp_path.glob("*.json"))
    assert len(json_files) == 1
    _reset()


def test_save_non_debug_level(tmp_path):
    _reset()
    logger.set_log_folder(str(tmp_path))
    logger.set_log_level("info")
    logger.save()
    json_files = list(tmp_path.glob("*.json"))
    assert len(json_files) == 0
    _reset()


# ---------------------------------------------------------------------------
# add_additional_error
# ---------------------------------------------------------------------------


def test_add_additional_error():
    _reset()
    logger.add_additional_error("guide.json", "SomeError", "Something went wrong")
    errors = logger._log_file["guide.json"]["additional_errors"]
    assert len(errors) == 1
    assert errors[0]["error"] == "SomeError"
    assert errors[0]["message"] == "Something went wrong"
    _reset()


# ---------------------------------------------------------------------------
# clear_log
# ---------------------------------------------------------------------------


def test_clear_log(tmp_path):
    _reset()
    logger.set_log_folder(str(tmp_path))
    (tmp_path / "test1.json").write_text("{}")
    (tmp_path / "test2.json").write_text("{}")
    logger.clear_log()
    remaining = list(tmp_path.iterdir())
    assert remaining == []
    _reset()
