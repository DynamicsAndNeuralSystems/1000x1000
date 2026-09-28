"""Class G: chaotic flows — one trajectory per usable dysts flow, delay systems, canonical regime sweeps."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from ..registry import family
from ..rng import rng_for
from ..util import add_noise, deterministic_noise_sigma, flow_series, rk4

FLOW = dict(deterministic="yes", chaotic="yes", linear="no", gaussian="no", stationary="yes",
            continuous_time="yes", reversible="no")


def _finish(x, rng, info):
    from ..registry import profile
    if profile() == "stationary1000" and np.unique(np.round(x, 12)).size < 100:
        raise RuntimeError("periodic orbit: redrawn in the stationary profile")
    sig = deterministic_noise_sigma(rng)
    info = dict(info, noise_sigma=sig, measurement_noise="yes" if sig > 0 else "no",
                deterministic="partly" if sig > 0 else "yes")
    # Retag by the tabulated largest Lyapunov exponent (per sample) rather than the family default:
    # lambda <= 0 is not chaotic (tori, cycles); chaos that grows by less than one e-fold over the
    # record (slow-mixing conservative systems, weakly chaotic forced oscillators) is only partly
    # expressed in it. Metadata only: draws and samples are unchanged.
    lam = info.get("lyapunov_max")
    if "chaotic" not in info and lam is not None and np.isfinite(lam):
        info["chaotic"] = "no" if lam <= 0 else "partly" if lam * len(x) < 1 else "yes"
    return add_noise(x, sig, rng), info


def _periodicity(x: np.ndarray) -> float:
    """Autocorrelation at the dominant-period lag: ~1 for a clean sinusoid."""
    from ..util import dominant_period
    x = np.asarray(x, float) - x.mean()
    P = int(round(dominant_period(x)))
    if not (2 <= P < x.size // 2):
        return 0.0
    return float((x[:-P] @ x[P:]) / (x @ x))


# Reversible in law but not as observed in stationary1000 (both fail a phase-randomised-surrogate test of
# time-reversal asymmetry): the Nose-Hoover series observes a coordinate that the reversing symmetry flips in
# sign, so its reversal is the series upside down; the lid-driven cavity is a periodically forced flow, area-
# preserving but not time-reversible.
_OBSERVED_IRREVERSIBLE = {"NoseHoover", "LidDrivenCavityFlow"}


def _reversible(name: str) -> str:
    from ..sources import reversible_systems
    from ..registry import profile
    if profile() == "stationary1000" and name in _OBSERVED_IRREVERSIBLE:
        return "no"
    return "yes" if name in reversible_systems() else "no"


def _lyap_table():
    from ..sources import lyapunov_table
    return lyapunov_table()


@family("G", "dysts-flow", 126, FLOW)
def dysts_flow(i, rng, T, S):
    """One trajectory per usable non-delay dysts flow (126): DOP853, resampled to ppp S[15, 40]
    points per period, random coordinate, perturbed initial condition, burn 400. lyapunov_max from
    a Benettin table (per sample); 13 systems are reversible in law."""
    from ..sources import trajectory as _trajectory, usable_systems
    from ..registry import profile
    from ..util import acf_time
    flows = [c for c in usable_systems() if c[2] == "flow"]
    name, ctor, cat = flows[i % len(flows)]
    ppp = S.integer("ppp", 15, 40)
    coord = int(rng.integers(0, 8))
    seed_tag = int(rng.integers(1 << 30))
    r = _trajectory(name, ctor, cat, T, rng_for("traj", f"s1000-{i}-{seed_tag}"), tag=f"s1000-{i}-{seed_tag}", ppp=ppp, coord=coord)
    if r is None:
        raise RuntimeError(f"dysts flow {name} unusable")
    if profile() == "stationary1000":
        # dysts's period estimate is off by > 2x for a third of its flows, so "points per period" is
        # not a reliable speed. Normalise by what is observed: if the autocorrelation time exceeds 5
        # samples, resample so it is ~3.5 (coarser sampling of a slow system).
        tau = acf_time(r[0])
        if tau > 5:
            ppp_fast = max(3, int(round(ppp * 3.5 / tau)))
            r_fast = _trajectory(name, ctor, cat, T, rng_for("traj", f"s1000-{i}-{seed_tag}-fast"), tag=f"s1000-{i}-{seed_tag}-fast", ppp=ppp_fast, coord=coord)
            if r_fast is not None:  # some systems (e.g. StickSlipOscillator) cannot be integrated coarsely
                r, ppp = r_fast, ppp_fast
        # a coordinate that is a near-perfect sinusoid (autocorrelation at the dominant period > 0.97)
        # is trivial to the eye: try the other coordinates, then fall back to the next system
        for k in range(1, 8):
            if _periodicity(r[0]) <= 0.95:
                break
            coord2 = (coord + k) % 8
            r2 = _trajectory(name, ctor, cat, T, rng_for("traj", f"s1000-{i}-{seed_tag}-c{k}"), tag=f"s1000-{i}-{seed_tag}-c{k}", ppp=ppp, coord=coord2)
            if r2 is not None:
                r, coord = r2, coord2
        else:
            raise RuntimeError(f"{name}: every coordinate is near-sinusoidal")
    info = dict(system=name, ppp=ppp, coord=coord, reversible=_reversible(name))
    tab = _lyap_table().get(name) or {}
    if "lam" in tab and "period_dysts" in tab:
        info["lyapunov_max"] = tab["lam"] * tab["period_dysts"] / ppp
    if "measured_period_over_dysts" in tab:
        info["period_samples"] = ppp * tab["measured_period_over_dysts"]
    return _finish(r[0], rng, info)


# --------------------------------------------------------------------------
# delay-differential equations (method of steps, fixed-step RK4 on an integer delay grid)
# --------------------------------------------------------------------------


def _dde(f, tau: float, dt: float, n_steps: int, x0: float, burn_steps: int, rng):
    """Scalar DDE x' = f(x, x_tau). History = x0 + small noise."""
    m = int(round(tau / dt))
    dt = tau / m
    hist = list(x0 + 0.01 * rng.standard_normal(m + 1))
    out = np.empty(n_steps)
    x = hist[-1]
    for s in range(burn_steps + n_steps):
        xd = hist[-m - 1]
        xd_half = 0.5 * (hist[-m - 1] + hist[-m])
        xd_next = hist[-m]
        k1 = f(x, xd)
        k2 = f(x + 0.5 * dt * k1, xd_half)
        k3 = f(x + 0.5 * dt * k2, xd_half)
        k4 = f(x + dt * k3, xd_next)
        x = x + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        hist.append(x)
        if len(hist) > m + 2:
            hist.pop(0)
        if s >= burn_steps:
            out[s - burn_steps] = x
    return out


def _resample_ppp(x_fine, dt, ppp, T, rng):
    """Subsample a finely integrated series to ppp points per dominant period."""
    from ..util import dominant_period
    per = dominant_period(x_fine[len(x_fine) // 4:]) * dt
    step = max(1, int(round(per / ppp / dt)))
    step = max(1, min(step, x_fine.size // T))  # never fewer than T points; ppp then reads higher
    x = x_fine[::step]
    if x.size < T:
        raise RuntimeError("DDE series too short after resampling")
    s0 = int(rng.integers(0, x.size - T + 1))
    return x[s0:s0 + T], per, step * dt


@family("G", "dde", 15, {**FLOW, "chaotic": "partly"}, profiles={"stationary1000": 0})
def dde(i, rng, T, S):
    """Delay-differential systems: Mackey-Glass (tau stratified over [8, 40]: periodic to
    high-dimensional chaos, 8), Ikeda DDE (3), Hutchinson delayed logistic (2), sine-delay
    x' = sin(x(t - tau)) (2)."""
    ppp = S.integer("ppp", 15, 40)
    if i < 8:
        tau = S.draw("mg_tau", 8.0, 40.0)
        f = lambda x, xd: 0.2 * xd / (1 + xd**10) - 0.1 * x
        dt, x0, t_burn, t_run = 0.1, 0.9, 600.0, 8000.0
        kind, par = "mackey-glass", dict(tau=tau, beta=0.2, gamma=0.1, n=10)
        chaotic = "yes" if tau > 16.8 else "no"
    elif i < 11:
        mu, tau = S.draw("ikeda_mu", 5.0, 30.0), 2.0
        f = lambda x, xd: -x + mu * math.sin(xd)
        dt, x0, t_burn, t_run = 0.01, 0.5, 100.0, 600.0
        kind, par, chaotic = "ikeda-dde", dict(mu=mu, tau=tau), "yes"
    elif i < 13:
        r, tau = S.draw("hutch_r", 1.6, 3.5), 1.0
        f = lambda x, xd: r * x * (1 - xd)
        dt, x0, t_burn, t_run = 0.01, 0.8, 100.0, 1500.0
        kind, par, chaotic = "hutchinson", dict(r=r, tau=tau), "no" if r < 2.5 else "partly"
    else:
        tau = S.draw("sine_tau", 3.0, 8.0)
        f = lambda x, xd: math.sin(xd)
        dt, x0, t_burn, t_run = 0.02, 0.3, 200.0, 8000.0
        kind, par, chaotic = "sine-delay", dict(tau=tau, stationary="no", nonstationary_kind="walk"), "partly"  # x is an unbounded phase
    xf = _dde(f, tau, dt, int(t_run / dt), x0, int(t_burn / dt), rng)
    x, per, dt_obs = _resample_ppp(xf, dt, ppp, T, rng)
    return _finish(x, rng, dict(kind=kind, **par, ppp=ppp, period_samples=per / dt_obs, chaotic=chaotic))


# --------------------------------------------------------------------------
# canonical regime sweeps
# --------------------------------------------------------------------------


def _lorenz(t, u, s, r, b):
    x, y, z = u
    return [s * (y - x), x * (r - z) - y, x * y - b * z]


def _rossler(t, u, a, b, c):
    x, y, z = u
    return [-y - z, x + a * y, b + z * (x - c)]


def _chua(t, u, alpha, beta, m0, m1):
    x, y, z = u
    h = m1 * x + 0.5 * (m0 - m1) * (abs(x + 1) - abs(x - 1))
    return [alpha * (y - x - h), x - y + z, -beta * y]


def _duffing(t, u, d, g, w):
    x, v, th = u
    return [v, x - x**3 - d * v + g * math.cos(th), w]


def _pendulum(t, u, d, g, w):
    th, v, ph = u
    return [v, -d * v - math.sin(th) + g * math.cos(ph), w]


def _double_pendulum(t, u):
    t1, t2, p1, p2 = u
    c, s = math.cos(t1 - t2), math.sin(t1 - t2)
    den = 1 + s * s
    dt1 = (p1 - p2 * c) / den
    dt2 = (2 * p2 - p1 * c) / den
    dp1 = -2 * math.sin(t1) - dt1 * dt2 * s
    dp2 = -math.sin(t2) + dt1 * dt2 * s
    return [dt1, dt2, dp1, dp2]


def _lorenz84(t, u, a, b, F, G):
    x, y, z = u
    return [-y * y - z * z - a * x + a * F, x * y - b * x * z - y + G, b * x * y + x * z - z]


def _chen(t, u, a, b, c):
    x, y, z = u
    return [a * (y - x), (c - a) * x - x * z + c * y, x * y - b * z]


@family("G", "canonical-sweep", 9, {**FLOW, "chaotic": "partly"})
def canonical_sweep(i, rng, T, S):
    """Regimes of canonical flows not represented by the dysts defaults: Lorenz rho = 24.5
    (co-existing attractors) and rho = 160 (NB: inside a periodic window); Rossler c = 4 (a period-1
    cycle; replaced by Chen in the stationary profile) and c = 8.5 (NB: a periodic orbit at a = b = 0.1, not a funnel);
    Chua double scroll; forced Duffing; driven damped pendulum; double pendulum; Lorenz-84."""
    ppp = S.integer("ppp", 15, 40)
    cases = [
        ("lorenz-rho24.5", _lorenz, [1.0, 1.0, 20.0], (10.0, 24.5, 8 / 3), "yes", 0),
        ("lorenz-rho160", _lorenz, [1.0, 1.0, 20.0], (10.0, 160.0, 8 / 3), "partly", 0),
        ("rossler-c4", _rossler, [1.0, 1.0, 0.0], (0.1, 0.1, 4.0), "no", 0),  # period-2: replaced by Chen in the stationary profile
        ("rossler-c8.5", _rossler, [1.0, 1.0, 0.0], (0.1, 0.1, 8.5), "yes", 0),
        ("chua", _chua, [0.1, 0.0, 0.0], (15.6, 28.0, -8 / 7, -5 / 7), "yes", 0),
        ("duffing-forced", _duffing, [0.1, 0.0, 0.0], (0.3, 0.5, 1.2), "yes", 0),
        ("driven-pendulum", _pendulum, [0.1, 0.0, 0.0], (0.5, 1.2, 2 / 3), "yes", 1),
        ("double-pendulum", _double_pendulum, [2.0, 2.5, 0.0, 0.0], (), "yes", 0),
        ("lorenz84", _lorenz84, [1.0, 1.0, 1.0], (0.25, 4.0, 8.0, 1.0), "yes", 0),
    ]
    from ..registry import profile
    if profile() == "stationary1000" and i == 2:
        cases[2] = ("chen", _chen, [-10.0, 0.0, 37.0], (35.0, 3.0, 28.0), "yes", 0)
    if profile() == "stationary1000" and i == 1:  # rho = 160 lies in a periodic window (lambda ~ 0): a chaotic high-rho regime instead
        cases[1] = ("lorenz-rho130", _lorenz, [1.0, 1.0, 20.0], (10.0, 130.0, 8 / 3), "yes", 0)
    if profile() == "stationary1000" and i == 3:  # c = 8.5 at a = b = 0.1 is a period-4 orbit: the chaotic screw-type funnel (lambda ~ 0.19) instead
        cases[3] = ("rossler-funnel", _rossler, [1.0, 1.0, 0.0], (0.3, 0.1, 14.0), "yes", 0)
    name, f, x0, args, chaotic, coord = cases[i]
    x0 = np.array(x0) * (1 + 0.05 * rng.standard_normal(len(x0))) + 0.01 * rng.standard_normal(len(x0))
    x, per = flow_series(f, x0, T, ppp, coord=coord, args=args, t_probe=300.0)
    if name in ("driven-pendulum", "double-pendulum"):
        x = np.sin(x)  # angles are unbounded when the pendulum rotates; observe sin(theta)
    info = dict(system=name, ppp=ppp, period_time=per, period_samples=ppp, chaotic=chaotic,
                periodic="yes" if chaotic == "no" else "no")
    if name == "double-pendulum":
        info["reversible"] = "yes"  # Hamiltonian
    return _finish(x, rng, info)


@family("G", "dde-stationary", 0, {**FLOW, "chaotic": "partly"}, profiles={"stationary1000": 15})
def dde_stationary(i, rng, T, S):
    """Delay-differential systems with bounded state: Mackey-Glass (tau stratified over [17, 40], chaotic, 9),
    Ikeda DDE (4), and two chaotic delay systems of distinct character (2): Ucar's prototype
    x' = x(t - tau) - x(t - tau)^3 (tau S[1.6, 1.7], slow wandering chaos) and the band-pass optoelectronic
    Ikeda oscillator (beta U[2, 2.5], chaotic square-wave switching). These replaced Hutchinson's delayed
    logistic (2026-09-26), whose delay-induced cycle is not chaotic and duplicates Nicholson's blowflies.
    The sine-delay system (an unbounded phase) is left to the full profile."""
    ppp = S.integer("ppp", 15, 40)
    if i < 9:
        tau = S.draw("mg_tau", 17.0, 40.0)  # chaotic range only: tau < 16.8 is a periodic orbit
        f = lambda x, xd: 0.2 * xd / (1 + xd**10) - 0.1 * x
        dt, x0, t_burn, t_run = 0.1, 0.9, 600.0, 8000.0
        kind, par = "mackey-glass", dict(tau=tau, beta=0.2, gamma=0.1, n=10)
        chaotic = "yes" if tau > 16.8 else "no"
    elif i < 13:
        mu, tau = S.draw("ikeda_mu", 5.0, 30.0), 2.0
        f = lambda x, xd: -x + mu * math.sin(xd)
        dt, x0, t_burn, t_run = 0.01, 0.5, 100.0, 600.0
        kind, par, chaotic = "ikeda-dde", dict(mu=mu, tau=tau), "yes"
    elif i == 13:
        tau = S.draw("ucar_tau", 1.6, 1.7)  # chaotic band (tau ~ 1.8 escapes)
        f = lambda x, xd: xd - xd**3
        dt, x0, t_burn, t_run = 0.005, 0.5, 200.0, 1500.0
        kind, par, chaotic = "ucar", dict(tau=tau), "yes"
    else:
        return _bandpass_ikeda(rng, T, S)
    xf = _dde(f, tau, dt, int(t_run / dt), x0, int(t_burn / dt), rng)
    x, per, dt_obs = _resample_ppp(xf, dt, ppp, T, rng)
    return _finish(x, rng, dict(kind=kind, **par, ppp=ppp, period_samples=per / dt_obs, chaotic=chaotic))


def _bandpass_ikeda(rng, T, S):
    """Band-pass optoelectronic Ikeda oscillator (Peil et al. 2009), dimensionless with unit delay:
    eps x' = -x - y/theta + beta sin^2(x(t - 1) + phi), y' = x; eps = 0.01, theta = 50, phi = -pi/4. The
    band-pass feedback gives DC-free chaotic switching between plateaus. Heun on the delay grid (dt = 0.001),
    observed every 0.02 (20 delays per record)."""
    beta = S.draw("bp_beta", 2.0, 2.5)
    eps, theta, phi, dt = 0.01, 50.0, -math.pi / 4, 0.001
    m = int(round(1.0 / dt))
    sub = 20
    n = sub * T + int(20 / dt)
    xs = np.empty(n + m + 1)
    xs[: m + 1] = 0.1 + 0.01 * rng.standard_normal(m + 1)
    y = 0.0
    for t in range(m, n + m):
        x, xd, xd1 = xs[t], xs[t - m], xs[t - m + 1]
        k1x, k1y = (-x - y / theta + beta * math.sin(xd + phi) ** 2) / eps, x
        x2, y2 = x + dt * k1x, y + dt * k1y
        k2x, k2y = (-x2 - y2 / theta + beta * math.sin(xd1 + phi) ** 2) / eps, x2
        xs[t + 1], y = x + 0.5 * dt * (k1x + k2x), y + 0.5 * dt * (k1y + k2y)
    x = xs[m + 1 + int(20 / dt):][::sub][:T]
    return _finish(x, rng, dict(kind="bandpass-ikeda", beta=beta, eps=eps, theta=theta, phi=phi, chaotic="yes"))


@family("G", "dysts-flow-coarse", 0, FLOW, profiles={"stationary1000": 15})
def dysts_flow_coarse(i, rng, T, S):
    """dysts flows sampled coarsely, ppp S[4, 10] points per period (80-250 periods per record): the
    regime of Empirical1000's own chaotic-flow series, which the 15-40 ppp convention does not reach."""
    from ..sources import trajectory as _trajectory, usable_systems
    flows = [c for c in usable_systems() if c[2] == "flow"]
    name, ctor, cat = flows[S.integer("which", 0, len(flows) - 1)]
    ppp = S.integer("ppp", 4, 10)
    coord = int(rng.integers(0, 8))
    tag = f"s1000c-{i}-{int(rng.integers(1 << 30))}"
    r = _trajectory(name, ctor, cat, T, rng_for("traj", tag), tag=tag, ppp=ppp, coord=coord)
    if r is None:
        raise RuntimeError(f"dysts flow {name} unusable")
    info = dict(system=name, ppp=ppp, coord=coord, reversible=_reversible(name))
    tab = _lyap_table().get(name) or {}
    if "lam" in tab and "period_dysts" in tab:
        info["lyapunov_max"] = tab["lam"] * tab["period_dysts"] / ppp
    if "measured_period_over_dysts" in tab:
        info["period_samples"] = ppp * tab["measured_period_over_dysts"]
    return _finish(r[0], rng, info)


EXTRA_SYSTEMS = ("Sakarya", "ZhouChen", "BlinkingRotlet", "Halvorsen", "RabinovichFabrikant", "Dadras")


@family("G", "dysts-flow-extra", 0, FLOW, profiles={"stationary1000": 6})
def dysts_flow_extra(i, rng, T, S):
    """A second realisation of six systems whose single instance was visually the most interesting:
    Sakarya, ZhouChen, BlinkingRotlet, Halvorsen, RabinovichFabrikant, Dadras. Different observed
    coordinate, sampling density and initial condition from the one in ``dysts-flow``."""
    from ..sources import catalogue as _catalogue, trajectory as _trajectory
    from ..util import acf_time
    by_name = {n: (n, c, k) for n, c, k in _catalogue()}
    name = EXTRA_SYSTEMS[i % len(EXTRA_SYSTEMS)]
    if name not in by_name:
        raise RuntimeError(f"{name} not in the dysts catalogue")
    _, ctor, cat = by_name[name]
    ppp = S.integer("ppp", 10, 40)
    coord = int(rng.integers(0, 8))
    seed_tag = int(rng.integers(1 << 30))
    r = _trajectory(name, ctor, cat, T, rng_for("traj", f"x{i}-{seed_tag}"), tag=f"x{i}-{seed_tag}", ppp=ppp, coord=coord)
    if r is None:
        raise RuntimeError(f"dysts flow {name} unusable")
    tau = acf_time(r[0])
    if tau > 5:
        ppp_fast = max(3, int(round(ppp * 3.5 / tau)))
        r_fast = _trajectory(name, ctor, cat, T, rng_for("traj", f"x{i}-{seed_tag}-f"), tag=f"x{i}-{seed_tag}-f", ppp=ppp_fast, coord=coord)
        if r_fast is not None:
            r, ppp = r_fast, ppp_fast
    for k in range(1, 3):  # near-sinusoidal coordinate: try the others
        if _periodicity(r[0]) <= 0.95:
            break
        r2 = _trajectory(name, ctor, cat, T, rng_for("traj", f"x{i}-{seed_tag}-c{k}"), tag=f"x{i}-{seed_tag}-c{k}", ppp=ppp, coord=(coord + k) % 3)
        if r2 is not None:
            r, coord = r2, (coord + k) % 3
    info = dict(system=name, ppp=ppp, coord=coord, second_realisation="yes",
                reversible=_reversible(name))
    tab = _lyap_table().get(name) or {}
    if "lam" in tab and "period_dysts" in tab:
        info["lyapunov_max"] = tab["lam"] * tab["period_dysts"] / ppp
    return _finish(r[0], rng, info)


@family("G", "blinking-rotlet", 0, {**FLOW, "chaotic": "partly"}, profiles={"stationary1000": 6})
def blinking_rotlet(i, rng, T, S):
    """Blinking rotlet (Meleshko & Aref 1996): a tracer in a Stokes flow stirred by two rotlets that
    switch on and off alternately. The switching period tau is stratified log-uniformly over [0.8, 10]:
    short periods give fast irregular mixing, long ones smooth rotations broken by bursts at each
    switch. Observed x or y, speed-normalised like the other flows."""
    import dysts.flows as DF
    from ..sources import trajectory as _trajectory
    from ..util import acf_time
    tau = S.draw("tau", 0.8, 10.0, log=True)

    def ctor(tau=tau):
        b = DF.BlinkingRotlet()
        b.params["tau"] = tau  # the constructor ignores a tau keyword: set it on the instance
        b.tau = tau
        return b
    coord = i % 2
    seed_tag = int(rng.integers(1 << 30))
    tag = f"br{i}-{seed_tag}-{tau:.4f}"
    r = _trajectory("BlinkingRotlet", ctor, "flow", T, rng_for("traj", tag), tag=tag, ppp=20, coord=coord)
    if r is None:
        raise RuntimeError("BlinkingRotlet unusable")
    ppp = 20
    t_acf = acf_time(r[0])
    if t_acf > 5:
        ppp_fast = max(3, int(round(ppp * 3.5 / t_acf)))
        r_fast = _trajectory("BlinkingRotlet", ctor, "flow", T, rng_for("traj", tag + "-f"), tag=tag + "-f", ppp=ppp_fast, coord=coord)
        if r_fast is not None:
            r, ppp = r_fast, ppp_fast
    return _finish(r[0], rng, dict(system="BlinkingRotlet", tau_switch=tau, ppp=ppp, coord=coord))


def _stadium_x(T, L, dt, rng, obs):
    """Stadium billiard (Bunimovich): straight segments |y| = 1 joined by unit semicircles centred at
    (+-L, 0). Unit-speed free flight with specular reflection, sampled every dt."""
    p = np.array([rng.uniform(-L, L), rng.uniform(-0.8, 0.8)])
    a = rng.uniform(0, 2 * np.pi)
    v = np.array([np.cos(a), np.sin(a)])
    out, t_next, t = np.empty(T + 200), 0.0, 0.0
    k = 0
    while k < T + 200:
        cands = []
        if v[1] > 0:
            th = (1 - p[1]) / v[1]
            if abs(p[0] + v[0] * th) <= L:
                cands.append((th, np.array([0.0, -1.0])))
        if v[1] < 0:
            th = (-1 - p[1]) / v[1]
            if abs(p[0] + v[0] * th) <= L:
                cands.append((th, np.array([0.0, 1.0])))
        for cx in (L, -L):
            d = p - np.array([cx, 0.0])
            bq = d @ v
            disc = bq * bq - (d @ d - 1.0)
            if disc >= 0:
                for th in (-bq + np.sqrt(disc), -bq - np.sqrt(disc)):
                    hit = p + v * th
                    if th > 1e-9 and (hit[0] - cx) * np.sign(cx) >= -1e-12:
                        cands.append((th, -(hit - np.array([cx, 0.0]))))
        th, n = min(cands, key=lambda c: c[0])
        while t_next <= t + th and k < T + 200:  # sample along this free flight
            q = p + v * (t_next - t)
            out[k] = q[obs]
            k += 1
            t_next += dt
        p = p + v * th
        t += th
        n = n / np.linalg.norm(n)
        v = v - 2 * (v @ n) * n
    return out[200:]


@family("G", "billiard", 0, {"deterministic": "yes", "chaotic": "yes", "linear": "no", "gaussian": "no",
                             "stationary": "yes", "continuous_time": "yes", "reversible": "yes"}, profiles={"stationary1000": 2})
def billiard(i, rng, T, S):
    """Bunimovich stadium billiard: Hamiltonian chaos made of straight flights and specular bounces.
    One coordinate (x for i = 0, y for i = 1) sampled at fixed time steps; half-length L stratified over
    [0.5, 2]; about three samples per flight."""
    L = S.draw("L", 0.5, 2.0)
    obs = i % 2
    # i = 0 sampled more coarsely: its sticky bouncing-ball episodes looked like a slow ramp (review 2026-09-25)
    x = _stadium_x(T, L, dt=0.6 if i else 1.0, rng=rng, obs=obs)
    return _finish(x, rng, dict(L=L, observed="x" if obs == 0 else "y"))


@family("G", "bouncing-ball", 0, {"deterministic": "yes", "chaotic": "yes", "linear": "no", "gaussian": "no",
                                  "stationary": "yes", "continuous_time": "yes", "reversible": "no"}, profiles={"stationary1000": 2})
def bouncing_ball(i, rng, T, S):
    """Ball bouncing on a sinusoidally vibrating table (Holmes 1982): ballistic flights under gravity
    joined by inelastic impacts (restitution e) with the table; chaotic for normalised table
    acceleration Gamma ~ 2.5-4. Ball height sampled at 6 points per table period."""
    e = S.draw("e", 0.6, 0.85)
    gam = rng.uniform(2.6, 3.8)
    g, w = 1.0, 2 * np.pi
    A = gam * g / w**2
    table = lambda t: A * np.sin(w * t)
    dtable = lambda t: A * w * np.cos(w * t)
    t0, z0 = 0.0, table(0.0)
    v0 = dtable(0.0) + rng.uniform(0.3, 0.8)
    dt_obs = 1.0 / 6
    n_out = T + 300
    out = np.empty(n_out)
    k, t_s = 0, 0.0
    short = 0
    while k < n_out:
        # next impact: first t > t0 where ball height meets the table
        zb = lambda t: z0 + v0 * (t - t0) - 0.5 * g * (t - t0) ** 2
        f = lambda t: zb(t) - table(t)
        h = 1e-3
        a = t0 + 1e-6
        while f(a + h) > 0:
            a += h
        lo, hi = a, a + h
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if f(mid) > 0:
                lo = mid
            else:
                hi = mid
        t1 = 0.5 * (lo + hi)
        while t_s <= t1 and k < n_out:
            out[k] = zb(t_s)
            k += 1
            t_s += dt_obs
        vb = v0 - g * (t1 - t0)
        vt = dtable(t1)
        v0 = vt - e * (vb - vt)
        z0, t0 = table(t1), t1
        short = short + 1 if t1 - t0 < 1e-3 else 0
        if v0 - vt < 1e-4:  # locked onto the table (chattering): kick off at the next upswing
            v0 = vt + 1e-2
    x = out[300:]
    return _finish(x, rng, dict(e=e, Gamma=gam, samples_per_period=6))
