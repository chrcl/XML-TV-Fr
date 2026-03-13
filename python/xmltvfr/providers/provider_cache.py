"""Provider-level HTTP response cache.

Migrated from PHP: src/Component/ProviderCache.php
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from xmltvfr.utils.utils import recurse_rmdir


class ProviderCache:
    """Stores and retrieves cached provider HTTP responses on disk.

    Files are stored under ``var/provider/`` relative to the current
    working directory, matching the PHP behaviour.
    """

    _PATH: str = "var/provider/"

    def __init__(self, file: str) -> None:
        self._file = file

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_content(self) -> str | None:
        """Return raw file content, or ``None`` if the cache file is absent."""
        path = Path(self._PATH) / self._file
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def get_array(self) -> dict:
        """Return the cached content parsed as a JSON object (default: ``{}``)."""
        content = self.get_content() or "{}"
        try:
            result = json.loads(content)
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError:
            return {}

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def set_array_key(self, key: str, content: object) -> None:
        """Load the cached dict, set *key* to *content*, then persist it."""
        array = self.get_array()
        array[key] = content
        self.set_content(json.dumps(array))

    def set_content(self, content: str) -> None:
        """Create the cache directory if needed, then write *content* to disk."""
        os.makedirs(self._PATH, exist_ok=True)
        path = Path(self._PATH) / self._file
        path.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    @classmethod
    def clear_cache(cls) -> None:
        """Recursively remove the entire ``var/provider/`` directory."""
        recurse_rmdir(cls._PATH)
