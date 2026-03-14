"""MultiColumnUI — two-column terminal display for EPG generation progress.

Migrated from PHP: src/Component/UI/MultiColumnUI.php
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from xmltvfr.ui.layout import Layout
from xmltvfr.utils.utils import colorize, get_max_terminal_length, has_one_thread_running

if TYPE_CHECKING:
    from xmltvfr.core.channels_manager import ChannelsManager


class MultiColumnUI:
    """Renders a two-column live display: threads on the left, events on the right.

    The display refreshes every 0.1 s (10 fps) until all channels have been
    processed and no thread is still running.
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
        """Return an async view coroutine factory for this guide.

        The returned callable, when invoked, produces a coroutine that runs
        the display loop.
        """
        Layout.show_cursor_on_exit()

        async def _view() -> None:
            if log_level == "none":
                return
            Layout.hide_cursor()
            has_thread_running = True
            while has_thread_running:
                layout_length = get_max_terminal_length()
                event_length = max(len(threads), 5)
                layout = Layout()
                layout.add_line(
                    [colorize("XML TV Fr - Génération des fichiers XMLTV", "light blue")],
                    [layout_length],
                )
                layout.add_line([" "], [layout_length])
                layout.add_line(
                    [
                        colorize("Chaines récupérées : ", "cyan")
                        + manager.get_status()
                        + "   |   "
                        + colorize("Fichier :", "cyan")
                        + f" {guide['filename']} ({index}/{guides_count})"
                    ],
                    [layout_length],
                )
                layout.add_line([" "], [layout_length])
                column_lengths = [layout_length // 2, layout_length // 2]
                layout.add_line(
                    [colorize("Threads:", "light blue"), colorize("Derniers évènements:", "light blue")],
                    column_lengths,
                )
                column1 = [f"Thread {i + 1} : {thread}" for i, thread in enumerate(threads)]
                column2 = manager.get_latest_events(event_length)
                for i in range(max(len(column1), len(column2))):
                    layout.add_line(
                        [column1[i] if i < len(column1) else "", column2[i] if i < len(column2) else ""],
                        column_lengths,
                    )
                self._cursor_position = layout.display(self._cursor_position)
                has_thread_running = manager.has_remaining_channels() or has_one_thread_running(threads)
                await asyncio.sleep(0.1)  # refresh rate: 10 fps

        return _view
