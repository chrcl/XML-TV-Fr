"""Voo provider — migrated from Voo.php."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_BODY = (
    '<SubQueryOptions><QueryOption path="Titles">'
    "/Props/Name,Pictures,ShortSynopsis,LongSynopsis,Genres,Events,SeriesCount,SeriesCollection"
    "</QueryOption>"
    '<QueryOption path="Titles/Events">/Props/IsAvailable</QueryOption>'
    '<QueryOption path="Products">'
    "/Props/ListPrice,OfferPrice,CouponCount,Name,EntitlementState,IsAvailable"
    "</QueryOption>"
    '<QueryOption path="Channels">/Props/Products</QueryOption>'
    '<QueryOption path="Channels/Products">'
    "/Filter/EntitlementEnd>2018-01-27T14:40:43Z/Props/EntitlementEnd,EntitlementState"
    "</QueryOption></SubQueryOptions>"
)


class Voo(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_voo.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        min_date, max_date = self.get_min_max_date(date)
        try:
            response = self._client.post(self.generate_url(channel_obj, min_date), data=_BODY, timeout=20)
            response.raise_for_status()
        except Exception:  # noqa: BLE001
            return False
        payload = safe_json_loads(response.text) or {}
        events = (((payload.get("Events") or {}).get("Event")) if isinstance(payload, dict) else None) or []
        if isinstance(events, dict):
            events = [events]
        if not events:
            return False
        for event in events:
            start = int(datetime.fromisoformat(event["AvailabilityStart"].replace("Z", "+00:00")).timestamp())
            start_date = datetime.fromtimestamp(start, tz=UTC)
            if start_date < min_date:
                continue
            if start_date > max_date:
                break
            end = int(datetime.fromisoformat(event["AvailabilityEnd"].replace("Z", "+00:00")).timestamp())
            title_data = (((event.get("Titles") or {}).get("Title")) or [{}])[0]
            program = Program.with_timestamp(start, end)
            program.add_title(title_data.get("Name"))
            program.add_desc(title_data.get("LongSynopsis"))
            program.add_category((((title_data.get("Genres") or {}).get("Genre")) or [{}])[0].get("Value"))
            program.add_icon((((title_data.get("Pictures") or {}).get("Picture")) or [{}])[0].get("Value"))
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        start = date.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = (date.astimezone(UTC) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return (
            "https://publisher.voomotion.be/traxis/web/Channel/"
            f"{self._channels_list[channel.id]}/Events/Filter/AvailabilityEnd%3C={end_str}%26%26AvailabilityStart%3E={start}"
            "/Sort/AvailabilityStart/Props/IsAvailable,Products,AvailabilityEnd,AvailabilityStart,ChannelId,AspectRatio,DurationInSeconds,Titles,Channels?output=json&Language=fr&Method=PUT"
        )
