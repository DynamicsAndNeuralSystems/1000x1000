"""Class I: noise-driven continuous-time dynamics (SDEs), Euler-Maruyama at fine dt, subsampled."""
from __future__ import annotations

import math

import numpy as np

from ..registry import family
from ..util import em_sde

SDE = dict(continuous_time="yes", linear="no", gaussian="no", stationary="yes", reversible="partly")


@family("I", "ou", 12, {**SDE, "linear": "yes", "gaussian": "yes", "reversible": "yes"}, profiles={"stationary1000": 16})
def ou(i, rng, T, S):
    """Ornstein-Uhlenbeck subsampled: correlation time tau LU[1, 20] samples (>= 50 correlation times per record)."""
    tau = S.draw("tau", 1.0, 20.0, log=True)
    dt = min(0.1, tau / 20)
    k = max(1, int(round(1 / dt)))
    dt = 1.0 / k
    out = em_sde(lambda x: -x / tau, lambda x: math.sqrt(2 / tau), [0.0], dt, T * k, rng, obs_every=k,
                 burn_steps=int(10 * tau * k))
    return out[:, 0], dict(tau=tau, timescale_samples=tau)


@family("I", "double-well", 12, {**SDE, "regime_switching": "yes"}, profiles={"stationary1000": 20})
def double_well(i, rng, T, S):
    """Langevin in V = x^4/4 - x^2/2: dx = (x - x^3) dt + sigma dW; sigma S[0.5, 1.1]: >= ~30 hops
    per record."""
    sig = S.draw("sigma", 0.5, 1.1)  # >= ~30 hops per record
    k = 10
    dt = 0.05
    out = em_sde(lambda x: x - x**3, lambda x: sig, [1.0], dt, T * k, rng, obs_every=k, burn_steps=2000)
    x = out[:, 0]
    hops = int(np.sum(np.diff(np.sign(x)) != 0))
    return x, dict(sigma=sig, hops=hops, bursty="yes" if hops < 15 else "no")


@family("I", "near-critical", 12, {**SDE}, profiles={"stationary1000": 18})
def near_critical(i, rng, T, S):
    """Normal forms with noise, kappa = mu/eta stratified over near (-0.15..-0.01) and far (-3..-1):
    pitchfork, radial Hopf (reflected), planar Hopf (omega drawn, observe x), saddle-node, transcritical."""
    kind = S.choice("kind", ["pitchfork", "hopf-radial", "hopf-planar", "saddle-node", "transcritical"])
    near = i % 2 == 0
    kappa = S.draw("kappa_near", -0.15, -0.01) if near else S.draw("kappa_far", -3.0, -1.0)
    # observation interval chosen so the linear relaxation time 1/|kappa| is ~25 samples: a slow
    # near-critical mode is observed more coarsely, so every record holds ~40 relaxation times
    dt = 0.01
    k = int(np.clip(round((1 / abs(kappa)) / 25 / dt), 1, 400))
    if kind == "pitchfork":
        out = em_sde(lambda x: kappa * x - x**3, lambda x: 1.0, [0.0], dt, T * k, rng, k, 5000)
        x = out[:, 0]
    elif kind == "hopf-radial":
        def drift(r):
            return kappa * r - r**3
        out = em_sde(drift, lambda r: 1.0, [0.5], dt, T * k, rng, k, 5000)
        x = np.abs(out[:, 0])
    elif kind == "hopf-planar":
        w = rng.uniform(0.3, 1.5)
        def drift(u):
            xx, yy = u
            r2 = xx * xx + yy * yy
            return np.array([kappa * xx - r2 * xx - w * yy, kappa * yy - r2 * yy + w * xx])
        out = em_sde(drift, lambda u: 1.0, [0.1, 0.0], dt, T * k, rng, k, 5000)
        x = out[:, 0]
    elif kind == "saddle-node":
        mu = -kappa  # distance to the fold on the side where the stable node exists: dx = mu - x^2
        out = em_sde(lambda x: (mu - x**2) if x > -2 else 10.0, lambda x: 0.3, [math.sqrt(mu)], dt, T * k, rng, k, 5000)
        x = out[:, 0]
    else:
        mu = -kappa  # transcritical: dx = mu x - x^2, stable branch x = mu
        out = em_sde(lambda x: (mu * x - x**2) if -0.2 < x < 3 + mu else (10.0 if x <= -0.2 else -10.0), lambda x: 0.3, [mu], dt, T * k, rng, k, 5000)  # soft walls: noise-induced escape below 0 is reflected
        x = out[:, 0]
    return x, dict(kind=kind, kappa=kappa, near="yes" if near else "no",
                   reversible="yes" if kind in ("pitchfork", "hopf-radial", "saddle-node", "transcritical") else "no")


def _vdp_noisy(mu):
    return lambda u: np.array([u[1], mu * (1 - u[0] ** 2) * u[1] - u[0]])


def _vdp_lienard(mu):
    # Lienard coordinates: well conditioned in the relaxation regime, where the phase-plane form's
    # velocity (~mu) blows up under noise
    return lambda u: np.array([mu * (u[0] - u[0] ** 3 / 3 - u[1]), u[0] / mu])


def _sl(mu, w):
    def f(u):
        r2 = u[0] ** 2 + u[1] ** 2
        return np.array([(mu - r2) * u[0] - w * u[1], (mu - r2) * u[1] + w * u[0]])
    return f


@family("I", "noisy-limit-cycle", 10, {**SDE, "periodic": "partly", "reversible": "no"}, profiles={"stationary1000": 8})
def noisy_limit_cycle(i, rng, T, S):
    """Van der Pol (even i) or Stuart-Landau (odd i) with additive noise LU[0.2, 1] (stationary: LU[0.3, 1],
    and odd i is a relaxation van der Pol in Lienard form instead): phase diffusion; ppp S[15, 40]."""
    from ..registry import profile
    stat = profile() == "stationary1000"
    sig = S.draw("sigma", 0.3, 1.0, log=True) if stat else S.draw("sigma", 0.2, 1.0, log=True)
    if i % 2 == 0:
        mu = rng.uniform(0.3, 3.0)
        per = 2 * math.pi * (1 + mu * mu / 16)
        f = _vdp_noisy(mu)
        par = dict(kind="vdp", mu=mu)
    elif stat:  # Stuart-Landau is a noisy sinusoid: use a relaxation van der Pol instead
        mu = rng.uniform(2.0, 5.0)
        per = (3 - 2 * math.log(2)) * mu + 2 * math.pi / mu  # relaxation-limit period estimate
        f = _vdp_lienard(mu)
        par = dict(kind="vdp-relaxation", mu=mu)
    else:
        mu, w = 1.0, 1.0
        per = 2 * math.pi / w
        f = _sl(mu, w)
        par = dict(kind="stuart-landau", mu=mu)
    ppp = S.integer("ppp", 15, 40)
    dt_obs = per / ppp
    k = max(1, int(round(dt_obs / 0.01)))
    dt = dt_obs / k
    out = em_sde(f, lambda u: sig, [1.0, 0.0], dt, T * k, rng, k, 50 * k)
    return out[:, 0], dict(sigma=sig, ppp=ppp, period_samples=ppp, **par)


def _lorenz_f(u):
    x, y, z = u
    return np.array([10 * (y - x), x * (28 - z) - y, x * y - 8 / 3 * z])


def _rossler_f(u):
    x, y, z = u
    return np.array([-y - z, x + 0.2 * y, 0.2 + z * (x - 5.7)])


def _chua_f(u):
    x, y, z = u
    h = -5 / 7 * x + 0.5 * (-8 / 7 + 5 / 7) * (abs(x + 1) - abs(x - 1))
    return np.array([15.6 * (y - x - h), x - y + z, -28.0 * y])


@family("I", "noisy-chaos", 8, {**SDE, "chaotic": "yes", "deterministic": "partly", "reversible": "no"}, profiles={"stationary1000": 14})
def noisy_chaos(i, rng, T, S):
    """Lorenz, Rossler or Chua with *dynamical* noise LU[0.03, 0.3] (stationary: LU[0.1, 0.5], ppp S[8, 20]) of the attractor SD: visibly
    noisy trajectories (below ~0.02 the noise is invisible against the deterministic motion)."""
    from ..registry import profile
    stat = profile() == "stationary1000"
    kind = ["lorenz", "rossler", "chua"][i % 3]
    eps = S.draw("noise", 0.1, 0.5, log=True) if stat else S.draw("noise", 0.03, 0.3, log=True)
    f, x0, per, sd = {"lorenz": (_lorenz_f, [1.0, 1.0, 20.0], 0.75, 8.0),
                      "rossler": (_rossler_f, [1.0, 1.0, 0.0], 6.1, 5.0),
                      "chua": (_chua_f, [0.1, 0.0, 0.0], 2.0, 1.5)}[kind]
    ppp = S.integer("ppp", 8, 20) if stat else S.integer("ppp", 15, 40)
    dt_obs = per / ppp
    k = max(1, int(round(dt_obs / 0.002)))
    dt = dt_obs / k
    if kind == "chua":
        eps = min(eps, 0.06)  # Chua's double scroll escapes under strong dynamical noise
    g = (lambda u: eps * sd) if kind == "lorenz" else (lambda u: np.array([eps * sd, eps * sd, 0.0]))  # Rossler's and Chua's z escape off-attractor
    out = em_sde(f, g, np.array(x0) * (1 + 0.05 * rng.standard_normal(3)), dt, T * k, rng, k, 200 * k)
    return out[:, 0], dict(kind=kind, noise=eps, ppp=ppp, period_samples=ppp)


@family("I", "stochastic-resonance", 6, {**SDE, "regime_switching": "yes", "periodic": "partly"}, profiles={"stationary1000": 12})
def stochastic_resonance(i, rng, T, S):
    """Double well + weak periodic forcing + noise: dx = (x - x^3 + A cos(w t)) dt + sigma dW, sigma
    stratified around the resonance optimum."""
    sig = S.draw("sigma", 0.3, 1.0)
    A, w = 0.25, 2 * math.pi / 60.0
    from ..registry import profile
    dt, k = 0.05, (40 if profile() == "stationary1000" else 20)  # coarser sampling: twice the hops per record
    t = [0.0]

    def drift(x):
        t[0] += dt
        return x - x**3 + A * math.cos(w * t[0])
    out = em_sde(drift, lambda x: sig, [1.0], dt, T * k, rng, k, 0)
    return out[:, 0], dict(sigma=sig, A=A, forcing_period_samples=2 * math.pi / w / (dt * k), period_samples=2 * math.pi / w / (dt * k))


@family("I", "excitable-fhn", 8, {**SDE, "event_like": "yes", "bursty": "partly", "reversible": "no"}, profiles={"stationary1000": 8})
def excitable_fhn(i, rng, T, S):
    """FitzHugh-Nagumo in the excitable regime, noise-driven spiking: sigma stratified so spikes per
    1000 samples run over ~[5, 80]."""
    from ..registry import profile
    stat = profile() == "stationary1000"
    if stat and i >= 5:
        # type-I excitability (a saddle-node on the circle) instead of FitzHugh-Nagumo's type II: the active
        # rotator (Shinomoto & Kuramoto 1986) d phi = (1 - b sin phi) dt + sigma dW, b > 1; observe -cos(phi).
        # Eight FHN instances were mutually redundant in hctsa space (2026-09-26).
        b, sig = S.draw("b_rot", 1.03, 1.1), rng.uniform(0.25, 0.35)
        out = em_sde(lambda p: 1.0 - b * math.sin(p), lambda p: sig, [0.0], 0.02, T * 25, rng, 25, 2000)
        ph = out[:, 0]
        return -np.cos(ph), dict(kind="active-rotator", b=b, sigma=sig, spikes=int((ph[-1] - ph[0]) // (2 * math.pi)))
    if stat:  # I = 0.35 is past the oscillation threshold (a noisy limit cycle): span the excitable range
        sig, I = S.draw("sigma", 0.15, 0.4, log=True), S.draw("I", 0.0, 0.32)
    else:
        sig, I = S.draw("sigma", 0.12, 0.5, log=True), 0.35
    a, b, eps = 0.7, 0.8, 0.08

    def drift(u):
        v, w = u
        return np.array([v - v**3 / 3 - w + I, eps * (v + a - b * w)])
    dt, k = 0.02, (40 if stat else 25)
    out = em_sde(drift, lambda u: np.array([sig, 0.0]), [-1.2, -0.6], dt, T * k, rng, k, 2000)
    v = out[:, 0]
    spikes = int(np.sum((v[1:] > 0.5) & (v[:-1] <= 0.5)))
    return v, dict(kind="fhn", sigma=sig, I=I, spikes=spikes, event_rate=spikes / T)


@family("I", "multiplicative-coloured", 4, {**SDE, "reversible": "no"}, profiles={"stationary1000": 5})
def multiplicative_coloured(i, rng, T, S):
    """Langevin with multiplicative noise dx = -x dt + sigma x dW (+ small additive, even i), or a
    linear relaxation driven by OU-coloured noise (odd i)."""
    dt, k = 0.01, 10
    if i % 2 == 0:
        sig = S.draw("sigma", 0.5, 1.4)
        out = em_sde(lambda x: -x + 0.5, lambda x: sig * abs(x) + 0.05, [0.5], dt, T * k, rng, k, 5000)
        return out[:, 0], dict(kind="multiplicative", sigma=sig, skewed="yes", heavy_tailed="yes")
    tau_c = S.draw("tau_c", 0.5, 20.0, log=True)
    k = max(1, int(round((1 + tau_c) / 5 / dt)))  # observe so the total correlation time is ~5 samples

    def drift(u):
        x, eta = u
        return np.array([-x + eta, -eta / tau_c])
    out = em_sde(drift, lambda u: np.array([0.0, math.sqrt(2 / tau_c)]), [0.0, 0.0], dt, T * k, rng, k, 5000)
    return out[:, 0], dict(kind="ou-driven", tau_c=tau_c, linear="yes", gaussian="yes", reversible="yes")


@family("I", "heteroclinic", 0, {**SDE, "regime_switching": "yes", "reversible": "no"}, profiles={"stationary1000": 3})
def heteroclinic(i, rng, T, S):
    """Noisy heteroclinic cycle (May & Leonard 1975; Busse & Heikes): three competing species
    x_k' = x_k (1 - x_k - alpha x_{k+1} - beta x_{k+2}) with alpha < 1 < beta, alpha + beta > 2, cycle
    between saddle states where one species dominates. Small noise delta sets how long each plateau
    lasts (~ln(1/delta)); observed as x_1 + x_2 / 2, so the three saddles read as three levels and the
    cyclic order of the switching is visible. Reflected at zero; ~30 dwells per record."""
    alpha, beta = 0.5, 2.0
    if i == 2:  # asymmetric competition: unequal saddles, so the plateaus differ in length (the symmetric pair was redundant)
        alpha, beta = np.array([0.3, 0.55, 0.8]), np.array([2.4, 1.9, 1.5])
    delta = S.draw("delta", 1e-3, 3e-2, log=True)
    dwell = math.log(1 / delta) / 0.2
    dt = 0.02
    k = max(1, int(round(30 * dwell / T / dt)))
    x = np.array([0.4, 0.3, 0.3])
    out = np.empty(T)
    burn_steps = 20000
    xi = rng.standard_normal((T * k + burn_steps, 3))
    sq = math.sqrt(dt)
    for s in range(T * k + burn_steps):
        f = x * (1 - x - alpha * np.roll(x, -1) - beta * np.roll(x, -2))
        x = np.abs(x + dt * f + delta * sq * xi[s])
        if s >= burn_steps and (s - burn_steps) % k == 0:
            out[(s - burn_steps) // k] = x[0] + 0.5 * x[1]
    asym = np.ndim(alpha) > 0
    return out, dict(alpha=list(alpha) if asym else alpha, beta=list(beta) if asym else beta, delta=delta,
                     dwell_time=dwell, observed="x1 + x2/2", kind="asymmetric" if asym else "symmetric")
