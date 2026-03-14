"""Program value object — an XMLTV ``<programme>`` element.

Migrated from PHP: src/ValueObject/Program.php
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from xmltvfr.domain.models.tag import Tag

_PARIS_TZ = ZoneInfo("Europe/Paris")


class Program(Tag):
    """An XMLTV programme element with strongly-typed start/stop times.

    The ``start`` and ``stop`` XML attributes are automatically set from the
    supplied datetime objects (converted to Europe/Paris before formatting).
    """

    SORTED_CHILDREN: list[str] = [
        "title",
        "sub-title",
        "desc",
        "credits",
        "date",
        "category",
        "keyword",
        "language",
        "orig-language",
        "length",
        "icon",
        "url",
        "country",
        "episode-num",
        "video",
        "audio",
        "previously-shown",
        "premiere",
        "last-chance",
        "new",
        "subtitles",
        "rating",
        "star-rating",
        "review",
        "audio-described",
    ]

    SORTED_CREDITS: list[str] = [
        "director",
        "actor",
        "writer",
        "adapter",
        "producer",
        "composer",
        "editor",
        "presenter",
        "commentator",
        "guest",
    ]

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def with_timestamp(cls, start: int, end: int) -> Program:
        """Create a Program from Unix timestamps (seconds since epoch)."""
        start_dt = datetime.fromtimestamp(start, tz=UTC)
        end_dt = datetime.fromtimestamp(end, tz=UTC)
        return cls(start=start_dt, end=end_dt)

    def __init__(self, start: datetime, end: datetime) -> None:
        if start > end:
            raise ValueError(f"Start date ({start}) must be before end date ({end})")

        # Convert to Europe/Paris for display and storage
        self._start: datetime = start.astimezone(_PARIS_TZ)
        self._end: datetime = end.astimezone(_PARIS_TZ)

        attributes = {
            "start": self._start.strftime("%Y%m%d%H%M%S %z"),
            "stop": self._end.strftime("%Y%m%d%H%M%S %z"),
        }
        super().__init__(
            name="programme",
            value={},
            attributes=attributes,
            sorted_children=self.SORTED_CHILDREN,
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_start(self) -> datetime:
        """Return the program start datetime (Europe/Paris)."""
        return self._start

    def get_end(self) -> datetime:
        """Return the program end datetime (Europe/Paris)."""
        return self._end

    # ------------------------------------------------------------------
    # Child element builders
    # ------------------------------------------------------------------

    def add_title(self, title: str | None, lang: str = "fr") -> None:
        """Add a ``<title>`` element (no-op if *title* is empty/None)."""
        if title:
            self.add_child(Tag("title", title, {"lang": lang}))

    def add_sub_title(self, subtitle: str | None, lang: str = "fr") -> None:
        """Add a ``<sub-title>`` element (no-op if *subtitle* is empty/None)."""
        if subtitle:
            self.add_child(Tag("sub-title", subtitle, {"lang": lang}))

    def add_desc(self, desc: str | None, lang: str = "fr") -> None:
        """Add a ``<desc>`` element (no-op if *desc* is empty/None)."""
        if desc:
            self.add_child(Tag("desc", desc, {"lang": lang}))

    def add_category(self, category: str | None, lang: str = "fr") -> None:
        """Add a ``<category>`` element (no-op if *category* is empty/None)."""
        if category:
            self.add_child(Tag("category", category, {"lang": lang}))

    def add_keyword(self, keyword: str, lang: str | None = None) -> None:
        """Add a ``<keyword>`` element."""
        self.add_child(Tag("keyword", keyword, {"lang": lang}))

    def add_icon(self, icon: str | None, width: str | None = None, height: str | None = None) -> None:
        """Add an ``<icon>`` element (no-op if *icon* is empty/None)."""
        if icon:
            self.add_child(Tag("icon", None, {"src": icon, "width": width, "height": height}))

    def add_credit(self, name: str | None, type_: str = "guest") -> None:
        """Add a person credit inside the ``<credits>`` block.

        If *type_* is not a recognised credit role it falls back to ``"guest"``.
        No-op if *name* is empty/None.
        """
        if not name:
            return
        if type_ not in self.SORTED_CREDITS:
            type_ = "guest"

        existing = self.get_children("credits")
        if existing:
            credit_tag = existing[0]
        else:
            credit_tag = Tag("credits", None, {}, self.SORTED_CREDITS)
            self.set_child(credit_tag)

        credit_tag.add_child(Tag(type_, name))

    def add_star_rating(self, stars: int | float, total_stars: int, system: str | None = None) -> None:
        """Add a ``<star-rating>`` element."""
        self.add_child(
            Tag(
                "star-rating",
                {"value": [Tag("value", f"{stars}/{total_stars}")]},
                {"system": system},
            )
        )

    def add_review(self, review: str, source: str | None = None, reviewer: str | None = None) -> None:
        """Add a ``<review>`` element of type ``text``."""
        self.add_child(
            Tag(
                "review",
                review,
                {"source": source, "reviewer": reviewer, "type": "text"},
            )
        )

    def add_subtitles(self, type_: str, lang: str | None = None) -> None:
        """Add a ``<subtitles>`` element."""
        self.add_child(Tag("subtitles", None, {"type": type_, "lang": lang}))

    def set_audio_described(self) -> None:
        """Mark the program as audio-described.

        Also appends an ``audio-description`` keyword for applications that do
        not support the non-standard ``<audio-described>`` tag.
        """
        self.set_child(Tag("audio-described", None, {}))
        for keyword in self.get_children("keyword"):
            if isinstance(keyword, Tag) and keyword.value == "audio-description":
                return
        self.add_keyword("audio-description")

    def set_previously_shown(self, start: datetime | None = None, channel: str | None = None) -> None:
        """Set the ``<previously-shown>`` element."""
        start_str: str | None = None
        if start is not None:
            start_str = start.astimezone(_PARIS_TZ).strftime("%Y%m%d%H%M%S %z")
        self.set_child(Tag("previously-shown", None, {"start": start_str, "channel": channel}))

    def set_premiere(self, value: str | None = None, lang: str | None = None) -> None:
        """Set the ``<premiere>`` element."""
        self.set_child(Tag("premiere", value, {"lang": lang}))

    def set_date(self, date: str) -> None:
        """Set the ``<date>`` element."""
        self.set_child(Tag("date", date, {}))

    def set_country(self, country: str, lang: str | None = None) -> None:
        """Set the ``<country>`` element."""
        self.set_child(Tag("country", country, {"lang": lang}))

    def set_episode_num(self, season: int | str | None, episode: int | str | None) -> None:
        """Set the ``<episode-num>`` in ``xmltv_ns`` format (0-indexed).

        No-op if both *season* and *episode* are falsy (``None`` or ``0``).
        """
        if not season and not episode:
            return

        s = max(int(season or 0) - 1, 0)
        e = max(int(episode or 0) - 1, 0)
        self.set_child(Tag("episode-num", f"{s}.{e}.", {"system": "xmltv_ns"}))

    def set_rating(self, rating: str | int | None, system: str = "CSA") -> None:
        """Set the ``<rating>`` element, including an icon if a picto is found."""
        if rating is None:
            return

        # Lazy import to avoid circular dependencies at module load time
        from xmltvfr.domain.static.rating_picto import RatingPicto  # noqa: PLC0415

        picto = RatingPicto.get_instance().get_picto_from_rating_system(str(rating), system)
        children: dict[str, list[Tag]] = {"value": [Tag("value", str(rating))]}
        if picto is not None:
            children["icon"] = [Tag("icon", None, {"src": picto})]
        self.set_child(Tag("rating", children, {"system": system}))
