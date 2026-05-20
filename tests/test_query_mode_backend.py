"""Backend unit tests for conversation query_mode."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from src.models import DEFAULT_QUERY_MODE, normalize_query_mode


def test_normalize_query_mode_defaults_to_include():
    assert normalize_query_mode(None) == DEFAULT_QUERY_MODE
    assert normalize_query_mode("") == DEFAULT_QUERY_MODE


def test_normalize_query_mode_accepts_valid_values():
    assert normalize_query_mode("include") == "include"
    assert normalize_query_mode("omit") == "omit"
    assert normalize_query_mode("opening_only") == "opening_only"
    assert normalize_query_mode("Opening-Only") == "opening_only"


def test_normalize_query_mode_rejects_invalid():
    with pytest.raises(ValueError, match="Invalid query_mode"):
        normalize_query_mode("invalid")
