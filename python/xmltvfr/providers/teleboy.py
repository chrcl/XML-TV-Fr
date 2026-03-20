"""Teleboy provider — migrated from Teleboy.php."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath


class Teleboy(AbstractProvider):
    _API_KEY: ClassVar[str] = ""

    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_teleboy.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False

        payload = (
            safe_json_loads(
                self._get_content_from_url(
                    self.generate_url(channel_obj, datetime.fromisoformat(date)),
                    headers={"x-teleboy-apikey": self.get_api_key()},
                )
            )
            or {}
        )
        items = (((payload.get("data") or {}).get("items")) if isinstance(payload, dict) else None) or []
        if not items:
            return False

        min_date, _ = self.get_min_max_date(date)
        for item in items:
            start = datetime.fromisoformat(item["begin"].replace("Z", "+00:00"))
            if start < min_date:
                continue
            program = Program.with_timestamp(
                int(start.timestamp()), int(datetime.fromisoformat(item["end"].replace("Z", "+00:00")).timestamp())
            )
            program.add_title(item.get("title"))
            program.add_sub_title(item.get("subtitle"))
            program.add_desc(item.get("short_description") or "Aucune description")
            program.add_category(((item.get("genre") or {}).get("name_fr")) or "Inconnu")
            if item.get("primary_image"):
                primary = item["primary_image"]
                program.add_icon(f"{primary['base_path']}raw/{primary['hash']}.jpg")
            if item.get("is_audio_description"):
                program.set_audio_described()
            if item.get("has_caption"):
                program.add_subtitles("teletext")
            if item.get("country"):
                program.set_country(item["country"])
            if item.get("year"):
                program.set_date(str(item["year"]))
            if item.get("new"):
                program.set_premiere()
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def get_api_key(self) -> str:
        if not type(self)._API_KEY:
            content = self._get_content_from_url("https://www.teleboy.ch/fr/")
            parts = content.split("tvapiKey:", 1)
            if len(parts) < 2:
                raise RuntimeError("API Error")
            key_parts = parts[1].split("'", 2)
            if len(key_parts) < 2 or not key_parts[1]:
                raise RuntimeError("API Error")
            type(self)._API_KEY = key_parts[1]
        return type(self)._API_KEY

    def generate_url(self, channel: Channel, date: datetime) -> str:
        date_start = date.strftime("%Y-%m-%d+00:00:00")
        date_end = date.strftime("%Y-%m-%d+23:59:59")
        channel_id = self._channels_list[channel.id]
        return (
            "https://api.teleboy.ch/epg/broadcasts?"
            f"begin={date_start}&end={date_end}"
            "&expand=flags,primary_image,genre,short_description"
            f"&limit=9999&skip=0&sort=station&station={channel_id}"
        )
