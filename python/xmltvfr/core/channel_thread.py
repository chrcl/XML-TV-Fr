"""ChannelThread — async worker that fetches EPG data for a single channel.

Migrated from PHP: src/Component/ChannelThread.php
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from xmltvfr.core.channels_manager import ChannelsManager
from xmltvfr.core.provider_task import ProviderTask
from xmltvfr.domain.models.epg_enum import EPGEnum
from xmltvfr.utils import logger
from xmltvfr.utils.terminal_icon import TerminalIcon
from xmltvfr.utils.utils import colorize, extract_provider_name

if TYPE_CHECKING:
    from xmltvfr.core.generator import Generator


class ChannelThread:
    """Processes all EPG dates for a single channel, iterating over providers.

    Each thread is assigned a channel via :meth:`set_channel` and then started
    with :meth:`start`, which schedules an asyncio task.  The task iterates
    over all dates for the channel, consulting the cache and trying providers
    in priority order.

    Parameters
    ----------
    manager:
        The :class:`~xmltvfr.core.channels_manager.ChannelsManager` co-ordinating
        work distribution.
    generator:
        The parent :class:`~xmltvfr.core.generator.Generator` (provides cache,
        provider list, date list, etc.).
    generator_id:
        A unique hex string identifying this generation run (used for log keys).
    channels_file:
        The channels JSON filename being processed (used for log keys).
    """

    def __init__(
        self,
        manager: ChannelsManager,
        generator: Generator,
        generator_id: str,
        channels_file: str,
    ) -> None:
        self._manager = manager
        self._generator = generator
        self._generator_id = generator_id
        self._channels_file = channels_file

        self._channel: str | None = None
        self._provider: str | None = None
        self._info: dict | None = None
        self._failed_providers: list[str] = []
        self._dates_gathered: list[str] = []
        self._extra_params: dict = {}
        self._status: str = ""
        self._date: str = ""
        self._is_running: bool = False
        self._has_started: bool = False

    # ------------------------------------------------------------------
    # Channel assignment
    # ------------------------------------------------------------------

    def set_channel(self, channel_info: dict) -> None:
        """Assign a new channel to this thread (called before :meth:`start`)."""
        self._has_started = False
        self._status = colorize("Démarrage...", "magenta")
        self._channel = channel_info["key"]
        self._info = channel_info["info"]
        self._failed_providers = channel_info.get("failedProviders", [])
        self._dates_gathered = channel_info.get("datesGathered", [])
        self._extra_params = channel_info.get("extraParams", {})

    # ------------------------------------------------------------------
    # String representation (shown in the UI)
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        if not self._has_started or not self._is_running:
            return colorize("En pause...", "yellow") + " " + TerminalIcon.pause()
        parts = [self._channel or "", self._date, self._provider or ""]
        status_str = " ".join(filter(None, parts))
        if self._status:
            status_str += " " + self._status
        return status_str + " " + TerminalIcon.spinner()

    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Schedule the async run coroutine as an asyncio task."""
        if not self._is_running:
            self._is_running = True
            asyncio.ensure_future(self._async_run())

    def is_running(self) -> bool:
        """Return ``True`` while this thread is processing a channel."""
        return self._is_running

    async def _async_run(self) -> None:
        """Wrap :meth:`_run` and reset the running flag when complete."""
        await self._run()
        self._is_running = False

    # ------------------------------------------------------------------
    # Provider helpers
    # ------------------------------------------------------------------

    def _get_remaining_providers(self) -> list:
        """Return providers that support this channel and have not yet failed."""
        info = self._info or {}
        providers = self._generator.get_providers(info.get("priority", []))
        providers = [p for p in providers if p.channel_exists(self._channel or "")]
        if self._failed_providers:
            failed_objs = self._generator.get_providers(self._failed_providers)
        else:
            failed_objs = []
        return [p for p in providers if p not in failed_objs]

    # ------------------------------------------------------------------
    # Provider result fetch (async, runs task in a thread)
    # ------------------------------------------------------------------

    async def _get_provider_result(self, provider_name: str, date: str) -> str:
        """Run a :class:`~xmltvfr.core.provider_task.ProviderTask` in a worker thread.

        Status strings sent by the provider are stored in ``self._status``
        so the UI can display them.
        """

        def _status_cb(msg: str) -> None:
            self._status = colorize(msg, "magenta")

        task = ProviderTask(provider_name, date, self._channel or "", self._extra_params, _status_cb)
        try:
            result = await asyncio.to_thread(task.run_sync)
        except Exception as exc:  # noqa: BLE001
            logger.log(f"\nProviderTask error [{provider_name}/{self._channel}/{date}]: {exc}\n")
            result = "false"
        finally:
            self._manager.remove_channel_from_provider(provider_name, self._channel or "")
        return result

    # ------------------------------------------------------------------
    # Data gathering (one provider, one date)
    # ------------------------------------------------------------------

    async def _get_data_from_provider(
        self,
        provider_name: str,
        provider: object,
        date: str,
        cache_key: str,
    ) -> dict:
        """Fetch data for *date* from *provider* and cache the result.

        Returns a result dict with keys: ``success``, ``provider``,
        ``isCache``, ``skipped``, ``isPartial``.
        """
        from xmltvfr.utils.utils import get_start_and_end_dates_from_xml_string

        cache = self._generator.get_cache()

        provider_result = await self._get_provider_result(provider_name, date)

        if provider_result == "false":
            self._failed_providers.append(provider_name)
            logger.add_channel_failed_provider(
                self._channels_file, self._channel or "", date, type(provider).__name__
            )
            return {"success": False}

        start_times, end_times = get_start_and_end_dates_from_xml_string(provider_result)
        configurator = self._generator.configurator
        state = provider.get_channel_state_from_times(start_times, end_times, configurator)

        if state == EPGEnum.PARTIAL_CACHE:
            # Check whether the existing cache (if any) is better
            if cache.get_state(cache_key) != EPGEnum.NO_CACHE:
                cache_content = cache.get(cache_key)
                cache_start_times, _ = get_start_and_end_dates_from_xml_string(cache_content)
                if cache_start_times and start_times and max(cache_start_times) > max(start_times):
                    return {"success": False}
            cache.store(cache_key, provider_result)
            return {"success": True, "provider": provider_name, "isCache": False, "skipped": False, "isPartial": True}

        cache.store(cache_key, provider_result)
        return {"success": True, "provider": provider_name, "isCache": False, "skipped": False, "isPartial": False}

    # ------------------------------------------------------------------
    # Data gathering (all providers, one date)
    # ------------------------------------------------------------------

    async def _gather_data(self, date: str) -> dict:
        """Gather EPG data for *date*, checking the cache and trying providers.

        Returns a result dict (same structure as :meth:`_get_data_from_provider`).
        """
        cache = self._generator.get_cache()
        cache_key = f"{self._channel}_{date}.xml"
        current_result: dict = {"success": False}

        if cache.get_state(cache_key) == EPGEnum.FULL_CACHE:
            provider_name = cache.get_provider_name(cache_key)
            return {"success": True, "provider": provider_name, "isCache": True, "skipped": False}

        providers = self._get_remaining_providers()
        for provider in providers:
            provider_name = extract_provider_name(provider)
            if not self._manager.can_use_provider(provider_name):
                return {"skipped": True}
            self._manager.add_channel_to_provider(provider_name, self._channel or "")
            self._provider = provider_name
            self._has_started = True
            self._status = colorize("En cours...", "magenta")

            result = await self._get_data_from_provider(provider_name, provider, date, cache_key)
            if result.get("success"):
                current_result = result
            if not current_result.get("isPartial") and result.get("success"):
                return current_result

        return current_result

    # ------------------------------------------------------------------
    # Status string helper
    # ------------------------------------------------------------------

    def _get_status_string(self, result: dict, cache_key: str) -> str:
        """Build a colourised status string (e.g. ``"OK - Orange ✅"``)."""
        cache = self._generator.get_cache()
        provider_name = ""
        emoji = TerminalIcon.success()

        if result.get("success"):
            provider_name = " - " + result["provider"]
            status_string = "OK"
            color = "green"
            if result.get("isPartial"):
                status_string += " (Partial)"
                color = "yellow"
            if result.get("isCache"):
                provider_name = " - " + cache.get_provider_name(cache_key)
                status_string += " (Cache)"
                color = "light yellow"
        else:
            if cache.get_state(cache_key):
                provider_name = " - " + cache.get_provider_name(cache_key)
                status_string = "OK (Forced Cache)"
                color = "yellow"
            else:
                emoji = TerminalIcon.error()
                status_string = "HS"
                color = "red"

        return colorize(status_string, color) + provider_name + " " + emoji

    # ------------------------------------------------------------------
    # Main run loop (async)
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        """Iterate over all dates for the assigned channel and gather EPG data."""
        cache = self._generator.get_cache()
        all_dates = self._generator.get_list_date()
        total = len(all_dates)
        # Skip dates already gathered (e.g. from a previous attempt)
        dates = [d for d in all_dates if d not in self._dates_gathered]
        progress = total - len(dates)

        for date in dates:
            logger.add_channel_entry(self._channels_file, self._channel or "", date)
            progress += 1
            self._date = f"{date} ({progress}/{total})"
            cache_key = f"{self._channel}_{date}.xml"

            result = await self._gather_data(date)

            if result.get("skipped"):
                # Cannot serve this channel right now — re-queue it
                self._manager.add_channel(
                    self._channel or "",
                    self._failed_providers,
                    self._dates_gathered,
                )
                return

            status_string = self._get_status_string(result, cache_key)
            self._add_event(date, status_string)

            if result.get("success"):
                logger.set_channel_successful_provider(
                    self._channels_file,
                    self._channel or "",
                    date,
                    result["provider"],
                    result.get("isCache", False),
                )
            elif cache.get_state(cache_key):
                provider_name = cache.get_provider_name(cache_key)
                logger.set_channel_successful_provider(
                    self._channels_file, self._channel or "", date, f"{provider_name} - Forced", True
                )
            elif getattr(self._generator.configurator, "enable_dummy", False):
                from xmltvfr.domain.models.dummy_channel import DummyChannel  # noqa: PLC0415

                dummy = DummyChannel(self._channel or "", date)
                cache.store(cache_key, self._generator.get_formatter().format_channel(dummy, None))

            self._dates_gathered.append(date)
            self._failed_providers = []

        self._manager.incr_channels_done()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_event(self, date: str, status_info: str) -> None:
        self._manager.add_event(f"{self._channel or ''} : {date} | {status_info}")

    # ------------------------------------------------------------------
    # Public accessors (used by UI and generator)
    # ------------------------------------------------------------------

    def get_channel(self) -> str | None:
        return self._channel

    def get_status(self) -> str | None:
        return self._status or None

    def get_date(self) -> str | None:
        return self._date or None

    def get_provider(self) -> str | None:
        return self._provider
