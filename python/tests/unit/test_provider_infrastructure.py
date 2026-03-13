"""Tests for provider infrastructure: ProviderCache, CacheFile, AbstractProvider."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import requests


def test_provider_cache_set_get_content(tmp_path, monkeypatch):
    from xmltvfr.providers.provider_cache import ProviderCache

    monkeypatch.setattr(ProviderCache, "_PATH", str(tmp_path) + "/")
    pc = ProviderCache("test.json")
    assert pc.get_content() is None
    pc.set_content("hello")
    assert pc.get_content() == "hello"


def test_provider_cache_get_array(tmp_path, monkeypatch):
    from xmltvfr.providers.provider_cache import ProviderCache

    monkeypatch.setattr(ProviderCache, "_PATH", str(tmp_path) + "/")
    pc = ProviderCache("test.json")
    assert pc.get_array() == {}
    pc.set_content('{"a": 1}')
    assert pc.get_array() == {"a": 1}


def test_provider_cache_set_array_key(tmp_path, monkeypatch):
    from xmltvfr.providers.provider_cache import ProviderCache

    monkeypatch.setattr(ProviderCache, "_PATH", str(tmp_path) + "/")
    pc = ProviderCache("test.json")
    pc.set_array_key("key1", "val1")
    assert pc.get_array() == {"key1": "val1"}


def test_cache_file_store_and_get(tmp_path):
    from xmltvfr.providers.cache_file import CacheFile

    config = MagicMock(force_today_grab=False, min_time_range=22 * 3600)
    cache = CacheFile(str(tmp_path / "cache"), config)
    cache.store("test_key.xml", "<content/>")
    assert cache.get("test_key.xml") == "<content/>"


def test_cache_file_get_state_no_cache(tmp_path):
    from xmltvfr.domain.models.epg_enum import EPGEnum
    from xmltvfr.providers.cache_file import CacheFile

    config = MagicMock(force_today_grab=False, min_time_range=22 * 3600)
    cache = CacheFile(str(tmp_path / "cache"), config)
    assert cache.get_state("missing.xml") == EPGEnum.NO_CACHE


def test_cache_file_clear(tmp_path):
    from xmltvfr.domain.models.epg_enum import EPGEnum
    from xmltvfr.providers.cache_file import CacheFile

    config = MagicMock(force_today_grab=False, min_time_range=22 * 3600)
    cache = CacheFile(str(tmp_path / "cache"), config)
    cache.store("test.xml", "<x/>")
    cache.clear("test.xml")
    assert cache.get_state("test.xml") == EPGEnum.NO_CACHE


def test_abstract_provider_channel_exists(tmp_path):
    from xmltvfr.providers.abstract_provider import AbstractProvider

    channels = {"TF1.fr": {"id": "1"}}
    json_path = tmp_path / "channels.json"
    json_path.write_text(json.dumps(channels))

    class ConcreteProvider(AbstractProvider):
        pass

    session = requests.Session()
    provider = ConcreteProvider(session, str(json_path), 0.9)
    assert provider.channel_exists("TF1.fr")
    assert not provider.channel_exists("Unknown.fr")


def test_abstract_provider_get_priority(tmp_path):
    from xmltvfr.providers.abstract_provider import AbstractProvider

    class ProviderA(AbstractProvider):
        pass

    session = requests.Session()
    ProviderA(session, "", 0.75)
    assert ProviderA.get_priority() == pytest.approx(0.75)


def test_abstract_provider_get_min_max_date():
    from datetime import timedelta

    from xmltvfr.providers.abstract_provider import AbstractProvider

    class ConcreteProvider(AbstractProvider):
        pass

    min_date, max_date = ConcreteProvider.get_min_max_date("2025-01-01")
    assert (max_date - min_date) == timedelta(hours=23, minutes=59, seconds=59)
