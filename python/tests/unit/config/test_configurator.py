"""Tests for Configurator."""

from __future__ import annotations

import json
import os

import pytest


def test_configurator_defaults():
    from xmltvfr.config.configurator import Configurator

    cfg = Configurator()
    assert cfg.nb_days == 8
    assert cfg.output_path == "./var/export/"
    assert cfg.cache_max_days == 8
    assert not cfg.delete_raw_xml
    assert cfg.enable_gz
    assert cfg.enable_zip
    assert not cfg.enable_xz
    assert not cfg.enable_dummy
    assert cfg.nb_threads == 1
    assert cfg.min_time_range == 22 * 3600


def test_configurator_custom_values():
    from xmltvfr.config.configurator import Configurator

    cfg = Configurator(nb_days=3, output_path="/tmp/out/", nb_threads=4)
    assert cfg.nb_days == 3
    assert cfg.output_path == "/tmp/out/"
    assert cfg.nb_threads == 4


def test_configurator_get_default_client():
    import requests

    from xmltvfr.config.configurator import Configurator

    client = Configurator.get_default_client()
    assert isinstance(client, requests.Session)
    assert "Mozilla" in client.headers.get("User-Agent", "")


def test_init_from_config_file(tmp_path):
    from xmltvfr.config.configurator import Configurator

    config = {
        "days": 5,
        "output_path": "/tmp/xmltv/",
        "nb_threads": 2,
        "enable_gz": False,
        "enable_zip": False,
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")

    cfg = Configurator.init_from_config_file(str(config_file))
    assert cfg.nb_days == 5
    assert cfg.output_path == "/tmp/xmltv/"
    assert cfg.nb_threads == 2
    assert not cfg.enable_gz
    assert not cfg.enable_zip


def test_init_from_config_file_not_found():
    from xmltvfr.config.configurator import Configurator

    with pytest.raises(FileNotFoundError):
        Configurator.init_from_config_file("/nonexistent/path/config.json")


def test_configurator_get_ui_default():
    from xmltvfr.config.configurator import Configurator
    from xmltvfr.ui.multi_column_ui import MultiColumnUI

    cfg = Configurator()
    assert isinstance(cfg.get_ui(), MultiColumnUI)


def test_configurator_get_ui_progressive():
    from xmltvfr.config.configurator import Configurator
    from xmltvfr.ui.progressive_ui import ProgressiveUI

    cfg = Configurator(ui=ProgressiveUI())
    assert isinstance(cfg.get_ui(), ProgressiveUI)


def test_configurator_get_generator(tmp_path):
    """get_generator() should return a MultiThreadedGenerator."""
    from xmltvfr.config.configurator import Configurator
    from xmltvfr.core.multi_threaded_generator import MultiThreadedGenerator

    # Point cache dir into tmp_path so no var/cache directory is created
    os.chdir(tmp_path)
    cfg = Configurator(
        nb_days=1,
        guides_to_generate=[{"channels": {}, "filename": "xmltv.xml"}],
    )
    gen = cfg.get_generator()
    assert isinstance(gen, MultiThreadedGenerator)
