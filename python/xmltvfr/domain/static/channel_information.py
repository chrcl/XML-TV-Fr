"""Singleton channel information lookup.

Migrated from PHP: src/StaticComponent/ChannelInformation.php
"""

from __future__ import annotations

import json
from typing import ClassVar

from xmltvfr.utils.resource_path import ResourcePath


class ChannelInformation:
    """Provides default channel name and icon lookups from the channels info JSON resource."""

    _instance: ClassVar[ChannelInformation | None] = None

    def __init__(self) -> None:
        path = ResourcePath.get_instance().get_channel_info_path()
        with path.open(encoding="utf-8") as fh:
            self._channel_info: dict[str, dict[str, str]] = json.load(fh)

    @classmethod
    def get_instance(cls) -> ChannelInformation:
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_channel_info(self) -> dict[str, dict[str, str]]:
        """Return the full channel info dictionary."""
        return self._channel_info

    def get_default_icon(self, channel_key: str) -> str | None:
        """Return the default icon URL for a channel key, or ``None`` if not found."""
        return self._channel_info.get(channel_key, {}).get("icon")

    def get_default_name(self, channel_key: str) -> str | None:
        """Return the default display name for a channel key, or ``None`` if not found."""
        return self._channel_info.get(channel_key, {}).get("name")
