"""Bouygues provider — migrated from Bouygues.php."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import parse_iso_datetime, safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_CREDIT_TYPES = {
    "Acteur": "actor",
    "Réalisateur": "director",
    "Scénariste": "writer",
    "Producteur": "producer",
    "Musique": "composer",
    "Créateur": "editor",
    "Présentateur vedette": "presenter",
    "Autre présentateur": "presenter",
    "Commentateur": "commentator",
    "Origine Scénario": "adapter",
    "Scénario": "adapter",
}
_CSA = {2: "-10", 3: "-12", 4: "-16", 5: "-18"}


class Bouygues(AbstractProvider):
    def __init__(
        self, client: requests.Session, _json_path: str, priority: float, extra_params: dict | None = None
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_bouygues.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        min_date, max_date = self.get_min_max_date(date)
        payload = safe_json_loads(self._get_content_from_url(self.generate_url(channel_obj, min_date, max_date))) or {}
        events = ((((payload.get("channel") or [{}])[0]).get("event")) if isinstance(payload, dict) else None) or []
        if not events:
            return False

        for raw_program in events:
            program_info = raw_program.get("programInfo") or {}
            genre = (program_info.get("genre") or [None])[0]
            sub_genre = (program_info.get("subGenre") or [None])[0]
            if genre and sub_genre and genre == sub_genre:
                sub_genre = (program_info.get("genre") or [None, None])[1]
            parental = raw_program.get("parentalGuidance")
            csa = "Tout public"
            if parental:
                try:
                    csa = _CSA.get(int(str(parental).split(".")[-1]), "Tout public")
                except ValueError:
                    pass

            start_dt = parse_iso_datetime(raw_program.get("startTime"))
            end_dt = parse_iso_datetime(raw_program.get("endTime"))
            if start_dt is None or end_dt is None:
                continue
            start_dt = start_dt.astimezone(UTC)
            if start_dt < min_date:
                continue
            if start_dt > max_date:
                return channel_obj

            program = Program.with_timestamp(int(start_dt.timestamp()), int(end_dt.timestamp()))
            for intervenant in program_info.get("character") or []:
                full_name = f"{intervenant.get('firstName', '')} {intervenant.get('lastName', '')}".strip()
                program.add_credit(
                    full_name,
                    _CREDIT_TYPES.get(intervenant.get("function", ""), intervenant.get("function", "guest").lower()),
                )
            program.add_title(program_info.get("longTitle"))
            program.add_sub_title(program_info.get("secondaryTitle"))
            program.add_desc(program_info.get("longSummary") or program_info.get("shortSummary"))
            series_info = program_info.get("seriesInfo") or {}
            program.set_episode_num(series_info.get("seasonNumber"), series_info.get("episodeNumber"))
            program.add_category(genre)
            program.add_category(sub_genre)
            media = raw_program.get("media") or []
            if media:
                program.add_icon("https://img.bouygtel.fr" + str(media[0].get("url") or ""))
            program.set_rating(csa)
            if program_info.get("countryOfOrigin"):
                program.set_country(program_info["countryOfOrigin"], "fr")
            if program_info.get("productionDate"):
                program.set_date(str(program_info["productionDate"]))
            channel_obj.add_program(program)

        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, min_date: datetime, max_date: datetime) -> str:
        params = {
            "profile": "detailed",
            "epgChannelNumber": self._channels_list[channel.id],
            "eventCount": 9999,
            "startTime": min_date.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endTime": (max_date.astimezone(UTC) + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"https://epg.cms.pfs.bouyguesbox.fr/cms/sne/live/epg/events.json?{query}"
