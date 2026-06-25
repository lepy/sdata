# -*- coding: utf-8 -*-
"""Vollständige Abdeckung von sdata/timestamp.py (ISO8601-Parser + TimeStamp)."""
import datetime
import time

import pytest

from sdata.timestamp import (
    parse_date, parse_timezone, to_int, ParseError, TimeStamp, UTC,
    local_tzname, get_utc_timestamp, get_local_timestamp,
    today_str, now_local_str, now_utc_str,
)


def test_to_int():
    assert to_int({"x": "5"}, "x") == 5
    assert to_int({}, "x", default_to_zero=True) == 0
    assert to_int({}, "x", required=False) is None
    with pytest.raises(ParseError):
        to_int({}, "x", required=True)


def test_parse_timezone_and_offsets():
    assert parse_timezone({"timezone": "Z"}) is UTC
    assert parse_timezone({"timezone": None}, default_timezone=UTC) is UTC
    assert parse_date("2020-01-01T00:00:00+02:30").utcoffset() == \
        datetime.timedelta(hours=2, minutes=30)
    assert parse_date("2020-01-01T00:00:00-05:00").utcoffset() == \
        datetime.timedelta(hours=-5)


def test_parse_date_valid_and_errors():
    d = parse_date("2020-12-11T09:04:00.660000+00:00")
    assert d.year == 2020 and d.microsecond == 660000
    assert parse_date("2020-01-01").tzinfo is UTC          # ohne tz -> default
    with pytest.raises(ParseError):
        parse_date(12345)                                  # kein String
    with pytest.raises(ParseError):
        parse_date("not-a-date")                           # kein Regex-Match
    with pytest.raises(ParseError):
        parse_date("2020-13-45")                           # Regex ok, datetime lehnt ab


def test_local_tzname_both_branches(monkeypatch):
    monkeypatch.setattr(time, "daylight", 1)
    assert local_tzname().startswith("Etc/GMT")
    monkeypatch.setattr(time, "daylight", 0)
    assert local_tzname().startswith("Etc/GMT")


def test_get_utc_local_timestamp():
    assert get_utc_timestamp("notadate") is None
    dt = parse_date("2020-01-01T00:00:00+00:00")
    assert get_utc_timestamp(dt).tzinfo is not None
    assert get_local_timestamp(dt).tzinfo is not None


def test_timestamp_class():
    t = TimeStamp("2020-12-11T09:04:00+00:00")
    assert "2020-12-11" in repr(t) and "2020-12-11" in str(t)
    assert "T" in t.utc and "T" in t.local
    assert isinstance(TimeStamp()._datetime, datetime.datetime)   # Default = now
    with pytest.raises(Exception):
        TimeStamp("garbage")


def test_str_helpers():
    assert "T" in today_str()
    assert "T" in now_local_str()
    assert "T" in now_utc_str()
