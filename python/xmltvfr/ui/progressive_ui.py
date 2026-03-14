"""ProgressiveUI — scrolling event log terminal display for EPG generation.

Migrated from PHP: src/Component/UI/ProgressiveUI.php
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING, Any

from xmltvfr.ui.layout import Layout
from xmltvfr.utils.utils import colorize, get_max_terminal_length, has_one_thread_running

if TYPE_CHECKING:
    from xmltvfr.core.channels_manager import ChannelsManager


class ProgressiveUI:
    """Renders a scrolling event log with a thread-status footer.

    Unlike :class:`~xmltvfr.ui.multi_column_ui.MultiColumnUI`, events are
    printed progressively as they arrive.  Only the thread-status footer at
    the bottom is redrawn in-place on each refresh cycle.

    The display refreshes every 0.1 s (10 fps).
    """

    def __init__(self) -> None:
        self._cursor_position: int = 0

    def get_closure(
        self,
        threads: list[Any],
        manager: ChannelsManager,
        guide: dict,
        log_level: str,
        index: int,
        guides_count: int,
    ) -> Any:
        """Return an async view coroutine factory for this guide."""
        Layout.show_cursor_on_exit()
        # Reset cursor position for each new guide
        self._cursor_position = 0

        async def _view() -> None:
            events_displayed = 0
            if log_level == "none":
                return
            Layout.hide_cursor()
            sys.stdout.write(colorize("XML TV Fr - Génération des fichiers XMLTV\n", "light blue"))
            sys.stdout.write(colorize("Fichier :", "cyan") + f" {guide['filename']} ({index}/{guides_count})\n")
            sys.stdout.flush()

            has_thread_running = True
            while has_thread_running:
                layout_length = get_max_terminal_length()
                events = manager.get_latest_events(2**31 - 1)
                count = len(events)
                layout = Layout()
                events_displayed_count = 0
                if count > events_displayed:
                    events_to_display = events[events_displayed:]
                    events_displayed_count = len(events_to_display)
                    events_displayed = count
                    for event in events_to_display:
                        layout.add_line([event], [layout_length])
                layout.add_line(["-" * layout_length], [layout_length])
                for i, thread in enumerate(threads):
                    layout.add_line([f"Thread {i + 1} : {thread}"], [layout_length])
                self._cursor_position = layout.display(self._cursor_position) - events_displayed_count
                has_thread_running = manager.has_remaining_channels() or has_one_thread_running(threads)
                await asyncio.sleep(0.1)  # refresh rate: 10 fps

        return _view
