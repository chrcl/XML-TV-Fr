"""MultiThreadedGenerator — async EPG generator using per-channel threads.

Migrated from PHP: src/Component/MultiThreadedGenerator.php
"""

from __future__ import annotations

import asyncio
import os
from datetime import date as date_module
from typing import TYPE_CHECKING

from xmltvfr.core.channel_thread import ChannelThread
from xmltvfr.core.channels_manager import ChannelsManager
from xmltvfr.core.generator import Generator
from xmltvfr.utils import logger
from xmltvfr.utils.utils import get_channels_from_guide, has_one_thread_running

if TYPE_CHECKING:
    from xmltvfr.config.configurator import Configurator


class MultiThreadedGenerator(Generator):
    """Generator that processes channels concurrently using asyncio tasks.

    Channels are distributed to a fixed pool of :class:`~xmltvfr.core.channel_thread.ChannelThread`
    workers.  An optional UI coroutine runs in parallel to refresh the terminal
    display every 0.1 s.

    Parameters
    ----------
    start:
        First date to generate EPG for (see :class:`~xmltvfr.core.generator.Generator`).
    stop:
        Last date to generate EPG for.
    configurator:
        Top-level configuration object.
    """

    def __init__(self, start: date_module, stop: date_module, configurator: Configurator) -> None:
        super().__init__(start, stop, configurator)

    # ------------------------------------------------------------------
    # Channel distribution loop
    # ------------------------------------------------------------------

    async def _generate_channels_async(self, threads: list[ChannelThread], manager: ChannelsManager) -> None:
        """Distribute channels from *manager* to idle threads until all are done.

        Uses cooperative scheduling (``await asyncio.sleep(0)``) to interleave
        with channel-thread coroutines and the UI coroutine.
        """
        threads_stack = list(threads)
        while manager.has_remaining_channels() or has_one_thread_running(threads):
            await asyncio.sleep(0)  # yield to other coroutines
            for _ in range(len(threads)):
                thread = threads_stack.pop(0)
                threads_stack.append(thread)
                if not thread.is_running():
                    channel_data = manager.shift_channel()
                    if not channel_data:
                        break
                    thread.set_channel(channel_data)
                    thread.start()
        await asyncio.sleep(0.5)  # let the UI coroutine write the last frame

    # ------------------------------------------------------------------
    # EPG generation (async entry point)
    # ------------------------------------------------------------------

    async def _generate_epg_async(self) -> None:
        """Async implementation of the EPG generation loop."""
        generator_id = os.urandom(10).hex()
        log_level = logger.get_log_level()
        logger.set_log_level("none")

        guides_count = len(self.guides)
        ui = self.configurator.get_ui()

        for index, guide in enumerate(self.guides, start=1):
            channels = get_channels_from_guide(guide)
            manager = ChannelsManager(channels, self)
            threads: list[ChannelThread] = [
                ChannelThread(manager, self, generator_id, guide["filename"])
                for _ in range(self.configurator.nb_threads)
            ]

            view_closure = ui.get_closure(threads, manager, guide, log_level, index, guides_count)
            # Schedule the UI coroutine concurrently (fire-and-forget)
            asyncio.ensure_future(view_closure())

            await self._generate_channels_async(threads, manager)

        logger.set_log_level(log_level)
        logger.log("\033[95m[EPG GRAB] \033[39mRécupération du guide des programmes terminée...\n")

    # ------------------------------------------------------------------
    # Abstract method implementation
    # ------------------------------------------------------------------

    def _generate_epg(self) -> None:
        """Run the async EPG generation loop in a new event loop."""
        asyncio.run(self._generate_epg_async())
