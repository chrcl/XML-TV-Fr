"""Tests for XmlFormatter."""

from __future__ import annotations

from unittest.mock import MagicMock

from xmltvfr.domain.models.tag import Tag
from xmltvfr.export.xml_formatter import XmlFormatter


def _make_program(start_ts: int, end_ts: int):
    """Build a real Program so as_xml() works."""
    from xmltvfr.domain.models.program import Program

    prog = Program.with_timestamp(start_ts, end_ts)
    return prog


class _FakeProvider:
    pass


def test_format_channel_adds_comment_for_provider():
    from xmltvfr.domain.models.channel import Channel

    formatter = XmlFormatter()
    ch = Channel(id="TF1.fr", icon=None, name="TF1")
    prog = _make_program(1_700_000_000, 1_700_007_200)
    prog.add_title("Show")
    ch.add_program(prog)

    provider = _FakeProvider()
    result = formatter.format_channel(ch, provider)
    assert "<!-- " in result
    assert "_FakeProvider" in result


def test_format_channel_no_comment_without_provider():
    from xmltvfr.domain.models.channel import Channel

    formatter = XmlFormatter()
    ch = Channel(id="TF1.fr", icon=None, name="TF1")
    prog = _make_program(1_700_000_000, 1_700_007_200)
    prog.add_title("Show")
    ch.add_program(prog)

    result = formatter.format_channel(ch, None)
    assert "<!-- " not in result


def test_format_channel_sets_channel_attribute():
    from xmltvfr.domain.models.channel import Channel

    formatter = XmlFormatter()
    ch = Channel(id="TF1.fr", icon=None, name="TF1")
    prog = _make_program(1_700_000_000, 1_700_007_200)
    prog.add_title("Show")
    ch.add_program(prog)

    result = formatter.format_channel(ch, None)
    assert 'channel="TF1.fr"' in result


def test_format_channel_fills_missing_title():
    """Programs without a title should get the default 'Aucun titre'."""
    from xmltvfr.domain.models.channel import Channel

    formatter = XmlFormatter()
    ch = Channel(id="TF1.fr", icon=None, name="TF1")
    prog = _make_program(1_700_000_000, 1_700_007_200)
    # Do NOT add a title
    ch.add_program(prog)

    result = formatter.format_channel(ch, None)
    assert "Aucun titre" in result


def test_format_channel_does_not_override_existing_title():
    from xmltvfr.domain.models.channel import Channel

    formatter = XmlFormatter()
    ch = Channel(id="TF1.fr", icon=None, name="TF1")
    prog = _make_program(1_700_000_000, 1_700_007_200)
    prog.add_title("My Show")
    ch.add_program(prog)

    result = formatter.format_channel(ch, None)
    assert "My Show" in result
    assert "Aucun titre" not in result


def test_format_channel_empty_channel():
    from xmltvfr.domain.models.channel import Channel

    formatter = XmlFormatter()
    ch = Channel(id="TF1.fr", icon=None, name="TF1")
    result = formatter.format_channel(ch, None)
    assert result == ""
