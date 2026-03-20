"""VirginPlus provider — migrated from VirginPlus.php."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.providers.provider_cache import ProviderCache
from xmltvfr.utils.resource_path import ResourcePath
from xmltvfr.utils.utils import get_canadian_rating_system

_BASE_URL = "https://tv.virginplus.ca/api/"
_HEADERS = {"X-Bell-API-Key": "fonse-web-2d842ffc", "Referer": "https://tv.virginplus.ca/guide"}
_TORONTO = ZoneInfo("America/Toronto")


class VirginPlus(AbstractProvider):
    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_virginplus.json"))
        super().__init__(client, resolved_path, priority)
        self._epg_from_date = datetime.now(_TORONTO)
        self._epg_to_date = datetime.now(_TORONTO)
        self._block_duration = 0
        self._epg_info: list[dict] = []
        self._is_configured = False
        self._disable_details = (extra_params or {}).get("virginplus_disable_details", False)
        self._gather_epg_information()

    def _gather_epg_information(self) -> None:
        cache = ProviderCache("virginplusEpgInformation")
        current_cache = cache.get_array()
        try:
            if not current_cache:
                info = safe_json_loads(self._get_content_from_url(_BASE_URL + "epg/v3/epgInfo")) or {}
                if info:
                    self._epg_from_date = datetime.fromisoformat(info["minStartTime"].replace("Z", "+00:00"))
                    self._epg_to_date = datetime.fromisoformat(info["maxEndTime"].replace("Z", "+00:00"))
                    self._block_duration = int(info["schedulesBlockHoursDuration"])
                    self._epg_info = (
                        safe_json_loads(
                            self._get_content_from_url(
                                _BASE_URL
                                + "epg/v3/channels?tvService=volt&epgChannelMap=MAP_TORONTO"
                                + f"&epgVersion={info['version']}"
                            )
                        )
                        or []
                    )
                    if self._epg_info:
                        self._is_configured = True
                        cache.set_array_key("minStartTime", info["minStartTime"])
                        cache.set_array_key("maxEndTime", info["maxEndTime"])
                        cache.set_array_key("blockDuration", self._block_duration)
                        cache.set_array_key("epgInfo", self._epg_info)
                        return
            elif not current_cache.get("hasFailed"):
                self._epg_from_date = datetime.fromisoformat(current_cache["minStartTime"].replace("Z", "+00:00"))
                self._epg_to_date = datetime.fromisoformat(current_cache["maxEndTime"].replace("Z", "+00:00"))
                self._block_duration = int(current_cache["blockDuration"])
                self._epg_info = current_cache["epgInfo"]
                self._is_configured = True
                return
        except Exception:  # noqa: BLE001
            pass
        cache.set_array_key("hasFailed", True)

    def _get_channel_info(self, channel_id: str) -> dict:
        for info in self._epg_info:
            if info.get("callSign") == channel_id:
                return info
        raise RuntimeError(f"Channel {channel_id} not found")

    def _get_blocks_information(self, channel_id: str, from_date: datetime, to_date: datetime) -> list[dict]:
        channel_info = self._get_channel_info(channel_id)
        cursor = self._epg_from_date
        blocks_information = []
        block_versions = channel_info.get("schedulesBlockVersions") or []
        index = 0
        while cursor < to_date and cursor < self._epg_to_date and index < len(block_versions):
            end_cursor = cursor + timedelta(hours=self._block_duration)
            if end_cursor >= from_date:
                blocks_information.append(
                    {"fromDate": cursor, "toDate": end_cursor, "blockVersion": block_versions[index]}
                )
            cursor = end_cursor
            index += 1
        return blocks_information

    def _add_details(self, program: Program, program_id: str) -> None:
        details = (
            safe_json_loads(
                self._get_content_from_url(_BASE_URL + f"epg/v3/programs/{program_id}", headers=dict(_HEADERS))
            )
            or {}
        )
        if not details:
            return
        program.add_desc(details.get("description"))
        program.set_episode_num(details.get("seasonNumber"), details.get("episodeNumber"))
        for category in details.get("categories") or []:
            program.add_category(category.get("category"))
        for crew in details.get("castAndCrew") or []:
            program.add_credit(crew.get("name"), str(crew.get("role", "guest")).lower())

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel) or not self._is_configured:
            return False
        min_date = datetime.fromisoformat(date).replace(tzinfo=_TORONTO)
        max_date = min_date + timedelta(days=1) - timedelta(seconds=1)
        min_start = min_date - timedelta(days=1) + timedelta(hours=12)
        channel_id = self.get_channels_list()[channel]
        blocks = self._get_blocks_information(channel_id, min_start, min_start + timedelta(days=2))
        for block_index, block in enumerate(blocks):
            programs = (
                safe_json_loads(
                    self._get_content_from_url(
                        self.generate_url(channel_obj, block["fromDate"], block["toDate"], block["blockVersion"]),
                        headers=dict(_HEADERS),
                    )
                )
                or []
            )
            if not programs:
                return False
            for index, item in enumerate(programs):
                start_date = datetime.fromisoformat(item["startTime"].replace("Z", "+00:00")).astimezone(_TORONTO)
                if start_date < min_date:
                    continue
                if start_date > max_date:
                    return channel_obj
                program = Program.with_timestamp(
                    int(datetime.fromisoformat(item["startTime"].replace("Z", "+00:00")).timestamp()),
                    int(datetime.fromisoformat(item["endTime"].replace("Z", "+00:00")).timestamp()),
                )
                program.add_title(item.get("title"))
                if item.get("episodeTitle"):
                    program.add_sub_title(item.get("episodeTitle"))
                if item.get("new"):
                    program.set_premiere()
                rating = str(item.get("rating") or "").split("-")[-1]
                rating_system = get_canadian_rating_system(rating, item.get("language", "fr"))
                if rating_system:
                    program.set_rating(rating, rating_system)
                program.add_category(str(item.get("showType", "")).capitalize())
                supplier = item.get("programSupplierId") or {}
                program.add_icon(
                    _BASE_URL
                    + "artwork/v3/artworks/artworkSelection/ASSET/"
                    + f"{supplier.get('supplier')}/{supplier.get('supplierId')}"
                    + "/SHOWCARD_BACKGROUND/2048x1024"
                )
                if not self._disable_details:
                    self.set_status(f"({block_index + 1}/{len(blocks)}) {round(index * 100 / len(programs), 2)} %")
                    self._add_details(program, item["programId"])
                channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, from_date: datetime, to_date: datetime, block_version: int = 1) -> str:
        channel_id = self._channels_list[channel.id]
        return (
            _BASE_URL + "epg/v3/byBlockVersion/schedules?tvService=volt&epgChannelMap=MAP_TORONTO"
            f"&callSign={requests.utils.quote(str(channel_id))}"
            f"&startTime={requests.utils.quote(from_date.strftime('%Y-%m-%dT%H:%M:%SZ'))}"
            f"&endTime={requests.utils.quote(to_date.strftime('%Y-%m-%dT%H:%M:%SZ'))}"
            f"&blockVersion={block_version}"
        )
