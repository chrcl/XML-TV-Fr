"""Tele2Semaines provider — migrated from Tele2Semaines.php."""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import strip_tags
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
_CREDIT_ROLES = {
    "Presentateur": "presenter",
    "Acteur": "actor",
    "Realisateur": "director",
    "Scénariste": "writer",
    "Musique": "composer",
}


class Tele2Semaines(AbstractProvider):
    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_tele2semaines.json"))
        super().__init__(client, resolved_path, priority)
        self._enable_details = (extra_params or {}).get("tele2semaines_enable_details", True)

    @staticmethod
    def _get_day_label(date: datetime) -> str:
        normalized = date.replace(hour=0, minute=0, second=0, microsecond=0)
        today = datetime.now(normalized.tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
        week_after = today + timedelta(days=6)
        if normalized < today:
            raise ValueError("Date is too early !")
        if normalized.date() == today.date():
            return ""
        if normalized > week_after:
            raise ValueError("Date is too late !")
        return _DAYS[normalized.strftime("%a")]

    @staticmethod
    def _get_credit_role(credit: str) -> str:
        return _CREDIT_ROLES.get(credit, "guest")

    def assign_details(self, href: str, program: Program) -> None:
        content = html.unescape(self._get_content_from_url(href))
        content = content.replace('<button class="overviewDetail-peopleShowMoreButton">Voir plus</button>', "")
        people = re.findall(
            r'<div class="overviewDetail-peopleList">.*?<span class="overviewDetail-title">(.*?): </span>(.*?)</div>',
            content,
            re.DOTALL,
        )
        for credit_type, people_html in people[1:]:
            tag = self._get_credit_role(credit_type)
            for person in strip_tags(people_html).split(","):
                program.add_credit(person.strip(), tag)
        review = re.search(r'<div class="review-content">(.*?)</div>', content, re.DOTALL)
        if review:
            program.add_review(review.group(1), "Tele 2 Semaines")

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        day = datetime.fromisoformat(date)
        day_after = day + timedelta(days=1)
        content = html.unescape(self._get_content_from_url(self.generate_url(day, channel_obj)))
        content_day_after = self._get_content_from_url(self.generate_url(day_after, channel_obj))
        programs = content.split('class="broadcastCard"')[1:]
        end_last = re.search(r'class="broadcastCard-start" datetime="(.*?)"', content_day_after, re.DOTALL)
        if not end_last:
            return False
        for index, raw_program in enumerate(programs, start=1):
            self.set_status(f"{round(index * 100 / len(programs), 2)} %")
            start_match = re.search(r'class="broadcastCard-start" datetime="(.*?)"', raw_program, re.DOTALL)
            if not start_match:
                continue
            if index == len(programs):
                end_value = end_last.group(1)
            else:
                next_match = re.search(r'class="broadcastCard-start" datetime="(.*?)"', programs[index], re.DOTALL)
                if not next_match:
                    continue
                end_value = next_match.group(1)
            program = Program(
                datetime.fromisoformat(start_match.group(1).replace("Z", "+00:00")),
                datetime.fromisoformat(end_value.replace("Z", "+00:00")),
            )
            href = re.search(r'href="(.*?)"', raw_program, re.DOTALL)
            genre = re.search(r'class="broadcastCard-format">(.*?)</p>', raw_program, re.DOTALL)
            title = re.search(r'<h2 class="broadcastCard-title">(.*?)</h2>', raw_program, re.DOTALL)
            src = re.search(r'srcset="(.*?)"', raw_program, re.DOTALL)
            synopsis = re.search(r'<p class="broadcastCard-synopsis">(.*?)</p>', raw_program, re.DOTALL)
            note = re.search(r'aria-label="Note de (.*?) sur (.*?)"', raw_program, re.DOTALL)
            program.add_title(strip_tags(title.group(1) if title else "Aucun titre"))
            program.add_desc(strip_tags(synopsis.group(1) if synopsis else "Aucune description").strip())
            program.add_category(strip_tags(genre.group(1) if genre else ""))
            if note:
                program.add_star_rating(int(note.group(1)), int(note.group(2)))
            if src:
                program.add_icon(src.group(1).split(" ")[0].replace("109x70", "1280x720"))
            channel_obj.add_program(program)
            if href and self._enable_details:
                self.assign_details(href.group(1), program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, date: datetime, channel: Channel) -> str:
        day_label = self._get_day_label(date)
        channel_id = self._channels_list[channel.id]
        if not day_label:
            return f"https://www.programme.tv/chaine/{channel_id}/"
        return f"https://www.programme.tv/chaine/{day_label}/{channel_id}/"
