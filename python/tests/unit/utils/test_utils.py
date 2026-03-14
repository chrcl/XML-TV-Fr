"""Unit tests for the utils module."""

from __future__ import annotations

import json

from xmltvfr.utils.terminal_icon import TerminalIcon
from xmltvfr.utils.utils import (
    colorize,
    get_canadian_rating_system,
    get_channels_from_guide,
    get_provider,
    get_providers,
    get_start_and_end_dates_from_xml_string,
    get_time_range_from_xml_string,
    has_one_thread_running,
    recurse_rmdir,
    replace_buggy_width_characters,
    slugify,
)

# ---------------------------------------------------------------------------
# colorize
# ---------------------------------------------------------------------------

_XML_SAMPLE = (
    '<programme start="20250101120000 +0100" stop="20250101130000 +0100">'
    "</programme>"
    '<programme start="20250101130000 +0100" stop="20250101140000 +0100">'
    "</programme>"
)


def test_colorize_with_color_name():
    result = colorize("hello", "red")
    assert "\033[31m" in result
    assert "hello" in result
    assert "\033[0m" in result


def test_colorize_with_numeric_color():
    result = colorize("world", 2)
    assert "\033[32m" in result
    assert "world" in result


def test_colorize_no_color_random():
    # Without a color the function should still wrap the content with ANSI codes
    result = colorize("random")
    assert "\033[0m" in result
    assert "random" in result


def test_colorize_all_named_colors():
    named = [
        "red",
        "green",
        "yellow",
        "blue",
        "magenta",
        "cyan",
        "light grey",
        "dark grey",
        "light red",
        "light cyan",
        "light yellow",
        "light blue",
        "light magenta",
        "light green",
    ]
    for name in named:
        result = colorize("x", name)
        assert "\033[" in result, f"No ANSI code for color '{name}'"


# ---------------------------------------------------------------------------
# XML timestamp helpers
# ---------------------------------------------------------------------------


def test_get_start_and_end_dates_from_xml():
    starts, ends = get_start_and_end_dates_from_xml_string(_XML_SAMPLE)
    assert len(starts) == 2
    assert len(ends) == 2
    # second start == first end
    assert starts[1] == ends[0]


def test_get_time_range_from_xml():
    # 2 hours of programming
    time_range = get_time_range_from_xml_string(_XML_SAMPLE)
    assert time_range == 2 * 3600


def test_get_time_range_from_xml_empty():
    assert get_time_range_from_xml_string("") == 0


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


def test_slugify():
    assert slugify("Hello World") == "hello-world"
    # Each contiguous block of non-alphanumeric chars becomes one dash
    assert slugify("TF1 & France 2") == "tf1-france-2"
    assert slugify("already-slug") == "already-slug"


# ---------------------------------------------------------------------------
# Canadian rating system
# ---------------------------------------------------------------------------


def test_get_canadian_rating_system():
    assert get_canadian_rating_system("PG") == "CHVRS"
    assert get_canadian_rating_system("14A") == "CHVRS"
    assert get_canadian_rating_system("18A") == "CHVRS"
    assert get_canadian_rating_system("R") == "CHVRS"
    assert get_canadian_rating_system("A") == "CHVRS"
    assert get_canadian_rating_system("G", lang="en") == "CHVRS"
    assert get_canadian_rating_system("G", lang="fr") == "RCQ"
    assert get_canadian_rating_system("13") == "RCQ"
    assert get_canadian_rating_system("16") == "RCQ"
    assert get_canadian_rating_system("18") == "RCQ"
    assert get_canadian_rating_system("X") is None


# ---------------------------------------------------------------------------
# recurse_rmdir
# ---------------------------------------------------------------------------


def test_recurse_rmdir(tmp_path):
    target = tmp_path / "subdir"
    target.mkdir()
    (target / "file.txt").write_text("data")
    assert recurse_rmdir(str(target)) is True
    assert not target.exists()


def test_recurse_rmdir_nonexistent(tmp_path):
    assert recurse_rmdir(str(tmp_path / "nope")) is False


# ---------------------------------------------------------------------------
# replace_buggy_width_characters
# ---------------------------------------------------------------------------


def test_replace_buggy_width_characters():
    success = TerminalIcon.success()
    error = TerminalIcon.error()
    pause = TerminalIcon.pause()
    test_str = f"prefix {success} middle {error} suffix {pause}"
    result = replace_buggy_width_characters(test_str)
    assert success not in result
    assert error not in result
    assert pause not in result
    # Each wide char is replaced with two spaces
    assert "  " in result


# ---------------------------------------------------------------------------
# get_channels_from_guide
# ---------------------------------------------------------------------------


def test_get_channels_from_guide_single_file(tmp_path):
    channels_file = tmp_path / "channels.json"
    channels_file.write_text(json.dumps({"TF1.fr": {"name": "TF1"}}))
    guide = {"channels": str(channels_file)}
    result = get_channels_from_guide(guide)
    assert result == {"TF1.fr": {"name": "TF1"}}


def test_get_channels_from_guide_list(tmp_path):
    file1 = tmp_path / "channels1.json"
    file2 = tmp_path / "channels2.json"
    file1.write_text(json.dumps({"TF1.fr": {"name": "TF1"}, "France2.fr": {"name": "France 2"}}))
    file2.write_text(json.dumps({"France3.fr": {"name": "France 3"}}))
    guide = {"channels": [str(file1), str(file2)]}
    result = get_channels_from_guide(guide)
    assert "TF1.fr" in result
    assert "France2.fr" in result
    assert "France3.fr" in result


# ---------------------------------------------------------------------------
# has_one_thread_running
# ---------------------------------------------------------------------------


def test_has_one_thread_running_true():
    class MockThread:
        def is_running(self) -> bool:
            return True

    assert has_one_thread_running([MockThread()]) is True


def test_has_one_thread_running_false():
    class MockThread:
        def is_running(self) -> bool:
            return False

    assert has_one_thread_running([MockThread()]) is False


# ---------------------------------------------------------------------------
# get_provider / get_providers
# ---------------------------------------------------------------------------


def test_get_provider_none():
    assert get_provider("NonExistent") is None


def test_get_providers_returns_list():
    result = get_providers()
    assert isinstance(result, list)
