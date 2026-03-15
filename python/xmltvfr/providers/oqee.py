"""Oqee provider — migrated from Oqee.php."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath


class Oqee(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_oqee.json"))
        super().__init__(client, resolved_path, priority)

    @staticmethod
    def _get_custom_match_title(current_title: str, desc: str) -> str:
        teams = re.search(r"opposant (.*?) et (.*?)\.", desc, re.DOTALL)
        if teams:
            return f"{current_title} | {teams.group(1)} / {teams.group(2)}"
        return current_title

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        date_obj = datetime.fromisoformat(f"{date} 00:00+00:00")
        timestamps = [date_obj + timedelta(hours=hours) for hours in (-6, 0, 6, 12, 18, 24)]
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False

        min_date, max_date = self.get_min_max_date(date)
        for timestamp in timestamps:
            payload = safe_json_loads(self._get_content_from_url(self.generate_url(channel_obj, timestamp))) or {}
            entries = (((payload.get("result") or {}).get("entries")) if isinstance(payload, dict) else None) or []
            if not entries:
                return False
            for entry in entries:
                live = entry.get("live") or {}
                start_date = datetime.fromtimestamp(int(live.get("start", 0)), tz=UTC)
                if start_date < min_date:
                    continue
                if start_date > max_date:
                    return channel_obj
                program = Program.with_timestamp(int(live["start"]), int(live["end"]))
                title = live.get("title") or "Aucun titre"
                desc = live.get("description") or "Aucune description"
                if channel.startswith("Ligue1Plus"):
                    title = self._get_custom_match_title(title, desc)
                program.add_title(title)
                program.add_sub_title(live.get("sub_title"))
                program.add_desc(desc)
                program.add_category(live.get("category"))
                program.add_category(live.get("sub_category"))
                program.add_icon(str((entry.get("pictures") or {}).get("main") or "").replace("h%d", "h1080"))
                if live.get("parental_rating"):
                    program.set_rating(f"-{live['parental_rating']}")
                if live.get("audio_description"):
                    program.set_audio_described()
                channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        return f"https://api.oqee.net/api/v1/epg/by_channel/{self._channels_list[channel.id]}/{int(date.timestamp())}"
