"""CacheFile — Python equivalent of CacheFile.php."""

from __future__ import annotations

import os
import time
from datetime import date as date_module
from pathlib import Path

from xmltvfr.domain.models.epg_enum import EPGEnum
from xmltvfr.utils.utils import get_time_range_from_xml_string


class CacheFile:
    def __init__(self, base_path: str, config: object) -> None:
        os.makedirs(base_path, exist_ok=True)
        self._base_path = base_path.rstrip(os.sep)
        self._config = config
        self._list_file: dict[str, dict] = {}
        self._created_keys: set[str] = set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_file_name(self, key: str) -> Path:
        return Path(self._base_path) / key

    def _get_file_content(self, key: str) -> str:
        return self._get_file_name(key).read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, key: str, content: str) -> None:
        file_name = self._get_file_name(key)
        file_name.write_text(content, encoding="utf-8")
        self._created_keys.add(key)
        self._list_file[key] = {
            "file": str(file_name),
            "key": key,
            "state": self.get_state(key),
        }

    def get_provider_name(self, key: str) -> str:
        """Read first line of cache file and extract provider name."""
        try:
            with open(self._get_file_name(key), encoding="utf-8") as fh:
                line = fh.readline()
        except Exception:  # noqa: BLE001
            return "Unknown"

        # PHP format:    <!-- racacax\XmlTv\Component\Provider\ProviderName -->
        # Python format: <!-- xmltvfr.providers.provider_name.ProviderName -->
        if "<!-- " in line and " -->" in line:
            inner = line.split("<!-- ")[1].split(" -->")[0]
            return inner.split("\\")[-1].split(".")[-1]
        return "Unknown"

    def get_state(self, key: str) -> int:
        if key in self._list_file:
            return self._list_file[key]["state"]

        file_path = self._get_file_name(key)
        today = date_module.today().isoformat()

        if today in key and getattr(self._config, "force_today_grab", False) and key not in self._created_keys:
            return EPGEnum.OBSOLETE_CACHE if file_path.exists() else EPGEnum.NO_CACHE

        if file_path.exists():
            time_range = get_time_range_from_xml_string(self._get_file_content(key))
            min_time_range = getattr(self._config, "min_time_range", 22 * 3600)
            return EPGEnum.FULL_CACHE if time_range >= min_time_range else EPGEnum.PARTIAL_CACHE

        return EPGEnum.NO_CACHE

    def get(self, key: str) -> str:
        if not self.get_state(key):
            raise Exception(f"Cache '{key}' not found")
        return self._get_file_content(key)

    def clear(self, key: str) -> bool:
        if not self.get_state(key):
            raise Exception(f"Cache '{key}' not found")
        file_path = self._get_file_name(key)
        self._list_file.pop(key, None)
        self._created_keys.discard(key)
        file_path.unlink()
        return True

    def clear_cache(self, max_cache_day: int) -> None:
        base = Path(self._base_path)
        if not base.exists():
            return
        now = time.time()
        for file_path in base.iterdir():
            if file_path.is_file() and (now - file_path.stat().st_mtime) >= 86400 * max_cache_day:
                file_path.unlink()
