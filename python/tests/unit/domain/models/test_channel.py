"""Unit tests for Channel value object."""

from unittest.mock import MagicMock

from xmltvfr.domain.models.channel import Channel


def _make_program(start: int, end: int):
    prog = MagicMock()
    prog.get_start.return_value = MagicMock()
    prog.get_start.return_value.timestamp.return_value = float(start)
    prog.get_end.return_value = MagicMock()
    prog.get_end.return_value.timestamp.return_value = float(end)
    return prog


def test_channel_creation():
    ch = Channel(id="TF1", icon="http://icon.png", name="TF1")
    assert ch.id == "TF1"
    assert ch.icon == "http://icon.png"
    assert ch.name == "TF1"
    assert ch.programs == []


def test_add_program():
    ch = Channel(id="TF1", icon=None, name=None)
    prog = _make_program(1000, 2000)
    ch.add_program(prog)
    assert ch.get_program_count() == 1


def test_order_program():
    ch = Channel(id="TF1", icon=None, name=None)
    prog1 = _make_program(2000, 3000)
    prog2 = _make_program(1000, 2000)
    ch.add_program(prog1)
    ch.add_program(prog2)
    ch.order_program()
    times = ch.get_start_times()
    assert times == sorted(times)


def test_get_program_count():
    ch = Channel(id="TF1", icon=None, name=None)
    assert ch.get_program_count() == 0
    ch.add_program(_make_program(1000, 2000))
    assert ch.get_program_count() == 1


def test_pop_last_program():
    ch = Channel(id="TF1", icon=None, name=None)
    prog = _make_program(1000, 2000)
    ch.add_program(prog)
    popped = ch.pop_last_program()
    assert popped is prog
    assert ch.get_program_count() == 0


def test_get_start_end_times():
    ch = Channel(id="TF1", icon=None, name=None)
    ch.add_program(_make_program(1000, 2000))
    ch.add_program(_make_program(2000, 3000))
    assert ch.get_start_times() == [1000, 2000]
    assert ch.get_end_times() == [2000, 3000]
