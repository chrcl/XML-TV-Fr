"""TVHebdo provider — migrated from TVHebdo.php."""

from __future__ import annotations

import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath
from xmltvfr.utils.utils import get_canadian_rating_system

_MONTREAL = ZoneInfo("America/Montreal")
_DEFAULT_ICON = "https://i.imgur.com/5CHM14O.png"


class TVHebdo(AbstractProvider):
    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_tvhebdo.json"))
        super().__init__(client, resolved_path, priority)
        self._proxy = (extra_params or {}).get("tvhebdo_proxy", ["http://kdbase.com/dreamland/browse.php?u=", "&b=24"])
        self._enable_details = (extra_params or {}).get("tvhebdo_enable_details", True)

    def get_data_per_day(self, channel: Channel, date_obj: datetime) -> list[dict]:
        referer = "".join(self._proxy) if isinstance(self._proxy, list) else str(self._proxy)
        content = self._get_content_from_url(self.generate_url(channel, date_obj), headers={"Referer": referer})
        host = self._proxy[0].split("/")[2] if isinstance(self._proxy, list) else ""
        content = html.unescape(content.replace('href="/', f'href="http://{host}/'))
        content = content.split("Mes<br>alertes courriel", 1)[1] if "Mes<br>alertes courriel" in content else ""
        if not content:
            return []
        times = __import__("re").findall(r'class="heure">(.*?)</td>', content)
        titles_and_urls = __import__("re").findall(r'class="titre">.*?href="(.*?)">(.*?)</a>', content)
        if len(times) != len(titles_and_urls):
            return []
        data = []
        for index, (url, title) in enumerate(titles_and_urls):
            start_date = datetime.fromisoformat(f"{date_obj.strftime('%Y-%m-%d')} {times[index]}").replace(
                tzinfo=_MONTREAL
            )
            data.append({"startDate": start_date, "title": title, "url": url})
        return data

    def fetch_programs(self, channel: Channel, date: str) -> list[tuple[Program, str]]:
        date_obj = datetime.fromisoformat(date)
        data = self.get_data_per_day(channel, date_obj - timedelta(days=1)) + self.get_data_per_day(channel, date_obj)
        programs_with_url: list[tuple[Program, str]] = []
        min_date = datetime.fromisoformat(date).replace(tzinfo=_MONTREAL)
        max_date = min_date + timedelta(days=1) - timedelta(seconds=1)
        for index, item in enumerate(data):
            if item["startDate"] < min_date:
                continue
            if item["startDate"] > max_date:
                return programs_with_url
            end_date = data[index + 1]["startDate"] if index + 1 < len(data) else item["startDate"] + timedelta(hours=1)
            program = Program(item["startDate"], end_date)
            program.add_title(item["title"])
            programs_with_url.append((program, item["url"]))
            channel.add_program(program)
        return programs_with_url

    def fill_program_details(self, program: Program, content: str) -> None:
        try:
            infos = (content.split("<h4>", 1)[1].split("</h4>", 1)[0] if "<h4>" in content else "").replace("\n", " ")
            infos_split = infos.split(" - ")
            genre = (infos_split[0] if len(infos_split) > 0 else "").strip()
            lang = (infos_split[2] if len(infos_split) > 2 else "fr").strip().lower()
            year = None
            rating = None
            if len(infos_split) > 3:
                potential = infos_split[3].strip()
                year = potential if potential.isdigit() else None
                rating = None if year else potential
            if len(infos_split) > 4 and infos_split[4].strip().isdigit():
                year = infos_split[4].strip()
            desc = content.split('<p id="dd_desc">', 1)[1].split("</p>", 1)[0] if '<p id="dd_desc">' in content else ""
            if year:
                desc += f"\n\nAnnée : {year}"
            intervenants = (
                content.split('<p id="dd_inter">', 1)[1].split("</p>", 1)[0] if '<p id="dd_inter">' in content else ""
            )
            desc = (desc + intervenants).replace("<br />", "\n")
            desc = "\n".join(line.strip() for line in desc.split("\n"))
            program.add_desc(desc, lang)
            program.add_category(genre, lang)
            current_role = "guest"
            for line in intervenants.split("<br />"):
                line = line.strip()
                if line == "Réalisation :":
                    current_role = "director"
                elif ":" in line:
                    current_role = "guest"
                elif line:
                    program.add_credit(line, current_role)
            program.add_icon(_DEFAULT_ICON)
            if rating and len(rating) < 4:
                rating_system = get_canadian_rating_system(rating, lang)
                if rating_system:
                    program.set_rating(rating, rating_system)
        except Exception:  # noqa: BLE001
            return

    def fill_details(self, programs_with_url: list[tuple[Program, str]]) -> None:
        for index, (program, url) in enumerate(programs_with_url, start=1):
            self.set_status(f"{round(index * 100 / len(programs_with_url), 2)} %")
            self.fill_program_details(program, self._get_content_from_url(url))

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        programs_with_url = self.fetch_programs(channel_obj, date)
        if self._enable_details:
            self.fill_details(programs_with_url)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        url = f"http://www.tvhebdo.com/horaire-tele/{self._channels_list[channel.id]}/date/{date.strftime('%Y-%m-%d')}"
        return f"{self._proxy[0]}{requests.utils.quote(url)}{self._proxy[1]}"
