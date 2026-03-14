"""Tests for Layout terminal helper."""

from __future__ import annotations

from unittest.mock import patch


def test_get_visible_length_plain():
    from xmltvfr.ui.layout import Layout

    assert Layout.get_visible_length("hello") == 5


def test_get_visible_length_strips_ansi():
    from xmltvfr.ui.layout import Layout

    # ANSI red colour codes should not count towards width
    coloured = "\033[31mhello\033[0m"
    assert Layout.get_visible_length(coloured) == 5


def test_display_returns_line_count():
    from xmltvfr.ui.layout import Layout

    layout = Layout()
    layout.add_line(["col1", "col2"], [10, 10])
    with patch("sys.stdout"):
        count = layout.display(0)
    assert count >= 1


def test_display_clears_old_lines():
    """When redrawing with a shorter layout, leftover lines should be cleared."""
    from xmltvfr.ui.layout import Layout

    layout = Layout()
    layout.add_line(["a"], [10])

    import sys

    cleared = []

    original_write = sys.stdout.write

    def tracking_write(s):
        cleared.append(s)
        return len(s)

    with patch("sys.stdout") as mock_stdout:
        mock_stdout.write.side_effect = tracking_write
        mock_stdout.flush.return_value = None
        # First call with 3 previous lines, but only 1 new line
        count = layout.display(3)

    # Should have written clear-line sequences for the extra 2 lines
    clear_sequences = [s for s in cleared if "\033[2K" in s]
    assert len(clear_sequences) >= 2
    assert count == 3  # returns max(new, old)
