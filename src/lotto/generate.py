"""Generate recommended Double Chromosphere numbers based on historical data."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .normalize import RED_COLUMNS, load_draws


@dataclass(frozen=True)
class Pick:
    reds: Tuple[int, ...]
    blue: int

    def to_line(self) -> str:
        red_part = " ".join(f"{value:02d}" for value in self.reds)
        return f"{red_part} | {self.blue:02d}"


def generate_numbers(
    frame: pd.DataFrame,
    count: int = 5,
    strategy: str = "weighted",
    seed: Optional[int] = None,
) -> List[Pick]:
    if count <= 0:
        raise ValueError("count must be positive")
    strategy = strategy.lower()
    if strategy not in {"weighted", "uniform"}:
        raise ValueError("strategy must be 'weighted' or 'uniform'")

    if frame.empty:
        raise ValueError("dataset is empty")

    rng = np.random.default_rng(seed)
    red_pool = np.arange(1, 34)
    blue_pool = np.arange(1, 17)

    red_weights = _compute_frequency(frame, red_pool, RED_COLUMNS)
    blue_weights = _compute_frequency(frame, blue_pool, ["blue"])

    constraints = _derive_constraints(frame)

    picks: List[Pick] = []
    seen = set()
    max_attempts = count * 100
    attempts = 0

    while len(picks) < count and attempts < max_attempts:
        attempts += 1
        if strategy == "uniform":
            reds = sorted(rng.choice(red_pool, size=6, replace=False))
            blue = int(rng.choice(blue_pool))
        else:
            reds = _weighted_sample(rng, red_pool, red_weights, k=6)
            blue = int(_weighted_sample(rng, blue_pool, blue_weights, k=1)[0])

        reds_tuple = tuple(sorted(int(value) for value in reds))
        if reds_tuple in seen:
            continue

        if not _respect_constraints(reds_tuple, constraints, rng):
            continue

        pick = Pick(reds=reds_tuple, blue=blue)
        seen.add(reds_tuple)
        picks.append(pick)

    if len(picks) < count:
        # Fallback using uniform picks to complete the quota
        while len(picks) < count:
            reds = tuple(sorted(int(value) for value in rng.choice(red_pool, size=6, replace=False)))
            if reds in seen:
                continue
            blue = int(rng.choice(blue_pool))
            seen.add(reds)
            picks.append(Pick(reds=reds, blue=blue))

    return picks


def generate_from_file(
    path: str | Path,
    count: int = 5,
    strategy: str = "weighted",
    seed: Optional[int] = None,
) -> List[Pick]:
    frame = load_draws(path)
    return generate_numbers(frame, count=count, strategy=strategy, seed=seed)


def save_picks(picks: Sequence[Pick], path: str | Path) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    lines = [pick.to_line() for pick in picks]
    path_obj.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _compute_frequency(frame: pd.DataFrame, pool: Iterable[int], columns: Sequence[str]) -> Dict[int, float]:
    counts = {int(number): 0.0 for number in pool}
    for column in columns:
        for value in frame[column].to_numpy(dtype=int):
            counts[int(value)] = counts.get(int(value), 0.0) + 1.0
    minimum = min(counts.values()) if counts else 0.0
    if minimum == 0.0:
        for key in counts:
            counts[key] = counts[key] + 1.0
    total = sum(counts.values())
    return {key: value / total for key, value in counts.items()}


def _weighted_sample(
    rng: np.random.Generator,
    pool: np.ndarray,
    weights: Dict[int, float],
    k: int,
) -> List[int]:
    available = pool.astype(int).tolist()
    selected: List[int] = []
    for _ in range(k):
        if not available:
            break
        probs = np.array([max(weights.get(value, 0.0), 1e-9) for value in available], dtype=float)
        probs = probs / probs.sum()
        index = int(rng.choice(len(available), p=probs))
        selected.append(int(available.pop(index)))
    return selected


def _derive_constraints(frame: pd.DataFrame) -> Dict[str, Tuple[float, float]]:
    reds = frame[RED_COLUMNS].to_numpy(dtype=int)
    red_sums = reds.sum(axis=1)
    mean_sum = float(np.mean(red_sums))
    std_sum = float(np.std(red_sums, ddof=0)) or 10.0
    lower_sum = max(float(np.min(red_sums)), mean_sum - 1.5 * std_sum)
    upper_sum = min(float(np.max(red_sums)), mean_sum + 1.5 * std_sum)

    odd_counts = (reds % 2 == 1).sum(axis=1)
    mean_odd = float(np.mean(odd_counts))
    lower_odd = max(0.0, mean_odd - 2.0)
    upper_odd = min(6.0, mean_odd + 2.0)

    return {
        "red_sum": (lower_sum, upper_sum),
        "odd_count": (lower_odd, upper_odd),
    }


def _respect_constraints(reds: Tuple[int, ...], constraints: Dict[str, Tuple[float, float]], rng: np.random.Generator) -> bool:
    red_sum = sum(reds)
    odd_count = sum(1 for value in reds if value % 2 == 1)

    lower_sum, upper_sum = constraints.get("red_sum", (0.0, math.inf))
    lower_odd, upper_odd = constraints.get("odd_count", (0.0, 6.0))

    if not (lower_sum <= red_sum <= upper_sum):
        # Soft constraint — allow with small probability to keep diversity
        return rng.random() < 0.1
    if not (lower_odd <= odd_count <= upper_odd):
        return rng.random() < 0.1
    return True
