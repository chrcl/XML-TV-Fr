"""Tele7Jours provider — Python equivalent of Tele7Jours.php.

Fetches EPG data from programme-television.org (Télé 7 Jours) and maps it
to the xmltvfr domain model.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_PARIS_TZ = ZoneInfo("Europe/Paris")

# French day names keyed by Python's strftime('%a') short name (locale-independent)
_DAYS: dict[str, str] = {
    "Mon": "lundi",
    "Tue": "mardi",
    "Wed": "mercredi",
    "Thu": "jeudi",
    "Fri": "vendredi",
    "Sat": "samedi",
    "Sun": "dimanche",
}

# Fallback duration when the HTML does not contain a duration field
_DEFAULT_PROGRAM_DURATION_MINUTES = 30
# Fallback season number when an episode marker (e.g. "E3") has no season component
_DEFAULT_SEASON = 1


class Tele7Jours(AbstractProvider):
    """Provider that retrieves EPG data from programme-television.org (Télé 7 Jours)."""

    def __init__(
        self,
        client: requests.Session,
        _json_path: str,  # noqa: ARG002 — ignored; path resolved via ResourcePath
        priority: float,
        extra_params: dict | None = None,
    ) -> None:
        resolved_path = str(
            ResourcePath.get_instance().get_channel_path("channels_tele7jours.json")
        )
        super().__init__(client, resolved_path, priority)

        params = extra_params or {}
        self._enable_details: bool = bool(params.get("tele7jours_enable_details", True))

    # ------------------------------------------------------------------
    # Day label
    # ------------------------------------------------------------------

    @staticmethod
    def _get_day_label(date: datetime) -> str:
        """Return the French day-label segment used in programme-television.org URLs.

        The label is one of: ``''`` (today), ``'hier'`` (yesterday), a French
        weekday name (e.g. ``'lundi'``), or a weekday name suffixed with
        ``'prochain'`` when the date is more than six days away.

        Args:
            date: The target date.  Timezone-naive values are treated as
                  Europe/Paris.

        Raises:
            ValueError: When *date* is strictly before yesterday.
        """
        today = datetime.now(_PARIS_TZ).replace(hour=0, minute=0, second=0, microsecond=0)

        # Normalise to midnight Paris time so date comparisons are by calendar day
        date_normalized = date.replace(hour=0, minute=0, second=0, microsecond=0)
        if date_normalized.tzinfo is None:
            date_normalized = date_normalized.replace(tzinfo=_PARIS_TZ)
        else:
            date_normalized = date_normalized.astimezone(_PARIS_TZ).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        yesterday = today - timedelta(days=1)
        week_after = today + timedelta(days=6)

        if date_normalized < yesterday:
            raise ValueError(f"Date is too early: {date_normalized.date()}")

        if date_normalized.date() == yesterday.date():
            return "hier"

        if date_normalized.date() == today.date():
            return ""

        day_abbr = date_normalized.strftime("%a")  # Mon, Tue, …
        day_label = _DAYS.get(day_abbr)
        if not day_label:
            raise ValueError(f"Invalid day abbreviation: {day_abbr!r}")

        if date_normalized > week_after:
            day_label += "prochain"

        return day_label

    # ------------------------------------------------------------------
    # URL builder
    # ------------------------------------------------------------------

    def generate_url(self, channel: Channel, day_label: str) -> str:
        """Return the programme page URL for *channel* on *day_label*.

        Args:
            channel: The channel whose slug is looked up in the channels list.
            day_label: French day label as returned by :meth:`_get_day_label`.
        """
        channel_slug: str = self._channels_list[channel.id]
        return f"https://www.programme-television.org/tv/chaines/{channel_slug}/{day_label}"

    # ------------------------------------------------------------------
    # Program parser
    # ------------------------------------------------------------------

    def _parse_program(self, date: str, p: str) -> Program | None:
        """Parse a single HTML broadcast block into a :class:`Program`.

        Args:
            date: ISO-format date string (``YYYY-MM-DD``) for the broadcast day.
            p:    Raw HTML fragment for one broadcast item.

        Returns:
            A fully populated :class:`Program`, or ``None`` when mandatory
            fields (start time or title) cannot be extracted.
        """
        start_time_m = re.search(
            r'<div class="tvgrid-broadcast__details-time">(.*?)</div>', p, re.DOTALL
        )
        title_m = re.search(
            r'<div class="tvgrid-broadcast__details-title">(.*?)</div>', p, re.DOTALL
        )
        subtitle_details_m = re.search(
            r'<div class="tvgrid-broadcast__details-season">(.*?)</div>', p, re.DOTALL
        )
        sub_details_m = re.search(
            r'<div class="tvgrid-broadcast__subdetails">(.*?)</div>', p, re.DOTALL
        )
        imgs_m = re.search(r'srcset="(.*?)"', p, re.DOTALL)
        url_m = re.search(r'href="(.*?)"', p, re.DOTALL)

        if not start_time_m or not title_m:
            return None

        # Convert "20h35" → "20:35"
        raw_time = start_time_m.group(1).strip().replace("h", ":")
        try:
            start_dt = datetime.fromisoformat(f"{date} {raw_time}").replace(tzinfo=_PARIS_TZ)
        except ValueError:
            return None

        # Parse sub-details: duration and première flag
        end_dt: datetime | None = None
        is_premiere = False
        sub_details_parts: list[str] = []

        if sub_details_m:
            sub_details_parts = sub_details_m.group(1).split("|")
            for sub_detail in sub_details_parts:
                sub_detail = sub_detail.strip()
                if sub_detail.endswith("mn"):
                    minutes_str = sub_detail[:-2].strip()
                    try:
                        minutes = int(minutes_str)
                        end_dt = start_dt + timedelta(minutes=minutes)
                    except ValueError:
                        pass
                elif sub_detail == "Inédit":
                    is_premiere = True

        # Fallback end time so Program.__init__ never receives None
        if end_dt is None:
            end_dt = start_dt + timedelta(minutes=_DEFAULT_PROGRAM_DURATION_MINUTES)

        program_obj = Program(start_dt, end_dt)

        if is_premiere:
            program_obj.set_premiere()

        # Title (strip any inline HTML tags)
        title_text = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
        program_obj.add_title(title_text)

        # Category: last pipe-separated item in sub_details
        if sub_details_parts:
            category = sub_details_parts[-1].strip()
            program_obj.add_category(category)

        # Subtitle / season-episode block
        if subtitle_details_m:
            subtitle_items: list[str] = []
            for subtitle_detail in subtitle_details_m.group(1).split("|"):
                subtitle_detail = subtitle_detail.strip()
                episode_m = re.match(r"^(?:S(\d+)\s*)?E(\d+)$", subtitle_detail, re.IGNORECASE)
                if episode_m:
                    season = int(episode_m.group(1)) if episode_m.group(1) else _DEFAULT_SEASON
                    episode = int(episode_m.group(2))
                    program_obj.set_episode_num(season, episode)
                else:
                    subtitle_items.append(subtitle_detail)
            if subtitle_items:
                program_obj.add_sub_title(" | ".join(subtitle_items))

        # Thumbnail image (last entry in srcset, highest resolution)
        if imgs_m:
            img_parts = imgs_m.group(1).split(",")
            last_img = img_parts[-1].strip().split(" ")[0]
            if last_img:
                program_obj.add_icon(last_img)

        # Optional detail-page enrichment
        if self._enable_details and url_m:
            self.add_details(program_obj, url_m.group(1))

        return program_obj

    # ------------------------------------------------------------------
    # Detail enrichment (optional)
    # ------------------------------------------------------------------

    @staticmethod
    def _get_tag_name(casting_tag: str) -> str:
        """Map a French casting-role label to an XMLTV credit type.

        Args:
            casting_tag: French role label (e.g. ``'Réalisateur'``).

        Returns:
            An XMLTV credit type string (``'director'``, ``'producer'``, or
            ``'guest'`` for everything else).
        """
        return {"Réalisateur": "director", "Producteur": "producer"}.get(casting_tag, "guest")

    def add_details(self, program_obj: Program, url: str) -> None:
        """Enrich *program_obj* with description and credits fetched from *url*.

        Args:
            program_obj: The program to enrich in-place.
            url:         Detail page URL on programme-television.org.
        """
        content = self._get_content_from_url(url)

        casting_matches = re.findall(
            r'<li class="casting__item">.*?'
            r'<p class="casting__name">(.*?)</p>.*?'
            r'<span class="casting__role">(.*?)</span>.*?'
            r"</li>",
            content,
            re.DOTALL,
        )
        for actor_name, role in casting_matches:
            tag = self._get_tag_name(role)
            if tag == "guest":
                program_obj.add_credit(f"{actor_name} ({role})", tag)
            else:
                program_obj.add_credit(actor_name, tag)

        details_m = re.search(
            r'<p class="program-details__summary-text">(.*?)</p>', content, re.DOTALL
        )
        if details_m:
            desc = re.sub(r"<[^>]+>", "", details_m.group(1)).strip()
            program_obj.add_desc(desc)

    # ------------------------------------------------------------------
    # EPG construction
    # ------------------------------------------------------------------

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        """Build a :class:`~xmltvfr.domain.models.channel.Channel` for *channel* on *date*.

        Args:
            channel: Channel identifier (e.g. ``'TF1.fr'``).
            date:    ISO-format date string (``YYYY-MM-DD``).

        Returns:
            A populated :class:`Channel` on success, or ``False`` when the
            channel is not supported by this provider or the date is out of
            the scraping window.
        """
        channel_obj: Channel = super().construct_epg(channel, date)

        if not self.channel_exists(channel):
            return False

        min_date, _ = self.get_min_max_date(date)

        try:
            day_label = self._get_day_label(min_date)
        except ValueError:
            return False

        content = self._get_content_from_url(self.generate_url(channel_obj, day_label))

        # Split on the broadcast item class to get individual program blocks
        programs = content.split('class="tvgrid-broadcast__item')
        count = len(programs)

        for i in range(1, count):
            percent = f"{round(i * 100 / count, 2)} %"
            self.set_status(percent)

            program_obj = self._parse_program(date, programs[i])
            if program_obj is not None:
                channel_obj.add_program(program_obj)

        return channel_obj
