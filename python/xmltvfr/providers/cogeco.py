"""Cogeco provider — migrated from Cogeco.php."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_TORONTO = ZoneInfo("America/Toronto")
_CATEGORIES_BY_CSS = {"tvm_td_grd_s": "Sport", "tvm_td_grd_r": "Télé-Réalité", "tvm_td_grd_m": "Cinéma"}
_CATEGORIES_IN_TITLE = {"Cinéma"}


class Cogeco(AbstractProvider):
    COOKIE_VALUE = "823D"

    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_cogeco.json"))
        super().__init__(client, resolved_path, priority)

    @staticmethod
    def _has_category_as_title(title: str) -> bool:
        return title in _CATEGORIES_IN_TITLE

    @staticmethod
    def _get_category(html: str) -> str:
        for css_class, category in _CATEGORIES_BY_CSS.items():
            if css_class in html:
                return category
        return "Inconnu"

    def _get_epg_data(self, start: datetime) -> str | None:
        payload = self._get_content_from_url(
            self.generate_url(start), headers={"Cookie": f"TVMDS_Cookie={self.COOKIE_VALUE}"}
        )
        return (payload and __import__("json").loads(payload).get("data")) if payload else None  # noqa: PLC2701

    @staticmethod
    def _generate_program_details_url(path: str) -> str:
        split_path = path.split(", ")
        return (
            "https://tvmds.tvpassport.com/tvmds/cogeco/grid_v3/program_details/program_details.php"
            f"?subid=tvpassport&ltid={split_path[0]}&stid={split_path[1]}&luid={Cogeco.COOKIE_VALUE}&lang=fr-ca&mode=json"
        )

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        channel_id = self.get_channels_list()[channel]
        min_date = datetime.fromisoformat(date).replace(tzinfo=_TORONTO)
        max_date = min_date + timedelta(days=1) - timedelta(seconds=1)
        if min_date < datetime.now(_TORONTO).replace(hour=0, minute=0, second=0, microsecond=0):
            return False
        span = 6
        min_start = min_date - timedelta(days=1) + timedelta(hours=span * 2)
        program_paths: list[str] = []
        program_categories: list[str] = []
        for index in range(6):
            self.set_status(f"Main data (1/2) : {round(index * 100 / 6, 2)} %")
            start = min_start + timedelta(hours=span * index)
            html = self._get_epg_data(start)
            if not html:
                return False
            found = False
            for channel_row in html.split("<!-- channel row -->")[1:]:
                channel_id_name = re.search(r'tvm_txt_chan_name">(.*?)</span>', channel_row)
                channel_number = re.search(r'tvm_txt_chan_num">(.*?)</span>', channel_row)
                channel_number_value = (channel_number.group(1) if channel_number else "").replace("&nbsp;", "")
                if (channel_id_name.group(1) if channel_id_name else "") in (
                    channel_id,
                    channel_number_value,
                ) or channel_number_value == channel_id:
                    found = True
                    for css_class, path in re.findall(r'class="(.*?)".*?onclick="prgm_details\((.*?)\)"', channel_row):
                        if path not in program_paths:
                            program_paths.append(path)
                            program_categories.append(self._get_category(css_class))
                    break
            if not found:
                return False
        current_cursor = min_start - timedelta(days=1) + timedelta(minutes=1)
        for index, path in enumerate(program_paths):
            self.set_status(f"Details (2/2) : {round(index * 100 / len(program_paths), 2)} %")
            content = self._get_content_from_url(self._generate_program_details_url(path))
            title = re.search(r'txt_showtitle bold">(.*?)</h3>', content, re.DOTALL)
            if not title:
                continue
            subtitle = re.search(r'txt_showname bold">(.*?)</p>', content, re.DOTALL)
            details = re.findall(r'tvm_td_detailsbot">(.*?)</span>', content, re.DOTALL)
            description = re.search(r'details_tvm_td_detailsbot">(.*?)</p>', content, re.DOTALL)
            img = re.search(r"img id='show_graphic' src=\"(.*?)\"", content, re.DOTALL)
            if len(details) < 3:
                continue
            hour, minute = details[1].split("h")
            start_dt = current_cursor.replace(hour=int(hour), minute=int(minute))
            if start_dt < current_cursor:
                start_dt += timedelta(days=1)
            current_cursor = start_dt
            if current_cursor < min_start or current_cursor < min_date:
                continue
            if current_cursor > max_date:
                return channel_obj
            duration = int(details[2].split(" ")[0].split("(")[-1])
            end_dt = start_dt + timedelta(minutes=duration)
            program = Program(start_dt, end_dt)
            title_text = title.group(1).strip()
            subtitle_text = (subtitle.group(1) if subtitle else "").strip()
            if self._has_category_as_title(title_text) and subtitle_text:
                program.add_title(subtitle_text)
            else:
                program.add_title(title_text)
                if subtitle_text:
                    program.add_sub_title(subtitle_text)
            if img:
                program.add_icon("https:" + img.group(1).replace("240x135", "1280x720"))
            program.add_category(program_categories[index])
            program.add_desc(description.group(1) if description else "Aucune description")
            if "(NOUVEAU)" in content:
                program.set_premiere()
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, date: datetime) -> str:
        return (
            "https://tvmds.tvpassport.com/tvmds/cogeco/grid_v3/grid.php"
            f"?subid=tvpassport&lu={self.COOKIE_VALUE}&wd=1138&ht=100000&mode=json&style=blue&wid=wh&st={int(date.timestamp())}"
            "&ch=1&tz=EST5EDT&lang=fr-ca&ctrlpos=top&items=99999&filter="
        )
