"""NouvelObs provider — migrated from NouvelObs.php."""

from __future__ import annotations

import re
from datetime import datetime

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import strip_tags
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_CSA = {"2": "-10", "3": "-12", "4": "-16", "5": "-18"}


class NouvelObs(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_nouvelobs.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        response = self._get_content_from_url(self.generate_url(channel_obj, datetime.fromisoformat(date)))
        programs = response.split('<table cellspacing="0" cellpadding="0" class="tab_grille">')
        if len(programs) < 3:
            return False
        for value in programs[2:]:
            content = value.split("</table>", 1)[0]
            start = re.search(r'<td class="logo_chaine.*?>(.*?)</td>', content)
            duration = re.search(r"<br/>\((.*?)\)</div></td>", content)
            if not start or not duration:
                continue
            start_value = f"{date} {start.group(1).replace('h', ':')}"
            start_ts = int(datetime.fromisoformat(start_value).timestamp())
            program = Program.with_timestamp(start_ts, start_ts + int(duration.group(1)) * 60)
            category = re.search(r'prog" />(.*?)<br/>', content)
            desc_matches = re.findall(r'<div class="b_d prog1">(.*?)</div>', content)
            title = re.search(r'class="titre b">(.*?)<', content)
            season = re.search(r'<span class="b">Saison (.*?) : Episode (.*?)</span>', content)
            image = re.search(r'src="(.*?)"', content)
            csa = re.search(r'line4">(.*?)<', content)
            category_text = strip_tags((category.group(1) if category else "Inconnu").split(">")[-1])
            desc_text = (
                strip_tags((desc_matches[1] if len(desc_matches) > 1 else "Aucune description").split(">")[-1])
                or "Aucune description"
            )
            program.add_category(category_text)
            program.add_desc(desc_text)
            program.add_title(title.group(1) if title else "Aucun titre")
            if season:
                program.set_episode_num(season.group(1), season.group(2).split("/")[0])
            if image:
                program.add_icon(image.group(1).replace("/p/p/", "/p/g/"))
            program.set_rating(_CSA.get(csa.group(1) if csa else "", "Tout public"))
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        return f"https://programme-tv.nouvelobs.com/chaine/{self._channels_list[channel.id]}/{date.strftime('%Y-%m-%d')}.php"
