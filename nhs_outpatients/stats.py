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
    performance", Statistics in Medicine 24:1185-1202, and "Handling
    over-dispersion of performance indicators", Qual Saf Health Care 14:347-351,
    in the form used for proportions in NHS and CQC monitoring: proportions are
    put on the variance-stabilising arcsine-square-root scale, where the sampling
    variance is 1/(4n); z-scores are winsorised at the 10th and 90th percentiles;
    phi is their mean square; and when phi shows overdispersion a between-unit
    variance tau^2 is added to every unit's sampling variance. Without this, very
    large NHS trusts make almost every point an "outlier".
    """
    if len(events) != len(totals) or len(events) < 3:
        raise ValueError("need at least three units with matching lengths")
    target = math.asin(math.sqrt(p0))
    variances = [1 / (4 * n) for n in totals]
    z = [(math.asin(math.sqrt(e / n)) - target) / math.sqrt(v) for e, n, v in zip(events, totals, variances)]
    lo, hi = _quantile(z, winsor), _quantile(z, 1 - winsor)
    zw = [min(max(value, lo), hi) for value in z]
    k = len(zw)
    phi = sum(value * value for value in zw) / k
    weights = [1 / v for v in variances]
    tau2 = 0.0
    if k * phi > k - 1:
        tau2 = (k * phi - (k - 1)) / (sum(weights) - sum(w * w for w in weights) / sum(weights))
    return {"phi": phi, "tau2": max(tau2, 0.0), "units": k, "scale": "arcsine square root"}


def funnel_limits(n: int, p0: float, z: float, tau2: float = 0.0) -> tuple[float, float]:
    """Lower and upper control limits for a proportion at volume n (arcsine scale, back-transformed)."""
    target = math.asin(math.sqrt(p0))
    half = z * math.sqrt(1 / (4 * n) + tau2)
    return math.sin(max(target - half, 0.0)) ** 2, math.sin(min(target + half, math.pi / 2)) ** 2


def _additive_tau2(z: list[float], variances: list[float], winsor: float) -> tuple[float, float]:
    """phi and tau^2 from z-scores and sampling variances (winsorised, DerSimonian-Laird form)."""
    lo, hi = _quantile(z, winsor), _quantile(z, 1 - winsor)
    zw = [min(max(value, lo), hi) for value in z]
    k = len(zw)
    phi = sum(value * value for value in zw) / k
    weights = [1 / v for v in variances]
    if k * phi <= k - 1:
        return phi, 0.0
    return phi, (k * phi - (k - 1)) / (sum(weights) - sum(w * w for w in weights) / sum(weights))


def ratio_overdispersion(observed: list[float], expected: list[float], winsor: float = 0.1) -> dict:
    """Overdispersion for indirectly standardised ratios O/E (Spiegelhalter 2005).

    O is treated as Poisson with mean E, so sqrt(O/E) has sampling variance
    1/(4E) around a target of 1. The same winsorised additive model as
    ``overdispersion`` is then applied on that square-root scale.
    """
    if len(observed) != len(expected) or len(observed) < 3:
        raise ValueError("need at least three units with matching lengths")
    if min(expected) <= 0:
        raise ValueError("expected counts must be positive")
    variances = [1 / (4 * e) for e in expected]
    z = [(math.sqrt(o / e) - 1) / math.sqrt(v) for o, e, v in zip(observed, expected, variances)]
    phi, tau2 = _additive_tau2(z, variances, winsor)
    return {"phi": phi, "tau2": tau2, "units": len(z), "scale": "square root of O/E"}


def ratio_limits(expected: float, z: float, tau2: float = 0.0) -> tuple[float, float]:
    """Control limits for O/E at expected count E (square-root scale, back-transformed)."""
    half = z * math.sqrt(1 / (4 * expected) + tau2)
    return max(1 - half, 0.0) ** 2, (1 + half) ** 2


def overdispersion_untransformed(events: list[int], totals: list[int], p0: float, winsor: float = 0.1) -> float:
    """tau^2 on the raw proportion scale; used only as a sensitivity check."""
    variances = [p0 * (1 - p0) / n for n in totals]
    z = [(e / n - p0) / math.sqrt(v) for e, n, v in zip(events, totals, variances)]
    lo, hi = _quantile(z, winsor), _quantile(z, 1 - winsor)
    zw = [min(max(value, lo), hi) for value in z]
    k = len(zw)
    phi = sum(value * value for value in zw) / k
    weights = [1 / v for v in variances]
    if k * phi <= k - 1:
        return 0.0
    return (k * phi - (k - 1)) / (sum(weights) - sum(w * w for w in weights) / sum(weights))
