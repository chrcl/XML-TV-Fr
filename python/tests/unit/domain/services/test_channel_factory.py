"""Tests for ChannelFactory domain service."""

from __future__ import annotations

from unittest.mock import patch

from xmltvfr.domain.models.channel import Channel
from xmltvfr.domain.services.channel_factory import ChannelFactory


def test_create_channel_returns_channel():
    """ChannelFactory.create_channel should return a Channel with the given key."""
    with (
        patch("xmltvfr.domain.static.channel_information.ChannelInformation.get_default_icon", return_value="http://icon.png"),
        patch("xmltvfr.domain.static.channel_information.ChannelInformation.get_default_name", return_value="TF1"),
    ):
        ch = ChannelFactory.create_channel("TF1.fr")

    assert isinstance(ch, Channel)
    assert ch.id == "TF1.fr"


def test_create_channel_uses_channel_information():
    """ChannelFactory should populate icon and name from ChannelInformation."""
    with (
        patch("xmltvfr.domain.static.channel_information.ChannelInformation.get_default_icon", return_value="http://icon.png"),
        patch("xmltvfr.domain.static.channel_information.ChannelInformation.get_default_name", return_value="TF1"),
    ):
        ch = ChannelFactory.create_channel("TF1.fr")

    assert ch.icon == "http://icon.png"
    assert ch.name == "TF1"


def test_create_channel_unknown_key_has_none_icon_and_name():
    """Unknown channel key should produce None icon and name (not raise)."""
    with (
        patch("xmltvfr.domain.static.channel_information.ChannelInformation.get_default_icon", return_value=None),
        patch("xmltvfr.domain.static.channel_information.ChannelInformation.get_default_name", return_value=None),
    ):
        ch = ChannelFactory.create_channel("Unknown.fr")

    assert ch.icon is None
    assert ch.name is None


def test_channel_factory_cannot_be_instantiated():
    """ChannelFactory is a static class — direct instantiation must raise."""
    import pytest

    with pytest.raises(TypeError):
        ChannelFactory()
