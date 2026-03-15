"""TV5 provider — migrated from TV5.php."""

from __future__ import annotations

from datetime import datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_HEADERS = {
    "Host": "bo-apac.tv5monde.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8"
    ),
    "Accept-Language": "fr-FR,fr-CA;q=0.8,en;q=0.5,en-US;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "DNT": "1",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Priority": "u=0, i",
}


class TV5(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_tv5.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        payload = (
            safe_json_loads(
                self._get_content_from_url(
                    self.generate_url(channel_obj, datetime.fromisoformat(date)), headers=dict(_HEADERS)
                )
            )
            or {}
        )
        items = payload.get("data") if isinstance(payload, dict) else None
        if not items:
            return False
        for value in items:
            program = Program.with_timestamp(
                int(datetime.fromisoformat(f"{value['utcstart']}+00:00").timestamp()),
                int(datetime.fromisoformat(f"{value['utcend']}+00:00").timestamp()),
            )
            program.add_title(value.get("title"))
            program.add_desc(value.get("description") or "Pas de description")
            program.add_category(value.get("category"))
            program.add_icon(value.get("image") or "")
            if value.get("season") is not None:
                program.add_sub_title(value.get("episode_name"))
                program.set_episode_num(value.get("season") or "1", value.get("episode") or "1")
            channel_obj.add_program(program)
        return channel_obj

    def generate_url(self, channel: Channel, date: datetime) -> str:
        channel_id = self._channels_list[channel.id]
        start = date.strftime("%Y-%m-%dT00:00:00")
        end = (date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        return (
            "https://bo-apac.tv5monde.com/tvschedule/full"
            f"?start={start}&end={end}"
            f"&key={channel_id}&timezone=Europe/Paris&language=EN"
        )
