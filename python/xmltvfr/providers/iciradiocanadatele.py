"""ICI Radio-Canada Télé provider — migrated from ICIRadioCanadaTele.php."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads, strip_tags
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_HEADERS = {
    "Host": "services.radio-canada.ca",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0",
    "Accept": "*/*",
    "Accept-Language": "fr-FR,fr-CA;q=0.8,en;q=0.5,en-US;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://ici.radio-canada.ca/",
    "Origin": "https://ici.radio-canada.ca",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-site",
    "Content-Type": "application/json",
    "X-Requested-With": "appTele-vcinq@19.3.4-node@v22.11.0",
    "Priority": "u=4",
}


class ICIRadioCanadaTele(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_iciradiocanada.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        date_obj = datetime.fromisoformat(date)
        previous = (
            safe_json_loads(
                self._get_content_from_url(
                    self.generate_url(channel_obj, date_obj - timedelta(days=1)), headers=dict(_HEADERS)
                )
            )
            or {}
        )
        payload = (
            safe_json_loads(
                self._get_content_from_url(self.generate_url(channel_obj, date_obj), headers=dict(_HEADERS))
            )
            or {}
        )
        broadcasts = ((previous.get("data") or {}).get("broadcasts") or []) + (
            ((payload.get("data") or {}).get("broadcasts")) or []
        )
        if not ((payload.get("data") or {}).get("broadcasts")):
            return False
        min_date, max_date = self.get_min_max_date(date)
        for index, broadcast in enumerate(broadcasts[:-1]):
            start_ts = int(datetime.fromisoformat(broadcast["startsAt"].replace("Z", "+00:00")).timestamp())
            start_date = datetime.fromtimestamp(start_ts, tz=UTC)
            if start_date < min_date:
                continue
            if start_date > max_date:
                return channel_obj
            end_ts = int(datetime.fromisoformat(broadcasts[index + 1]["startsAt"].replace("Z", "+00:00")).timestamp())
            program = Program.with_timestamp(start_ts, end_ts)
            program.add_category(broadcast.get("subtheme"))
            program.add_icon(
                str((broadcast.get("image") or {}).get("url") or "")
                .replace("{0}", "635")
                .replace("{1}", "16x9")
            )
            program.add_title(broadcast.get("title"))
            program.add_desc(strip_tags(broadcast.get("descriptionHtml") or "Aucune description"))
            if broadcast.get("hasVideoDescription"):
                program.set_audio_described()
            if broadcast.get("hasClosedCaptions"):
                program.add_subtitles("teletext")
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        channel_id = self._channels_list[channel.id]
        formatted_date = date.strftime("%Y-%m-%d")
        return (
            "https://services.radio-canada.ca/bff/tele/graphql?opname=getBroadcasts"
            "&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22c3f32e9e14b027abb59011e5e9f8ac0a2c8554889b68cbe1e7879c74fa1c7679%22%7D%7D"
            f"&variables=%7B%22params%22%3A%7B%22date%22%3A%22{formatted_date}%22%2C%22regionId%22%3A{channel_id}%7D%7D"
        )
