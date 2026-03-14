"""Singleton path resolver for resource files.

Migrated from PHP: src/Component/ResourcePath.php
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import ClassVar


class ResourcePath:
    """Resolves paths to the resources bundled with the xmltvfr package.

    Uses :func:`importlib.resources.files` so that resource files are found
    correctly regardless of whether the package was installed in editable mode
    or as a regular wheel/sdist installation.
    """

    _instance: ClassVar[ResourcePath | None] = None

    def __init__(self) -> None:
        # importlib.resources.files() returns the package root regardless of
        # install mode (editable, wheel, zip-import …).  Converting to a real
        # Path here keeps the rest of the code identical to before.
        self._resource_path: Path = Path(str(importlib.resources.files("xmltvfr") / "resources"))

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

    def get_config_path(self, filename: str) -> Path:
        """Return the path to a default config resource file."""
        return self._resource_path / "config" / filename
