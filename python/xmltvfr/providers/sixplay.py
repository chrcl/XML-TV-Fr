"""SixPlay provider — migrated from SixPlay.php."""

from __future__ import annotations

from datetime import UTC, datetime

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath


class SixPlay(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_6play.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        page: int | None = 1
        channel_id = self._channels_list[channel_obj.id]
        min_date, max_date = self.get_min_max_date(date)
        while page is not None:
            payload = (
                safe_json_loads(
                    self._get_content_from_url(self.generate_url(channel_obj, datetime.fromisoformat(date), page))
                )
                or {}
            )
            programs = payload.get(channel_id) if isinstance(payload, dict) else None
            if not programs:
                break
            page = None if len(programs) < 100 else page + 1
            for raw_program in programs:
                start_date = datetime.fromtimestamp(
                    int(
                        datetime.fromisoformat(
                            raw_program["real_diffusion_start_date"].replace("Z", "+00:00")
                        ).timestamp()
                    ),
                    tz=UTC,
                )
                if start_date < min_date:
                    continue
                if start_date > max_date:
                    page = None
                    break
                csa = "Tout public"
                if ((raw_program.get("csa") or {}).get("age") or 0) > 0:
                    csa = str(-int(raw_program["csa"]["age"]))
                image = None
                for image_data in raw_program.get("images") or []:
                    if image_data.get("role") == "vignette":
                        image = f"https://images.6play.fr/v2/images/{image_data['id']}/raw"
                        break
                program = Program.with_timestamp(
                    int(
                        datetime.fromisoformat(
                            raw_program["real_diffusion_start_date"].replace("Z", "+00:00")
                        ).timestamp()
                    ),
                    int(
                        datetime.fromisoformat(
                            raw_program["real_diffusion_end_date"].replace("Z", "+00:00")
                        ).timestamp()
                    ),
                )
                program.add_title(raw_program.get("title"))
                program.add_sub_title(raw_program.get("subtitle"))
                program.add_desc(raw_program.get("description"))
                program.add_category("Inconnu")
                program.add_icon(image)
                program.set_rating(csa)
                channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime, page: int = 1) -> str:
        channel_id = self._channels_list[channel.id]
        offset = 100 * (page - 1)
        return (
            "https://pc.middleware.6play.fr/6play/v2/platforms/m6group_web/services/m6replay/guidetv"
            f"?channel={channel_id}&from={date.strftime('%Y-%m-%d 00:00:00')}"
            f"&offset={offset}&limit=100&to={date.strftime('%Y-%m-%d 23:59:59')}&with=realdiffusiondates"
        )
