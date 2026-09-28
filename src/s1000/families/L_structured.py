"""Class L: structured, composite and coupled processes (long-lag dependence, replayed segments, phase
coupling, coupled systems, mixtures)."""
from __future__ import annotations

import math

import numpy as np
from scipy.integrate import solve_ivp

from ..registry import family
from ..util import add_noise, ar_filter, burn, deterministic_noise_sigma, dominant_period, stable_ar

ST = dict(gaussian="no", stationary="yes")


@family("L", "longlag-comb", 6, {**ST, "linear": "yes", "gaussian": "yes", "reversible": "yes"})
def longlag_comb(i, rng, T, S):
    """Long-lag-only dependence: u_t = e_t + phi u_{t-L} on the innovations (white below L), then a
    random stable AR(p <= 4); L S[40, 160], |phi| S[0.2, 0.35]; odd i use the nonlinear variant
    u_t = e_t + phi (min(u_{t-L}^2, 4) - c) with c ~ its mean (AC(L) ~ 0, dependence present; c = 0.953 is
    approximate: E[min(Z^2, 4)] = 0.921 for standard normal Z, and u is not N(0, 1), so AC(L) is ~0.03 at |phi| = 0.35)."""
    from ..sources import longlag_simulate as _simulate
    L = S.integer("L", 40, 160)
    phi = S.draw("phi", 0.2, 0.35) * rng.choice([-1.0, 1.0])
    p = int(rng.integers(0, 5))
    a = stable_ar(p, rng, 0.5)
    e = rng.standard_normal(T + 3 * L + 500)
    if i % 2 == 0:
        x = _simulate(a, phi, L, e)
        kind = "linear"
    else:
        u = e.copy()
        c = 0.953  # E[min(Z^2, 4)] for standard normal Z
        for t in range(L, u.size):
            u[t] += phi * (min(u[t - L] ** 2, 4.0) - c)
        x = ar_filter(u, a) if p else u
        kind = "quadratic"
    return burn(x, T), dict(L=L, phi=phi, p=p, a=a, kind=kind, linear="yes" if kind == "linear" else "no",
                            gaussian="yes" if kind == "linear" else "no")


@family("L", "cyclostationary-switch", 6, {**ST, "linear": "yes", "gaussian": "yes", "stationary": "partly", "reversible": "no"})
def cyclo_switch(i, rng, T, S):
    """One-sample switch of the dynamics: x_t = phi(t) x_{t-L} + s(t) e_t with phi alternating with
    period P (P = 2 for even i, P in {3, 4} for odd i); equal chain variances so only the correlation switches."""
    L = S.integer("L", 2, 12)
    P = 2 if i % 2 == 0 else int(rng.integers(3, 5))
    mean_phi = rng.uniform(0.25, 0.55) * rng.choice([-1.0, 1.0])
    dphi = rng.uniform(0.3, 0.6)
    phis = [mean_phi + dphi * (k - (P - 1) / 2) / max(1, (P - 1) / 2) * 0.5 for k in range(P)]
    phis = [max(-0.95, min(0.95, ph)) for ph in phis]
    n = T + 500
    e = rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(L, n):
        ph = phis[t % P]
        x[t] = ph * x[t - L] + math.sqrt(1 - ph * ph) * e[t]
    return burn(x, T), dict(L=L, P=P, phis=phis, period_samples=P)


@family("L", "replay-recurrence", 4, {**ST, "linear": "no", "reversible": "no"})
def replay_recurrence(i, rng, T, S):
    """AR(1)-coloured innovations (phi U[0.3, 0.8]) replay 15-30% of their own past in segments of 20-60
    samples copied from random earlier positions, with fresh noise U[0.05, 0.2] SD added."""
    from ..sources import replay_series
    return replay_series(i, T)


@family("L", "pac", 5, {**ST, "linear": "no", "reversible": "no"})
def pac(i, rng, T, S):
    """Phase-amplitude coupling: a fast rhythm whose envelope follows a slow rhythm's phase (theta-gamma
    narrow and broad band, delta-beta, alpha-gamma; noise sigma = 0.8)."""
    from ..sources import pac_series
    from ..registry import profile
    if profile() == "stationary1000" and i == 4:
        # i = 2 and i = 4 would repeat the delta-beta realisation (found 2026-09-26): i = 4 is instead a fifth
        # coupling, sleep slow-oscillation phase -> spindle amplitude
        return pac_series(0, T, systems={"slow-spindle": dict(slow=(100, 140), fast=(7, 9), jitter=0.05)})
    return pac_series(i, T)


@family("L", "qpc", 5, {**ST, "linear": "no", "reversible": "no"})
def qpc(i, rng, T, S):
    """Quadratic phase coupling: three narrowband components with theta3 = theta1 + theta2 + pi/2
    tracked at every instant; complex-OU envelopes with coherence time tau LU[20, 120]."""
    from ..sources import qpc_series
    return qpc_series(i, T)


def _lorenz(t, u, s, r, b):
    x, y, z = u
    return [s * (y - x), x * (r - z) - y, x * y - b * z]


def _coupled_lr(t, u, eps):
    # Lorenz drives Rossler (x-coupling into the Rossler x equation), time-rescaled Lorenz
    xl, yl, zl, xr, yr, zr = u
    dl = [10 * (yl - xl), xl * (28 - zl) - yl, xl * yl - 8 / 3 * zl]
    dr = [-yr - zr + eps * (xl / 8 * 5 - xr), xr + 0.2 * yr, 0.2 + zr * (xr - 5.7)]
    return [0.15 * d for d in dl] + dr


def _coupled_rr(t, u, eps, dw):
    x1, y1, z1, x2, y2, z2 = u
    w1, w2 = 1.0 + dw, 1.0 - dw
    return [-w1 * y1 - z1 + eps * (x2 - x1), w1 * x1 + 0.165 * y1, 0.2 + z1 * (x1 - 10),
            -w2 * y2 - z2 + eps * (x1 - x2), w2 * x2 + 0.165 * y2, 0.2 + z2 * (x2 - 10)]


@family("L", "coupled-systems", 8, {**ST, "linear": "no", "deterministic": "yes", "chaotic": "yes", "reversible": "no"})
def coupled_systems(i, rng, T, S):
    """Coupled chaotic systems, coupling stratified across the synchronisation transition: Lorenz ->
    Rossler unidirectional (observe the slave), two bidirectionally coupled Rosslers with a frequency
    mismatch (phase synchronisation), coupled logistic maps, master-slave with delay (full profile), and in
    stationary1000 a Kaneko coupled map lattice (one site of a ring of 100 diffusively coupled logistic maps
    x -> 1 - a x^2) in two regimes: spatiotemporal intermittency (i=5) and fully developed turbulence (i=6)."""
    from ..registry import profile as _prof
    kind = (["lorenz-rossler", "lorenz-rossler", "rossler-rossler", "rossler-rossler", "rossler-rossler",
             "cml-intermittency", "cml-turbulence", "lorenz-rossler"] if _prof() == "stationary1000"
            else ["lorenz-rossler", "lorenz-rossler", "rossler-rossler", "rossler-rossler", "coupled-logistic",
                  "coupled-logistic", "delayed-master-slave", "lorenz-rossler"])[i]
    eps = S.draw("coupling", 0.02, 1.0, log=True)
    ppp = S.integer("ppp", 15, 40)
    if kind in ("lorenz-rossler", "rossler-rossler"):
        f = _coupled_lr if kind == "lorenz-rossler" else _coupled_rr
        args = (eps,) if kind == "lorenz-rossler" else (eps, 0.02)
        x0 = np.array([1, 1, 20, 1, 1, 0.0] if kind == "lorenz-rossler" else [1, 1, 0, -1, 1, 0.0]) + 0.1 * rng.standard_normal(6)
        tp = np.arange(0, 600, 0.02)
        sp = solve_ivp(f, (0, tp[-1]), x0, t_eval=tp, method="DOP853", rtol=1e-8, atol=1e-10, args=args)
        y = sp.y[3, tp.size // 3:]
        per = dominant_period(y) * 0.02
        dt_obs = per / ppp
        n_burn = 30 * ppp
        te = np.arange(n_burn + T) * dt_obs
        sol = solve_ivp(f, (0, te[-1]), sp.y[:, -1], t_eval=te, method="DOP853", rtol=1e-8, atol=1e-10, args=args)
        x = sol.y[3, n_burn:]
        observed = "x"
        from ..registry import profile as _p
        from .G_flows import _periodicity
        if _p() == "stationary1000" and _periodicity(x) > 0.95:  # phase-coherent Rossler x: observe its z spikes
            x, observed = sol.y[5, n_burn:], "z"
        par = dict(coupling=eps, ppp=ppp, period_samples=ppp, continuous_time="yes", observed=observed)
    elif kind == "coupled-logistic":
        c = eps * 0.5
        r = rng.uniform(3.7, 4.0)
        u, v = rng.uniform(0.2, 0.8, 2)
        x = np.empty(T + 500)
        for t in range(T + 500):
            fu, fv = r * u * (1 - u), r * v * (1 - v)
            u, v = (1 - c) * fu + c * fv, (1 - c) * fv + c * fu
            x[t] = v
        x = x[500:]
        par = dict(coupling=c, r=r)
    elif kind.startswith("cml-"):  # Kaneko (1989) diffusive CML; regime bounds mapped over seeds (2026-09-26)
        a, eps = ((rng.uniform(1.78, 1.82), 0.3) if kind == "cml-intermittency"
                  else (rng.uniform(1.95, 2.0), rng.uniform(0.03, 0.08)))
        L, site = 100, 0
        u = rng.uniform(-1, 1, L)
        x = np.empty(T + 5000)
        for t in range(x.size):
            f = 1 - a * u * u
            u = (1 - eps) * f + 0.5 * eps * (np.roll(f, 1) + np.roll(f, -1))
            x[t] = u[site]
        x = x[5000:]
        par = dict(coupling=eps, a=a, lattice_size=L)
    else:
        d = int(rng.integers(5, 40))
        r = 3.99 if _prof() == "stationary1000" else 3.9
        master = np.empty(T + 500 + d)
        m = rng.uniform(0.2, 0.8)
        for t in range(master.size):
            m = r * m * (1 - m)
            master[t] = m
        x = np.empty(T + 500)
        s_ = rng.uniform(0.2, 0.8)
        for t in range(T + 500):
            s_ = (1 - eps) * r * s_ * (1 - s_) + eps * master[t]
            x[t] = s_
        x = x[500:]
        par = dict(coupling=eps, delay=d, r=r)
    from ..registry import profile
    if profile() == "stationary1000" and np.unique(np.round(x, 12)).size < 100:
        raise RuntimeError("synchronised onto a periodic orbit: redrawn in the stationary profile")
    sig = deterministic_noise_sigma(rng)
    return add_noise(x, sig, rng), dict(kind=kind, **par, noise_sigma=sig, measurement_noise="yes" if sig > 0 else "no",
                                        deterministic="partly" if sig > 0 else "yes")


@family("L", "mixture", 6, {**ST, "linear": "no", "deterministic": "partly", "chaotic": "partly"})
def mixture(i, rng, T, S):
    """Additive mixtures: Lorenz + AR(1) (ratio S[0.3, 3]); Lorenz under a heavy noise floor
    (SNR <= 0 dB); Rossler + a seasonal AR; sum of two independent processes of different kinds."""
    kind = ["lorenz+ar", "lorenz-floor", "rossler+seasonal", "lorenz+ar", "lorenz-floor", "ar+telegraph"][i]
    ratio = S.draw("ratio", 0.3, 3.0, log=True)
    ppp = int(rng.integers(15, 41))
    tp = np.arange(0, (30 * ppp + T) * 0.75 / ppp, 0.75 / ppp)
    if kind.startswith("lorenz"):
        sol = solve_ivp(_lorenz, (0, tp[-1]), [1.0 + rng.uniform(), 1.0, 20.0], t_eval=tp, method="DOP853",
                        rtol=1e-8, atol=1e-10, args=(10.0, 28.0, 8 / 3))
        d = sol.y[0, -T:]
    elif kind.startswith("rossler"):
        f = lambda t, u: [-u[1] - u[2], u[0] + 0.2 * u[1], 0.2 + u[2] * (u[0] - 5.7)]
        tp = np.arange(0, (30 * ppp + T) * 6.1 / ppp, 6.1 / ppp)
        sol = solve_ivp(f, (0, tp[-1]), [1.0 + rng.uniform(), 1.0, 0.0], t_eval=tp, method="DOP853", rtol=1e-8, atol=1e-10)
        d = sol.y[0, -T:]
    else:
        d = None
    if kind == "lorenz+ar":
        phi = rng.uniform(0.5, 0.95)
        s = burn(ar_filter(rng.standard_normal(T + 500) * math.sqrt(1 - phi**2), [phi]), T)
        x = (d - d.mean()) / d.std() + ratio * s
        par = dict(phi=phi, ratio=ratio)
    elif kind == "lorenz-floor":
        snr_db = rng.uniform(-6, 0)
        s = 10 ** (-snr_db / 20)
        x = (d - d.mean()) / d.std() + s * rng.standard_normal(T)
        par = dict(snr_db=snr_db, measurement_noise="yes", noise_sigma=s)
    elif kind == "rossler+seasonal":
        P = rng.uniform(20, 80)
        s = np.sin(2 * np.pi * np.arange(T) / P) + 0.3 * rng.standard_normal(T)
        x = (d - d.mean()) / d.std() + ratio * s
        par = dict(period_samples=P, ratio=ratio)
    else:
        phi = rng.uniform(0.5, 0.95)
        s = burn(ar_filter(rng.standard_normal(T + 500) * math.sqrt(1 - phi**2), [phi]), T)
        rate = rng.uniform(0.01, 0.1)
        tg = np.cumprod(np.where(rng.uniform(size=T) < rate, -1.0, 1.0))
        x = s + ratio * tg
        par = dict(phi=phi, rate=rate, ratio=ratio, deterministic="no", chaotic="na", regime_switching="yes")
    return x, dict(kind=kind, ppp=ppp, **par)


@family("L", "on-off", 0, {**ST, "linear": "no", "bursty": "yes", "event_like": "partly", "skewed": "yes", "reversible": "no"},
        profiles={"stationary1000": 3})
def on_off(i, rng, T, S):
    """On-off intermittency (Platt, Spiegel & Tresser 1993; Heagy, Platt & Hammel 1994): a logistic
    response x_{n+1} = a xi_n x_n (1 - x_n) driven by a chaotic signal xi_n that is exactly uniform on
    [0, 1] (the r = 4 logistic map through its conjugacy to the tent map). The invariant state x = 0
    loses transverse stability at a = e; just above it the response idles near zero and bursts."""
    a = S.draw("a", 2.9, 3.2)  # nearer a_c = e the laminar (off) phases outgrow the record
    z = rng.uniform(0.1, 0.9)
    x = rng.uniform(0.01, 0.1)
    n = T + 2000
    out = np.empty(n)
    for t in range(n):
        z = 4 * z * (1 - z)
        if z <= 0.0 or z >= 1.0:  # the float r = 4 orbit can land on 0 or 1: nudge it back
            z = rng.uniform(0.1, 0.9)
        xi = (2 / math.pi) * math.asin(math.sqrt(z))
        x = a * xi * x * (1 - x) + 1e-12  # a floor far below the bursts keeps x = 0 from absorbing
        out[t] = x
    return out[2000:], dict(a=a, a_critical=math.e, deterministic="yes", chaotic="yes")
