"""TeleLoisirs provider — migrated from TeleLoisirs.php."""

from __future__ import annotations

from datetime import datetime

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers._helpers import safe_json_loads, strip_tags
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath


class TeleLoisirs(AbstractProvider):
    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_teleloisirs.json"))
        super().__init__(client, resolved_path, priority)

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        content = self._get_content_from_url(self.generate_url(channel_obj, datetime.fromisoformat(date)))
        blocks = content.split('<div class="mainBroadcastCard reverse"')[1:]
        count = len(blocks)
        for index, block in enumerate(blocks):
            self.set_status(f"{round(index * 100 / count, 2)} %")
            title_href_parts = block.split('href="', 1)
            if len(title_href_parts) < 2:
                continue
            href, _, rest = title_href_parts[1].partition('" title="')
            title, _, _ = rest.partition('"')
            srcset = (block.split('srcset="', 1)[1] if 'srcset="' in block else "").split('"', 1)[0]
            image = srcset.split(" ")[0].replace("64x90", "640x360") if srcset else ""
            genre = (
                
                    (
                        block.split('<div class="mainBroadcastCard-genre">', 1)[1]
                        if '<div class="mainBroadcastCard-genre">' in block
                        else ""
                    ).split("</div>", 1)[0]
                
            ).strip()
            genre_format = (
                
                    (
                        block.split('<p class="mainBroadcastCard-format">', 1)[1]
                        if '<p class="mainBroadcastCard-format">' in block
                        else ""
                    ).split("</p>", 1)[0]
                
            ).strip()
            subtitle = (
                
                    (
                        block.split('<p class="mainBroadcastCard-subtitle">', 1)[1]
                        if '<p class="mainBroadcastCard-subtitle">' in block
                        else ""
                    ).split("</p>", 1)[0]
                
            ).strip()
            start_section = block.split('<p class="mainBroadcastCard-startingHour"', 1)
            if len(start_section) < 2:
                continue
            hour = start_section[1].split(">", 1)[1].split("<", 1)[0]
            duration_raw = (
                block.split('<span class="mainBroadcastCard-durationContent">', 1)[1]
                if '<span class="mainBroadcastCard-durationContent">' in block
                else ""
            ).split("<", 1)[0]
            if not duration_raw:
                return False
            duration_clean = duration_raw.replace("min", "")
            duration_parts = duration_clean.split("h")
            duration = 60 * int(duration_parts[0])
            if len(duration_parts) == 2:
                duration = 3600 * int(duration_parts[0]) + 60 * int(duration_parts[1])
            start_ts = int(datetime.fromisoformat(f"{date} {hour.replace('h', ':')}").timestamp())
            program = Program.with_timestamp(start_ts, start_ts + duration)
            detail = self._get_content_from_url(f"https://www.programme-tv.net{href}")
            detail_json_block = detail.split('<script type="application/ld+json">', 1)
            synopsis = ""
            if len(detail_json_block) > 1:
                detail_json = safe_json_loads(detail_json_block[1].split("</script>", 1)[0]) or {}
                synopsis = strip_tags(detail_json.get("description"))
                if detail_json.get("dateCreated"):
                    program.set_date(str(detail_json["dateCreated"]))
                if detail_json.get("countryOfOrigin"):
                    program.set_country(detail_json["countryOfOrigin"], "fr")
                review = detail_json.get("review") or {}
                if review:
                    program.add_review(review.get("description") or review.get("reviewBody"))
                    if review.get("reviewRating"):
                        program.add_star_rating(review["reviewRating"]["ratingValue"], 5)
                program.set_episode_num(
                    ((detail_json.get("partOfSeason") or {}).get("seasonNumber")),
                    detail_json.get("episodeNumber"),
                )
                for key in ("actor", "director"):
                    for person in detail_json.get(key) or []:
                        program.add_credit(person.get("name"), key)
            else:
                if '<div class="synopsis-text">' in detail:
                    synopsis = strip_tags(detail.split('<div class="synopsis-text">', 1)[1].split("</div>", 1)[0])
                participants = detail.split('figcaption class="personCard-mediaLegend')[1:]
                for participant in participants:
                    parts = participant.split(">")
                    name = parts[2].split("<", 1)[0].strip() if len(parts) > 2 else ""
                    role = (
                        participant.split('"personCard-mediaLegendRole">', 1)[1].split("<", 1)[0].strip()
                        if '"personCard-mediaLegendRole">' in participant
                        else ""
                    )
                    tag = "presenter" if role == "Présentateur" else "director" if role == "Réalisateur" else "guest"
                    program.add_credit(name, tag)
            program.add_title(title)
            program.add_sub_title(subtitle)
            program.add_category(genre)
            program.add_category(genre_format)
            program.add_icon(image)
            program.add_desc(synopsis.strip())
            if "mainBroadcastCard-rebroadcast" in block:
                program.set_previously_shown()
            if "mainBroadcastCard-new" in block:
                program.set_premiere()
            if "mainBroadcastCard-deaf" in block:
                program.add_subtitles("teletext")
            if "mainBroadcastCard-audioDescription" in block:
                program.set_audio_described()
            channel_obj.add_program(program)
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        channel_id = self._channels_list[channel.id]
        if date.strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d"):
            return f"https://www.programme-tv.net/programme/chaine/{channel_id}"
        return f"https://www.programme-tv.net/programme/chaine/{date.strftime('%Y-%m-%d')}/{channel_id}"

    def get_logo(self, channel: str) -> str | None:
        super().get_logo(channel)
        channel_url = self._channels_list[channel]
        content = self._get_content_from_url("https://www.programme-tv.net/_esi/channel-list/?bouquet=perso&modal=0")
        parts = content.split(channel_url, 1)
        if len(parts) < 2:
            return None
        delimited = parts[1].split("</li>", 1)[0]
        if 'src="' not in delimited:
            return None
        image = delimited.split('src="', 1)[1].split('"', 1)[0]
        image = image.replace("/80/", "/100/")
        return image.replace("34x34", "480x480")
