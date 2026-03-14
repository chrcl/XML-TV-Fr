"""Generator — abstract base class for XMLTV EPG generation.

Migrated from PHP: src/Component/Generator.php
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import date as date_module
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from xmltvfr.domain.static.channel_information import ChannelInformation
from xmltvfr.export.xml_exporter import XmlExporter
from xmltvfr.export.xml_formatter import XmlFormatter
from xmltvfr.providers.cache_file import CacheFile
from xmltvfr.providers.provider_cache import ProviderCache
from xmltvfr.utils import logger
from xmltvfr.utils.utils import extract_provider_name, get_channels_from_guide

if TYPE_CHECKING:
    from xmltvfr.config.configurator import Configurator


class Generator(ABC):
    """Abstract base for EPG generators.

    Subclasses must implement :meth:`_generate_epg`.

    Parameters
    ----------
    start:
        First date to generate EPG for.
    stop:
        Last date to generate EPG for (inclusive).
    configurator:
        The top-level configuration object.
    """

    def __init__(
        self,
        start: date_module,
        stop: date_module,
        configurator: Configurator,
    ) -> None:
        self.configurator = configurator

        # Build the list of date strings from start to stop (inclusive)
        self.list_date: list[str] = []
        current = start
        while current <= stop:
            self.list_date.append(current.isoformat())
            current += timedelta(days=1)

        self.guides: list[dict] = []
        self.providers: list[Any] = []
        self._exporter: XmlExporter | None = None
        self._formatter: XmlFormatter | None = None
        self._cache: CacheFile | None = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def add_guides(self, guides_as_array: list[dict]) -> None:
        """Set the list of guides to generate."""
        self.guides = guides_as_array

    def set_providers(self, providers: list[Any]) -> None:
        """Set the provider list."""
        self.providers = providers

    def get_providers(self, filter_list: list[str] | None = None) -> list[Any]:
        """Return providers, optionally filtered to *filter_list*.

        *filter_list* may contain simple class names (e.g. ``"Orange"``) or
        fully-qualified module paths.  An empty or ``None`` list returns all
        providers.
        """
        if not filter_list:
            return self.providers
        result = []
        for provider in self.providers:
            name = extract_provider_name(provider)
            fqn = f"{type(provider).__module__}.{type(provider).__name__}"
            if name in filter_list or fqn in filter_list:
                result.append(provider)
        return result

    def set_exporter(self, exporter: XmlExporter) -> None:
        """Attach an :class:`~xmltvfr.export.xml_exporter.XmlExporter`."""
        self._exporter = exporter
        self._formatter = exporter.get_formatter()

    def set_cache(self, cache: CacheFile) -> None:
        """Attach a :class:`~xmltvfr.providers.cache_file.CacheFile`."""
        self._cache = cache

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_cache(self) -> CacheFile:
        """Return the cache instance (raises if not yet set)."""
        assert self._cache is not None, "set_cache() must be called before get_cache()"
        return self._cache

    def get_formatter(self) -> XmlFormatter:
        """Return the formatter instance (raises if not yet set)."""
        assert self._formatter is not None, "set_exporter() must be called before get_formatter()"
        return self._formatter

    def get_list_date(self) -> list[str]:
        """Return the list of date strings (``"YYYY-MM-DD"``) for this run."""
        return self.list_date

    # ------------------------------------------------------------------
    # Abstract
    # ------------------------------------------------------------------

    @abstractmethod
    def _generate_epg(self) -> None:
        """Fetch EPG data for all channels in all guides."""

    # ------------------------------------------------------------------
    # Top-level orchestration
    # ------------------------------------------------------------------

    def generate(self) -> None:
        """Generate EPG data, clear provider caches, and save logs."""
        ProviderCache.clear_cache()
        self._generate_epg()
        ProviderCache.clear_cache()
        logger.save()

    def export_epg(self, export_path: str) -> None:
        """Build and write XMLTV output files for every guide.

        Parameters
        ----------
        export_path:
            Directory path where output files are written.  Created if it
            does not exist.
        """
        assert self._exporter is not None, "set_exporter() must be called before export_epg()"
        assert self._cache is not None, "set_cache() must be called before export_epg()"

        os.makedirs(export_path, exist_ok=True)
        default_info = ChannelInformation.get_instance()

        for guide in self.guides:
            channels = get_channels_from_guide(guide)
            self._exporter.start_export(os.path.join(export_path, guide["filename"]))

            list_cache_keys: list[str] = []
            list_aliases: dict[str, str] = {}

            for channel_key, channel_info in channels.items():
                icon = channel_info.get("icon") or default_info.get_default_icon(channel_key)
                name = channel_info.get("name") or default_info.get_default_name(channel_key) or channel_key
                alias = channel_info.get("alias", channel_key)
                if alias != channel_key:
                    list_aliases[channel_key] = alias
                self._exporter.add_channel(alias, name, icon)
                for date_str in self.list_date:
                    list_cache_keys.append(f"{channel_key}_{date_str}.xml")

            for key_cache in list_cache_keys:
                if not self._cache.get_state(key_cache):
                    continue
                try:
                    cache_content = self._cache.get(key_cache)
                except Exception:  # noqa: BLE001
                    continue

                channel_id = key_cache.split("_")[0]
                if channel_id in list_aliases:
                    cache_content = cache_content.replace(
                        f'channel="{channel_id}"',
                        f'channel="{list_aliases[channel_id]}"',
                    )

                try:
                    self._exporter.add_programs_as_string(cache_content)
                except Exception:  # noqa: BLE001
                    self._cache.clear(key_cache)

            self._exporter.stop_export()

    def clear_cache(self, max_cache_day: int) -> None:
        """Remove cache entries older than *max_cache_day* days."""
        assert self._cache is not None, "set_cache() must be called before clear_cache()"
        self._cache.clear_cache(max_cache_day)
