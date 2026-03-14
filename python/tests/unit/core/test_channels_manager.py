"""Tests for ChannelsManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_generator(providers=None):
    """Build a minimal mock Generator."""
    gen = MagicMock()
    gen.get_providers.return_value = providers or []
    gen.configurator.extra_params = {}
    return gen


def test_channels_manager_initial_state():
    from xmltvfr.core.channels_manager import ChannelsManager

    channels = {"TF1.fr": {}, "M6.fr": {}}
    gen = _make_generator()
    manager = ChannelsManager(channels, gen)

    assert manager.has_remaining_channels()
    assert manager.get_status() == "0 / 2"


def test_incr_channels_done():
    from xmltvfr.core.channels_manager import ChannelsManager

    channels = {"TF1.fr": {}}
    gen = _make_generator()
    manager = ChannelsManager(channels, gen)
    manager.incr_channels_done()
    assert manager.get_status() == "1 / 1"


def test_add_and_get_events():
    from xmltvfr.core.channels_manager import ChannelsManager

    channels = {}
    gen = _make_generator()
    manager = ChannelsManager(channels, gen)
    manager.add_event("event 1")
    manager.add_event("event 2")
    manager.add_event("event 3")

    assert manager.get_latest_events(2) == ["event 2", "event 3"]
    assert manager.get_latest_events(10) == ["event 1", "event 2", "event 3"]


def test_can_use_provider_initially():
    from xmltvfr.core.channels_manager import ChannelsManager

    gen = _make_generator()
    manager = ChannelsManager({}, gen)
    assert manager.can_use_provider("Orange")


def test_add_channel_to_provider_blocks_it():
    from xmltvfr.core.channels_manager import ChannelsManager

    gen = _make_generator()
    manager = ChannelsManager({}, gen)
    manager.add_channel_to_provider("Orange", "TF1.fr")
    assert not manager.can_use_provider("Orange")


def test_remove_channel_from_provider_frees_it():
    from xmltvfr.core.channels_manager import ChannelsManager

    gen = _make_generator()
    manager = ChannelsManager({}, gen)
    manager.add_channel_to_provider("Orange", "TF1.fr")
    manager.remove_channel_from_provider("Orange", "TF1.fr")
    assert manager.can_use_provider("Orange")


def test_shift_channel_returns_first_available():
    from xmltvfr.core.channels_manager import ChannelsManager

    channels = {"TF1.fr": {}, "M6.fr": {}}
    # Providers: no channel exists in any provider => always available
    gen = _make_generator()
    manager = ChannelsManager(channels, gen)

    data = manager.shift_channel()
    assert data["key"] in ("TF1.fr", "M6.fr")
    assert manager.get_status() == "0 / 2"  # not yet done


def test_shift_channel_empty_when_no_channels():
    from xmltvfr.core.channels_manager import ChannelsManager

    gen = _make_generator()
    manager = ChannelsManager({}, gen)
    assert manager.shift_channel() == {}


def test_has_remaining_channels_false_after_all_shifted():
    from xmltvfr.core.channels_manager import ChannelsManager

    channels = {"TF1.fr": {}}
    gen = _make_generator()
    manager = ChannelsManager(channels, gen)
    manager.shift_channel()
    assert not manager.has_remaining_channels()
