"""SFR provider — migrated from SFR.php."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_CSA = {"2": "-10", "3": "-12", "4": "-16", "5": "-18"}


class SFR(AbstractProvider):
    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:
        provider_name = (extra_params or {}).get("provider", "sfr")
        resolved_path = str(ResourcePath.get_instance().get_channel_path(f"channels_{provider_name}.json"))
        super().__init__(client, resolved_path, priority)

    @staticmethod
    def _fix_broken_json(content: str) -> str:
        fixed = content
        for field in ("description", "title", "longSynopsis"):
            fixed = re.sub(
                rf'("{field}"\s*:\s*")(.+?)("(?=\s*[}},]))',
                lambda match: match.group(1) + re.sub(r'(?<!\\)"', r'\\"', match.group(2)) + match.group(3),
                fixed,
                flags=re.DOTALL,
            )
        return fixed

    def _parse_json(self, content: str) -> dict | None:
        for payload in (content, self._fix_broken_json(content)):
            try:
                return json.loads(payload)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return None

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False

        channel_id = self.get_channels_list()[channel]
        selected_date = datetime.fromisoformat(date)
        json_day_before = self._parse_json(
            self._get_content_from_url(self.generate_url(channel_obj, selected_date - timedelta(days=1)))
        )
        json_today = self._parse_json(self._get_content_from_url(self.generate_url(channel_obj, selected_date)))
        if not json_today:
            return False

        programs = (((json_today.get("epg") or {}).get(channel_id)) if isinstance(json_today, dict) else None) or []
        if not programs:
            return False
        previous = (((json_day_before or {}).get("epg") or {}).get(channel_id)) or []
        programs = list(previous) + list(programs)

        min_date, max_date = self.get_min_max_date(date)
        for raw_program in programs:
            start_date = datetime.fromtimestamp(int(raw_program["startDate"]) / 1000, tz=UTC)
            if start_date < min_date:
                continue
            if start_date > max_date:
                break
            program_title = raw_program.get("title") or ""
            if raw_program.get("eventName"):
                program_title += f" | {raw_program['eventName']}"
            program = Program.with_timestamp(int(raw_program["startDate"]) // 1000, int(raw_program["endDate"]) // 1000)
            program.add_title(program_title)
            program.add_sub_title(raw_program.get("subTitle"))
            program.set_episode_num(raw_program.get("seasonNumber"), raw_program.get("episodeNumber"))
            program.add_desc(raw_program.get("description"))
            program.add_category(raw_program.get("genre"))
            images = raw_program.get("images") or []
            if images:
                program.add_icon(images[0].get("url"))
            program.set_rating(_CSA.get(str(raw_program.get("moralityLevel")), "Tout public"))
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:  # noqa: ARG002
        return f"https://static-cdn.tv.sfr.net/data/epg/gen8/guide_web_{date.strftime('%Y%m%d')}.json"
