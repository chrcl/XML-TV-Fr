"""Telecablesat provider — migrated from Telecablesat.php."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

import requests

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.models.program import Program
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.utils.resource_path import ResourcePath

_BASE_URL = "https://tv-programme.telecablesat.fr"


class Telecablesat(AbstractProvider):
    def __init__(
        self,
        client: requests.Session,
        _json_path: str,
        priority: float,
        extra_params: dict | None = None,
    ) -> None:  # noqa: ARG002
        resolved_path = str(ResourcePath.get_instance().get_channel_path("channels_telecablesat.json"))
        super().__init__(client, resolved_path, priority)
        self._enable_details = (extra_params or {}).get("telecablesat_enable_details", True)

    def _get_content(self, url: str) -> str | None:
        for _ in range(3):
            content = self._get_content_from_url(url)
            if content:
                return content
        return None

    def _add_details(self, program: Program, url: str, diffusion_id: str) -> bool:
        content = self._get_content(url)
        if not content:
            return False
        content = content.split('<div class="top-menu">', 1)[1].split("<h2>Prochains épisodes</h2>", 1)[0]
        content = content.replace("<br>", "\n").replace("<br />", "\n")
        csa = re.search(r'class="age-(.*?)"', content)
        if csa:
            program.set_rating("-" + csa.group(1))
        season = re.search(r'itemprop="episodeNumber">(.*?)</span>', content, re.DOTALL)
        episode = re.search(r'</span>\((.*?)/<span itemprop="numberOfEpisodes">', content, re.DOTALL)
        program.set_episode_num(season.group(1) if season else None, episode.group(1) if episode else None)
        critique = (
            (content.split("<h2>Critique</h2>", 1)[1] if "<h2>Critique</h2>" in content else "")
            .split("<p>", 1)[1]
            .split("<", 1)[0]
            if "<h2>Critique</h2>" in content and "<p>" in content.split("<h2>Critique</h2>", 1)[1]
            else ""
        )
        resume_match = re.search(r"<h2>Résumé</h2>.*?<p>(.*?)</p>", content, re.DOTALL)
        subtitle = re.search(r'<h2 class="subtitle">(.*?)</h2>', content, re.DOTALL)
        directors = re.search(r'itemprop="director">(.*?)</span>', content, re.DOTALL)
        actors = re.findall(r'span itemprop="actor">(.*?)</span>(.*?)<', content, re.DOTALL)
        presenter = re.search(
            r'<div class="label w40">.*?Présentateur.*?</div>.*?<div class="text w60">(.*?)</div>', content, re.DOTALL
        )
        imgs = re.search(
            r'<div class="overlayerpicture">.*?<img class="lazy" alt=".*?" data-src="(.*?)"', content, re.DOTALL
        )
        diffusion_info = re.search(
            rf"<div data-chaine.*?data-diffusion='{diffusion_id}'>(.*?)<ul class=\"bouquets\">", content, re.DOTALL
        )
        if diffusion_info:
            if 'class="ear"' in diffusion_info.group(1):
                program.add_subtitles("teletext")
            if 'class="eye"' in diffusion_info.group(1):
                program.set_audio_described()
        if subtitle:
            program.add_sub_title(subtitle.group(1))
        if imgs:
            program.add_icon("https:" + imgs.group(1))
        desc = ""
        if resume_match:
            desc += resume_match.group(1).strip() + "\n\n"
        if critique:
            program.add_review(critique.strip())
        if directors:
            desc += f"Réalisateur(s) : {directors.group(1).strip()}\n"
            for director in directors.group(1).split(","):
                program.add_credit(director.strip(), "director")
        if presenter:
            desc += f"Présentateur(s) : {presenter.group(1).strip()}\n"
            for host in presenter.group(1).split(","):
                program.add_credit(host.strip(), "presenter")
        if actors:
            desc += "Acteurs : "
            for actor_name, actor_role in actors:
                program.add_credit(actor_name.strip(), "actor")
                desc += f"{actor_name.strip()}{actor_role} "
            desc += "\n"
        program.add_desc(desc)
        return True

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)
        if not self.channel_exists(channel):
            return False
        channel_content = self._channels_list[channel]
        channel_id = channel_content["id"]
        urls = [
            self.generate_url(channel_obj, datetime.fromisoformat(date) - timedelta(days=1)),
            self.generate_url(channel_obj, datetime.fromisoformat(date)),
        ]
        min_date, max_date = self.get_min_max_date(date)
        for url_index, url in enumerate(urls):
            content = self._get_content(url) or ""
            channels = re.findall(r'logos_chaines/(.*?).png" title="(.*?)"', content)
            channel_index = next((i for i, values in enumerate(channels) if values[0] == channel_id), -1)
            if channel_index >= 0:
                split_rows = content.split('<div class="row">')
                channel_row = split_rows[channel_index + 1] if channel_index + 1 < len(split_rows) else ""
                if channel_row:
                    times = re.findall(r'data-start="(.*?)" data-end="(.*?)"', channel_row)
                    imgs = re.findall(r'data-src="(.*?)"', channel_row)
                    genres_and_titles = re.findall(
                        r'<div class="hour-type">.*?</span>(.*?)</div>.*?<span class="title">(.*?)</span>',
                        channel_row,
                        re.DOTALL,
                    )
                    links = re.findall(r'class="link" href="(.*?)"', channel_row)
                    diffusion_ids = re.findall(r'data-diffusion="(.*?)"', channel_row)
                    count = len(times)
                    if len(imgs) != count or len(genres_and_titles) != count or len(links) != count:
                        return False
                    for index in range(count):
                        start_date = datetime.fromtimestamp(int(times[index][0]), tz=min_date.tzinfo)
                        if start_date < min_date:
                            continue
                        if start_date > max_date:
                            break
                        program = Program.with_timestamp(int(times[index][0]), int(times[index][1]))
                        program.add_title((genres_and_titles[index][1] or "").strip())
                        program.add_category((genres_and_titles[index][0] or "").strip())
                        self.set_status(f"{round(index * 100 / count, 2)} % ({url_index + 1}/2)")
                        channel_obj.add_program(program)
                        if self._enable_details and not self._add_details(
                            program, _BASE_URL + links[index], diffusion_ids[index]
                        ):
                            break
                        program.add_icon("https:" + imgs[index])
        return channel_obj if channel_obj.get_program_count() > 0 else False

    def generate_url(self, channel: Channel, date: datetime) -> str:
        channel_content = self._channels_list[channel.id]
        return f"{_BASE_URL}/programmes-tele/?date={date.strftime('%Y-%m-%d')}&page={channel_content['page']}"
