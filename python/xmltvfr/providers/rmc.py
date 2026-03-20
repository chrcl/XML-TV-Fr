"""RMC provider — thin SFR variant migrated from RMC.php."""

from __future__ import annotations

from datetime import datetime

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.providers.sfr import SFR


class RMC(SFR):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        super().__init__(client, _json_path, priority, {"provider": "rmc"})

    def generate_url(self, channel: Channel, date: datetime) -> str:  # noqa: ARG002
        return f"https://static-cdn.tv.sfr.net/data/epg/bfmrmc/guide_web_{date.strftime('%Y%m%d')}.json"
