"""PlayTV provider — migrated from PlayTV.php."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_UTC = ZoneInfo("UTC")


class PlayTV(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_playtv.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        min_date, _ = self.get_min_max_date(date)
        payload = safe_json_loads(self._get_content_from_url(self.generate_url(channel_obj, min_date))) or {}
        data = payload.get("data") if isinstance(payload, dict) else None
        if not data:
            return False

        for value in data:
            start = datetime.fromisoformat(value["start_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(value["end_at"].replace("Z", "+00:00"))
            program = Program(start, end)
            attrs = ((value.get("media") or {}).get("attrs")) or {}
            category = ((((value.get("media") or {}).get("path") or [{}])[0]).get("category")) or "Inconnu"
            program.add_category(category.capitalize())
            texts = attrs.get("texts") or {}
            program.add_desc(texts.get("long") or texts.get("short") or "Aucune description")
            program.add_title(value.get("title"))
            program.add_sub_title(value.get("subtitle"))
            if attrs.get("episode"):
                program.set_episode_num(attrs.get("season") or "1", attrs.get("episode"))
            images = attrs.get("images") or {}
            image = (((images.get("large") or [{}])[0]).get("url")) or (
                ((images.get("thumbnail") or [{}])[0]).get("url")
            )
            program.add_icon(image)
            channel_obj.add_program(program)
        return channel_obj

    def generate_url(self, channel: Channel, date: datetime) -> str:
        channel_id = self._channels_list[channel.id]
        start_date = date.astimezone(_UTC)
        end_date = start_date + timedelta(days=1)
        return (
            "https://api.playtv.fr/broadcasts?include=media"
            f"&filter[channel_id]={channel_id}"
            f"&filter[airing_between]={start_date.strftime('%Y-%m-%dT%H:%M:%SZ')},{end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )
