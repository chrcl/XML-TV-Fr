"""Orange provider — migrated from Orange.php."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_PARIS_TZ = ZoneInfo("Europe/Paris")
_CSA = {"2": "-10", "3": "-12", "4": "-16", "5": "-18"}


class Orange(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_orange.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False

        start_date = datetime.fromisoformat(date).replace(tzinfo=_PARIS_TZ)
        response_day_before = self._get_content_from_url(self.generate_url(channel_obj, start_date - timedelta(days=1)))
        response = self._get_content_from_url(self.generate_url(channel_obj, start_date))
        if "Invalid request" in response or "504 Gateway Time-out" in response:
            return False

        json_day_before = safe_json_loads(response_day_before) or []
        json_today = safe_json_loads(response)
        if not isinstance(json_today, list) or (isinstance(json_today, dict) and "code" in json_today):
            return False

        programs = list(json_day_before) + list(json_today)
        min_date, max_date = self.get_min_max_date(date)
        for value in programs:
            if not value.get("diffusionDate") or not value.get("duration"):
                continue
            begin = datetime.fromtimestamp(value["diffusionDate"], tz=UTC).astimezone(_PARIS_TZ)
            if begin < min_date:
                continue
            if begin > max_date:
                break

            program = Program(begin, begin + timedelta(seconds=int(value["duration"])))
            program.add_desc(value.get("synopsis"))
            program.add_category(value.get("genre"))
            program.add_category(value.get("genreDetailed"))
            covers = value.get("covers") or []
            if covers:
                program.add_icon(covers[-1].get("url"))
            program.set_rating(_CSA.get(str(value.get("csa")), "Tout public"))

            season = value.get("season") or {}
            if season:
                season_number = season.get("number") or "1"
                episode_number = value.get("episodeNumber") or "1"
                program.add_title(((season.get("serie") or {}).get("title")) or value.get("title") or "Aucun titre")
                program.set_episode_num(season_number, episode_number)
                program.add_sub_title(value.get("title"))
            else:
                program.add_title(value.get("title") or "Aucun titre")

            if value.get("audioDescription"):
                program.set_audio_described()
            channel_obj.add_program(program)

        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        channel_id = self._channels_list[channel.id]
        params = {
            "period": date.strftime("%Y-%m-%d"),
            "epgIds": channel_id,
            "mco": "OFR",
        }
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"https://rp-ott-mediation-tv.woopic.com/api-gw/live/v3/applications/PC/programs?{query}"
