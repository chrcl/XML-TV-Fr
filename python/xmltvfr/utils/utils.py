"""Static utility functions.

Migrated from PHP: src/Component/Utils.php
"""

from __future__ import annotations

import importlib
import json
import os
import pkgutil
import random
import re
import shutil
from datetime import datetime
from typing import Any

from xmltvfr.utils.terminal_icon import TerminalIcon

# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------
_providers: list[type] | None = None


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------


def _is_valid_provider(obj: Any, full_module_name: str) -> bool:
    """Return ``True`` if *obj* is a provider class defined in *full_module_name*."""
    return (
        isinstance(obj, type) and obj.__module__ == full_module_name and callable(getattr(obj, "construct_epg", None))
    )


def get_providers() -> list[type]:
    """Return all provider classes found in the ``xmltvfr.providers`` package.

    Results are cached after the first call.
    """
    global _providers
    if _providers is not None:
        return _providers

    import xmltvfr.providers as _providers_pkg

    discovered: list[type] = []
    pkg_path = _providers_pkg.__path__
    pkg_name = _providers_pkg.__name__

    for _finder, module_name, _ispkg in pkgutil.iter_modules(pkg_path):
        full_name = f"{pkg_name}.{module_name}"
        try:
            module = importlib.import_module(full_name)
        except Exception:  # noqa: BLE001
            continue
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if _is_valid_provider(obj, full_name):
                discovered.append(obj)

    _providers = discovered
    return _providers


def get_provider(provider_name: str) -> type | None:
    """Return the provider class whose simple class name matches *provider_name*."""
    for provider in get_providers():
        if provider.__name__ == provider_name:
            return provider
    return None


def get_channel_data_from_provider(provider: Any, channel_id: str, date: str) -> str:
    """Invoke ``provider.construct_epg(channel_id, date)`` and return formatted XML or ``'false'``."""
    try:
        obj = provider.construct_epg(channel_id, date)
    except Exception:  # noqa: BLE001
        obj = False

    if not obj or getattr(obj, "get_program_count", lambda: 0)() == 0:
        return "false"

    # Lazy import to avoid circular dependency with XmlFormatter (if present)
    try:
        from xmltvfr.export.xml_formatter import XmlFormatter  # type: ignore[import]

        formatter = XmlFormatter()
        return formatter.format_channel(obj, provider)
    except ImportError:
        return "false"


def extract_provider_name(provider: Any) -> str:
    """Return the simple class name of *provider*."""
    return type(provider).__name__


# ---------------------------------------------------------------------------
# Thread helpers
# ---------------------------------------------------------------------------


def has_one_thread_running(threads: list) -> bool:
    """Return ``True`` if at least one thread in *threads* reports ``is_running()``."""
    for thread in threads:
        if callable(getattr(thread, "is_running", None)) and thread.is_running():
            return True
    return False


# ---------------------------------------------------------------------------
# Colour / terminal helpers
# ---------------------------------------------------------------------------

# NOTE: The mapping below intentionally mirrors the PHP source (src/Component/Utils.php).
# In the original PHP, numeric codes 10 and 14 — as well as 'light cyan' and 'light green' —
# all share \033[92m (bright green). This is a quirk of the original implementation preserved
# here for exact parity.
_COLOR_MAP: dict[str | int, str] = {
    1: "\033[31m",
    "red": "\033[31m",
    2: "\033[32m",
    "green": "\033[32m",
    3: "\033[33m",
    "yellow": "\033[33m",
    4: "\033[34m",
    "blue": "\033[34m",
    5: "\033[35m",
    "magenta": "\033[35m",
    6: "\033[36m",
    "cyan": "\033[36m",
    7: "\033[37m",
    "light grey": "\033[37m",
    8: "\033[90m",
    "dark grey": "\033[90m",
    9: "\033[91m",
    "light red": "\033[91m",
    10: "\033[92m",  # intentionally same as 14/'light green' — matches PHP source
    "light cyan": "\033[92m",  # intentionally same — matches PHP source
    11: "\033[93m",
    "light yellow": "\033[93m",
    12: "\033[94m",
    "light blue": "\033[94m",
    13: "\033[95m",
    "light magenta": "\033[95m",
    14: "\033[92m",  # intentionally same as 10/'light cyan' — matches PHP source
    "light green": "\033[92m",
}


def colorize(content: str, color: str | int | None = None) -> str:
    """Wrap *content* with ANSI colour codes.

    If *color* is ``None`` a random colour (1–14) is chosen.
    """
    if color is None:
        key: str | int = random.randint(1, 14)
    elif isinstance(color, str) and not color.isnumeric():
        key = color.lower()
    else:
        key = int(color) if isinstance(color, str) else color

    header = _COLOR_MAP.get(key, "")
    footer = "\033[0m"
    return header + content + footer


def get_max_terminal_length() -> int:
    """Return the number of columns available in the current terminal (fallback: 180)."""
    try:
        size = os.get_terminal_size()
        return size.columns
    except OSError:
        return 180


def replace_buggy_width_characters(string: str) -> str:
    """Replace wide emoji characters with spaces of equivalent display width.

    Some emoji (success, error, pause) have unpredictable ``wcwidth`` results;
    replacing them with spaces allows accurate line-length calculations.
    """
    wide_chars = [TerminalIcon.success(), TerminalIcon.error(), TerminalIcon.pause()]
    for char in wide_chars:
        string = string.replace(char, "  ")
    return string


# ---------------------------------------------------------------------------
# File system helpers
# ---------------------------------------------------------------------------


def recurse_rmdir(dir_path: str) -> bool:
    """Recursively remove *dir_path* and all its contents.

    Returns ``True`` on success, ``False`` if the path did not exist.
    """
    if os.path.isdir(dir_path):
        shutil.rmtree(dir_path)
        return True
    return False


# ---------------------------------------------------------------------------
# XML date / time helpers
# ---------------------------------------------------------------------------


def _parse_epg_datetime(dt_str: str) -> int:
    """Parse an EPG datetime string (``'%Y%m%d%H%M%S %z'``) and return a Unix timestamp."""
    try:
        dt = datetime.strptime(dt_str.strip(), "%Y%m%d%H%M%S %z")
        return int(dt.timestamp())
    except ValueError:
        return 0


def get_start_and_end_dates_from_xml_string(xml_content: str) -> tuple[list[int], list[int]]:
    """Extract all ``start`` and ``stop`` timestamps from an XMLTV string.

    Returns a tuple ``(start_timestamps, stop_timestamps)`` as lists of Unix ints.
    """
    start_matches = re.findall(r'start="(.*?)"', xml_content)
    end_matches = re.findall(r'stop="(.*?)"', xml_content)
    start_dates = [_parse_epg_datetime(s) for s in start_matches]
    end_dates = [_parse_epg_datetime(s) for s in end_matches]
    return start_dates, end_dates


def get_time_range_from_xml_string(xml_content: str) -> int:
    """Return the difference (in seconds) between the earliest start and latest stop time.

    Returns ``0`` if no timestamps are found.
    """
    start_dates, end_dates = get_start_and_end_dates_from_xml_string(xml_content)
    if not start_dates or not end_dates:
        return 0
    return max(end_dates) - min(start_dates)


# ---------------------------------------------------------------------------
# Rating helpers
# ---------------------------------------------------------------------------


def get_canadian_rating_system(rating: str, lang: str = "fr") -> str | None:
    """Return the Canadian rating system name for *rating*, or ``None`` if unknown."""
    if rating in ("PG", "14A", "18A", "R", "A") or (rating == "G" and lang == "en"):
        return "CHVRS"
    if rating in ("G", "13", "16", "18"):
        return "RCQ"
    return None


# ---------------------------------------------------------------------------
# Guide / channel helpers
# ---------------------------------------------------------------------------


def get_channels_from_guide(guide: dict) -> dict:
    """Load and merge all channel definitions referenced by *guide*.

    *guide['channels']* may be:
    - a ``str`` path to a single JSON file, or
    - a ``list`` of JSON file paths (merged left-to-right, later files win).
    """
    channels_value = guide.get("channels", [])
    if isinstance(channels_value, str):
        with open(channels_value, encoding="utf-8") as fh:
            return json.load(fh)
    if isinstance(channels_value, list):
        merged: dict = {}
        for channel_file in channels_value:
            try:
                with open(channel_file, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, json.JSONDecodeError):
                data = {}
            merged.update(data)
        return merged
    return {}


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------


def slugify(string: str) -> str:
    """Convert *string* to a URL-friendly slug (lowercase, spaces → dashes)."""
    return re.sub(r"[^A-Za-z0-9-]+", "-", string).strip("-").lower()


# ---------------------------------------------------------------------------
# UI factory
# ---------------------------------------------------------------------------


def get_ui(ui: str) -> Any:
    """Return a ``MultiColumnUI`` or ``ProgressiveUI`` instance.

    Imports are deferred to avoid circular dependencies.
    """
    # Lazy import
    try:
        from xmltvfr.ui.multi_column_ui import MultiColumnUI  # type: ignore[import]
        from xmltvfr.ui.progressive_ui import ProgressiveUI  # type: ignore[import]
    except ImportError:
        # UI modules not yet migrated — return a no-op placeholder
        return object()

    if ui == "MultiColumnUI":
        return MultiColumnUI()
    return ProgressiveUI()
