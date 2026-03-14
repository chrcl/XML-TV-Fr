"""Layout — terminal layout and cursor-control helpers.

Migrated from PHP: src/Component/UI/Layout.php
"""

from __future__ import annotations

import re
import signal
import sys

from xmltvfr.utils.utils import replace_buggy_width_characters


class Layout:
    """Manages a block of terminal lines that can be redrawn in-place.

    Each call to :meth:`display` moves the cursor up to the previously rendered
    position and redraws all lines, ensuring the block does not grow on
    repeated calls.

    Example usage::

        layout = Layout()
        layout.add_line(["column 1", "column 2"], [40, 40])
        cursor_pos = layout.display(cursor_pos)
    """

    def __init__(self) -> None:
        self._lines: list[list[str]] = []
        self._lines_column_layouts: list[list[int]] = []

    # ------------------------------------------------------------------
    # Cursor helpers (class-level)
    # ------------------------------------------------------------------

    @staticmethod
    def hide_cursor() -> None:
        """Hide the terminal cursor."""
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    @staticmethod
    def _show_cursor() -> None:
        """Show the terminal cursor."""
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    @classmethod
    def show_cursor_on_exit(cls) -> None:
        """Register handlers that restore the cursor on normal exit and SIGINT."""

        def _restore(_signum=None, _frame=None) -> None:
            cls._show_cursor()

        # Register shutdown hook
        import atexit

        atexit.register(_restore)

        # Register SIGINT (Ctrl+C) handler if supported (not on Windows)
        if hasattr(signal, "SIGINT"):
            try:
                signal.signal(signal.SIGINT, lambda s, f: (_restore(), sys.exit(0)))
            except (OSError, ValueError):
                pass  # not in main thread or signal already handled

    @staticmethod
    def reset_screen() -> None:
        """Clear the terminal screen and move the cursor to the top-left."""
        sys.stdout.write("\033[H\033[J")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Line management
    # ------------------------------------------------------------------

    def add_line(self, columns: list[str], layout: list[int]) -> None:
        """Add a row of *columns*, each padded/truncated to the widths in *layout*.

        Parameters
        ----------
        columns:
            List of cell strings (may contain ANSI colour codes).
        layout:
            List of visible character widths, one per column.
        """
        self._lines.append(columns)
        self._lines_column_layouts.append(layout)

    # ------------------------------------------------------------------
    # Visible-width helper
    # ------------------------------------------------------------------

    @staticmethod
    def get_visible_length(string: str) -> int:
        """Return the visible (display) width of *string*, stripping ANSI codes."""
        # Strip ANSI colour/control sequences
        clean = re.sub(r"\x1b\[[0-9;]*m", "", string)
        # Replace known wide emoji characters with fixed-width spaces
        clean = replace_buggy_width_characters(clean)
        # Use wcswidth-like calculation; fall back to len() for non-CJK
        try:
            import unicodedata

            width = 0
            for ch in clean:
                eaw = unicodedata.east_asian_width(ch)
                width += 2 if eaw in ("W", "F") else 1
            return width
        except Exception:  # noqa: BLE001
            return len(clean)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def display(self, cursor_position: int) -> int:
        """Render all lines to stdout and return the new cursor position.

        If *cursor_position* > 0 the cursor is moved up that many rows before
        drawing so existing output is overwritten.

        Parameters
        ----------
        cursor_position:
            Number of rows that were printed in the previous call.  Pass ``0``
            on the first call.

        Returns
        -------
        int
            The number of rows that were drawn (to be passed back on the next
            call).
        """
        if cursor_position > 0:
            self._move_cursor_up(cursor_position)

        line_count = self._get_line_count()

        for i in range(len(self._lines)):
            self._display_line(i)

        # If the new block is shorter, clear the leftover lines
        if line_count < cursor_position:
            for _ in range(line_count, cursor_position):
                self._clear_line()
                sys.stdout.write("\n")
            line_count = cursor_position

        sys.stdout.flush()
        return line_count

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _display_line(self, i: int) -> None:
        line = self._lines[i]
        layout = self._lines_column_layouts[i]
        for j in range(len(layout)):
            column_length = layout[j]
            column = line[j] if j < len(line) else ""
            current_len = self.get_visible_length(column)
            # Truncate if too wide
            while current_len > column_length and column:
                column = column[:-1]
                current_len = self.get_visible_length(column)
            # Pad if too narrow
            if current_len < column_length:
                column += " " * (column_length - current_len)
            sys.stdout.write(column + "\033[0m")
        sys.stdout.write("\n")

    def _get_line_count(self) -> int:
        """Return the total number of terminal rows that would be occupied."""
        all_text: list[str] = []
        for line in self._lines:
            all_text.append(" ".join(line))
        combined = "\n".join(all_text)
        return len(combined.split("\n"))

    @staticmethod
    def _move_cursor_up(n: int) -> None:
        sys.stdout.write(f"\033[{n}A")
        sys.stdout.flush()

    @staticmethod
    def _clear_line() -> None:
        sys.stdout.write("\033[2K")
