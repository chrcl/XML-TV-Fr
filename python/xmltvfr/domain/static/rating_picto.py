"""Singleton ratings-picto lookup.

Migrated from PHP: src/StaticComponent/RatingPicto.php
"""

from __future__ import annotations

import json
from typing import ClassVar

from xmltvfr.utils.resource_path import ResourcePath


class RatingPicto:
    """Maps rating labels to icon URLs, loaded from the ratings_picto.json resource."""

    _instance: ClassVar[RatingPicto | None] = None

    def __init__(self) -> None:
        path = ResourcePath.get_instance().get_rating_picto_path()
        with path.open(encoding="utf-8") as fh:
            self._rating_picto_info: dict[str, dict[str, str]] = json.load(fh)

    @classmethod
    def get_instance(cls) -> RatingPicto:
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_picto_from_rating_system(self, rating: str | None, system: str | None) -> str | None:
        """Return the icon URL for the given rating and system, or ``None`` if not found."""
        if rating is None or system is None:
            return None
        return self._rating_picto_info.get(system.lower(), {}).get(rating.lower())
