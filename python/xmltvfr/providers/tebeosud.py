"""Tebeosud provider — migrated from Tebeosud.php."""

from __future__ import annotations

import re
from datetime import datetime

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath


class Tebeosud(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_tebeosud.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        content = self._get_content_from_url(self.generate_url(channel_obj, datetime.fromisoformat(date))).replace(
            '"', "'"
        )
        hours = re.findall(r"<p class='hour-program'>(.*?)</p>", content, re.DOTALL)
        titles = re.findall(r"<span class='video-card-date'>(.*?)</span>", content, re.DOTALL)
        images = re.findall(r"<div class='program-card-content'> <img .*?src='(.*?)'.*?>", content, re.DOTALL)
        if not titles:
            return False
        for index, title in enumerate(titles):
            start = int(datetime.fromisoformat(f"{date} {hours[index]}").timestamp())
            if index == len(titles) - 1:
                end = start + 3600
            elif index + 1 < len(hours):
                end = int(datetime.fromisoformat(f"{date} {hours[index + 1]}").timestamp())
            else:
                continue
            program = Program.with_timestamp(start, end)
            program.add_title(title.strip())
            program.add_desc("Aucune description")
            if index < len(images):
                program.add_icon(images[index])
            program.add_category("Inconnu")
            channel_obj.add_program(program)
        channel_obj.order_program()
        return channel_obj

    def generate_url(self, channel: Channel, date: datetime) -> str:  # noqa: ARG002
        return f"https://www.tebeo.bzh/programme/{date.strftime('%d-%m-%Y')}/"
