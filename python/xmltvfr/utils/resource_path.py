"""Singleton path resolver for resource files.

Migrated from PHP: src/Component/ResourcePath.php
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar


class ResourcePath:
    """Resolves paths to the resources/ directory at the repo root."""

    _instance: ClassVar[ResourcePath | None] = None

    def __init__(self) -> None:
        # __file__ is python/xmltvfr/utils/resource_path.py
        # parents[0] = utils/, parents[1] = xmltvfr/, parents[2] = python/, parents[3] = repo root
        self._resource_path: Path = Path(__file__).parents[3] / "resources"

    @classmethod
    def get_instance(cls) -> ResourcePath:
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_channel_path(self, channel: str) -> Path:
        """Return the path to a channel config file."""
        return self._resource_path / "channel_config" / channel

    def get_channel_info_path(self) -> Path:
        """Return the path to the default channels info JSON file."""
        return self._resource_path / "information" / "default_channels_infos.json"

    def get_rating_picto_path(self) -> Path:
        """Return the path to the ratings picto JSON file."""
        return self._resource_path / "information" / "ratings_picto.json"
