"""Terminal icon helpers.

Migrated from PHP: src/Component/TerminalIcon.php
"""

from __future__ import annotations

import time


class TerminalIcon:
    """Provides static terminal icon/emoji helpers."""

    @staticmethod
    def pause() -> str:
        """Return the pause emoji."""
        return "\u23f8\ufe0f"

    @staticmethod
    def spinner() -> str:
        """Return a braille spinner character that cycles at ~10 fps."""
        parts = ["\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827", "\u2807", "\u280f"]
        index = int(time.time() * 10) % 10
        return parts[index]

    @staticmethod
    def success() -> str:
        """Return the success (check mark) emoji."""
        return "\u2705"

    @staticmethod
    def error() -> str:
        """Return the error (cross mark) emoji."""
        return "\u274c"
