"""Tests for number generation strategies."""

import pandas as pd

from lotto.generate import Pick, generate_numbers


def _sample_frame() -> pd.DataFrame:
    rows = [
        {
            "date": "2024-01-01",
            "issue": "2024001",
            "red1": 1,
            "red2": 5,
            "red3": 10,
            "red4": 18,
            "red5": 21,
            "red6": 30,
            "blue": 6,
        },
        {
            "date": "2024-01-04",
            "issue": "2024002",
            "red1": 3,
            "red2": 6,
            "red3": 13,
            "red4": 22,
            "red5": 27,
            "red6": 33,
            "blue": 4,
        },
        {
            "date": "2024-01-07",
            "issue": "2024003",
            "red1": 2,
            "red2": 9,
            "red3": 14,
            "red4": 19,
            "red5": 26,
            "red6": 32,
            "blue": 3,
        },
        {
            "date": "2024-01-09",
            "issue": "2024004",
            "red1": 4,
            "red2": 7,
            "red3": 12,
            "red4": 20,
            "red5": 25,
            "red6": 31,
            "blue": 8,
        },
        {
            "date": "2024-01-11",
            "issue": "2024005",
            "red1": 5,
            "red2": 11,
            "red3": 16,
            "red4": 23,
            "red5": 28,
            "red6": 29,
            "blue": 12,
        },
        {
            "date": "2024-01-14",
            "issue": "2024006",
            "red1": 6,
            "red2": 8,
            "red3": 15,
            "red4": 17,
            "red5": 24,
            "red6": 30,
            "blue": 1,
        },
    ]
    return pd.DataFrame(rows)


def test_uniform_generation_is_deterministic_with_seed():
    frame = _sample_frame()
    picks_a = generate_numbers(frame, count=3, strategy="uniform", seed=123)
    picks_b = generate_numbers(frame, count=3, strategy="uniform", seed=123)
    assert [pick.to_line() for pick in picks_a] == [pick.to_line() for pick in picks_b]
    for pick in picks_a:
        assert isinstance(pick, Pick)
        assert len(pick.reds) == 6
        assert sorted(pick.reds) == list(pick.reds)
        assert len(set(pick.reds)) == 6
        assert all(1 <= value <= 33 for value in pick.reds)
        assert 1 <= pick.blue <= 16


def test_weighted_generation_respects_constraints():
    frame = _sample_frame()
    picks = generate_numbers(frame, count=5, strategy="weighted", seed=42)
    assert len(picks) == 5
    sums = [sum(pick.reds) for pick in picks]
    assert min(sums) >= 40  # within historical range of sample data
    assert max(sums) <= 170
    unique_lines = {pick.to_line() for pick in picks}
    assert len(unique_lines) == len(picks)
