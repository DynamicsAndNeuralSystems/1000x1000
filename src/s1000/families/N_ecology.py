"""Class N, ecology and epidemiology (12)."""
from __future__ import annotations

import math

import numpy as np

from ..registry import family

ECO = dict(domain="ecology", linear="no", gaussian="no", stationary="yes", discrete_valued="partly", skewed="yes")  # integer counts with many levels


def _gillespie(rates_fn, x0, updates, t_end, sample_dt, rng, max_events=2_000_000):
    """Generic SSA sampled on a fixed grid. rates_fn(x) -> array of propensities; updates[k] is
    the state change for reaction k."""
    x = np.array(x0, dtype=float)
    n_out = int(t_end / sample_dt)
    out = np.empty((n_out, x.size))
    t, j, nxt = 0.0, 0, 0.0
    for _ in range(max_events):
        r = rates_fn(x)
        tot = r.sum()
        tau = rng.exponential(1 / tot) if tot > 0 else 1e18
        while nxt < t + tau and j < n_out:
            out[j] = x
            j += 1
            nxt += sample_dt
        if j >= n_out:
            break
        t += tau
        k = int(np.searchsorted(np.cumsum(r), rng.uniform() * tot))
        x = x + updates[min(k, len(updates) - 1)]
    while j < n_out:
        out[j] = x
        j += 1
    return out


@family("N", "predator-prey-ssa", 3, {**ECO, "periodic": "partly", "reversible": "no"})
def predator_prey_ssa(i, rng, T, S):
    """Stochastic Lotka-Volterra (i<2) or Rosenzweig-MacArthur (i=2) predator-prey by Gillespie SSA;
    population scale stratified so demographic noise is visible; prey series sampled at fixed intervals."""
    from ..registry import profile
    scale = S.draw("scale", 200, 800, log=True) if profile() == "stationary1000" else S.draw("scale", 50, 400, log=True)
    if i < 2:
        a, b, c, d = 1.0, 1.0 / scale, 1.0 / scale, 1.0

        def rates(x):
            N, P = x
            return np.array([a * N + 0.5, b * N * P, c * N * P + 0.05, d * P])  # small immigration
        updates = [np.array([1, 0]), np.array([-1, 0]), np.array([0, 1]), np.array([0, -1])]
        from ..registry import profile
        sdt = 0.25 if profile() == "stationary1000" else 0.1  # coarser sampling: ~2.5x the cycles per record
        out = _gillespie(rates, [int(scale), int(scale * 0.8)], updates, T * sdt, sdt, rng)
        return out[:, 0], dict(kind="lotka-volterra", scale=scale)
    r, K, a, h, e, m = 1.0, 4 * scale, 1.0 / scale, 1.0, 0.5, 0.2

    def rates(x):
        N, P = x
        att = a * N * P / (1 + a * h * N)
        return np.array([r * N + 0.5, r * N * N / K, att, e * att + 0.05, m * P])  # small immigration
    updates = [np.array([1, 0]), np.array([-1, 0]), np.array([-1, 0]), np.array([0, 1]), np.array([0, -1])]
    out = _gillespie(rates, [int(scale), int(scale * 0.3)], updates, T * 0.2, 0.2, rng)
    return out[:, 0], dict(kind="rosenzweig-macarthur", scale=scale)


@family("N", "blowflies-ricker", 4, {**ECO, "discrete_valued": "no", "reversible": "no"})
def blowflies_ricker(i, rng, T, S):
    """Nicholson's blowflies (delayed feedback N' = P N(t - tau) exp(-N(t - tau)/N0) - delta N, i<2,
    P stratified over the cycling regime; limit cycles, not chaos, at these parameters) and the Ricker map with environmental noise (i>=2)."""
    if i < 2:
        from .G_flows import _dde
        from ..registry import profile
        if profile() == "stationary1000":  # Gurney, Blythe & Nisbet (1980) parameters: a large, sharp-peaked limit cycle (lambda ~ 0; checked 2026-09-26)
            P = S.draw("P", 6.0, 12.0)
            delta, N0, tau, span = 0.175, 100.0, 15.0, 1.0
            if i == 1:  # a longer delay gives the double-peaked cycle, distinct from i = 0 (review 2026-09-25)
                P = rng.uniform(25.0, 35.0)
                delta, tau, span = 0.25, 20.0, 1.5
        else:
            P = S.draw("P", 4.0, 15.0)
            delta, N0, tau, span = 0.5, 100.0, 8.0, 0.5
        f = lambda n, nd: P * nd * math.exp(-nd / N0) - delta * n
        dt = 0.05
        xf = _dde(f, tau, dt, int(T * span / dt), 100.0, int(400 / dt), rng)
        x = xf[:: max(1, int(round(span / dt)))][:T]
        return x * (1 + 0.02 * rng.standard_normal(T)), dict(kind="nicholson", P=P, tau=tau, continuous_time="yes",
                                                             **({"delta": delta, "N0": N0} if profile() == "stationary1000" else {}))
    r = S.draw("r", 1.8, 3.2)
    sig = rng.uniform(0.05, 0.3)
    x = np.empty(T + 300)
    v = 1.0
    for t in range(x.size):
        v = v * math.exp(r * (1 - v) + sig * rng.standard_normal())
        x[t] = v
    return x[300:], dict(kind="ricker-env", r=r, sigma=sig, chaotic="partly")


@family("N", "sir-seir", 4, {**ECO, "bursty": "yes", "regime_switching": "partly", "reversible": "no"}, profiles={"stationary1000": 6})
def sir_seir(i, rng, T, S):
    """Seasonally forced stochastic SIR (even i) / SEIR (odd i) with births, deaths and immigration
    (Gillespie; weekly case counts): measles-like multi-annual epidemics, fade-outs and reintroduction."""
    R0 = S.draw("R0", 1.5, 15.0, log=True)
    N = int(rng.choice([50_000, 200_000, 1_000_000]))
    gamma = 1 / 13.0  # per day
    sigma = 1 / 8.0
    mu = 1 / (50 * 365)
    beta0 = R0 * gamma
    amp = rng.uniform(0.1, 0.3)
    imm = 2.0 / 365
    seir = i % 2 == 1
    day = [0.0]
    cases = [0]

    def rates(x):
        Sx, Ex, Ix, Rx = x
        b = beta0 * (1 + amp * math.cos(2 * math.pi * day[0] / 365))
        return np.array([b * Sx * Ix / N + imm * Sx / N * 100, sigma * Ex if seir else 0.0, gamma * Ix, mu * N, mu * (Sx + Ex + Ix + Ru(Rx))])

    def Ru(r):
        return r
    inf = np.array([-1, 1, 0, 0]) if seir else np.array([-1, 0, 1, 0])
    updates = [inf, np.array([0, -1, 1, 0]), np.array([0, 0, -1, 1]), np.array([1, 0, 0, 0]), np.array([0, 0, 0, -1])]
    # custom loop to count incident cases per week
    x = np.array([N / R0, 0 if not seir else 20, 20, N - N / R0 - 20], dtype=float)
    from ..registry import profile
    stat = profile() == "stationary1000"
    bin_days = 14.0 if stat else 7.0          # fortnightly counts: twice the epidemics per record
    burn_bins = int(5 * 365 / bin_days) if stat else 0   # five years discarded: no initial-epidemic artefact
    t, week, nxt = 0.0, 0, bin_days
    out = np.empty(T)
    cnt = 0
    for _ in range(20_000_000):
        day[0] = t
        r = rates(x)
        tot = r.sum()
        tau = rng.exponential(1 / tot) if tot > 0 else 1e9
        while t + tau >= nxt and week < T + burn_bins:
            if week >= burn_bins:
                out[week - burn_bins] = cnt
            cnt, week, nxt = 0, week + 1, nxt + bin_days
        if week >= T + burn_bins:
            break
        t += tau
        k = int(np.searchsorted(np.cumsum(r), rng.uniform() * tot))
        k = min(k, 4)
        x = np.maximum(x + updates[k], 0)
        if k == (1 if seir else 0):
            cnt += 1
    if week < T + burn_bins:
        out[max(0, week - burn_bins):] = 0.0
    return out, dict(kind="seir" if seir else "sir", R0=R0, N=N, amplitude=amp, period_samples=365.25 / bin_days, event_like="partly")


@family("N", "logistic-extinction", 1, {**ECO, "regime_switching": "yes", "reversible": "no"}, profiles={"stationary1000": 0})
def logistic_extinction(i, rng, T, S):
    """Logistic growth with demographic noise, extinction at zero and Poisson recolonisation."""
    r, K, imm = 0.3, 30.0, 0.01
    n = 0
    x = np.empty(T)
    for t in range(T):
        births = rng.poisson(r * n) if n > 0 else 0
        deaths = rng.poisson(r * n * n / K) if n > 0 else 0
        n = max(0, n + births - deaths)
        if n == 0 and rng.uniform() < imm:
            n = 2
        x[t] = n
    return x, dict(r=r, K=K, immigration=imm, event_like="partly")
