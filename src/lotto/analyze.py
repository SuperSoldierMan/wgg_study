"""Analysis utilities for Double Chromosphere draw datasets."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

from .normalize import RED_COLUMNS, load_draws


@dataclass
class AnalysisMetrics:
    total_draws: int
    red_frequency: Dict[int, int]
    blue_frequency: Dict[int, int]
    red_omission: Dict[str, Dict[int, int]]
    blue_omission: Dict[str, Dict[int, int]]
    red_sum: Dict[str, float]
    odd_even: Dict[str, float | int]
    zone_distribution: Dict[str, float]
    zone_average: Dict[str, float]
    consecutive: Dict[str, float]
    same_tail: Dict[str, float]
    repeat: Dict[str, float]
    span: Dict[str, float]
    latest_draw: Dict[str, str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_draws": self.total_draws,
            "red_frequency": self.red_frequency,
            "blue_frequency": self.blue_frequency,
            "red_omission": self.red_omission,
            "blue_omission": self.blue_omission,
            "red_sum": self.red_sum,
            "odd_even": self.odd_even,
            "zone_distribution": self.zone_distribution,
            "zone_average": self.zone_average,
            "consecutive": self.consecutive,
            "same_tail": self.same_tail,
            "repeat": self.repeat,
            "span": self.span,
            "latest_draw": self.latest_draw,
        }


def compute_metrics(frame: pd.DataFrame) -> AnalysisMetrics:
    if frame.empty:
        raise ValueError("Dataset is empty; cannot compute metrics.")

    total_draws = len(frame)
    red_counts = Counter()
    red_arrays = frame[RED_COLUMNS].to_numpy(dtype=int)
    for row in red_arrays:
        red_counts.update(int(value) for value in row)

    red_frequency = {number: red_counts.get(number, 0) for number in range(1, 34)}

    blue_counts = Counter(int(value) for value in frame["blue"].to_numpy(dtype=int))
    blue_frequency = {number: blue_counts.get(number, 0) for number in range(1, 17)}

    red_omission = _compute_omission(
        frame,
        range(1, 34),
        lambda row: [int(row[col]) for col in RED_COLUMNS],
    )
    blue_omission = _compute_omission(frame, range(1, 17), lambda row: [int(row["blue"])])

    red_sums = red_arrays.sum(axis=1)
    red_sum_stats = {
        "min": int(red_sums.min()),
        "max": int(red_sums.max()),
        "mean": float(np.round(red_sums.mean(), 2)),
        "median": float(np.round(float(np.median(red_sums)), 2)),
        "std": float(np.round(red_sums.std(ddof=0), 2)),
    }

    odd_counts = (red_arrays % 2 == 1).sum()
    even_counts = red_arrays.size - odd_counts
    odd_per_draw = (red_arrays % 2 == 1).sum(axis=1)
    odd_even_stats: Dict[str, float | int] = {
        "odd_total": int(odd_counts),
        "even_total": int(even_counts),
        "odd_ratio": float(np.round(odd_counts / red_arrays.size, 4)),
        "average_odds_per_draw": float(np.round(odd_per_draw.mean(), 2)),
    }

    zone_distribution, zone_average = _compute_zones(red_arrays)
    consecutive_stats = _compute_consecutive(red_arrays)
    same_tail_stats = _compute_same_tail(red_arrays)
    repeat_stats = _compute_repeat(red_arrays)
    span_stats = _compute_span(red_arrays)

    latest = frame.iloc[-1]
    latest_draw = {
        "date": str(latest["date"]),
        "issue": str(latest["issue"]),
        "reds": [int(latest[col]) for col in RED_COLUMNS],
        "blue": int(latest["blue"]),
    }

    return AnalysisMetrics(
        total_draws=total_draws,
        red_frequency=red_frequency,
        blue_frequency=blue_frequency,
        red_omission=red_omission,
        blue_omission=blue_omission,
        red_sum=red_sum_stats,
        odd_even=odd_even_stats,
        zone_distribution=zone_distribution,
        zone_average=zone_average,
        consecutive=consecutive_stats,
        same_tail=same_tail_stats,
        repeat=repeat_stats,
        span=span_stats,
        latest_draw=latest_draw,
    )


def render_report(metrics: AnalysisMetrics) -> str:
    red_freq_sorted = sorted(metrics.red_frequency.items(), key=lambda item: item[1], reverse=True)
    top_reds = ", ".join(f"{num:02d} ({count})" for num, count in red_freq_sorted[:10])
    top_blues = ", ".join(
        f"{num:02d} ({metrics.blue_frequency[num]})" for num in range(1, 17)
        if metrics.blue_frequency[num] == max(metrics.blue_frequency.values())
    )

    lines = [
        "# 双色球历史数据分析报告",
        "",
        f"- 覆盖期数：{metrics.total_draws}",
        f"- 最近一期：{metrics.latest_draw['issue']} ({metrics.latest_draw['date']})",
        f"- 最常见红球（前10）：{top_reds}",
        f"- 最常见蓝球：{top_blues}",
        "",
        "## 红球和值统计",
        (
            f"- 最小值：{metrics.red_sum['min']}\n"
            f"- 最大值：{metrics.red_sum['max']}\n"
            f"- 平均值：{metrics.red_sum['mean']}\n"
            f"- 标准差：{metrics.red_sum['std']}"
        ),
        "",
        "## 奇偶分布",
        (
            f"- 奇数总数：{metrics.odd_even['odd_total']}\n"
            f"- 偶数总数：{metrics.odd_even['even_total']}\n"
            f"- 奇数占比：{metrics.odd_even['odd_ratio']:.2%}\n"
            f"- 单期平均奇数个数：{metrics.odd_even['average_odds_per_draw']}"
        ),
        "",
        "## 红球三区分布 (1-11 / 12-22 / 23-33)",
        *[
            f"- {zone}：总计 {metrics.zone_distribution[zone]}，单期均值 {metrics.zone_average[zone]:.2f}"
            for zone in ("1-11", "12-22", "23-33")
        ],
        "",
        "## 连号与同尾分析",
        (
            f"- 含连号的期数：{metrics.consecutive['with_consecutive']}\n"
            f"- 连号平均长度：{metrics.consecutive['average_longest']:.2f}\n"
            f"- 含同尾号的期数：{metrics.same_tail['with_same_tail']}\n"
            f"- 单期最大同尾个数：{metrics.same_tail['max_same_tail']}"
        ),
        "",
        "## 重复号与跨度",
        (
            f"- 平均重复红球数：{metrics.repeat['average_overlap']:.2f}\n"
            f"- 含重复红球的期数：{metrics.repeat['with_overlap']}\n"
            f"- 跨度最小：{metrics.span['min']}\n"
            f"- 跨度最大：{metrics.span['max']}\n"
            f"- 跨度均值：{metrics.span['mean']:.2f}"
        ),
    ]
    return "\n".join(lines)


def save_report(report: str, path: str | Path) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.write_text(report, encoding="utf-8")


def save_metrics(metrics: AnalysisMetrics, path: str | Path) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.write_text(json.dumps(metrics.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def analyse_file(in_path: str | Path) -> AnalysisMetrics:
    frame = load_draws(in_path)
    return compute_metrics(frame)


def _compute_omission(
    frame: pd.DataFrame,
    domain: Iterable[int],
    extractor,
) -> Dict[str, Dict[int, int]]:
    current = {number: 0 for number in domain}
    maximum = {number: 0 for number in domain}

    for _, row in frame.iterrows():
        numbers = set(extractor(row))
        for number in current:
            if number in numbers:
                current[number] = 0
            else:
                current[number] += 1
                maximum[number] = max(maximum[number], current[number])

    return {
        "current": current,
        "max": maximum,
    }


def _compute_zones(red_arrays: np.ndarray) -> tuple[Dict[str, int], Dict[str, float]]:
    zone_ranges = {
        "1-11": (1, 11),
        "12-22": (12, 22),
        "23-33": (23, 33),
    }
    distribution = {zone: 0 for zone in zone_ranges}
    counts_per_draw = {zone: [] for zone in zone_ranges}

    for row in red_arrays:
        for zone, (low, high) in zone_ranges.items():
            count = int(sum(1 for value in row if low <= value <= high))
            distribution[zone] += count
            counts_per_draw[zone].append(count)

    zone_average = {
        zone: float(np.round(np.mean(counts), 2)) if counts else 0.0
        for zone, counts in counts_per_draw.items()
    }
    return distribution, zone_average


def _compute_consecutive(red_arrays: np.ndarray) -> Dict[str, float]:
    with_consecutive = 0
    longest_runs: List[int] = []

    for row in red_arrays:
        sorted_row = sorted(int(value) for value in row)
        longest = 1
        current = 1
        has_consecutive = False
        for idx in range(1, len(sorted_row)):
            if sorted_row[idx] - sorted_row[idx - 1] == 1:
                current += 1
                has_consecutive = True
            else:
                longest = max(longest, current)
                current = 1
        longest = max(longest, current)
        if has_consecutive:
            with_consecutive += 1
        longest_runs.append(longest)

    average_longest = float(np.round(np.mean(longest_runs), 2)) if longest_runs else 0.0
    return {
        "with_consecutive": with_consecutive,
        "average_longest": average_longest,
    }


def _compute_same_tail(red_arrays: np.ndarray) -> Dict[str, float]:
    with_same_tail = 0
    max_same_tail = 0

    for row in red_arrays:
        tails = Counter(int(value) % 10 for value in row)
        duplicates = [count for count in tails.values() if count > 1]
        if duplicates:
            with_same_tail += 1
            max_same_tail = max(max_same_tail, max(duplicates))

    return {
        "with_same_tail": with_same_tail,
        "max_same_tail": max_same_tail,
    }


def _compute_repeat(red_arrays: np.ndarray) -> Dict[str, float]:
    overlaps: List[int] = []
    previous = None
    with_overlap = 0

    for row in red_arrays:
        current_set = set(int(value) for value in row)
        if previous is not None:
            overlap = len(current_set & previous)
            overlaps.append(overlap)
            if overlap:
                with_overlap += 1
        previous = current_set

    average_overlap = float(np.round(np.mean(overlaps), 2)) if overlaps else 0.0
    return {
        "with_overlap": with_overlap,
        "average_overlap": average_overlap,
    }


def _compute_span(red_arrays: np.ndarray) -> Dict[str, float]:
    spans = [int(max(row) - min(row)) for row in red_arrays]
    return {
        "min": int(min(spans)) if spans else 0,
        "max": int(max(spans)) if spans else 0,
        "mean": float(np.round(np.mean(spans), 2)) if spans else 0.0,
    }
