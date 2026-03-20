"""Unit tests for the Tele7Jours provider."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
import requests

_PARIS_TZ = ZoneInfo("Europe/Paris")


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_provider(channels: dict | None = None, enable_details: bool = True):
    """Instantiate a :class:`Tele7Jours` with an in-memory channels list."""
    from xmltvfr.providers.tele7jours import Tele7Jours

    session = requests.Session()
    with patch("xmltvfr.providers.tele7jours.ResourcePath") as mock_rp:
        # Write a temp JSON file so AbstractProvider can load it
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(channels or {"TF1.fr": "tf1", "France2.fr": "france-2"}, f)
            tmp_path = f.name

        mock_rp.get_instance.return_value.get_channel_path.return_value = tmp_path
        provider = Tele7Jours(
            session,
            "",
            0.6,
            extra_params={"tele7jours_enable_details": enable_details},
        )

    return provider


# ---------------------------------------------------------------------------
# _get_day_label
# ---------------------------------------------------------------------------


class TestGetDayLabel:
    """Tests for Tele7Jours._get_day_label."""

    def _today(self) -> datetime:
        return datetime.now(_PARIS_TZ).replace(hour=0, minute=0, second=0, microsecond=0)

    def test_today_returns_empty_string(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        label = Tele7Jours._get_day_label(self._today())
        assert label == ""

    def test_yesterday_returns_hier(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        yesterday = self._today() - timedelta(days=1)
        label = Tele7Jours._get_day_label(yesterday)
        assert label == "hier"

    def test_tomorrow_returns_french_day_name(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        tomorrow = self._today() + timedelta(days=1)
        label = Tele7Jours._get_day_label(tomorrow)
        # Must be one of the seven French day names (without 'prochain')
        french_days = {"lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"}
        assert label in french_days

    def test_in_six_days_returns_day_name_without_prochain(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        target = self._today() + timedelta(days=6)
        label = Tele7Jours._get_day_label(target)
        assert "prochain" not in label

    def test_in_seven_days_returns_day_name_with_prochain(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        target = self._today() + timedelta(days=7)
        label = Tele7Jours._get_day_label(target)
        assert label.endswith("prochain")

    def test_date_before_yesterday_raises_value_error(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        too_early = self._today() - timedelta(days=2)
        with pytest.raises(ValueError, match="too early"):
            Tele7Jours._get_day_label(too_early)

    def test_naive_datetime_treated_as_paris_tz(self):
        """A tz-naive datetime equal to today should return ''."""
        from xmltvfr.providers.tele7jours import Tele7Jours

        naive_today = datetime.now(_PARIS_TZ).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        label = Tele7Jours._get_day_label(naive_today)
        assert label == ""


# ---------------------------------------------------------------------------
# generate_url
# ---------------------------------------------------------------------------


class TestGenerateUrl:
    def test_url_format(self):
        from xmltvfr.domain.models.channel import Channel

        provider = _make_provider({"TF1.fr": "tf1"})
        channel = Channel("TF1.fr", None, None)
        url = provider.generate_url(channel, "lundi")
        assert url == "https://www.programme-television.org/tv/chaines/tf1/lundi"

    def test_url_today_empty_day_label(self):
        from xmltvfr.domain.models.channel import Channel

        provider = _make_provider({"France2.fr": "france-2"})
        channel = Channel("France2.fr", None, None)
        url = provider.generate_url(channel, "")
        assert url == "https://www.programme-television.org/tv/chaines/france-2/"


# ---------------------------------------------------------------------------
# _get_tag_name
# ---------------------------------------------------------------------------


class TestGetTagName:
    def test_realisateur_maps_to_director(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        assert Tele7Jours._get_tag_name("Réalisateur") == "director"

    def test_producteur_maps_to_producer(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        assert Tele7Jours._get_tag_name("Producteur") == "producer"

    def test_unknown_maps_to_guest(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        assert Tele7Jours._get_tag_name("Acteur principal") == "guest"


# ---------------------------------------------------------------------------
# _parse_program
# ---------------------------------------------------------------------------

_HTML_BLOCK = """
  ">
  <a href="https://www.programme-television.org/programme/12345/the-show">
    <img srcset="https://img.example.com/show_small.jpg 300w, https://img.example.com/show_large.jpg 600w"
         alt="The Show"/>
    <div class="tvgrid-broadcast__details-time">20h35</div>
    <div class="tvgrid-broadcast__details-title">The Show</div>
    <div class="tvgrid-broadcast__details-season">S02E05 | Titre de l'épisode</div>
    <div class="tvgrid-broadcast__subdetails">90mn | Inédit | Série</div>
  </a>
"""

_HTML_BLOCK_NO_DURATION = """
  ">
  <a href="https://www.programme-television.org/programme/99/simple">
    <div class="tvgrid-broadcast__details-time">08h00</div>
    <div class="tvgrid-broadcast__details-title">Simple Show</div>
    <div class="tvgrid-broadcast__subdetails">Film</div>
  </a>
"""


class TestParseProgram:
    def test_parses_title_and_start_time(self):
        provider = _make_provider(enable_details=False)
        program = provider._parse_program("2025-06-10", _HTML_BLOCK)

        assert program is not None
        title_tags = program.get_children("title")
        assert len(title_tags) == 1
        assert title_tags[0].value == "The Show"

    def test_parses_start_datetime_correctly(self):
        provider = _make_provider(enable_details=False)
        program = provider._parse_program("2025-06-10", _HTML_BLOCK)

        assert program is not None
        expected_start = datetime(2025, 6, 10, 20, 35, tzinfo=_PARIS_TZ)
        assert program.get_start() == expected_start

    def test_parses_duration_into_end_time(self):
        provider = _make_provider(enable_details=False)
        program = provider._parse_program("2025-06-10", _HTML_BLOCK)

        assert program is not None
        expected_end = datetime(2025, 6, 10, 20, 35, tzinfo=_PARIS_TZ) + timedelta(minutes=90)
        assert program.get_end() == expected_end

    def test_premiere_flag_set_when_inedit(self):
        provider = _make_provider(enable_details=False)
        program = provider._parse_program("2025-06-10", _HTML_BLOCK)

        assert program is not None
        assert program.get_children("premiere") != []

    def test_category_extracted_from_last_sub_detail(self):
        provider = _make_provider(enable_details=False)
        program = provider._parse_program("2025-06-10", _HTML_BLOCK)

        assert program is not None
        cat_tags = program.get_children("category")
        assert len(cat_tags) == 1
        assert cat_tags[0].value == "Série"

    def test_episode_num_parsed(self):
        provider = _make_provider(enable_details=False)
        program = provider._parse_program("2025-06-10", _HTML_BLOCK)

        assert program is not None
        ep_tags = program.get_children("episode-num")
        assert len(ep_tags) == 1
        # Season 2 (0-indexed = 1), Episode 5 (0-indexed = 4)
        assert ep_tags[0].value == "1.4."

    def test_subtitle_non_episode_parts_joined(self):
        provider = _make_provider(enable_details=False)
        program = provider._parse_program("2025-06-10", _HTML_BLOCK)

        assert program is not None
        sub_tags = program.get_children("sub-title")
        assert len(sub_tags) == 1
        assert sub_tags[0].value == "Titre de l'épisode"

    def test_icon_extracted_from_srcset(self):
        provider = _make_provider(enable_details=False)
        program = provider._parse_program("2025-06-10", _HTML_BLOCK)

        assert program is not None
        icon_tags = program.get_children("icon")
        assert len(icon_tags) == 1
        # Last entry in srcset (highest resolution)
        assert "show_large.jpg" in icon_tags[0].attributes["src"]

    def test_fallback_duration_when_no_duration_given(self):
        """When no duration is present in sub-details, a 30-minute default is used."""
        provider = _make_provider(enable_details=False)
        program = provider._parse_program("2025-06-10", _HTML_BLOCK_NO_DURATION)

        assert program is not None
        expected_end = datetime(2025, 6, 10, 8, 0, tzinfo=_PARIS_TZ) + timedelta(minutes=30)
        assert program.get_end() == expected_end

    def test_returns_none_when_start_time_missing(self):
        provider = _make_provider(enable_details=False)
        result = provider._parse_program("2025-06-10", "<div>No time here</div>")
        assert result is None

    def test_details_called_when_enabled(self):
        """add_details should be invoked when _enable_details is True and a URL is present."""
        provider = _make_provider(enable_details=True)
        with patch.object(provider, "add_details") as mock_add_details:
            provider._parse_program("2025-06-10", _HTML_BLOCK)
            mock_add_details.assert_called_once()
            call_url = mock_add_details.call_args[0][1]
            assert call_url.startswith("https://www.programme-television.org/")

    def test_details_not_called_when_disabled(self):
        """add_details must NOT be invoked when _enable_details is False."""
        provider = _make_provider(enable_details=False)
        with patch.object(provider, "add_details") as mock_add_details:
            provider._parse_program("2025-06-10", _HTML_BLOCK)
            mock_add_details.assert_not_called()


# ---------------------------------------------------------------------------
# add_details
# ---------------------------------------------------------------------------

_DETAIL_HTML = """
<html>
<body>
  <p class="program-details__summary-text">
    An exciting <strong>drama</strong> series.
  </p>
  <ul>
    <li class="casting__item">
      <p class="casting__name">Jane Doe</p>
      <span class="casting__role">Réalisateur</span>
    </li>
    <li class="casting__item">
      <p class="casting__name">John Smith</p>
      <span class="casting__role">Acteur principal</span>
    </li>
  </ul>
</body>
</html>
"""


class TestAddDetails:
    def test_description_added_stripped_of_tags(self):
        from xmltvfr.domain.models.program import Program

        provider = _make_provider()
        start = datetime(2025, 6, 10, 20, 0, tzinfo=_PARIS_TZ)
        end = datetime(2025, 6, 10, 21, 0, tzinfo=_PARIS_TZ)
        program = Program(start, end)

        with patch.object(provider, "_get_content_from_url", return_value=_DETAIL_HTML):
            provider.add_details(program, "https://example.com/detail")

        desc_tags = program.get_children("desc")
        assert len(desc_tags) == 1
        assert "drama" in desc_tags[0].value
        assert "<strong>" not in desc_tags[0].value

    def test_director_credit_added(self):
        from xmltvfr.domain.models.program import Program

        provider = _make_provider()
        start = datetime(2025, 6, 10, 20, 0, tzinfo=_PARIS_TZ)
        end = datetime(2025, 6, 10, 21, 0, tzinfo=_PARIS_TZ)
        program = Program(start, end)

        with patch.object(provider, "_get_content_from_url", return_value=_DETAIL_HTML):
            provider.add_details(program, "https://example.com/detail")

        credits = program.get_children("credits")
        assert credits
        director_tags = credits[0].get_children("director")
        assert len(director_tags) == 1
        assert director_tags[0].value == "Jane Doe"

    def test_unknown_role_added_as_guest_with_role_suffix(self):
        from xmltvfr.domain.models.program import Program

        provider = _make_provider()
        start = datetime(2025, 6, 10, 20, 0, tzinfo=_PARIS_TZ)
        end = datetime(2025, 6, 10, 21, 0, tzinfo=_PARIS_TZ)
        program = Program(start, end)

        with patch.object(provider, "_get_content_from_url", return_value=_DETAIL_HTML):
            provider.add_details(program, "https://example.com/detail")

        credits = program.get_children("credits")
        assert credits
        guest_tags = credits[0].get_children("guest")
        assert len(guest_tags) == 1
        assert "John Smith" in guest_tags[0].value
        assert "Acteur principal" in guest_tags[0].value

    def test_no_crash_when_content_is_empty(self):
        from xmltvfr.domain.models.program import Program

        provider = _make_provider()
        start = datetime(2025, 6, 10, 20, 0, tzinfo=_PARIS_TZ)
        end = datetime(2025, 6, 10, 21, 0, tzinfo=_PARIS_TZ)
        program = Program(start, end)

        with patch.object(provider, "_get_content_from_url", return_value=""):
            provider.add_details(program, "https://example.com/detail")

        assert program.get_children("desc") == []
        assert program.get_children("credits") == []


# ---------------------------------------------------------------------------
# construct_epg
# ---------------------------------------------------------------------------

_GRID_HTML = (
    'class="tvgrid-broadcast__item'
    """">
  <a href="https://www.programme-television.org/programme/1/news">
    <div class="tvgrid-broadcast__details-time">20h00</div>
    <div class="tvgrid-broadcast__details-title">Journal télévisé</div>
    <div class="tvgrid-broadcast__subdetails">30mn | Magazine</div>
  </a>
"""
    'class="tvgrid-broadcast__item'
    """">
  <a href="https://www.programme-television.org/programme/2/film">
    <div class="tvgrid-broadcast__details-time">20h35</div>
    <div class="tvgrid-broadcast__details-title">Le Grand Film</div>
    <div class="tvgrid-broadcast__subdetails">120mn | Cinéma</div>
  </a>
"""
)


class TestConstructEpg:
    def test_returns_false_for_unknown_channel(self):
        provider = _make_provider({"TF1.fr": "tf1"})
        result = provider.construct_epg("Unknown.fr", "2025-06-10")
        assert result is False

    def test_returns_channel_with_programs(self):
        provider = _make_provider({"TF1.fr": "tf1"}, enable_details=False)

        with (
            patch.object(provider, "_get_content_from_url", return_value=_GRID_HTML),
            patch.object(
                provider,
                "_get_day_label",
                return_value="mardi",
            ),
        ):
            result = provider.construct_epg("TF1.fr", "2025-06-10")

        from xmltvfr.domain.models.channel import Channel

        assert isinstance(result, Channel)
        assert result.get_program_count() == 2

    def test_programs_have_correct_titles(self):
        provider = _make_provider({"TF1.fr": "tf1"}, enable_details=False)

        with patch.object(provider, "_get_content_from_url", return_value=_GRID_HTML):
            with patch.object(
                type(provider),
                "_get_day_label",
                staticmethod(lambda d: "mardi"),
            ):
                result = provider.construct_epg("TF1.fr", "2025-06-10")

        titles = [
            p.get_children("title")[0].value for p in result.get_programs()
        ]
        assert "Journal télévisé" in titles
        assert "Le Grand Film" in titles

    def test_returns_false_when_date_too_early(self):
        provider = _make_provider({"TF1.fr": "tf1"})
        # Use a date far in the past — _get_day_label will raise ValueError
        result = provider.construct_epg("TF1.fr", "2020-01-01")
        assert result is False

    def test_status_callback_called(self):
        provider = _make_provider({"TF1.fr": "tf1"}, enable_details=False)
        status_calls: list[str] = []
        provider.set_status_callback(status_calls.append)

        with patch.object(provider, "_get_content_from_url", return_value=_GRID_HTML):
            with patch.object(
                type(provider),
                "_get_day_label",
                staticmethod(lambda d: "mardi"),
            ):
                provider.construct_epg("TF1.fr", "2025-06-10")

        assert len(status_calls) > 0


# ---------------------------------------------------------------------------
# Provider initialisation
# ---------------------------------------------------------------------------


class TestInit:
    def test_default_enable_details_is_true(self):
        provider = _make_provider()
        assert provider._enable_details is True

    def test_enable_details_can_be_disabled(self):
        provider = _make_provider(enable_details=False)
        assert provider._enable_details is False

    def test_channels_list_loaded(self):
        provider = _make_provider({"TF1.fr": "tf1", "M6.fr": "m6"})
        assert provider.channel_exists("TF1.fr")
        assert provider.channel_exists("M6.fr")
        assert not provider.channel_exists("Unknown.fr")

    def test_priority_stored(self):
        from xmltvfr.providers.tele7jours import Tele7Jours

        assert Tele7Jours.get_priority() == pytest.approx(0.6)
