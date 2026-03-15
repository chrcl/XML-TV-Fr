"""TV5Global provider — migrated from TV5Global.php."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import match1, strip_tags
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr-CA;q=0.8,en;q=0.5,en-US;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-GPC": "1",
    "Sec-Fetch-User": "?1",
    "Priority": "u=0, i",
}


class TV5Global(AbstractProvider):
    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_tv5global.json"))
        super().__init__(client, resolved_path, priority)
        self._enable_details = (extra_params or {}).get("tv5global_enable_details", True)

    def _get_content_or_retry(self, url: str, root_domain: str) -> str:
        suffix = ""
        for attempt in range(5):
            content = self._get_content_from_url(
                url + suffix,
                headers={**_HEADERS, "Host": root_domain},
                ignore_cache=True,
            )
            if "502 Bad Gateway" not in content:
                return content
            self.set_status(f"Erreur 502, essai n°{attempt + 2}...")
            suffix += "&"
        return ""

    def _add_details(self, program: Program, url: str) -> None:
        try:
            content = self._get_content_from_url(url, headers=dict(_HEADERS))
            season = match1(r'class="field-label-inline">Saison</span>.*?<span>(.*?)</span>', content, re.DOTALL)
            episode = match1(
                r'class="field__label">Épisode</div>.*?<div class="field__item">(.*?)</div>', content, re.DOTALL
            )
            summary = match1(r'field--type-text-with-summary.*?">(.*?)</div>', content, re.DOTALL)
            if episode:
                program.set_episode_num(int(season or "1"), int(episode))
            if summary and "googletag" not in summary:
                program.add_desc(strip_tags(summary))
        except Exception:  # noqa: BLE001
            return

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        min_date, max_date = self.get_min_max_date(date)
        date_obj = datetime.fromisoformat(date)
        content = self._get_content_or_retry(
            self.generate_url(channel_obj, date_obj), self.get_root_domain(channel_obj)
        )
        day_before = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
        for marker in (f"jour-{day_before}", f"jour-{date}", f"jour-{day_after}"):
            content = content.replace(marker, "PROGRAM_SPLIT")
        programs = content.split("PROGRAM_SPLIT")
        for index in range(1, len(programs) - 1):
            self.set_status(f"{round(index * 100 / len(programs), 2)} %")
            current = programs[index]
            start_time = match1(r'datetime="(.*?)"', current, re.DOTALL)
            end_time = match1(r'datetime="(.*?)"', programs[index + 1], re.DOTALL)
            if not start_time or not end_time:
                continue
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            if start_dt < min_date:
                continue
            if start_dt > max_date:
                return channel_obj
            genre = match1(r'field-categorie.*?field-content">(.*?)</div>', current, re.DOTALL)
            title_or_subtitle = match1(r'field-title.*?field-content">(.*?)</span>', current, re.DOTALL)
            title = match1(r'field-serie.*?field-content">(.*?)</span>', current, re.DOTALL)
            image = match1(r'data-src="(.*?)"', current)
            href = match1(r'href="(.*?)"', current)
            program = Program(start_dt, end_dt)
            if title:
                program.add_title(title)
                program.add_sub_title(title_or_subtitle or "Aucun sous-titre")
            else:
                program.add_title(title_or_subtitle or "Aucun titre")
            if self._enable_details and href:
                self._add_details(program, f"https://{self.get_root_domain(channel_obj)}{href}")
            program.add_category(genre or "Inconnu")
            if image:
                program.add_icon(f"https://{self.get_root_domain(channel_obj)}{image}")
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def get_root_domain(self, channel: Channel) -> str:
        return f"{self._channels_list[channel.id]}.tv5monde.com"

    def generate_url(self, channel: Channel, date: datetime) -> str:
        return f"https://{self.get_root_domain(channel)}/tv-guide?day={date.strftime('%Y-%m-%d')}"
