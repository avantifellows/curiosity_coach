"""Unit tests for chapter chat intent selection (no database)."""
import pytest

from src.projects.progress_selection import (
    ChapterIntentKind,
    build_core_chat_theme,
    select_intent_from_spine_and_status,
)


def test_select_first_ongoing_in_spine_order():
    spine = [(10, "Qa", "FUa"), (11, "Qa", "FUb"), (12, "Qb", "FUc")]
    status = {10: "done", 11: "ongoing", 12: "not_started"}
    r = select_intent_from_spine_and_status(spine, status)
    assert r.kind == ChapterIntentKind.ACTIVE
    assert r.foundational_unit_id == 11
    assert r.core_chat_theme is not None
    assert "FUb" in r.core_chat_theme


def test_ongoing_before_not_started():
    spine = [(1, "q", "a"), (2, "q", "b")]
    status = {1: "not_started", 2: "ongoing"}
    r = select_intent_from_spine_and_status(spine, status)
    assert r.foundational_unit_id == 2


def test_first_not_started_when_no_ongoing():
    spine = [(1, "q", "a"), (2, "q", "b")]
    status = {1: "done", 2: "not_started"}
    r = select_intent_from_spine_and_status(spine, status)
    assert r.kind == ChapterIntentKind.ACTIVE
    assert r.foundational_unit_id == 2


def test_chapter_complete_when_all_done():
    spine = [(1, "q", "a"), (2, "q", "b")]
    status = {1: "done", 2: "done"}
    r = select_intent_from_spine_and_status(spine, status)
    assert r.kind == ChapterIntentKind.CHAPTER_COMPLETE


def test_not_subscribed_when_missing_progress_row():
    spine = [(1, "q", "a"), (2, "q", "b")]
    status = {1: "not_started"}
    r = select_intent_from_spine_and_status(spine, status)
    assert r.kind == ChapterIntentKind.NOT_SUBSCRIBED


def test_empty_spine_no_units():
    r = select_intent_from_spine_and_status([], {})
    assert r.kind == ChapterIntentKind.NO_UNITS


def test_build_core_chat_theme_truncation():
    long_fu = "x" * 20000
    t = build_core_chat_theme("short q", long_fu)
    assert len(t) <= 12000
    assert "truncated" in t
