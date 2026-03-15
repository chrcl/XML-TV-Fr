"""Telerama provider — Python equivalent of Telerama.php.

Fetches EPG data from the Telerama API and maps it to the xmltvfr domain model.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_PARIS_TZ = ZoneInfo("Europe/Paris")

_HOST = "https://apps.telerama.fr/tlr/v1/free-android-phone/"
_USER_AGENT = (
    "TLR/4.11 (free; fr; ABTest 322) Android/13/33 (tablet; Galaxy Tab S6 Samsung Device)"
)
_HEADERS = {"User-Agent": _USER_AGENT}

_CSA_RATINGS = (10, 12, 16, 18)


class Telerama(AbstractProvider):
    """Provider that retrieves EPG data from the Telerama API."""

    def __init__(
        self,
        client: requests.Session,
        _json_path: str,  # noqa: ARG002 — ignored; path resolved via ResourcePath
        priority: float,
        extra_params: dict | None = None,
    ) -> None:
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_telerama.json"))
        super().__init__(client, resolved_path, priority)

        params = extra_params or {}
        self._enable_details: bool = bool(params.get("telerama_enable_details", True))

    # ------------------------------------------------------------------
    # URL builder
    # ------------------------------------------------------------------

    def generate_url(self, date: datetime) -> str:
        """Return the API URL for the programme grid of *date*."""
        return f"{_HOST}tv-program/grid?date={date.strftime('%Y-%m-%d')}"

    # ------------------------------------------------------------------
    # EPG construction
    # ------------------------------------------------------------------

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        """Build a :class:`~xmltvfr.domain.models.channel.Channel` for *channel* on *date*.

        Returns ``False`` when the channel is not supported by this provider.
        """
        channel_obj: Channel = super().construct_epg(channel, date)

        if not self.channel_exists(channel):
            return False

        channel_id = self.get_channels_list()[channel]

        # Parse target date (naive → Paris TZ)
        target_dt = datetime.fromisoformat(date).replace(tzinfo=_PARIS_TZ)
        day_before_dt = target_dt - timedelta(days=1)

        # Fetch raw JSON for the day before and the target day
        content_day_before = self._get_content_from_url(
            self.generate_url(day_before_dt), headers=dict(_HEADERS)
        )
        content = self._get_content_from_url(
            self.generate_url(target_dt), headers=dict(_HEADERS)
        )

        try:
            json_day_before: dict = json.loads(content_day_before)
        except (json.JSONDecodeError, ValueError):
            json_day_before = {}

        try:
            json_today: dict = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            json_today = {}

        broadcasts_before: list[dict] = self._extract_broadcasts(json_day_before, channel_id)
        broadcasts_today: list[dict] = self._extract_broadcasts(json_today, channel_id)
        channel_programs: list[dict] = broadcasts_before + broadcasts_today

        count = len(channel_programs)
        min_date, max_date = self.get_min_max_date(date)

        for index, program in enumerate(channel_programs):
            percent = f"{round(index * 100 / count, 2) if count else 0} %"
            self.set_status(percent)

            start_str: str | None = program.get("start_date")
            if not start_str:
                continue

            try:
                program_start = datetime.fromisoformat(start_str).astimezone(_PARIS_TZ)
            except (ValueError, TypeError):
                continue

            if program_start < min_date:
                continue
            if program_start > max_date:
                return channel_obj

            channel_obj.add_program(self._generate_program(program))

        return channel_obj

    # ------------------------------------------------------------------
    # Broadcasts helper
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_broadcasts(json_data: dict, channel_id: str) -> list[dict]:
        """Extract the broadcast list for *channel_id* from a parsed API response dict."""
        return json_data.get("channels", {}).get(channel_id, {}).get("broadcasts", []) or []

    # ------------------------------------------------------------------
    # Program factory
    # ------------------------------------------------------------------

    def _generate_program(self, program: dict) -> Program:
        """Convert a raw Telerama broadcast dict into a :class:`~xmltvfr.domain.models.program.Program`."""
        start_ts = int(datetime.fromisoformat(program["start_date"]).timestamp())
        end_ts = int(datetime.fromisoformat(program["end_date"]).timestamp())
        program_obj = Program.with_timestamp(start_ts, end_ts)

        program_obj.add_title(program.get("title") or "Aucun titre")

        raw_type = program.get("type") or "Aucune catégorie"
        program_obj.add_category(re.sub(r"<[^>]+>", "", raw_type).capitalize())

        if program.get("is_inedit"):
            program_obj.set_premiere()

        illustration = program.get("illustration") or {}
        img_url: str | None = illustration.get("url")
        if img_url:
            img_url = img_url.replace("{{width}}", "1280").replace("{{height}}", "720")
            program_obj.add_icon(img_url)

        flags: list[str] = program.get("flags") or []
        for csa_rating in _CSA_RATINGS:
            if f"moins-de-{csa_rating}" in flags:
                program_obj.set_rating(csa_rating)

        if "audiodescription" in flags:
            program_obj.set_audio_described()

        if "teletexte" in flags:
            program_obj.add_subtitles("teletext")

        deeplink: str | None = program.get("deeplink")
        if self._enable_details and deeplink:
            self._assign_details(program_obj, deeplink)

        return program_obj

    # ------------------------------------------------------------------
    # Detail enrichment (optional)
    # ------------------------------------------------------------------

    def _assign_details(self, program_obj: Program, deeplink: str) -> None:
        """Enrich *program_obj* with metadata fetched from the Telerama detail API."""
        clean_deeplink = deeplink.replace("tlrm://", "")
        detail_url = f"{_HOST}{clean_deeplink}"

        raw = self._get_content_from_url(detail_url, headers=dict(_HEADERS))
        try:
            details: dict = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return

        content: str | None = (
            details.get("templates", {}).get("raw_content", {}).get("content")
        )
        if not content:
            return

        # Season / episode
        season = self._get_element_value(content, "Saison")
        episode_raw = self._get_element_value(content, "\u00c9pisode")
        episode = episode_raw.split("/")[0] if episode_raw else None
        if season or episode:
            program_obj.set_episode_num(season, episode)

        # Synopsis
        synopsis_match = re.search(
            r'<p class="sheet__synopsis-content">(.*?)</p>', content, re.DOTALL
        )
        if synopsis_match:
            program_obj.add_desc(synopsis_match.group(1))

        # Sub-title from article subtitle
        subtitle_match = re.search(
            r'<p class="article__page-subtitle">(.*?)</p>', content, re.DOTALL
        )
        if subtitle_match:
            program_obj.add_sub_title(subtitle_match.group(1))

        # Sub-title from episode title field
        episode_title = self._get_element_value(content, "Titre de l\u2019\u00e9pisode")
        if episode_title:
            program_obj.add_sub_title(episode_title)

        # Credits
        scenario = self._get_element_value(content, "Sc\u00e9nario")
        if scenario:
            program_obj.add_credit(scenario, "writer")

        director = self._get_element_value(content, "R\u00e9alisateur")
        if director:
            program_obj.add_credit(director, "director")

        presenter = self._get_element_value(content, "Pr\u00e9sentateur")
        if presenter:
            program_obj.add_credit(presenter, "presenter")

        # Genre (additional category)
        genre = self._get_element_value(content, "Genre")
        if genre:
            program_obj.add_category(re.sub(r"<[^>]+>", "", genre))

        # Casting
        casting_matches = re.findall(
            r'<p class="sheet__info-item-label sheet__info-item-label--casting">(.*?)</p>'
            r".*?"
            r'<p class="sheet__info-item-value">(.*?)</p>',
            content,
            re.DOTALL,
        )
        for actor_name, actor_role in casting_matches:
            program_obj.add_credit(f"{actor_name} ({actor_role})", "actor")

    # ------------------------------------------------------------------
    # HTML helper
    # ------------------------------------------------------------------

    def _get_element_value(self, content: str, element: str) -> str | None:
        """Extract the value of a ``sheet__info-item-value`` paragraph following *element*.

        Mirrors PHP's ``getElementValue`` method.
        """
        pattern = (
            r'<p class="sheet__info-item-label">'
            + re.escape(element)
            + r"</p>.*?"
            r'<p class="sheet__info-item-value">(.*?)</p>'
        )
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None
