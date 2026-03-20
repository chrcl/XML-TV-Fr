"""L'Equipe Live provider — migrated from LEquipeLive.php."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.epg_enum import EPGEnum
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import match1
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.providers.provider_cache import ProviderCache
from xmltvfr.utils.resource_path import ResourcePath

_DAYS = {"Lun": "Mon", "Mar": "Tue", "Mer": "Wed", "Jeu": "Thu", "Ven": "Fri", "Sam": "Sat", "Dim": "Sun"}


class LEquipeLive(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_lequipelive.json"))
        super().__init__(client, resolved_path, priority)
        self._cache = ProviderCache("lequipeLive")
        self._days_date = self._get_days_date()

    @staticmethod
    def _get_days_date() -> dict[str, str]:
        result: dict[str, str] = {}
        cursor = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for _ in range(7):
            cursor += timedelta(days=1)
            result[cursor.strftime("%a")] = cursor.strftime("%Y-%m-%d")
        return result

    def _format_time(self, raw_time: str) -> int:
        cleaned = raw_time.replace("h", ":")
        if cleaned.endswith(":"):
            cleaned += "00"
        parts = cleaned.split(".")
        if len(parts) == 1:
            return int(datetime.fromisoformat(f"{datetime.now().strftime('%Y-%m-%d')} {parts[0].strip()}").timestamp())
        day = _DAYS.get(parts[0].strip(), parts[0].strip())
        date_value = self._days_date[day]
        return int(datetime.fromisoformat(f"{date_value} {parts[1].strip()}").timestamp())

    def _parse_item(self, item: str) -> dict[str, str | int]:
        return {
            "id": (match1(r'<h2 class="ColeaderWidget__title".*?>(.*?)</h2>', item, re.DOTALL) or "").strip(),
            "title": (match1(r'<div.*?class="ArticleTags__item".*?>(.*?)</div>', item, re.DOTALL) or "").strip(),
            "subtitle": (match1(r'<p class="ColeaderWidget__subtitle".*?>(.*?)</p>', item, re.DOTALL) or "").strip(),
            "time": self._format_time(
                (match1(r'<span class="ColeaderLabels__text".*?>(.*?)</span>', item, re.DOTALL) or "00h00").strip()
            ),
            "img": match1(r'src="(.*?)"', item, re.DOTALL) or "",
        }

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        content = self._cache.get_content() or self._get_content_from_url(
            self.generate_url(channel_obj, datetime.fromisoformat(date))
        )
        if content and not self._cache.get_content():
            self._cache.set_content(content)
        try:
            zone = content.split('alt="À suivre en direct"', 1)[1].split('class="CarouselWidget__headerTitle"', 1)[0]
        except IndexError:
            return False
        channel_id = self.get_channels_list()[channel]
        items = [self._parse_item(item) for item in zone.split('class="CarouselWidget__item"')[1:]]
        channel_items = [item for item in items if item["id"] == channel_id]
        min_time = int(datetime.fromisoformat(date).timestamp())
        max_time = int((datetime.fromisoformat(date) + timedelta(days=1)).timestamp())
        for index, item in enumerate(channel_items):
            if min_time <= int(item["time"]) <= max_time:
                next_time = int(channel_items[index + 1]["time"]) if index + 1 < len(channel_items) else 2**31 - 1
                end_time = min(next_time, int(item["time"]) + 7200)
                program = Program.with_timestamp(int(item["time"]), end_time)
                program.add_title(str(item["title"]))
                program.add_sub_title(str(item["subtitle"]))
                program.add_category("Sports")
                program.add_icon(str(item["img"]))
                channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def get_channel_state_from_times(
        self, start_times: list[int], end_times: list[int], config: object
    ) -> int:  # noqa: ARG002
        return EPGEnum.FULL_CACHE if start_times else EPGEnum.NO_CACHE

    def generate_url(self, channel: Channel, date: datetime) -> str:  # noqa: ARG002
        return "https://www.lequipe.fr/tv/"
