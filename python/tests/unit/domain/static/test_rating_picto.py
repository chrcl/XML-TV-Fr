"""Unit tests for the RatingPicto singleton.

The ratings_picto.json resource file has the following structure:
  {
    "csa":   {"-10": url, "-12": url, "-16": url, "-18": url},
    "fcc":   {"tv-y": url, ...},
    "rcq":   {"g": url, "13": url, "16": url, "18": url},
    "chvrs": {"g": url, "pg": url, "14a": url, "18a": url, "r": url, "a": url}
  }
"""

from __future__ import annotations

from xmltvfr.domain.static.rating_picto import RatingPicto


def _reset_singleton() -> None:
    """Reset the singleton so each test starts from a clean slate."""
    RatingPicto._instance = None


# ---------------------------------------------------------------------------
# get_picto_from_rating_system — None inputs
# ---------------------------------------------------------------------------


def test_get_picto_none_rating():
    _reset_singleton()
    instance = RatingPicto.get_instance()
    assert instance.get_picto_from_rating_system(None, "csa") is None


def test_get_picto_none_system():
    _reset_singleton()
    instance = RatingPicto.get_instance()
    assert instance.get_picto_from_rating_system("tp", None) is None


# ---------------------------------------------------------------------------
# get_picto_from_rating_system — unknown inputs
# ---------------------------------------------------------------------------


def test_get_picto_invalid_system():
    _reset_singleton()
    instance = RatingPicto.get_instance()
    assert instance.get_picto_from_rating_system("pg", "unknown_system") is None


def test_get_picto_invalid_rating():
    """An unknown rating in a valid system should return None."""
    _reset_singleton()
    instance = RatingPicto.get_instance()
    # "csa" is a real system; "invalid_rating" is not a valid CSA label
    assert instance.get_picto_from_rating_system("invalid_rating", "csa") is None


# ---------------------------------------------------------------------------
# get_picto_from_rating_system — valid lookup
# ---------------------------------------------------------------------------


def test_get_picto_valid_csa_rating():
    """A valid CSA rating should return a non-empty URL string."""
    _reset_singleton()
    instance = RatingPicto.get_instance()
    result = instance.get_picto_from_rating_system("-10", "csa")
    assert isinstance(result, str)
    assert result.startswith("http")


# ---------------------------------------------------------------------------
# Singleton behaviour
# ---------------------------------------------------------------------------


def test_singleton():
    _reset_singleton()
    instance1 = RatingPicto.get_instance()
    instance2 = RatingPicto.get_instance()
    assert instance1 is instance2
