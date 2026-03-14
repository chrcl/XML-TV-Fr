"""ChannelsManager — distributes channel work to ChannelThread workers.

Migrated from PHP: src/Component/ChannelsManager.php
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xmltvfr.utils.utils import extract_provider_name

if TYPE_CHECKING:
    from xmltvfr.core.generator import Generator


class ChannelsManager:
    """Tracks pending channels and co-ordinates provider usage across threads.

    The manager maintains a queue of channels that still need to be processed
    and records which providers are currently in use (one provider per channel
    at a time, per the PHP original).  Threads call :meth:`shift_channel` to
    claim the next available channel and :meth:`remove_channel_from_provider`
    when they are done with a provider.

    Parameters
    ----------
    channels:
        Mapping of ``channel_key → channel_info`` loaded from a guide JSON
        file.
    generator:
        The :class:`~xmltvfr.core.generator.Generator` instance that owns this
        manager; used to look up the provider list.
    """

    def __init__(self, channels: dict, generator: Generator) -> None:
        self._channels_count: int = len(channels)
        self._channels_done: int = 0
        self._channels_info: dict = channels
        self._generator = generator
        self._channels: list[str] = list(channels.keys())
        self._providers_used: dict[str, list[str]] = {}
        self._providers_failed_by_channel: dict[str, list[str]] = {}
        self._dates_gathered_by_channel: dict[str, list[str]] = {}
        self._events: list[str] = []

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    def add_event(self, event: str) -> None:
        """Append *event* to the running event log."""
        self._events.append(event)

    def get_latest_events(self, number: int) -> list[str]:
        """Return the last *number* events (or all events if fewer exist)."""
        slice_size = min(len(self._events), number)
        return self._events[-slice_size:]

    # ------------------------------------------------------------------
    # Progress tracking
    # ------------------------------------------------------------------

    def incr_channels_done(self) -> None:
        """Increment the count of fully-processed channels."""
        self._channels_done += 1

    def get_status(self) -> str:
        """Return a human-readable ``"done / total"`` progress string."""
        return f"{self._channels_done} / {self._channels_count}"

    # ------------------------------------------------------------------
    # Provider usage tracking
    # ------------------------------------------------------------------

    def remove_channel_from_provider(self, provider: str, channel: str) -> None:
        """Release *channel* from *provider*'s in-use list."""
        if provider in self._providers_used:
            try:
                self._providers_used[provider].remove(channel)
            except ValueError:
                pass

    def can_use_provider(self, provider: str) -> bool:
        """Return ``True`` if no channel is currently being fetched from *provider*."""
        return provider not in self._providers_used or len(self._providers_used[provider]) == 0

    def add_channel_to_provider(self, provider: str, channel: str) -> None:
        """Mark *channel* as being fetched from *provider*."""
        self._providers_used.setdefault(provider, []).append(channel)

    # ------------------------------------------------------------------
    # Channel queue
    # ------------------------------------------------------------------

    def has_remaining_channels(self) -> bool:
        """Return ``True`` if there are still channels waiting in the queue."""
        return len(self._channels) > 0

    def add_channel(self, channel: str, providers_failed: list[str], dates_gathered: list[str]) -> None:
        """Re-queue *channel* (e.g. because the only available provider was busy)."""
        self._channels.append(channel)
        self._providers_failed_by_channel[channel] = providers_failed
        self._dates_gathered_by_channel[channel] = dates_gathered

    def _is_channel_available(self, key: str) -> bool:
        """Return whether *key* can be assigned to a thread right now."""
        channel_info = self._channels_info.get(key, {})
        providers = self._generator.get_providers(channel_info.get("priority", []))
        failed_names = self._providers_failed_by_channel.get(key, [])
        failed_providers = self._generator.get_providers(failed_names) if failed_names else []

        for provider in providers:
            if provider in failed_providers:
                continue
            if not provider.channel_exists(key):
                continue
            provider_name = extract_provider_name(provider)
            if not self.can_use_provider(provider_name):
                return False
            return True

        return True

    def shift_channel(self) -> dict:
        """Pop the next available channel from the queue and return its data.

        If no channel can be immediately served (all available providers are
        busy) returns an empty dict.  Channels that cannot be served are pushed
        back onto the end of the queue.

        Returns
        -------
        dict
            A mapping with keys ``"key"``, ``"info"``, ``"failedProviders"``,
            ``"datesGathered"``, and ``"extraParams"``; or an empty dict when
            no channel is available.
        """
        max_loop = len(self._channels)
        key: str | None = None

        for _ in range(max_loop):
            tmp_key = self._channels.pop(0)
            if self._is_channel_available(tmp_key):
                key = tmp_key
                break
            # Not available yet — push back to the end of the queue
            self.add_channel(
                tmp_key,
                self._providers_failed_by_channel.get(tmp_key, []),
                self._dates_gathered_by_channel.get(tmp_key, []),
            )

        if key is None:
            return {}

        # Retrieve extra_params from the configurator via the generator
        extra_params: dict = {}
        configurator = getattr(self._generator, "configurator", None)
        if configurator is not None:
            extra_params = getattr(configurator, "extra_params", {})

        return {
            "key": key,
            "info": self._channels_info.get(key, {}),
            "failedProviders": self._providers_failed_by_channel.get(key, []),
            "datesGathered": self._dates_gathered_by_channel.get(key, []),
            "extraParams": extra_params,
        }
