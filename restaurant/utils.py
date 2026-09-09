"""
Small utility functions used across the restaurant data pipeline.
"""

from __future__ import annotations

import datetime
from datetime import date, timedelta
from typing import Iterator

import pandas as pd


def unique_values(df: pd.DataFrame, column: str) -> set:
    """Return the set of non-NaN unique values in *column*."""
    return {x for x in df[column] if x == x}


def next_month(month_str: str) -> str:
    """Given a month string like ``'01_2023'``, return the next month.

    Format: ``MM_YYYY``.
    """
    month, year = int(month_str.split("_")[0]), int(month_str.split("_")[1])
    if month == 12:
        return f"01_{year + 1}"
    return f"{month + 1:02d}_{year}"


def daterange(start_date: date, end_date: date) -> Iterator[date]:
    """Yield every date from *start_date* through *end_date* inclusive."""
    days = int((end_date - start_date).days) + 1
    for n in range(days):
        yield start_date + timedelta(n)


def two_weeks_prior(date_str: str) -> str:
    """Return ``YYYY-MM-DD`` for 14 days before *date_str*."""
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return (dt - timedelta(weeks=2)).strftime("%Y-%m-%d")


def one_year_prior(date_str: str) -> str:
    """Return ``YYYY-MM-DD`` for the same weekday roughly one year before *date_str*."""
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    target_weekday = dt.weekday()
    candidate = dt.replace(year=dt.year - 1)
    while candidate.weekday() != target_weekday:
        candidate += timedelta(days=1)
    return candidate.strftime("%Y-%m-%d")


def get_after_first_word(text: str) -> str:
    """Return everything after the first whitespace-delimited word."""
    words = text.split()
    return " ".join(words[1:]) if len(words) > 1 else ""


def find_in_dict(term: str, lookup: dict[str, set[str]]) -> str:
    """Reverse-lookup: find which key's set contains *term*. Return ``""`` if not found."""
    for key, values in lookup.items():
        if term in values:
            return key
    return ""


def assign_lookup(
    df: pd.DataFrame,
    source_col: str,
    target_col: str,
    lookup: dict[str, set[str]],
) -> None:
    """Add *target_col* to *df* by reverse-looking up *source_col* in *lookup*."""
    df[target_col] = df[source_col].apply(lambda v: find_in_dict(v, lookup))
