"""Class N, physics and engineering (16) and economics and social (5)."""
from __future__ import annotations

import math

import numpy as np
from scipy import signal

from ..registry import family
from ..util import ar_filter, burn, em_sde, rk4

ENG = dict(domain="engineering", linear="no", gaussian="no", stationary="yes")
ECON = dict(domain="economics", linear="no", gaussian="no")


@family("N", "onoff-traffic", 3, {**ENG, "long_memory": "yes", "discrete_valued": "partly", "bursty": "yes", "reversible": "yes"})
def onoff_traffic(i, rng, T, S):
    """Aggregated ON/OFF sources with heavy-tailed (Pareto, tail S[1.5, 1.9]) ON and OFF periods
    (Willinger et al.): self-similar packet counts per bin."""
    from ..registry import profile
    a = S.draw("tail", 1.5, 1.9)  # H = (3 - a)/2 <= 0.75
    n_src = int(rng.integers(150, 400)) if profile() == "stationary1000" else int(rng.integers(20, 100))
    x = np.zeros(T)
    stat = profile() == "stationary1000"
    for _ in range(n_src):
        t = -rng.pareto(a) * 10
        on = rng.uniform() < 0.5
        amp = rng.uniform(0.5, 1.5) if stat else 1.0  # continuous source rates: real-valued aggregate
        while t < T:
            L = (1 + rng.pareto(a)) * (2 if stat else 5)
            if on and t + L > 0:  # (a period ending before t = 0 used to give a negative slice end)
                a0, b0 = max(0, int(t)), min(T, int(math.ceil(t + L)))
                x[a0:b0] += amp
            t += L
            on = not on
    return x, dict(tail=a, n_sources=n_src, hurst_H=(3 - a) / 2)


def _rosenberg(n, oq=0.6):
    t = np.linspace(0, 1, n, endpoint=False)
    g = np.where(t < oq, 3 * (t / oq) ** 2 - 2 * (t / oq) ** 3, 0.0)
    return np.gradient(g)


@family("N", "speech", 3, {**ENG, "regime_switching": "yes", "reversible": "no"})
def speech(i, rng, T, S):
    """Source-filter speech: a glottal pulse train (Rosenberg pulses with jitter and shimmer) or
    noise, through a slowly time-varying all-pole vocal-tract filter, with voiced/unvoiced switching;
    8 kHz equivalent, ~125 ms of signal."""
    f0 = S.draw("f0", 90.0, 250.0, log=True)
    fs = 8000.0
    n = T + 400
    src = np.zeros(n)
    t = 0.0
    voiced = True
    seg_end = int(rng.uniform(200, 600))
    while int(t) < n:
        if int(t) >= seg_end:
            voiced = not voiced or rng.uniform() < 0.7
            seg_end = int(t) + int(rng.uniform(200, 600))
        if voiced:
            P = fs / f0 * (1 + 0.02 * rng.standard_normal())
            pulse = _rosenberg(int(P)) * (1 + 0.1 * rng.standard_normal())
            a0, b0 = int(t), min(n, int(t) + pulse.size)
            src[a0:b0] += pulse[: b0 - a0]
            t += P
        else:
            a0, b0 = int(t), min(n, int(t) + 80)
            src[a0:b0] += 0.02 * rng.standard_normal(b0 - a0)
            t += 80
    formants = np.array([rng.uniform(300, 800), rng.uniform(900, 1800), rng.uniform(2200, 3000)])
    bw = np.array([80.0, 100.0, 150.0])
    out = src.copy()
    y = np.zeros(n)
    # slowly varying formants: recompute the filter every 100 samples
    for s in range(0, n, 100):
        drift = 1 + 0.15 * np.sin(2 * np.pi * s / n * rng.uniform(1, 3) + rng.uniform(0, 6.28))
        seg = out[s:s + 100]
        for F, B in zip(formants * drift, bw):
            r = math.exp(-math.pi * B / fs)
            a = [1, -2 * r * math.cos(2 * math.pi * F / fs), r * r]
            seg = signal.lfilter([1 - r], a, seg)
        y[s:s + 100] = seg
    return burn(y, T), dict(f0=f0, formants=formants, period_samples=fs / f0, periodic="partly", bursty="partly")


@family("N", "bearing-vibration", 2, {**ENG, "event_like": "partly", "periodic": "partly", "reversible": "no"})
def bearing_vibration(i, rng, T, S):
    """Rotating-machine vibration with a bearing fault: a jittered impulse train at the fault
    frequency (period S[15, 60] samples) exciting a resonance (Q S[5, 30]) plus broadband noise."""
    P = S.draw("fault_period", 15, 60, log=True)
    Q = S.draw("Q", 5, 30, log=True)
    fr = rng.uniform(0.1, 0.35)
    n = T + 500
    imp = np.zeros(n)
    t = rng.uniform(0, P)
    while t < n:
        imp[int(t)] += rng.uniform(0.7, 1.3)
        t += P * (1 + 0.02 * rng.standard_normal())
    r = math.exp(-math.pi * fr / Q)
    a = [1, -2 * r * math.cos(2 * math.pi * fr), r * r]
    x = signal.lfilter([1 - r], a, imp)
    x = x / x.std()
    noise = rng.uniform(0.1, 0.5)  # (drawn before the noise itself, as before)
    from ..registry import profile as _pp
    return burn(x, T) + noise * rng.standard_normal(T), dict(fault_period=P, Q=Q, resonance=fr, period_samples=P, measurement_noise="yes",
                                                           **({"noise_sd": noise} if _pp() == "stationary1000" else {}))


@family("N", "collective", 3, {**ENG, "reversible": "partly"})
def collective(i, rng, T, S):
    """Collective dynamics: Kuramoto ensemble (N = 100) order parameter r(t) with coupling stratified
    across the synchronisation transition (i<2), and 2-D Ising magnetisation (Metropolis, 32 x 32)
    with T/T_c S[1.03, 1.4], the disordered side (i=2)."""
    if i < 2:
        N = 100
        K = S.draw("K", 0.5, 3.0)
        w = rng.standard_normal(N)
        th = rng.uniform(0, 2 * np.pi, N)
        dt, k = 0.05, 4
        out = np.empty(T)
        for s in range(T * k + 2000):
            z = np.mean(np.exp(1j * th))
            th = th + dt * (w + K * abs(z) * np.sin(np.angle(z) - th)) + 0.2 * math.sqrt(dt) * rng.standard_normal(N)
            if s >= 2000 and (s - 2000) % k == 0:
                out[(s - 2000) // k] = abs(z)
        return out, dict(kind="kuramoto", K=K, N=N, continuous_time="yes")
    L = 32
    Tc = 2 / math.log(1 + math.sqrt(2))
    Temp = S.draw("T_over_Tc", 1.03, 1.4) * Tc  # paramagnetic side: finite correlation length and time
    spins = rng.choice([-1, 1], (L, L))
    out = np.empty(T)
    for s in range(T + 200):
        for _ in range(L * L):
            a, b = rng.integers(0, L, 2)
            nb = spins[(a + 1) % L, b] + spins[a - 1, b] + spins[a, (b + 1) % L] + spins[a, b - 1]
            dE = 2 * spins[a, b] * nb
            if dE <= 0 or rng.uniform() < math.exp(-dE / Temp):
                spins[a, b] *= -1
        if s >= 200:
            out[s - 200] = spins.mean()
    return out, dict(kind="ising", T_over_Tc=Temp / Tc, L=L, regime_switching="partly", long_memory="partly")


@family("N", "laser-feedback", 2, {**ENG, "bursty": "yes", "event_like": "partly", "continuous_time": "yes", "reversible": "no"})
def laser_feedback(i, rng, T, S):
    """Lang-Kobayashi semiconductor laser with delayed optical feedback in the low-frequency-
    fluctuation regime: intensity dropouts. Dimensionless form; feedback strength stratified."""
    from collections import deque
    kappa = S.draw("kappa", 0.08, 0.2)
    alpha, tau, P, Tn, w0tau = 4.0, 1000.0, 1.0, 1000.0, rng.uniform(0, 2 * np.pi)
    dt = 0.05
    m = int(round(tau / dt))
    hist = deque([0.1 * (1 + 0j)] * (m + 1), maxlen=m + 1)
    E, Nn = 0.1 + 0j, 0.0
    fb = kappa * np.exp(-1j * w0tau)
    sub = 400  # observation every 20 time units
    n_steps = sub * T + 20 * m
    out = np.empty(T)

    def rhs(E, Nn, Ed):
        return 0.5 * (1 + 1j * alpha) * Nn * E + fb * Ed, (P - Nn - (1 + Nn) * abs(E) ** 2) / Tn
    for s in range(n_steps):
        Ed = hist[0]
        k1E, k1N = rhs(E, Nn, Ed)
        k2E, k2N = rhs(E + dt * k1E, Nn + dt * k1N, Ed)
        E = E + 0.5 * dt * (k1E + k2E) + 1e-3 * math.sqrt(dt) * (rng.standard_normal() + 1j * rng.standard_normal())
        Nn = Nn + 0.5 * dt * (k1N + k2N)
        hist.append(E)
        if s >= 20 * m and (s - 20 * m) % sub == 0:
            out[(s - 20 * m) // sub] = abs(E) ** 2
    from ..registry import profile as _pp
    return out, dict(kappa=kappa, alpha=alpha, **({"w0tau": w0tau} if _pp() == "stationary1000" else {}))


@family("N", "oregonator", 2, {**ENG, "continuous_time": "yes", "periodic": "partly", "reversible": "no"})
def oregonator(i, rng, T, S):
    """Belousov-Zhabotinsky reaction (Oregonator, Tyson scaling): relaxation oscillations, f S[0.6, 1.4]
    (inside the oscillatory range, about 0.52 < f < 2.4); observe log(x) (HBrO2)."""
    from ..util import flow_series
    f_ = S.draw("f", 0.6, 1.4)
    eps, q = 0.04, 0.0008

    def rhs(t, u):
        x, y, z = u
        return [(q * y - x * y + x * (1 - x)) / eps, (-q * y - x * y + f_ * z) / 0.0004, x - z]
    ppp = int(rng.integers(15, 41))
    x, per = flow_series(rhs, [0.1, 0.1, 0.1], T, ppp, coord=0, t_probe=60.0, rtol=1e-7, method="LSODA")
    from ..registry import profile as _pp
    return np.log(np.clip(x, 1e-9, None)), dict(f=f_, period_time=per, skewed="yes", **({"ppp": ppp, "period_samples": float(ppp)} if _pp() == "stationary1000" else {}))


@family("N", "nagel-schreckenberg", 1, {**ENG, "discrete_valued": "yes", "bursty": "yes", "reversible": "no"}, profiles={"stationary1000": 0})
def nagel_schreckenberg(i, rng, T, S):
    """Nagel-Schreckenberg traffic cellular automaton (v_max = 5, p = 0.3): the count of cars passing
    a fixed detector per 5 time steps, at a density near the jamming transition."""
    L, vmax, p = 500, 5, 0.3
    rho = 0.17
    n_cars = int(rho * L)
    pos = np.sort(rng.choice(L, n_cars, replace=False))
    vel = rng.integers(0, vmax + 1, n_cars)
    out = np.zeros(T)
    det = L // 2
    for s in range(5 * T + 500):
        gaps = (np.roll(pos, -1) - pos - 1) % L
        vel = np.minimum(vel + 1, vmax)
        vel = np.minimum(vel, gaps)
        vel = np.where(rng.uniform(size=n_cars) < p, np.maximum(vel - 1, 0), vel)
        new = (pos + vel) % L
        passed = ((pos <= det) & (pos + vel > det)).sum()
        pos = new
        if s >= 500:
            out[(s - 500) // 5] += passed
    return out, dict(density=rho, p=p, L=L)


@family("N", "finance-sde", 2, {**ECON, "stationary": "no", "nonstationary_kind": "walk", "continuous_time": "yes"}, profiles={"stationary1000": 0})
def finance_sde(i, rng, T, S):
    """Geometric Brownian motion (Black-Scholes price path, i=0) and the Heston model (price with
    stochastic variance, i=1); daily sampling over ~4 years."""
    dt = 1 / 252
    if i == 0:
        mu, sig = S.draw("mu", -0.1, 0.2), rng.uniform(0.1, 0.5)
        r = (mu - 0.5 * sig**2) * dt + sig * math.sqrt(dt) * rng.standard_normal(T)
        return 100 * np.exp(np.cumsum(r)), dict(kind="gbm", mu=mu, sigma=sig, linear="yes", gaussian="partly")
    kappa, theta, xi, rho = 3.0, 0.04, S.draw("xi", 0.2, 0.8), -0.7
    v, s = theta, 100.0
    out = np.empty(T)
    for t in range(T):
        z1 = rng.standard_normal()
        z2 = rho * z1 + math.sqrt(1 - rho**2) * rng.standard_normal()
        v = max(v + kappa * (theta - v) * dt + xi * math.sqrt(max(v, 0) * dt) * z2, 1e-6)
        s *= math.exp(-0.5 * v * dt + math.sqrt(v * dt) * z1)
        out[t] = s
    return out, dict(kind="heston", xi=xi, heteroskedastic="yes", heavy_tailed="yes")


@family("N", "agent-market", 3, {**ECON, "stationary": "partly", "regime_switching": "yes", "reversible": "no"}, profiles={"stationary1000": 0})
def agent_market(i, rng, T, S):
    """Kirman herding (ants) model: the fraction of agents in one state, with recruitment and
    spontaneous conversion (i<2; epsilon stratified so the marginal runs from unimodal to bimodal
    with bursty switches); zero-intelligence order flow (i=2): mid-price from random limit orders."""
    if i < 2:
        N = 100
        eps = S.draw("epsilon", 0.002, 0.05, log=True)
        k = 0.5
        n1 = N // 2
        out = np.empty(T)
        for t in range(T):
            for _ in range(N):
                p_up = (N - n1) / N * (eps + k * n1 / (N - 1))
                p_dn = n1 / N * (eps + k * (N - n1) / (N - 1))
                u = rng.uniform()
                if u < p_up:
                    n1 = min(N, n1 + 1)
                elif u < p_up + p_dn:
                    n1 = max(0, n1 - 1)
            out[t] = n1 / N
        return out, dict(kind="kirman", epsilon=eps, N=N, bursty="yes")
    bids, asks = [99.0], [101.0]
    mid = np.empty(T)
    for t in range(T):
        for _ in range(20):
            side = rng.uniform() < 0.5
            best_bid, best_ask = max(bids) if bids else 99.0, min(asks) if asks else 101.0
            if rng.uniform() < 0.3:  # market order
                if side and asks:
                    asks.remove(min(asks))
                elif (not side) and bids:
                    bids.remove(max(bids))
            else:  # limit order placed within a spread-relative band
                if side:
                    bids.append(round(best_ask - rng.exponential(1.0), 2))
                else:
                    asks.append(round(best_bid + rng.exponential(1.0), 2))
            if rng.uniform() < 0.2:  # cancellation
                if side and bids and len(bids) > 1:
                    bids.remove(bids[int(rng.integers(len(bids)))])
                elif (not side) and asks and len(asks) > 1:
                    asks.remove(asks[int(rng.integers(len(asks)))])
        if not bids:
            bids.append((min(asks) if asks else 100.0) - 1)
        if not asks:
            asks.append(max(bids) + 1)
        mid[t] = 0.5 * (max(bids) + min(asks))
    return mid, dict(kind="zero-intelligence", stationary="no", nonstationary_kind="walk")


@family("N", "kirman", 0, {**ECON, "stationary": "yes", "regime_switching": "yes", "reversible": "no", "bursty": "yes"}, profiles={"stationary1000": 3})
def kirman(i, rng, T, S):
    """Kirman herding (ants) model: fraction of agents in one state, recruitment k = 0.5 and spontaneous
    conversion epsilon LU[0.01, 0.05] (unimodal to bimodal with bursty switches)."""
    N = 300
    eps = S.draw("epsilon", 0.01, 0.05, log=True)
    k = 0.5
    n1 = N // 2
    out = np.empty(T)
    for t in range(T):
        for _ in range(3 * N):  # three sweeps per sample: faster switching relative to the record
            p_up = (N - n1) / N * (eps + k * n1 / (N - 1))
            p_dn = n1 / N * (eps + k * (N - n1) / (N - 1))
            u = rng.uniform()
            if u < p_up:
                n1 = min(N, n1 + 1)
            elif u < p_up + p_dn:
                n1 = max(0, n1 - 1)
        out[t] = n1 / N
    return out, dict(epsilon=eps, N=N)
