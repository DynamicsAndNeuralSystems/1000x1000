"""Class D: long memory, self-similarity, multifractality."""
from __future__ import annotations

import numpy as np

from ..registry import family
from ..util import arfima as _arfima, fgn, powerlaw_noise, stable_innov

LM = dict(linear="yes", gaussian="yes", stationary="yes", long_memory="yes", reversible="yes")


@family("D", "fgn", 12, LM, profiles={"stationary1000": 14})
def fgn_family(i, rng, T, S):
    """Fractional Gaussian noise (exact Davies-Harte), H stratified over [0.02, 0.9]."""
    H = S.draw("H", 0.02, 0.9)
    return fgn(T, H, rng), dict(hurst_H=H, long_memory="yes" if H > 0.6 else ("no" if H < 0.4 else "partly"))


@family("D", "fbm", 10, {**LM, "stationary": "no", "nonstationary_kind": "walk"}, profiles={"stationary1000": 0})
def fbm(i, rng, T, S):
    """Fractional Brownian motion, H stratified over (0.1, 0.95)."""
    H = S.draw("H", 0.1, 0.95)
    return np.cumsum(fgn(T, H, rng)), dict(hurst_H=H)


@family("D", "arfima", 12, LM, profiles={"stationary1000": 14})
def arfima_family(i, rng, T, S):
    """ARFIMA(p, d, q), d stratified over [-0.45, 0.4], p, q in {0, 1}."""
    d = S.draw("d", -0.45, 0.4)
    p, q = int(rng.integers(0, 2)), int(rng.integers(0, 2))
    ar = [rng.uniform(-0.6, 0.6)] if p else ()
    ma = [rng.uniform(-0.6, 0.6)] if q else ()
    x = _arfima(T, d, rng, ar=ar, ma=ma)
    return x, dict(arfima_d=d, ar=list(ar), ma=list(ma), hurst_H=d + 0.5,
                   long_memory="yes" if abs(d) > 0.15 else "partly")


@family("D", "one-over-f", 8, LM, profiles={"stationary1000": 0})
def one_over_f(i, rng, T, S):
    """1/f^beta noise by spectral synthesis, beta stratified over [0, 3]; beta > 1 is non-stationary."""
    beta = S.draw("beta", 0.0, 3.0)
    x = powerlaw_noise(T, beta, rng)
    return x, dict(spectral_beta=beta, stationary="yes" if beta < 1 else "no",
                   nonstationary_kind="none" if beta < 1 else "walk",
                   long_memory="yes" if beta > 0.3 else "no")


@family("D", "mrw", 10, {"gaussian": "no", "stationary": "yes", "long_memory": "yes", "heteroskedastic": "yes",
                        "bursty": "yes", "heavy_tailed": "yes", "linear": "no"}, profiles={"stationary1000": 12})
def mrw(i, rng, T, S):
    """Multifractal random walk increments (Bacry-Delour-Muzy): fGn_H x exp(log-correlated
    volatility); H S[0.3, 0.7], lambda^2 S[0.03, 0.15], integral scale LU[64, 1024];
    odd i on Student-t (nu U[3.5, 8]) innovations. Generated at 8192 and windowed."""
    from ..sources import multifractal as _source
    H = S.draw("H", 0.3, 0.7)
    lam2 = S.draw("lam2", 0.03, 0.15)
    L = int(S.draw("L", 64, 1024, log=True))
    fam = "mrw-lognormal" if i % 2 == 0 else "mrw-student"
    p = dict(H=H, lam2=lam2, L=L)
    if fam == "mrw-student":
        p["df"] = rng.uniform(3.5, 8.0)
    x, _, _ = _source(fam, 8192, p, rng)
    s0 = int(rng.integers(0, 8192 - T))
    return x[s0:s0 + T], dict(hurst_H=H, lam2=lam2, L=L, kind=fam, **({"df": p["df"]} if "df" in p else {}))


@family("D", "discrete-cascade", 8, {"gaussian": "no", "stationary": "yes", "long_memory": "yes",
                                     "heteroskedastic": "yes", "bursty": "yes", "linear": "no", "skewed": "partly"}, profiles={"stationary1000": 10})
def discrete_cascade(i, rng, T, S):
    """Binomial p-model (even i, p S[0.55, 0.68]) or log-Poisson cascade (odd i): fGn x dyadic
    multiplicative volatility, random grid phase."""
    from ..sources import multifractal as _source
    H = rng.uniform(0.3, 0.7)
    if i % 2 == 0:
        p = dict(H=H, b=2, pm=S.draw("pm", 0.55, 0.68))
        fam = "binomial-cascade"
    else:
        p = dict(H=H, b=int(rng.integers(2, 4)), beta=S.draw("beta", 0.6, 0.9), lam=rng.uniform(0.2, 1.0))
        fam = "log-poisson"
    x, _, _ = _source(fam, 8192, p, rng)
    s0 = int(rng.integers(0, 8192 - T))
    return x[s0:s0 + T], dict(kind=fam, hurst_H=H, **{k: v for k, v in p.items() if k != "H"})


@family("D", "lmsv", 4, {"gaussian": "no", "stationary": "yes", "long_memory": "yes", "heteroskedastic": "yes", "linear": "no"})
def lmsv(i, rng, T, S):
    """Long-memory stochastic volatility: fGn_H x exp(s fGn_{Hw}), Hw S[0.75, 0.95], s S[0.3, 0.8]."""
    from ..sources import multifractal as _source
    p = dict(H=rng.uniform(0.3, 0.7), Hw=S.draw("Hw", 0.75, 0.95), sw=S.draw("sw", 0.3, 0.8))
    x, _, _ = _source("lmsv", 8192, p, rng)
    s0 = int(rng.integers(0, 8192 - T))
    return x[s0:s0 + T], dict(hurst_H=p["H"], Hw=p["Hw"], sw=p["sw"])


@family("D", "levy-flight", 6, {"gaussian": "no", "stationary": "no", "nonstationary_kind": "walk",
                               "heavy_tailed": "yes", "linear": "yes", "bursty": "yes"}, profiles={"stationary1000": 0})
def levy_flight(i, rng, T, S):
    """Levy flight: cumulative sum of symmetric alpha-stable increments, alpha S[1.1, 1.9]."""
    al = S.draw("alpha", 1.1, 1.9)
    return np.cumsum(stable_innov(T, al, 0.0, rng)), dict(alpha=al)


@family("D", "mbm", 4, {**LM, "stationary": "no", "nonstationary_kind": "drift"}, profiles={"stationary1000": 0})
def mbm(i, rng, T, S):
    """Multifractional Brownian motion: H(t) sweeps linearly (even i) or sinusoidally (odd i)
    between two values in (0.2, 0.8); built by blending fBm increments of local H."""
    H0, H1 = S.draw("H0", 0.2, 0.8), rng.uniform(0.2, 0.8)
    t = np.arange(T) / T
    Ht = H0 + (H1 - H0) * (t if i % 2 == 0 else 0.5 * (1 - np.cos(2 * np.pi * t)))
    Hgrid = np.linspace(0.2, 0.8, 7)
    incs = np.stack([fgn(T, h, np.random.Generator(np.random.PCG64(int(rng.integers(0, 2**63))))) for h in Hgrid])
    idx = np.clip(np.searchsorted(Hgrid, Ht) - 1, 0, len(Hgrid) - 2)
    w = (Ht - Hgrid[idx]) / (Hgrid[1] - Hgrid[0])
    inc = (1 - w) * incs[idx, np.arange(T)] + w * incs[idx + 1, np.arange(T)]
    return np.cumsum(inc), dict(H0=H0, H1=H1, sweep="linear" if i % 2 == 0 else "sinusoid")


@family("D", "one-over-f-stationary", 0, LM, profiles={"stationary1000": 8})
def one_over_f_stationary(i, rng, T, S):
    """1/f^beta noise by spectral synthesis, beta stratified over [0, 0.95] (the stationary range)."""
    beta = S.draw("beta", 0.0, 0.95)
    return powerlaw_noise(T, beta, rng), dict(spectral_beta=beta, long_memory="yes" if beta > 0.3 else "no")
