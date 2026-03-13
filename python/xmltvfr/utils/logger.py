"""Module-level static logger.

Migrated from PHP: src/Component/Logger.php
"""

from __future__ import annotations

import glob
import json
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Module-level state (mirrors PHP static class properties)
# ---------------------------------------------------------------------------
_level: str = "none"
_debug_folder: str = "var/logs"
_last_log: str = ""
_log_file: dict = {}

# Maximum width used when overwriting the current terminal line
_MAX_LINE_LENGTH: int = 100


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def set_log_level(level: str) -> None:
    """Set the active log level (e.g. ``'none'``, ``'info'``, ``'debug'``)."""
    global _level
    _level = level


def set_log_folder(path: str) -> None:
    """Create *path* if it does not exist and store it as the log folder."""
    global _debug_folder
    os.makedirs(path, mode=0o755, exist_ok=True)
    _debug_folder = path.rstrip(os.sep)


def get_last_log() -> str:
    """Return the most recently logged string."""
    return _last_log


def log(log_str: str) -> None:
    """Print *log_str* unless level is ``'none'``, and store it as the last log."""
    global _last_log
    _last_log = log_str
    if _level == "none":
        return
    print(log_str, end="")


def update_line(content: str) -> None:
    """Overwrite the current terminal line with *content* without advancing the cursor."""
    global _last_log
    previous_log = _last_log
    combined = "\r" + _last_log + content
    combined = combined[:_MAX_LINE_LENGTH]
    log("\r" + " " * _MAX_LINE_LENGTH)
    log(combined)
    # Restore _last_log so the caller's context is preserved
    _last_log = previous_log


def save() -> None:
    """Write a JSON log file when level is ``'debug'``."""
    if _level != "debug":
        return
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_path = os.path.join(_debug_folder, f"logs{timestamp}.json")
    with open(log_path, "w", encoding="utf-8") as fh:
        json.dump(_log_file, fh)
    log(f"\033[36m[LOGS] \033[39m Export des logs vers {log_path}\n")


def add_channel_entry(channel_file: str, channel: str, date: str) -> None:
    """Ensure a log entry exists for the given channel / date combination."""
    _log_file.setdefault(channel_file, {}).setdefault("channels", {}).setdefault(date, {})
    if channel not in _log_file[channel_file]["channels"][date]:
        _log_file[channel_file]["channels"][date][channel] = {
            "success": False,
            "provider": None,
            "cache": False,
            "failed_providers": [],
        }


def add_channel_failed_provider(channel_file: str, channel: str, date: str, provider: str) -> None:
    """Record a failed provider attempt for a channel / date combination."""
    add_channel_entry(channel_file, channel, date)
    _log_file[channel_file]["channels"][date][channel]["failed_providers"].append(provider)
    _log_file[channel_file].setdefault("failed_providers", {})[provider] = True


def set_channel_successful_provider(
    channel_file: str,
    channel: str,
    date: str,
    provider: str,
    is_cache: bool = False,
) -> None:
    """Mark a channel / date combination as successfully retrieved from *provider*."""
    add_channel_entry(channel_file, channel, date)
    entry = _log_file[channel_file]["channels"][date][channel]
    entry["success"] = True
    entry["provider"] = provider
    entry["cache"] = is_cache


def has_channel_successful_provider(channel_file: str, channel: str, date: str) -> bool:
    """Return ``True`` if the channel / date combination was successfully retrieved."""
    try:
        return bool(_log_file[channel_file]["channels"][date][channel]["success"])
    except (KeyError, TypeError):
        return False


def add_additional_error(channel_file: str, error: str, message: str) -> None:
    """Append an additional error entry to the log for *channel_file*."""
    _log_file.setdefault(channel_file, {}).setdefault("additional_errors", []).append(
        {"error": error, "message": message}
    )


def clear_log() -> None:
    """Remove all files inside the current log folder."""
    for file_path in glob.glob(os.path.join(_debug_folder, "*")):
        try:
            os.unlink(file_path)
        except OSError:
            pass


def get_log_level() -> str:
    """Return the current log level."""
    return _level
