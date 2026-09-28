"""Per-series gates (design §5.1). A series that fails is regenerated under a
named retry seed; the attempt number is recorded, so the corpus is still a
pure function of the names."""
from __future__ import annotations

import numpy as np


def window_stationarity(x: np.ndarray, W: int = 5) -> tuple[float, float, float]:
    """(statav_mean, statav_std, var_ratio) over W non-overlapping windows (hctsa SY_StatAv)."""
    s = x.std() or 1.0
    w = x[: (x.size // W) * W].reshape(W, -1)
    m, sd = w.mean(1), w.std(1)
    return float(m.std() / s), float(sd.std() / s), float(sd.max() ** 2 / max(sd.min() ** 2, 1e-12))


VARIANCE_EXEMPT = ("bursty", "event_like")  # spike trains, rainfall, ETAS: unequal windows are the point


def stationarity_gate(x: np.ndarray, tags: dict, cls: str = "") -> str | None:
    """Stationary-profile gate: the record must look stationary in mean over 5 windows
    (statav_mean <= 0.5: i.i.d. gives 0.07, an AR(1) with a 20-sample correlation time ~0.45),
    and in variance (statav_std <= 0.5, max/min window variance <= 20) unless the family is an
    event process whose windows are unequal by construction. Conditional heteroskedasticity is not
    exempt: a GARCH/SV process is stationary and must look it at this length, which bounds its persistence."""
    sm, ss, vr = window_stationarity(x)
    if sm > 0.5:
        return f"mean drifts across windows (statav_mean {sm:.2f})"
    if not any(tags.get(t) == "yes" for t in VARIANCE_EXEMPT):
        # a settled deterministic attractor has no reason to change amplitude across the record,
        # so F/G/L/H are held to a tighter bound: it catches trajectories still spiralling out
        det = cls in ("F", "G", "H", "L") and tags.get("deterministic") in ("yes", "partly")
        ss_max, vr_max = (0.3, 6.0) if det else (0.5, 20.0)
        if ss > ss_max or vr > vr_max:
            return f"variance drifts across windows (statav_std {ss:.2f}, ratio {vr:.1f})"
    return None


def real_valued_gate(x: np.ndarray, tags: dict, cls: str) -> str | None:
    """Stationary-profile gate: real-valued data only (no discrete-valued families, >= 100 distinct
    values), and no periodic orbits among the deterministic maps and flows (F, G) — the periodic
    class H is where designed periodicity lives."""
    if tags.get("discrete_valued") == "yes":
        return "discrete-valued (real-valued corpus)"
    if np.unique(x).size < 100:
        return f"only {np.unique(x).size} distinct values (real-valued corpus)"
    if cls in ("F", "G") and tags.get("periodic") == "yes":
        return "periodic orbit (F/G must be chaotic or quasi-periodic)"
    return None


def gate(x: np.ndarray, tags: dict) -> str | None:
    """None if the series passes; else the reason."""
    if x.ndim != 1:
        return "not 1-D"
    if not np.all(np.isfinite(x)):
        return "non-finite values"
    if np.abs(x).max() > 1e12:
        return "overflow-scale values"
    if x.std() == 0:
        return "constant"
    if tags.get("discrete_valued") != "yes" and np.unique(x).size < 10:
        return "fewer than 10 distinct values"
    if tags.get("discrete_valued") == "yes" and np.unique(x).size < 2:
        return "single-valued"
    return None
