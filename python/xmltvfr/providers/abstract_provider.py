"""AbstractProvider — Python equivalent of AbstractProvider.php."""

from __future__ import annotations

import hashlib
import html
import json
from abc import ABC
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import ClassVar
from zoneinfo import ZoneInfo

import requests

from xmltvfr.domain.models.epg_enum import EPGEnum
from xmltvfr.providers.provider_cache import ProviderCache


class AbstractProvider(ABC):
    _priority: ClassVar[dict[str, float]] = {}

    def __init__(
        self,
        client: requests.Session,
        json_path: str,
        priority: float,
    ) -> None:
        self._channels_list: dict = {}
        self._status_callback: Callable[[str], None] | None = None

        if json_path:
            import pathlib

            p = pathlib.Path(json_path)
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    self._channels_list = data if isinstance(data, dict) else {}
                except Exception:  # noqa: BLE001
                    pass

        type(self)._priority[type(self).__name__] = priority
        self._client = client

    # ------------------------------------------------------------------
    # Status / callback
    # ------------------------------------------------------------------

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        self._status_callback = callback

    def set_status(self, status: str) -> None:
        if self._status_callback:
            self._status_callback(status)

    # ------------------------------------------------------------------
    # Priority
    # ------------------------------------------------------------------

    @classmethod
    def get_priority(cls) -> float:
        return cls._priority.get(cls.__name__, 0.5)

    # ------------------------------------------------------------------
    # EPG construction
    # ------------------------------------------------------------------

    def construct_epg(self, channel: str, date: str) -> object:
        from xmltvfr.domain.services.channel_factory import ChannelFactory  # lazy

        return ChannelFactory.create_channel(channel)

    # ------------------------------------------------------------------
    # Logo
    # ------------------------------------------------------------------

    def get_logo(self, channel: str) -> str | None:
        if not self.channel_exists(channel):
            raise Exception(f"Channel {channel} does not exist in this provider")
        return None

    # ------------------------------------------------------------------
    # Channels
    # ------------------------------------------------------------------

    def get_channels_list(self) -> dict:
        return self._channels_list

    def channel_exists(self, channel: str) -> bool:
        return channel in self._channels_list

    # ------------------------------------------------------------------
    # Date helpers
    # ------------------------------------------------------------------

    @classmethod
    def get_min_max_date(cls, date: str) -> tuple[datetime, datetime]:
        tz = ZoneInfo("Europe/Paris")
        min_start = datetime.fromisoformat(date).replace(tzinfo=tz)
        max_start = min_start + timedelta(days=1) - timedelta(seconds=1)
        return min_start, max_start

    # ------------------------------------------------------------------
    # HTTP / cache
    # ------------------------------------------------------------------

    def _get_content_from_url(
        self,
        url: str,
        headers: dict | None = None,
        ignore_cache: bool = False,
    ) -> str:
        if headers is None:
            headers = {}
        if not headers.get("User-Agent"):
            headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0"

        cache_key = hashlib.md5((url + json.dumps(headers, sort_keys=True)).encode()).hexdigest()
        cache = ProviderCache(cache_key)

        if not ignore_cache:
            content = cache.get_content()
            if content:
                return content

        try:
            resp = self._client.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            content = html.unescape(resp.text)
        except Exception:  # noqa: BLE001
            return ""

        cache.set_content(content)
        return content

    # ------------------------------------------------------------------
    # State from times
    # ------------------------------------------------------------------

    def get_channel_state_from_times(
        self,
        start_times: list[int],
        end_times: list[int],
        config: object,
    ) -> int:
        if not start_times:
            return EPGEnum.NO_CACHE
        if max(end_times) - min(start_times) > config.min_time_range:  # type: ignore[attr-defined]
            return EPGEnum.FULL_CACHE
        return EPGEnum.PARTIAL_CACHE

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return type(self).__name__
