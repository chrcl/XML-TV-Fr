"""MyCanal provider — migrated from MyCanal.php."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import ClassVar

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr-CA;q=0.9,en;q=0.8,en-US;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Priority": "u=0, i",
}
_OFFER_ZONES = {
    "fr": "cpfra",
    "bj": "cpafr",
    "bf": "cpafr",
    "bi": "cpafr",
    "cm": "cpafr",
    "cv": "cpafr",
    "cg": "cpafr",
    "ci": "cpafr",
    "dj": "cpafr",
    "ga": "cpafr",
    "gm": "cpafr",
    "gh": "cpafr",
    "gp": "cpant",
    "gn": "cpafr",
    "gw": "cpafr",
    "gq": "cpafr",
    "gf": "cpant",
    "mg": "cpmdg",
    "ml": "cpafr",
    "mq": "cpant",
    "mu": "cpmus",
    "mr": "cpafr",
    "yt": "cpreu",
    "nc": "cpncl",
    "ne": "cpafr",
    "pl": "cppol",
    "cf": "cpafr",
    "cd": "cpafr",
    "re": "cpreu",
    "rw": "cpafr",
    "bl": "cpant",
    "mf": "cpant",
    "sn": "cpafr",
    "sl": "cpafr",
    "ch": "cpche",
    "td": "cpafr",
    "tg": "cpafr",
    "wf": "cpncl",
}
_CSA = {"2": "-10", "3": "-12", "4": "-16", "5": "-18"}


class MyCanal(AbstractProvider):
    _API_KEYS: ClassVar[dict[str, str]] = {}

    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_mycanal.json"))
        super().__init__(client, resolved_path, priority)
        self._region = "fr"
        self._enable_details = (extra_params or {}).get("mycanal_enable_details", True)

    def get_api_key(self) -> str:
        if self._region not in type(self)._API_KEYS:
            payload = (
                safe_json_loads(
                    self._get_content_from_url(
                        "https://hodor.canalplus.pro/api/v2/mycanal/authenticate.json/android/6.0"
                        f"?appLocation={self._region}&offerZone={_OFFER_ZONES[self._region]}",
                        headers=dict(_HEADERS),
                        ignore_cache=True,
                    )
                )
                or {}
            )
            token = payload.get("token") if isinstance(payload, dict) else None
            if not token:
                raise RuntimeError("Impossible to retrieve MyCanal API Key")
            type(self)._API_KEYS[self._region] = str(token)
        return type(self)._API_KEYS[self._region]

    def _get_program_list(self, channel: Channel, date: str) -> list[dict]:
        program_list: list[dict] = []
        last_index = -1
        min_start, max_start = self.get_min_max_date(date)
        start_date = datetime.fromisoformat(date) - timedelta(days=1)
        while True:
            self.set_status("Délimitation des programmes")
            payload = (
                safe_json_loads(
                    self._get_content_from_url(self.generate_url(channel, start_date), headers=dict(_HEADERS))
                )
                or {}
            )
            slices = payload.get("timeSlices") if isinstance(payload, dict) else None
            if not slices:
                return program_list
            summaries = []
            for section in slices:
                summaries.extend(section.get("contents") or [])
            if not summaries:
                return program_list
            for program in summaries:
                start_time = datetime.fromtimestamp(
                    int(program["startTime"]) / 1000,
                    tz=min_start.tzinfo,
                )
                if last_index >= 0:
                    program_list[last_index]["endTime"] = start_time
                if min_start <= start_time <= max_start:
                    last_index += 1
                    program_list.append(
                        {
                            "startTime": start_time,
                            "title": program.get("title"),
                            "subTitle": program.get("subtitle"),
                            "URLPage": ((program.get("onClick") or {}).get("URLPage")),
                        }
                    )
                elif start_time > max_start:
                    return program_list
            start_date += timedelta(days=1)

    def _fetch_details(self, program_list: list[dict]) -> None:
        for index, program in enumerate(program_list):
            self.set_status(f"{round(index * 100 / len(program_list), 2)} %")
            if not program.get("URLPage"):
                continue
            detail = (
                safe_json_loads(
                    self._get_content_from_url(program["URLPage"], headers=dict(_HEADERS), ignore_cache=True)
                )
                or {}
            )
            detail_info = detail.get("detail") or {}
            informations = detail_info.get("informations") or {}
            episodes = ((detail.get("episodes") or {}).get("contents")) or []
            episode0 = episodes[0] if episodes else {}
            tracking = ((detail.get("tracking") or {}).get("dataLayer")) or {}
            program["title"] = informations.get("title") or program.get("title") or "Aucun titre"
            program["subTitle"] = episode0.get("subtitle") or program.get("subTitle")
            program["description"] = episode0.get("summary") or informations.get("summary")
            selected = detail_info.get("selectedEpisode") or {}
            program["season"] = selected.get("seasonNumber")
            program["episode"] = selected.get("episodeNumber")
            program["genre"] = tracking.get("genre")
            program["genreDetailed"] = tracking.get("subgenre")
            program["closedCaptioning"] = informations.get("closedCaptioning")
            program["reviews"] = informations.get("reviews") or []
            icon = episode0.get("URLImage") or informations.get("URLImage") or ""
            program["icon"] = icon.replace("{resolutionXY}", "640x360").replace("{imageQualityPercentage}", "80")
            program["productionYear"] = informations.get("productionYear")
            parental = ((episode0.get("parentalRatings") or informations.get("parentalRatings") or [{}])[0]).get(
                "value"
            )
            program["csa"] = _CSA.get(str(parental), "Tout public")

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        self._region = self._channels_list[channel]["region"]
        program_list = self._get_program_list(channel_obj, date)
        if self._enable_details:
            self._fetch_details(program_list)
        for item in program_list:
            if not item.get("endTime"):
                continue
            program = Program(item["startTime"], item["endTime"])
            program.add_title(item.get("title"))
            program.add_sub_title(item.get("subTitle"))
            program.add_desc(item.get("description"))
            program.set_episode_num(item.get("season"), item.get("episode"))
            program.add_category(item.get("genre"))
            program.add_category(item.get("genreDetailed"))
            program.add_icon(item.get("icon"))
            program.set_rating(item.get("csa"))
            if item.get("productionYear"):
                program.set_date(str(item["productionYear"]))
            if item.get("closedCaptioning"):
                program.add_subtitles("teletext")
            for review in item.get("reviews") or []:
                if review.get("review"):
                    program.add_review(review["review"], review.get("name"))
                if (review.get("stars") or {}).get("value"):
                    program.add_star_rating(review["stars"]["value"], 5, (review.get("stars") or {}).get("type"))
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        channel_id = self._channels_list[channel.id]["id"]
        today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        day = round((date.timestamp() - today_midnight.timestamp()) / 86400)
        return f"https://hodor.canalplus.pro/api/v2/mycanal/channels/{self.get_api_key()}/{channel_id}/broadcasts/day/{day}"
