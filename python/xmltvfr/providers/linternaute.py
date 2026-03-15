"""LInternaute provider — migrated from LInternaute.php."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import match1, strip_tags
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_DAYS = {
    "Mon": "lundi",
    "Tue": "mardi",
    "Wed": "mercredi",
    "Thu": "jeudi",
    "Fri": "vendredi",
    "Sat": "samedi",
    "Sun": "dimanche",
}
_MONTHS = {
    1: "janvier",
    2: "fevrier",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "aout",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "decembre",
}
_TAG_NAMES = {
    "Réalisateur": "director",
    "Producteur": "producer",
    "Scénariste": "writer",
    "Acteurs": "actor",
    "Présentateur": "presenter",
    "Avec": "actor",
    "Réalisé par": "director",
}


class LInternaute(AbstractProvider):
    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_linternaute.json"))
        super().__init__(client, resolved_path, priority)
        self._enable_details = (extra_params or {}).get("linternaute_enable_details", True)

    @staticmethod
    def _get_day_label(date: datetime) -> str:
        normalized = date.replace(hour=0, minute=0, second=0, microsecond=0)
        if normalized.strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d"):
            return ""
        month = _MONTHS[int(normalized.strftime("%m"))]
        return (
            f"-{_DAYS[normalized.strftime('%a')]}"
            f"-{normalized.strftime('%d')}-{month}-{normalized.strftime('%Y')}"
        )

    @staticmethod
    def _get_tag_name(casting_tag: str) -> str | None:
        return _TAG_NAMES.get(unicodedata.normalize("NFC", casting_tag))

    def _add_credits(self, program: Program, credits: list[tuple[str, str]]) -> None:
        for credit_type, credit_values in credits:
            tag = self._get_tag_name(credit_type.strip())
            if not tag:
                continue
            for credit in strip_tags(credit_values).split(","):
                program.add_credit(credit.strip(), tag)

    def add_details(self, program: Program, link: str) -> None:
        try:
            if not link.startswith("https://"):
                link = "https://www.linternaute.com" + link
            content = self._get_content_from_url(link)
            desc = match1(r'<div id="top" class="bu_ccmeditor">(.*?)</div>', content, re.DOTALL)
            if not desc:
                desc = match1(
                    r'<p><strong><a id="synopsis" name="synopsis">Synopsis </a>- </strong>(.*?)</p>',
                    content,
                    re.DOTALL,
                )
            if desc:
                program.add_desc(strip_tags(desc))
            precise_note = match1(r'<span class="app_stars__note">.*?<span>.*?<span>(.*?)</span>', content, re.DOTALL)
            stars = float(precise_note) if precise_note else max(content.count('fill="#FC0"') - 1, 0)
            if stars > 0:
                program.add_star_rating(stars, 5)
            credits_1 = re.findall(
                r'<div class="grid_line gutter grid--norwd">.*?'
                r'<div class="grid_left w25">(.*?)</div>.*?'
                r'<div class="grid_last">.*?<b>(.*?)</b>.*?</div>.*?</div>',
                content,
                re.DOTALL,
            )
            self._add_credits(program, credits_1)
            credits_2 = re.findall(r"<dl>.*?<dd>(.*?):</dd>.*?<dt>(.*?)</dt>.*?</dl>", content, re.DOTALL)
            self._add_credits(program, credits_2)
            csa = match1(r'<span class="bu_tvprogram_broadcasting_pegi">(.*?)</span>', content, re.DOTALL)
            if csa:
                program.set_rating(-int(csa))
            season = match1(r'episode_navigation_locator--season".*?>Saison (\d+)</a>', content, re.DOTALL)
            episode = match1(r"bu_tvprogram_episode_navigation_locator--mobile.*?EP(\d+)</span>", content, re.DOTALL)
            if episode:
                program.set_episode_num(season, episode)
        except Exception:  # noqa: BLE001
            return

    def _parse_program(self, date: str, raw_program: str) -> Program:
        times = re.search(
            r'<div class="grid_col bu_tvprogram_logo">.*?<div>(.*?)</div>.*?<div>(.*?)</div>.*?</div>',
            raw_program,
            re.DOTALL,
        )
        href = match1(r'href="(.*?)"', raw_program, re.DOTALL)
        desc = match1(r'<span class="bu_tvprogram_typo5">(.*?)</span>', raw_program, re.DOTALL)
        title = match1(r'<span class="bu_tvprogram_typo2">(.*?)</span>', raw_program, re.DOTALL)
        subtitle = match1(r'<span class="bu_tvprogram_typo3">(.*?)</span>', raw_program, re.DOTALL)
        category = match1(r'<span class="bu_tvprogram_typo4">(.*?)</span>', raw_program, re.DOTALL)
        img = match1(r'src="(.*?)"', raw_program, re.DOTALL)
        start_time = (times.group(1) if times else "00h00").replace("h", ":")
        end_time = (times.group(2) if times else "00h30").replace("h", ":")
        start_dt = datetime.fromisoformat(f"{date} {start_time.strip()}")
        end_dt = datetime.fromisoformat(f"{date} {end_time.strip()}")
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        program = Program(start_dt, end_dt)
        program.add_title(strip_tags(title))
        if subtitle:
            program.add_sub_title(strip_tags(subtitle))
        category_parts = (category or "").split("-")
        program.add_category((category_parts[1] if len(category_parts) > 1 else category_parts[0]).strip())
        if img:
            program.add_icon(img)
        if self._enable_details and href:
            self.add_details(program, href)
        if not program.get_children("desc"):
            program.add_desc(strip_tags(desc))
        return program

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        min_date, _ = self.get_min_max_date(date)
        content = self._get_content_from_url(self.generate_url(channel_obj, self._get_day_label(min_date)))
        programs = content.split('class="bu_tvprogram_grid__line grid_row"')[1:]
        for index, raw_program in enumerate(programs, start=1):
            self.set_status(f"{round(index * 100 / len(programs), 2)} %")
            channel_obj.add_program(self._parse_program(date, raw_program))
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, day_label: str) -> str:
        return f"https://www.linternaute.com/television/programme-{self._channels_list[channel.id]}{day_label}/"
