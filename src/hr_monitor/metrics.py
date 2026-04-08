from math import sqrt
from statistics import fmean, stdev
from typing import Sequence
from .exceptions import HRVCalculationError


def _require_non_empty(intervals_ms: Sequence[float]) -> None:
    if len(intervals_ms) == 0:
        raise HRVCalculationError("RR intervals list cannot be empty.")


def _require_at_least_two(intervals_ms: Sequence[float], metric_name: str) -> None:
    if len(intervals_ms) < 2:
        raise HRVCalculationError(f"{metric_name} requires at least two RR intervals.")


def hr_mean_bpm(intervals_ms: Sequence[float]) -> float:
    """Return mean heart rate (bpm) from RR intervals in milliseconds."""
    _require_non_empty(intervals_ms)
    return fmean(60000.0 / rr for rr in intervals_ms)


def sdnn_ms(intervals_ms: Sequence[float]) -> float:
    """Return SDNN (sample standard deviation) in milliseconds."""
    _require_at_least_two(intervals_ms, "SDNN")
    return stdev(intervals_ms)


def rmssd_ms(intervals_ms: Sequence[float]) -> float:
    """Return RMSSD in milliseconds from RR intervals."""
    _require_at_least_two(intervals_ms, "RMSSD")
    diffs = [curr - prev for prev, curr in zip(intervals_ms, intervals_ms[1:])]
    squared_sum = sum(diff**2 for diff in diffs)
    return sqrt(squared_sum / len(diffs))
