"""Unit tests for ResourcePath."""

from __future__ import annotations

from pathlib import Path

from xmltvfr.utils.resource_path import ResourcePath


def _fresh_instance() -> ResourcePath:
    """Return a fresh (non-singleton) ResourcePath for isolated testing."""
    ResourcePath._instance = None
    return ResourcePath.get_instance()


def test_get_channel_path():
    rp = _fresh_instance()
    result = rp.get_channel_path("TF1.json")
    assert isinstance(result, Path)
    assert result.name == "TF1.json"
    assert result.parent.name == "channel_config"
    assert result.parent.parent.name == "resources"


def test_get_channel_info_path():
    rp = _fresh_instance()
    result = rp.get_channel_info_path()
    assert isinstance(result, Path)
    assert result.name == "default_channels_infos.json"
    assert result.parent.name == "information"


def test_get_rating_picto_path():
    rp = _fresh_instance()
    result = rp.get_rating_picto_path()
    assert isinstance(result, Path)
    assert result.name == "ratings_picto.json"
    assert result.parent.name == "information"


def test_singleton():
    ResourcePath._instance = None
    instance_a = ResourcePath.get_instance()
    instance_b = ResourcePath.get_instance()
    assert instance_a is instance_b
