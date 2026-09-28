"""Class C: linear non-Gaussian. Where time-irreversibility lives without chaos."""
from __future__ import annotations

import numpy as np

from ..registry import family
from ..util import ar_filter, burn, ma_filter, skew_innov, stable_ar, stable_innov

LNG = dict(linear="yes", gaussian="no", stationary="yes")
BURN = 2000


@family("C", "ar-skew", 8, {**LNG, "skewed": "yes", "reversible": "no"}, profiles={"stationary1000": 10})
def ar_skew(i, rng, T, S):
    """AR(p<=3) with centred-gamma innovations, shape LU[0.4, 3] (skewness 2/sqrt(shape))."""
    p = S.integer("p", 1, 3)
    a = stable_ar(p, rng, 0.8) if p > 1 else np.array([S.draw("phi", 0.3, 0.95)])
    k = S.draw("shape", 0.4, 3.0, log=True)
    e = skew_innov(T + BURN, k, rng)
    return burn(ar_filter(e, a), T), dict(p=p, a=a, shape=k)


@family("C", "arma-heavy", 8, {**LNG, "heavy_tailed": "yes", "reversible": "yes"}, profiles={"stationary1000": 9})
def arma_heavy(i, rng, T, S):
    """AR(p <= 3) -- no MA part, despite the family name -- with Student-t (nu S[1.5, 4]) or symmetric alpha-stable (alpha S[1.2, 1.9]) innovations;
    in the stationary profile Student-t only, nu S[3, 6] (finite variance)."""
    from ..registry import profile
    stat = profile() == "stationary1000"
    p = int(rng.integers(1, 4))
    a = stable_ar(p, rng, 0.8)
    if i % 2 == 0 or stat:
        nu = S.draw("nu_finite", 3.0, 6.0) if stat else S.draw("nu", 1.5, 4.0)
        e = rng.standard_t(nu, T + BURN)
        info = dict(kind="student", nu=nu)
    else:
        al = S.draw("alpha", 1.2, 1.9)
        e = stable_innov(T + BURN, al, 0.0, rng)
        info = dict(kind="stable", alpha=al)
    return burn(ar_filter(e, a), T), dict(p=p, a=a, **info)


@family("C", "ma-asym-skew", 6, {**LNG, "skewed": "yes", "reversible": "no"}, profiles={"stationary1000": 7})
def ma_asym_skew(i, rng, T, S):
    """One-sided decaying MA(q) with skewed innovations (Weiss 1975): linear, non-Gaussian, asymmetric filter."""
    q = S.integer("q", 2, 6)
    r = rng.uniform(0.6, 0.95)
    th = rng.uniform(0.2, 1.0, q) * r ** np.arange(1, q + 1)
    k = rng.uniform(0.4, 3.0)
    return burn(ma_filter(skew_innov(T + BURN, k, rng), th), T), dict(q=q, theta=th, shape=k)


@family("C", "levy-ou", 8, {**LNG, "skewed": "partly", "event_like": "partly", "reversible": "no"}, profiles={"stationary1000": 9})
def levy_ou(i, rng, T, S):
    """Levy-driven OU: compound-Poisson jumps (rate LU[0.05, 0.4]/sample, exponential sizes, one-sided
    for even i, two-sided for odd i) with exponential decay S[0.6, 0.93]; i % 4 < 2 add Gaussian noise (SD 0.3)."""
    rate = S.draw("rate", 0.05, 0.4, log=True)
    d = S.draw("decay", 0.6, 0.93)  # decay time 2.5-14 samples
    one_sided = i % 2 == 0
    n = T + BURN
    jumps = (rng.uniform(size=n) < rate) * rng.exponential(1.0, n)
    if not one_sided:
        jumps *= rng.choice([-1.0, 1.0], n)
    e = jumps + (0.3 * rng.standard_normal(n) if i % 4 < 2 else 0.0)
    from ..registry import profile as _pp
    extra = dict(gauss_sd=0.3 if i % 4 < 2 else 0.0) if _pp() == "stationary1000" else {}  # the added Gaussian noise (record it)
    return burn(ar_filter(e, [d]), T), dict(rate=rate, decay=d, one_sided=one_sided,
                                            skewed="yes" if one_sided else "no", event_rate=rate, **extra)


@family("C", "ar-bounded", 8, {**LNG, "reversible": "yes"})
def ar_bounded(i, rng, T, S):
    """AR(1) with binary (+-1, even i) or uniform (odd i) innovations, phi S(-0.9, 0.9)."""
    phi = S.draw("phi", -0.9, 0.9)
    n = T + BURN
    e = rng.choice([-1.0, 1.0], n) if i % 2 == 0 else rng.uniform(-1, 1, n)
    return burn(ar_filter(e, [phi]), T), dict(phi=phi, innovation="binary" if i % 2 == 0 else "uniform")


@family("C", "shot-noise", 8, {**LNG, "skewed": "yes", "event_like": "yes", "reversible": "no"}, profiles={"stationary1000": 9})
def shot_noise(i, rng, T, S):
    """Poisson-driven pulses with a random pulse shape (exponential, alpha-function, Gaussian,
    rectangular; the stationary profile omits rectangular), rate LU[0.05, 0.3]/sample, width LU[1.5, 6] samples."""
    from ..registry import profile
    kind = S.choice("kind", ["exponential", "alpha", "gaussian"] if profile() == "stationary1000" else ["exponential", "alpha", "gaussian", "rect"])
    rate = S.draw("rate", 0.05, 0.3, log=True)
    w = S.draw("width", 1.5, 6, log=True)
    n = T + BURN
    drive = (rng.uniform(size=n) < rate) * rng.exponential(1.0, n)
    t = np.arange(int(6 * w) + 1)
    if kind == "exponential":
        h = np.exp(-t / w)
    elif kind == "alpha":
        h = (t / w) * np.exp(1 - t / w)
    elif kind == "gaussian":
        h = np.exp(-0.5 * ((t - 3 * w) / w) ** 2)
    else:
        h = (t < w).astype(float)
    x = np.convolve(drive, h)[:n]
    return burn(x, T), dict(kind=kind, rate=rate, width=w, event_rate=rate,
                            reversible="yes" if kind in ("gaussian", "rect") else "no")
