"""Proximus provider — migrated from Proximus.php."""

from __future__ import annotations

import re
from datetime import datetime
from typing import ClassVar

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Accept": "*/*",
    "Accept-Language": "fr-FR,fr-CA;q=0.8,en;q=0.5,en-US;q=0.3",
    "Origin": "https://www.pickx.be",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "cross-site",
    "TE": "trailers",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Referer": "https://www.pickx.be/",
}
_CSA = {"10": "-10", "12": "-12", "16": "-16", "18": "-18"}


class Proximus(AbstractProvider):
    _VERSION: ClassVar[str | None] = None

    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_proximus.json"))
        super().__init__(client, resolved_path, priority)

    def get_version(self) -> str:
        if type(self)._VERSION is None:
            content = self._get_content_from_url(
                "https://www.pickx.be/fr/television/programme-tv",
                headers=dict(_HEADERS),
                ignore_cache=True,
            )
            match = re.search(r'"hashes":\["(.*?)"\]', content)
            if not match:
                raise RuntimeError("No access to Proximus API")
            payload = (
                safe_json_loads(
                    self._get_content_from_url(
                        f"https://www.pickx.be/api/s-{match.group(1)}",
                        headers=dict(_HEADERS),
                        ignore_cache=True,
                    )
                )
                or {}
            )
            version = payload.get("version") if isinstance(payload, dict) else None
            if not version:
                raise RuntimeError("No access to Proximus API")
            type(self)._VERSION = str(version)
        return type(self)._VERSION

    @staticmethod
    def _format_category(category: str) -> str:
        return category.split("C.")[-1]

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        payload = safe_json_loads(
            self._get_content_from_url(
                self.generate_url(channel_obj, datetime.fromisoformat(date)),
                headers=dict(_HEADERS),
            )
        )
        programs = payload if isinstance(payload, list) else []
        if not programs:
            return False

        min_date, max_date = self.get_min_max_date(date)
        for item in programs:
            start_date = datetime.fromisoformat(item["programScheduleStart"].replace("Z", "+00:00"))
            if start_date < min_date:
                continue
            if start_date > max_date:
                break
            raw_program = item.get("program") or {}
            csa = _CSA.get(str(raw_program.get("VCHIP") or ""), "Tout public")
            program = Program.with_timestamp(
                int(start_date.timestamp()),
                int(datetime.fromisoformat(item["programScheduleEnd"].replace("Z", "+00:00")).timestamp()),
            )
            program.add_title(raw_program.get("title") or "Aucun titre")
            program.add_desc(raw_program.get("description") or "Aucune description")
            program.add_category(self._format_category(item.get("category") or "Inconnu"))
            program.add_category(self._format_category(item.get("subCategory") or "Inconnu"))
            if item.get("supportForVisuallyImpaired"):
                program.set_audio_described()
            if item.get("supportForHearingImpaired"):
                program.add_subtitles("teletext")
            if raw_program.get("posterFileName"):
                program.add_icon(
                    "https://experience-cache.cdi.streaming.proximustv.be/posterserver/poster/EPG/"
                    + str(raw_program["posterFileName"])
                )
            program.set_rating(csa)
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        channel_id = self.get_channels_list()[channel.id]
        return (
            f"https://px-epg.azureedge.net/airings/{self.get_version()}/{date.strftime('%Y-%m-%d')}"
            f"/channel/{channel_id}?timezone=Europe%2FParis"
        )
