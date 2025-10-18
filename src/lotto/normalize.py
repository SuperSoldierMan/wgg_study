"""Utilities for normalising Double Chromosphere draw data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from .exceptions import NormalizationError


@dataclass(frozen=True)
class Draw:
    """Normalised representation of a single lottery draw."""

    date: date
    issue: str
    reds: List[int]
    blue: int

    def __post_init__(self) -> None:  # type: ignore[override]
        validate_draw_components(self.date, self.issue, self.reds, self.blue)

    def to_dict(self) -> dict:
        reds_sorted = sorted(self.reds)
        record = {
            "date": self.date.isoformat(),
            "issue": self.issue,
            "blue": int(self.blue),
        }
        for idx, value in enumerate(reds_sorted, start=1):
            record[f"red{idx}"] = int(value)
        return record


RED_COLUMNS = [f"red{i}" for i in range(1, 7)]
ALL_COLUMNS = ["date", "issue", *RED_COLUMNS, "blue"]


def validate_draw_components(
    draw_date: date,
    issue: str,
    reds: Iterable[int],
    blue: int,
) -> None:
    red_list = list(reds)
    if len(red_list) != 6:
        raise NormalizationError("Each draw must contain exactly six red balls.")
    if len(set(red_list)) != 6:
        raise NormalizationError("Red balls in a draw must be unique.")
    if not all(1 <= value <= 33 for value in red_list):
        raise NormalizationError("Red balls must be between 1 and 33 inclusive.")
    if not 1 <= blue <= 16:
        raise NormalizationError("Blue ball must be between 1 and 16 inclusive.")
    if not isinstance(draw_date, date):
        raise NormalizationError("Draw date must be a date object.")
    if not issue:
        raise NormalizationError("Draw issue identifier must be provided.")


def normalise_draws(draws: Iterable[Draw]) -> pd.DataFrame:
    """Convert an iterable of :class:`Draw` objects to a tidy DataFrame."""

    records = [draw.to_dict() for draw in draws]
    if not records:
        return pd.DataFrame(columns=ALL_COLUMNS)
    frame = pd.DataFrame.from_records(records)
    frame = frame[ALL_COLUMNS]
    frame.sort_values(["date", "issue"], inplace=True)
    frame.reset_index(drop=True, inplace=True)
    return frame


def save_draws(frame: pd.DataFrame, path: str | Path) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path_obj, index=False)


def load_draws(path: str | Path) -> pd.DataFrame:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Draw dataset not found: {path_obj}")
    frame = pd.read_csv(path_obj, dtype={"issue": str})
    expected = set(ALL_COLUMNS)
    if not expected.issubset(frame.columns):
        missing = ", ".join(sorted(expected - set(frame.columns)))
        raise NormalizationError(f"Dataset missing expected columns: {missing}")
    # ensure ordering and types
    frame = frame[ALL_COLUMNS]
    frame[RED_COLUMNS + ["blue"]] = frame[RED_COLUMNS + ["blue"]].astype(int)
    return frame


def parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise NormalizationError(f"Unsupported date format: {value!r}")
