"""Unit tests for Program value object."""

from datetime import UTC, datetime

import pytest

from xmltvfr.domain.models.program import Program


def test_program_with_timestamp():
    """Program.with_timestamp creates a valid Program."""
    start_ts = 1_700_000_000
    end_ts = 1_700_007_200
    prog = Program.with_timestamp(start_ts, end_ts)
    assert isinstance(prog, Program)


def test_program_start_before_end_raises():
    """Program raises ValueError if start >= end."""
    start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    end = datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC)
    with pytest.raises(ValueError):
        Program(start=start, end=end)


def test_program_add_title():
    prog = Program.with_timestamp(1_700_000_000, 1_700_007_200)
    prog.add_title("My Show")
    titles = prog.get_children("title")
    assert len(titles) == 1
    assert titles[0].value == "My Show"


def test_program_add_category():
    prog = Program.with_timestamp(1_700_000_000, 1_700_007_200)
    prog.add_category("Drama")
    cats = prog.get_children("category")
    assert len(cats) == 1
    assert cats[0].value == "Drama"


def test_program_set_rating():
    prog = Program.with_timestamp(1_700_000_000, 1_700_007_200)
    prog.set_rating("Tous publics")
    ratings = prog.get_children("rating")
    assert len(ratings) == 1


def test_program_set_episode_num():
    prog = Program.with_timestamp(1_700_000_000, 1_700_007_200)
    prog.set_episode_num(season=2, episode=5)
    eps = prog.get_children("episode-num")
    assert len(eps) == 1
    # season 2 → index 1, episode 5 → index 4
    assert eps[0].value == "1.4."


def test_program_set_episode_num_zero():
    """set_episode_num with both None/0 does nothing."""
    prog = Program.with_timestamp(1_700_000_000, 1_700_007_200)
    prog.set_episode_num(season=0, episode=0)
    eps = prog.get_children("episode-num")
    assert len(eps) == 0


def test_program_add_credit():
    prog = Program.with_timestamp(1_700_000_000, 1_700_007_200)
    prog.add_credit("John Doe", "director")
    credits_list = prog.get_children("credits")
    assert len(credits_list) == 1
    directors = credits_list[0].get_children("director")
    assert len(directors) == 1
    assert directors[0].value == "John Doe"


def test_program_as_xml_structure():
    prog = Program.with_timestamp(1_700_000_000, 1_700_007_200)
    prog.add_title("Test Show")
    xml = prog.as_xml()
    assert "<programme " in xml
    assert 'start="' in xml
    assert 'stop="' in xml
    assert "<title" in xml
    assert "Test Show" in xml
    assert "</programme>" in xml
