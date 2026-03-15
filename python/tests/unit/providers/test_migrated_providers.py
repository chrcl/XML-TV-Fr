"""Content-return tests for migrated providers."""

from __future__ import annotations

import importlib
import json
import tempfile
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import requests

_PARIS = ZoneInfo("Europe/Paris")
_TORONTO = ZoneInfo("America/Toronto")


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def _make_provider(
    module_name: str,
    class_name: str,
    channels: dict,
    *,
    priority: float = 0.5,
    extra_params: dict | None = None,
    extra_patchers: list | None = None,
):
    module = importlib.import_module(f"xmltvfr.providers.{module_name}")
    provider_class = getattr(module, class_name)
    session = requests.Session()
    with ExitStack() as stack:
        for patcher in extra_patchers or []:
            stack.enter_context(patcher)
        resource_module = (
            f"xmltvfr.providers.{module_name}"
            if hasattr(module, "ResourcePath")
            else provider_class.__mro__[1].__module__
        )
        mock_rp = stack.enter_context(patch(f"{resource_module}.ResourcePath"))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump(channels, handle)
            tmp_path = handle.name
        mock_rp.get_instance.return_value.get_channel_path.return_value = tmp_path
        provider = provider_class(session, "", priority, extra_params=extra_params)
    return provider


def _titles(channel) -> list[str]:
    return [program.get_children("title")[0].value for program in channel.get_programs()]


def _assert_channel_title(channel, expected_title: str) -> None:
    assert channel is not False
    assert channel.get_program_count() >= 1
    assert expected_title in _titles(channel)


def test_orange_returns_programs():
    provider = _make_provider("orange", "Orange", {"TF1.fr": "123"}, priority=0.95)
    start_ts = int(datetime(2025, 6, 10, 20, 0, tzinfo=_PARIS).timestamp())
    payload = [
        {
            "diffusionDate": start_ts,
            "duration": 3600,
            "synopsis": "Desc",
            "genre": "Film",
            "genreDetailed": "Action",
            "covers": [{"url": "https://img/orange.jpg"}],
            "csa": "3",
            "title": "Orange Show",
            "audioDescription": True,
        }
    ]
    with patch.object(provider, "_get_content_from_url", side_effect=["[]", json.dumps(payload)]):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "Orange Show")


def test_playtv_returns_programs():
    provider = _make_provider("playtv", "PlayTV", {"TF1.fr": "10"}, priority=0.45)
    payload = {
        "data": [
            {
                "start_at": "2025-06-10T20:00:00Z",
                "end_at": "2025-06-10T21:00:00Z",
                "title": "PlayTV Show",
                "subtitle": "Episode 1",
                "media": {
                    "attrs": {
                        "texts": {"short": "Desc"},
                        "images": {"large": [{"url": "https://img/playtv.jpg"}]},
                        "season": "1",
                        "episode": "2",
                    },
                    "path": [{"category": "divertissement"}],
                },
            }
        ]
    }
    with patch.object(provider, "_get_content_from_url", return_value=json.dumps(payload)):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "PlayTV Show")


def test_bouygues_returns_programs():
    provider = _make_provider("bouygues", "Bouygues", {"TF1.fr": "1"}, priority=0.9)
    payload = {
        "channel": [
            {
                "event": [
                    {
                        "startTime": "2025-06-10T20:00:00+00:00",
                        "endTime": "2025-06-10T21:00:00+00:00",
                        "parentalGuidance": "foo.3",
                        "media": [{"url": "/img.jpg"}],
                        "programInfo": {
                            "longTitle": "Bouygues Show",
                            "secondaryTitle": "Sub",
                            "longSummary": "Desc",
                            "genre": ["Film"],
                            "subGenre": ["Action"],
                            "character": [{"firstName": "John", "lastName": "Doe", "function": "Acteur"}],
                        },
                    }
                ]
            }
        ]
    }
    with patch.object(provider, "_get_content_from_url", return_value=json.dumps(payload)):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "Bouygues Show")


def test_oqee_returns_programs():
    provider = _make_provider("oqee", "Oqee", {"TF1.fr": "11"}, priority=0.5)
    first = {
        "result": {
            "entries": [
                {
                    "live": {
                        "start": int(datetime(2025, 6, 10, 20, 0, tzinfo=ZoneInfo("UTC")).timestamp()),
                        "end": int(datetime(2025, 6, 10, 21, 0, tzinfo=ZoneInfo("UTC")).timestamp()),
                        "title": "Oqee Show",
                        "description": "Desc",
                        "category": "Sport",
                        "sub_category": "Football",
                        "parental_rating": 12,
                        "audio_description": True,
                    },
                    "pictures": {"main": "https://img/h%d/test.jpg"},
                }
            ]
        }
    }
    second = {
        "result": {
            "entries": [
                {
                    "live": {
                        "start": int(datetime(2025, 6, 11, 5, 0, tzinfo=ZoneInfo("UTC")).timestamp()),
                        "end": int(datetime(2025, 6, 11, 6, 0, tzinfo=ZoneInfo("UTC")).timestamp()),
                        "title": "Future",
                        "description": "Desc",
                    },
                    "pictures": {},
                }
            ]
        }
    }
    with patch.object(provider, "_get_content_from_url", side_effect=[json.dumps(first), json.dumps(second)]):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "Oqee Show")


def test_sfr_returns_programs():
    provider = _make_provider("sfr", "SFR", {"TF1.fr": "321"}, priority=0.85)
    payload = {
        "epg": {"321": [{"startDate": 1749585600000, "endDate": 1749589200000, "title": "SFR Show", "genre": "Info"}]}
    }
    with patch.object(provider, "_get_content_from_url", side_effect=[json.dumps({"epg": {}}), json.dumps(payload)]):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "SFR Show")


def test_rmc_returns_programs():
    provider = _make_provider("rmc", "RMC", {"RMC.fr": "654"}, priority=0.85)
    payload = {
        "epg": {"654": [{"startDate": 1749585600000, "endDate": 1749589200000, "title": "RMC Show", "genre": "Info"}]}
    }
    with patch.object(provider, "_get_content_from_url", side_effect=[json.dumps({"epg": {}}), json.dumps(payload)]):
        result = provider.construct_epg("RMC.fr", "2025-06-10")
    _assert_channel_title(result, "RMC Show")


def test_tv5_returns_programs():
    provider = _make_provider("tv5", "TV5", {"TV5.fr": "tv5key"}, priority=0.6)
    payload = {
        "data": [
            {
                "utcstart": "2025-06-10T20:00:00",
                "utcend": "2025-06-10T21:00:00",
                "title": "TV5 Show",
                "description": "Desc",
                "category": "Doc",
            }
        ]
    }
    with patch.object(provider, "_get_content_from_url", return_value=json.dumps(payload)):
        result = provider.construct_epg("TV5.fr", "2025-06-10")
    _assert_channel_title(result, "TV5 Show")


def test_sixplay_returns_programs():
    provider = _make_provider("sixplay", "SixPlay", {"M6.fr": "m6"}, priority=0.2)
    payload = {
        "m6": [
            {
                "real_diffusion_start_date": "2025-06-10T20:00:00+00:00",
                "real_diffusion_end_date": "2025-06-10T21:00:00+00:00",
                "title": "SixPlay Show",
                "description": "Desc",
                "images": [{"role": "vignette", "id": "abc"}],
                "csa": {"age": 10},
            }
        ]
    }
    with patch.object(provider, "_get_content_from_url", return_value=json.dumps(payload)):
        result = provider.construct_epg("M6.fr", "2025-06-10")
    _assert_channel_title(result, "SixPlay Show")


def test_iciradiocanadatele_returns_programs():
    provider = _make_provider("iciradiocanadatele", "ICIRadioCanadaTele", {"ICI.ca": "100"}, priority=0.65)
    payload = {
        "data": {
            "broadcasts": [
                {
                    "startsAt": "2025-06-10T20:00:00Z",
                    "title": "ICI Show",
                    "subtheme": "News",
                    "descriptionHtml": "<p>Desc</p>",
                    "image": {"url": "https://img/{0}/{1}"},
                },
                {"startsAt": "2025-06-10T21:00:00Z", "title": "Next Show", "subtheme": "News"},
            ]
        }
    }
    with patch.object(
        provider, "_get_content_from_url", side_effect=[json.dumps({"data": {"broadcasts": []}}), json.dumps(payload)]
    ):
        result = provider.construct_epg("ICI.ca", "2025-06-10")
    _assert_channel_title(result, "ICI Show")


def test_voo_returns_programs():
    provider = _make_provider("voo", "Voo", {"VOO.fr": "42"}, priority=0.6)
    payload = {
        "Events": {
            "Event": [
                {
                    "AvailabilityStart": "2025-06-10T20:00:00Z",
                    "AvailabilityEnd": "2025-06-10T21:00:00Z",
                    "Titles": {
                        "Title": [
                            {
                                "Name": "Voo Show",
                                "LongSynopsis": "Desc",
                                "Genres": {"Genre": [{"Value": "Film"}]},
                                "Pictures": {"Picture": [{"Value": "https://img/voo.jpg"}]},
                            }
                        ]
                    },
                }
            ]
        }
    }
    provider._client.post = lambda *args, **kwargs: _FakeResponse(json.dumps(payload))  # type: ignore[method-assign]
    result = provider.construct_epg("VOO.fr", "2025-06-10")
    _assert_channel_title(result, "Voo Show")


def test_lequipelive_returns_programs():
    today = datetime.now().strftime("%Y-%m-%d")
    provider = _make_provider("lequipelive", "LEquipeLive", {"LEquipe.fr": "CHAINE1"}, priority=0.1)
    html = (
        'alt="À suivre en direct"'
        'class="CarouselWidget__item"<h2 class="ColeaderWidget__title">CHAINE1</h2>'
        '<div class="ArticleTags__item">LEquipe Show</div><p class="ColeaderWidget__subtitle">Sub</p>'
        '<span class="ColeaderLabels__text">20h00</span><img src="https://img/lequipe.jpg"/>'
        'class="CarouselWidget__item"<h2 class="ColeaderWidget__title">CHAINE1</h2>'
        '<div class="ArticleTags__item">Second</div><p class="ColeaderWidget__subtitle">Sub2</p>'
        '<span class="ColeaderLabels__text">22h00</span><img src="https://img/lequipe2.jpg"/>'
        'class="CarouselWidget__headerTitle"'
    )
    with patch.object(provider, "_get_content_from_url", return_value=html):
        result = provider.construct_epg("LEquipe.fr", today)
    _assert_channel_title(result, "LEquipe Show")


def test_nouvelobs_returns_programs():
    provider = _make_provider("nouvelobs", "NouvelObs", {"TF1.fr": "tf1"}, priority=0.46)
    html = (
        '<table cellspacing="0" cellpadding="0" class="tab_grille"></table>'
        '<table cellspacing="0" cellpadding="0" class="tab_grille"></table>'
        '<table cellspacing="0" cellpadding="0" class="tab_grille">'
        '<td class="logo_chaine">20h00</td><div class="b_d prog1">Cat</div><div class="b_d prog1">Desc</div>'
        '<br/>(60)</div></td><span class="titre b">NouvelObs Show</span>class="prog" />Film<br/>'
        'line4">3< src="https://img/nobs.jpg"/>'
        "</table>"
    )
    with patch.object(provider, "_get_content_from_url", return_value=html):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "NouvelObs Show")


def test_tebeosud_returns_programs():
    provider = _make_provider("tebeosud", "Tebeosud", {"Tebeo.fr": "x"}, priority=0.2)
    html = (
        "<p class='hour-program'>20:00</p><p class='hour-program'>21:00</p>"
        "<span class='video-card-date'>Tebeo Show</span><span class='video-card-date'>Second</span>"
        "<div class='program-card-content'> <img src='https://img/t1.jpg'></div>"
        "<div class='program-card-content'> <img src='https://img/t2.jpg'></div>"
    )
    with patch.object(provider, "_get_content_from_url", return_value=html):
        result = provider.construct_epg("Tebeo.fr", "2025-06-10")
    _assert_channel_title(result, "Tebeo Show")


def test_teleboy_returns_programs():
    provider = _make_provider("teleboy", "Teleboy", {"TF1.fr": "111"}, priority=0.4)
    payload = {
        "data": {
            "items": [
                {
                    "begin": "2025-06-10T20:00:00Z",
                    "end": "2025-06-10T21:00:00Z",
                    "title": "Teleboy Show",
                    "short_description": "Desc",
                    "genre": {"name_fr": "Film"},
                    "primary_image": {"base_path": "https://img/", "hash": "abc"},
                }
            ]
        }
    }
    with (
        patch.object(provider, "get_api_key", return_value="key"),
        patch.object(provider, "_get_content_from_url", return_value=json.dumps(payload)),
    ):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "Teleboy Show")


def test_proximus_returns_programs():
    provider = _make_provider("proximus", "Proximus", {"TF1.fr": "222"}, priority=0.59)
    payload = [
        {
            "programScheduleStart": "2025-06-10T20:00:00Z",
            "programScheduleEnd": "2025-06-10T21:00:00Z",
            "category": "C.Film",
            "subCategory": "C.Action",
            "program": {"title": "Proximus Show", "description": "Desc", "posterFileName": "poster.jpg", "VCHIP": "12"},
        }
    ]
    with (
        patch.object(provider, "get_version", return_value="v1"),
        patch.object(provider, "_get_content_from_url", return_value=json.dumps(payload)),
    ):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "Proximus Show")


def test_sudinfo_returns_programs():
    today = datetime.now(_PARIS).strftime("%Y-%m-%d")
    provider = _make_provider(
        "sudinfo",
        "SudInfo",
        {"TF1.fr": {"name": "TF1", "id": "1"}},
        priority=0.5,
        extra_params={"sudinfo_enable_details": False},
    )
    payload = {
        "pageProps": {
            "content": [
                {
                    "airingStartDateTime": f"{today}T20:00:00+00:00",
                    "airingEndDateTime": f"{today}T21:00:00+00:00",
                    "title": "SudInfo Show",
                    "subTitle": "Sub",
                    "contentSubCategory": {"name": "Film"},
                    "images": [{"url": "/square/img.jpg"}],
                    "slug": "/programme/test/item",
                }
            ]
        }
    }
    with (
        patch.object(provider, "get_build_id", return_value="build1"),
        patch.object(provider, "_get_content_from_url", return_value=json.dumps(payload)),
    ):
        result = provider.construct_epg("TF1.fr", today)
    _assert_channel_title(result, "SudInfo Show")


def test_tele2semaines_returns_programs():
    today = datetime.now().strftime("%Y-%m-%d")
    provider = _make_provider(
        "tele2semaines",
        "Tele2Semaines",
        {"TF1.fr": "tf1"},
        priority=0.6,
        extra_params={"tele2semaines_enable_details": False},
    )
    main = (
        'class="broadcastCard"'
        '<div class="broadcastCard-start" datetime="2025-06-10T20:00:00+00:00"></div>'
        '<a href="https://detail"></a><p class="broadcastCard-format">Film</p>'
        '<h2 class="broadcastCard-title">Tele2 Show</h2><p class="broadcastCard-synopsis">Desc</p>'
        'srcset="https://img/tele2.jpg 1x"'
    )
    day_after = 'class="broadcastCard-start" datetime="2025-06-11T00:00:00+00:00"'
    with patch.object(provider, "_get_content_from_url", side_effect=[main, day_after]):
        with patch.object(type(provider), "_get_day_label", staticmethod(lambda d: "")):
            result = provider.construct_epg("TF1.fr", today)
    _assert_channel_title(result, "Tele2 Show")


def test_teleloisirs_returns_programs():
    today = datetime.now().strftime("%Y-%m-%d")
    provider = _make_provider("teleloisirs", "TeleLoisirs", {"TF1.fr": "tf1"}, priority=0.6)
    main = (
        '<div class="mainBroadcastCard reverse" href="/detail" title="TeleLoisirs Show">'
        'srcset="https://img/64x90.jpg 1x"'
        '<div class="mainBroadcastCard-genre">Film</div>'
        '<p class="mainBroadcastCard-format">Action</p>'
        '<p class="mainBroadcastCard-subtitle">Sub</p>'
        '<p class="mainBroadcastCard-startingHour">20h00</p>'
        '<span class="mainBroadcastCard-durationContent">90min</span>'
        "</div>"
    )
    detail = '<script type="application/ld+json">{"description":"Desc","actor":[{"name":"Actor"}]}</script>'
    with patch.object(provider, "_get_content_from_url", side_effect=[main, detail]):
        result = provider.construct_epg("TF1.fr", today)
    _assert_channel_title(result, "TeleLoisirs Show")


def test_tv5global_returns_programs():
    provider = _make_provider(
        "tv5global",
        "TV5Global",
        {"TV5MONDE.fr": "europe"},
        priority=0.6,
        extra_params={"tv5global_enable_details": False},
    )
    content = (
        "jour-2025-06-09"
        'datetime="2025-06-10T20:00:00+00:00" field-categorie field-content">Film</div>'
        'field-title field-content">TV5Global Show</span> data-src="/img.jpg" href="/detail"'
        "jour-2025-06-10"
        'datetime="2025-06-10T21:00:00+00:00"'
        "jour-2025-06-11"
    )
    with patch.object(provider, "_get_content_from_url", return_value=content):
        result = provider.construct_epg("TV5MONDE.fr", "2025-06-10")
    _assert_channel_title(result, "TV5Global Show")


def test_linternaute_returns_programs():
    provider = _make_provider(
        "linternaute",
        "LInternaute",
        {"TF1.fr": "tf1"},
        priority=0.45,
        extra_params={"linternaute_enable_details": False},
    )
    content = (
        'class="bu_tvprogram_grid__line grid_row"'
        '<div class="grid_col bu_tvprogram_logo"><div>20h00</div><div>21h00</div></div>'
        '<span class="bu_tvprogram_typo2">Linternaute Show</span>'
        '<span class="bu_tvprogram_typo4">X - Film</span>'
        '<span class="bu_tvprogram_typo5">Desc</span>'
        'src="https://img/linternaute.jpg"'
    )
    with patch.object(provider, "_get_content_from_url", return_value=content):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "Linternaute Show")


def test_cogeco_returns_programs():
    today = datetime.now(_TORONTO).strftime("%Y-%m-%d")
    provider = _make_provider("cogeco", "Cogeco", {"TVA.ca": "100"}, priority=0.61)
    grid_html = (
        "<!-- channel row -->"
        '<span class="hidden-phone tvm_txt_chan_name">100</span><span class="tvm_txt_chan_num">100</span>'
        'class="tvm_td_grd_m" onclick="prgm_details(1, 2)"'
        'class="tvm_td_grd_m" onclick="prgm_details(3, 4)"'
    )
    first_detail = (
        'txt_showtitle bold">Early Show</h3>'
        'txt_showname bold">Sub</p>'
        'tvm_td_detailsbot">Info</span>'
        'tvm_td_detailsbot">11h00</span>'
        'tvm_td_detailsbot">(60 min)</span>'
        'details_tvm_td_detailsbot">Desc</p>'
        "img id='show_graphic' src=\"//img/240x135.jpg\""
    )
    second_detail = (
        'txt_showtitle bold">Cogeco Show</h3>'
        'txt_showname bold">Sub</p>'
        'tvm_td_detailsbot">Info</span>'
        'tvm_td_detailsbot">10h00</span>'
        'tvm_td_detailsbot">(60 min)</span>'
        'details_tvm_td_detailsbot">Desc</p>'
        "img id='show_graphic' src=\"//img/240x135.jpg\""
    )
    with (
        patch.object(provider, "_get_epg_data", return_value=grid_html),
        patch.object(
            provider,
            "_get_content_from_url",
            side_effect=[first_detail, second_detail],
        ),
    ):
        result = provider.construct_epg("TVA.ca", today)
    _assert_channel_title(result, "Cogeco Show")


def test_mycanal_returns_programs():
    provider = _make_provider(
        "mycanal",
        "MyCanal",
        {"Canal.fr": {"id": "1", "region": "fr"}},
        priority=0.7,
        extra_params={"mycanal_enable_details": False},
    )
    payload = {
        "timeSlices": [
            {
                "contents": [
                    {
                        "startTime": int(datetime(2025, 6, 10, 20, 0).timestamp() * 1000),
                        "title": "MyCanal Show",
                        "subtitle": "Sub",
                        "onClick": {"URLPage": "https://detail"},
                    },
                    {
                        "startTime": int(datetime(2025, 6, 11, 1, 0).timestamp() * 1000),
                        "title": "Too Late",
                        "onClick": {"URLPage": "https://detail2"},
                    },
                ]
            }
        ]
    }
    with (
        patch.object(provider, "get_api_key", return_value="token"),
        patch.object(provider, "_get_content_from_url", return_value=json.dumps(payload)),
    ):
        result = provider.construct_epg("Canal.fr", "2025-06-10")
    _assert_channel_title(result, "MyCanal Show")


def test_virginplus_returns_programs():
    patcher = patch("xmltvfr.providers.virginplus.VirginPlus._gather_epg_information", lambda self: None)
    provider = _make_provider(
        "virginplus",
        "VirginPlus",
        {"CTV.ca": "CTV"},
        priority=0.66,
        extra_params={"virginplus_disable_details": True},
        extra_patchers=[patcher],
    )
    provider._is_configured = True
    provider._epg_from_date = datetime(2025, 6, 9, tzinfo=_TORONTO)
    provider._epg_to_date = datetime(2025, 6, 12, tzinfo=_TORONTO)
    provider._block_duration = 8
    provider._epg_info = [{"callSign": "CTV", "schedulesBlockVersions": [1]}]
    payload = [
        {
            "startTime": "2025-06-10T20:00:00Z",
            "endTime": "2025-06-10T21:00:00Z",
            "title": "VirginPlus Show",
            "showType": "movie",
            "programSupplierId": {"supplier": "sup", "supplierId": "id"},
            "rating": "CA-13",
            "language": "fr",
        }
    ]
    with (
        patch.object(
            provider,
            "_get_blocks_information",
            return_value=[{"fromDate": datetime(2025, 6, 10), "toDate": datetime(2025, 6, 11), "blockVersion": 1}],
        ),
        patch.object(provider, "_get_content_from_url", return_value=json.dumps(payload)),
    ):
        result = provider.construct_epg("CTV.ca", "2025-06-10")
    _assert_channel_title(result, "VirginPlus Show")


def test_tvhebdo_returns_programs():
    provider = _make_provider(
        "tvhebdo",
        "TVHebdo",
        {"TVA.ca": "tva"},
        priority=0.2,
        extra_params={"tvhebdo_enable_details": False},
    )
    data = [
        {
            "startDate": datetime(2025, 6, 10, 20, 0, tzinfo=ZoneInfo("America/Montreal")),
            "title": "TVHebdo Show",
            "url": "https://detail",
        },
        {
            "startDate": datetime(2025, 6, 10, 21, 0, tzinfo=ZoneInfo("America/Montreal")),
            "title": "Next",
            "url": "https://detail2",
        },
    ]
    with patch.object(provider, "get_data_per_day", side_effect=[[], data]):
        result = provider.construct_epg("TVA.ca", "2025-06-10")
    _assert_channel_title(result, "TVHebdo Show")


def test_telecablesat_returns_programs():
    provider = _make_provider(
        "telecablesat",
        "Telecablesat",
        {"TF1.fr": {"id": "tf1", "page": "1"}},
        priority=0.55,
        extra_params={"telecablesat_enable_details": False},
    )
    content = (
        'logos_chaines/tf1.png" title="TF1"'
        '<div class="row">'
        'data-start="1749585600" data-end="1749589200" '
        'data-src="//img/telecable.jpg" '
        '<div class="hour-type"></span>Film</div><span class="title">Telecable Show</span>'
        'class="link" href="/detail" data-diffusion="123"'
    )
    with patch.object(provider, "_get_content", side_effect=["", content]):
        result = provider.construct_epg("TF1.fr", "2025-06-10")
    _assert_channel_title(result, "Telecable Show")
