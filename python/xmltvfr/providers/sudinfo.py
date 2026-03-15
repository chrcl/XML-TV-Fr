"""SudInfo provider — migrated from SudInfo.php."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import ClassVar

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath
from xmltvfr.utils.utils import slugify

_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "fr-FR,fr-CA;q=0.8,en;q=0.5,en-US;q=0.3",
    "Connection": "keep-alive",
    "DNT": "1",
    "Host": "programmestv.sudinfo.be",
    "Priority": "u=0, i",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-GPC": "1",
    "TE": "trailers",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
}
_DAYS = {
    "Mon": "lundi",
    "Tue": "mardi",
    "Wed": "mercredi",
    "Thu": "jeudi",
    "Fri": "vendredi",
    "Sat": "samedi",
    "Sun": "dimanche",
}
_BASE_URL = "https://programmestv.sudinfo.be"
_CREDIT_TYPES = {
    "Acteur": "actor",
    "Producteur": "producer",
    "Maison de Production": "producer",
    "Réalisateur": "director",
    "Scénario": "writer",
    "Présentateur": "presenter",
}


class SudInfo(AbstractProvider):
    _BUILD_ID: ClassVar[str | None] = None

    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_sudinfo.json"))
        super().__init__(client, resolved_path, priority)
        self._enable_details = (extra_params or {}).get("sudinfo_enable_details", True)

    def get_build_id(self) -> str:
        if type(self)._BUILD_ID is None:
            content = self._get_content_from_url(f"{_BASE_URL}/programme-tv/ce-soir", headers=dict(_HEADERS))
            match = re.search(r'"buildId":"(.*?)"', content)
            if not match:
                raise RuntimeError("Cannot retrieve build id")
            type(self)._BUILD_ID = match.group(1)
        return type(self)._BUILD_ID

    @staticmethod
    def _get_day_label(date: datetime) -> str:
        normalized = date.replace(hour=0, minute=0, second=0, microsecond=0)
        today = datetime.now(normalized.tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        week_after = today + timedelta(days=6)
        if normalized < yesterday:
            raise ValueError("Date is too early !")
        if normalized.date() == yesterday.date():
            return "hier"
        if normalized.date() == today.date():
            return "aujourdhui"
        day_label = _DAYS[normalized.strftime("%a")]
        if normalized > week_after:
            day_label += "prochain"
        return day_label

    def _add_casting(self, casting: list[dict], program: Program) -> None:
        for cast in casting:
            name = " ".join(part for part in [cast.get("firstname"), cast.get("lastname")] if part).strip()
            if cast.get("role"):
                name = f"{name} ({cast['role']})".strip()
            function_name = ((cast.get("castFunction") or {}).get("name")) or ""
            program.add_credit(name, _CREDIT_TYPES.get(function_name, "guest"))

    def _add_details(self, programs_with_slug: list[tuple[str, Program]], build_id: str) -> None:
        count = len(programs_with_slug)
        for index, (slug, program) in enumerate(programs_with_slug):
            self.set_status(f"Details | ({index}/{count})")
            payload = (
                safe_json_loads(
                    self._get_content_from_url(self.generate_url_from_slug(slug, build_id), headers=dict(_HEADERS))
                )
                or {}
            )
            content = ((payload.get("pageProps") or {}).get("content")) if isinstance(payload, dict) else {}
            content = content or {}
            program.add_category((content.get("category") or {}).get("name"))
            texts = content.get("texts") or []
            if texts:
                program.add_desc((texts[0] or {}).get("detail"))
            if content.get("yearOfProduction"):
                program.set_date(str(content["yearOfProduction"]))
            self._add_casting(content.get("casting") or [], program)
        self.set_status("Terminé")

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        min_date, max_date = self.get_min_max_date(date)
        day_labels = [self._get_day_label(min_date - timedelta(days=1)), self._get_day_label(min_date)]
        build_id = self.get_build_id()
        programs_with_slug: list[tuple[str, Program]] = []
        for day_label in day_labels:
            self.set_status("Informations principales")
            payload = (
                safe_json_loads(
                    self._get_content_from_url(
                        self.generate_url(channel_obj, day_label, build_id), headers=dict(_HEADERS)
                    )
                )
                or {}
            )
            content = (((payload.get("pageProps") or {}).get("content")) if isinstance(payload, dict) else None) or []
            for raw_program in content:
                start_date = datetime.fromisoformat(raw_program["airingStartDateTime"].replace("Z", "+00:00"))
                end_date = datetime.fromisoformat(raw_program["airingEndDateTime"].replace("Z", "+00:00"))
                if start_date < min_date:
                    continue
                if start_date > max_date:
                    break
                program = Program(start_date, end_date)
                programs_with_slug.append((raw_program["slug"], program))
                program.add_title(raw_program.get("title"))
                program.add_sub_title(raw_program.get("subTitle"))
                program.add_category((raw_program.get("contentSubCategory") or {}).get("name"))
                images = raw_program.get("images") or []
                image = (((images[0] if images else {}).get("url")) or "").replace("/square/", "/landscape/")
                if image:
                    program.add_icon(
                        "https://ipx-programmestv.sudinfo.be/_ipx/f_webp,sharpen_100,w_1280,h_720/" + image
                    )
                channel_obj.add_program(program)
        if self._enable_details:
            self._add_details(programs_with_slug, build_id)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, day_label: str, build_id: str) -> str:
        channel_info = self._channels_list[channel.id]
        slug = slugify(channel_info["name"])
        channel_id = channel_info["id"]
        return (
            f"{_BASE_URL}/_next/data/{build_id}/programme-tv/chaine/{slug}/{channel_id}/{day_label}.json"
            f"?slug={slug}&slug={channel_id}&slug={day_label}"
        )

    @staticmethod
    def generate_url_from_slug(slug: str, build_id: str) -> str:
        parts = slug.split("/")
        return f"{_BASE_URL}/_next/data/{build_id}{slug}.json?slug={parts[2]}&slug={parts[3]}"
