"""Small, tested statistical helpers. Standard library only."""
from __future__ import annotations

import math


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion."""
    if n <= 0:
        raise ValueError("n must be positive")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def risk_ratio(a: int, n1: int, b: int, n2: int, z: float = 1.96) -> tuple[float, float, float]:
    """Ratio of two proportions (a/n1) / (b/n2) with a Katz log-scale interval."""
    if min(a, b) <= 0:
        raise ValueError("both groups need at least one event")
    ratio = (a / n1) / (b / n2)
    se = math.sqrt(1 / a - 1 / n1 + 1 / b - 1 / n2)
    return ratio, ratio * math.exp(-z * se), ratio * math.exp(z * se)


def _quantile(values: list[float], q: float) -> float:
    items = sorted(values)
    pos = (len(items) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(items) - 1)
    return items[lo] + (items[hi] - items[lo]) * (pos - lo)


def overdispersion(events: list[int], totals: list[int], p0: float, winsor: float = 0.1) -> dict:
    """Additive random-effects overdispersion for a funnel plot of proportions.

    Follows Spiegelhalter (2005), "Funnel plots for comparing institutional
    performance", Statistics in Medicine 24:1185-1202: z-scores are winsorised at
    the 10th and 90th percentiles, phi is their mean square, and when phi shows
    overdispersion a between-unit variance tau^2 is added to every unit's sampling
    variance. Without this, very large NHS trusts make almost every point an
    "outlier" because the binomial limits shrink to nothing.
    """
    if len(events) != len(totals) or len(events) < 3:
        raise ValueError("need at least three units with matching lengths")
    variances = [p0 * (1 - p0) / n for n in totals]
    z = [(e / n - p0) / math.sqrt(v) for e, n, v in zip(events, totals, variances)]
    lo, hi = _quantile(z, winsor), _quantile(z, 1 - winsor)
    zw = [min(max(value, lo), hi) for value in z]
    k = len(zw)
    phi = sum(value * value for value in zw) / k
    weights = [1 / v for v in variances]
    tau2 = 0.0
    if k * phi > k - 1:
        tau2 = (k * phi - (k - 1)) / (sum(weights) - sum(w * w for w in weights) / sum(weights))
    return {"phi": phi, "tau2": max(tau2, 0.0), "units": k}


def funnel_halfwidth(n: int, p0: float, z: float, tau2: float = 0.0) -> float:
    return z * math.sqrt(p0 * (1 - p0) / n + tau2)
