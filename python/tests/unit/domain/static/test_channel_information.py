"""Unit tests for the ChannelInformation singleton.

The default_channels_infos.json resource contains entries such as:
  {"01TV.fr": {"name": "TECH & CO", "icon": "<url>"}, ...}
"""

from __future__ import annotations

from xmltvfr.domain.static.channel_information import ChannelInformation

# A real key that is present in default_channels_infos.json
_KNOWN_KEY = "01TV.fr"


def _reset_singleton() -> None:
    """Reset the singleton so each test starts from a clean slate."""
    ChannelInformation._instance = None


# ---------------------------------------------------------------------------
# get_channel_info
# ---------------------------------------------------------------------------


def test_get_channel_info_returns_dict():
    _reset_singleton()
    instance = ChannelInformation.get_instance()
    result = instance.get_channel_info()
    assert isinstance(result, dict)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# get_default_icon
# ---------------------------------------------------------------------------


def test_get_default_icon_known():
    _reset_singleton()
    instance = ChannelInformation.get_instance()
    icon = instance.get_default_icon(_KNOWN_KEY)
    assert isinstance(icon, str)
    assert len(icon) > 0


def test_get_default_icon_unknown():
    _reset_singleton()
    instance = ChannelInformation.get_instance()
    assert instance.get_default_icon("UnknownChannel.xyz") is None


# ---------------------------------------------------------------------------
# get_default_name
# ---------------------------------------------------------------------------


def test_get_default_name_known():
    _reset_singleton()
    instance = ChannelInformation.get_instance()
    name = instance.get_default_name(_KNOWN_KEY)
    assert isinstance(name, str)
    assert len(name) > 0


def test_get_default_name_unknown():
    _reset_singleton()
    instance = ChannelInformation.get_instance()
    assert instance.get_default_name("UnknownChannel.xyz") is None


# ---------------------------------------------------------------------------
# Singleton behaviour
# ---------------------------------------------------------------------------


def test_singleton():
    _reset_singleton()
    instance1 = ChannelInformation.get_instance()
    instance2 = ChannelInformation.get_instance()
    assert instance1 is instance2
