"""Shared generators used by several families: dysts trajectories, multifractal sources, long-lag
autoregressions, replayed-segment noise, phase-amplitude coupling and quadratic phase coupling.

Each keeps its own named random streams (``stream(label, ...)``), unprefixed by the corpus name, so
the series they produce are fixed by those labels alone.
"""
from __future__ import annotations

import cmath
import json
import math
import signal
import warnings
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from .rng import seed_of

DATA = Path(__file__).resolve().parent / "data"


def stream(*parts) -> np.random.Generator:
    """A generator addressed by name alone (no corpus prefix)."""
    return np.random.Generator(np.random.PCG64(seed_of(*parts)))


def rank_remap(x: np.ndarray, target_sorted: np.ndarray) -> np.ndarray:
    """Put x onto the marginal of target_sorted, keeping x's rank order (ties share a rank)."""
    from scipy.stats import rankdata
    x = np.asarray(x, dtype=float)
    target_sorted = np.sort(np.asarray(target_sorted, dtype=float))
    if target_sorted.size != x.size:
        target_sorted = np.quantile(target_sorted, np.linspace(0, 1, x.size))
    idx = np.clip(rankdata(x, method="average") - 1.0, 0, x.size - 1)
    lo, hi = np.floor(idx).astype(int), np.ceil(idx).astype(int)
    w = idx - lo
    return (1.0 - w) * target_sorted[lo] + w * target_sorted[hi]


def tilted_blend(x: np.ndarray, rng: np.random.Generator, tilt: float, n_sweeps: float = 2.0,
                 target_sorted: np.ndarray | None = None) -> np.ndarray:
    """A linear process carrying x's spectrum whose spectral slope sweeps in time: two phase-randomised
    realisations of x's amplitude spectrum, power split between them in quadrature across log frequency
    (tilt sets how unevenly), blended by a slow quadrature weight (n_sweeps cycles), then rank-remapped
    onto x's marginal. tilt = 0 is stationary."""
    x = np.asarray(x, dtype=float)
    n = x.size
    amp = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(n)
    u = np.zeros_like(f)
    u[1:] = (np.log(f[1:]) - np.log(f[1])) / (np.log(f[-1]) - np.log(f[1]))
    theta = np.clip(np.pi / 4 + tilt * (u - 0.5) * (np.pi / 2), 0.05, np.pi / 2 - 0.05)
    s1 = np.sqrt(2.0) * amp * np.cos(theta)
    s2 = np.sqrt(2.0) * amp * np.sin(theta)

    def realise(S):
        ph = rng.uniform(0, 2 * np.pi, S.size)
        ph[0] = 0.0
        return np.fft.irfft(S * np.exp(1j * ph), n=n)

    a, b = realise(s1), realise(s2)
    t = np.arange(n) / n
    w2 = 0.5 * (1.0 + np.sin(2 * np.pi * n_sweeps * t + rng.uniform(0, 2 * np.pi)))
    z = np.sqrt(w2) * a + np.sqrt(1.0 - w2) * b
    return rank_remap(z, np.sort(x) if target_sorted is None else target_sorted)


# ---------------------------------------------------------------------------------------------------
# dysts trajectories
# ---------------------------------------------------------------------------------------------------
BURN_POINTS = 400        # discarded after the perturbed initial condition
TIMEOUT = 20             # seconds per trajectory; a few dysts systems are stiff at their native dt
CACHE = Path(__file__).resolve().parents[2] / "data" / "cache" / "trajectories"  # git-ignored


class _Timeout(Exception):
    pass


@contextmanager
def _time_limit(seconds: int):
    def handler(signum, frame):
        raise _Timeout()
    old = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def catalogue():
    """Every dysts flow and map, as (name, constructor, "flow" | "map"). Delay-differential systems are
    left out: their Fortran integrator cannot be interrupted by the per-trajectory timeout."""
    import dysts.base as B
    import dysts.flows as Fl
    import dysts.maps as M
    out = []
    for name in sorted(n for n in dir(Fl) if n[0].isupper() and not n.startswith("_")):
        ctor = getattr(Fl, name)
        if isinstance(ctor, type) and issubclass(ctor, B.DynSysDelay):
            continue
        out.append((name, ctor, "flow"))
    for name in sorted(n for n in dir(M) if n[0].isupper() and not n.startswith("_")):
        out.append((name, getattr(M, name), "map"))
    return out


_USABLE = None


def usable_systems():
    """The dysts systems that produce a usable 1000-sample series at their default parameters, in
    catalogue order (the list is fixed: data/usable_systems.json)."""
    global _USABLE
    if _USABLE is None:
        by_name = {c[0]: c for c in catalogue()}
        names = json.loads((DATA / "usable_systems.json").read_text())
        _USABLE = [by_name[n] for n in names if n in by_name]
    return _USABLE


def cache_path(name: str, length: int, tag: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / f"{name}_{length}_{tag}.npz"


def trajectory(name, ctor, category, length: int, rng: np.random.Generator, tag: str = "series",
               ppp_range: tuple = (15, 41), ppp: int | None = None, coord: int | None = None):
    """(x, category) for one observed coordinate of one trajectory, or None if the system fails at its
    default parameters. The initial condition is perturbed (5%), flows are resampled to ``ppp`` points
    per period (drawn from ``ppp_range`` unless given), the coordinate is drawn unless given, and
    BURN_POINTS samples are discarded. Trajectories are deterministic in ``rng`` and cached."""
    if ppp_range != (15, 41):
        tag = f"{tag}_ppp{ppp_range[0]}-{ppp_range[1]}"
    if ppp is not None or coord is not None:
        tag = f"{tag}_p{ppp}c{coord}"
    cp = cache_path(name, length, tag)
    if cp.exists():
        z = np.load(cp, allow_pickle=False)
        return z["x"], str(z["cat"])
    r = _trajectory(name, ctor, category, length, rng, ppp_range, ppp, coord)
    if r is not None:
        np.savez(cp, x=r[0], cat=r[1])
    return r


def _trajectory(name, ctor, category, length, rng, ppp_range=(15, 41), ppp=None, coord=None):
    try:
        sysobj = ctor()
        ic = np.asarray(sysobj.ic, dtype=float)
        sysobj.ic = ic * (1.0 + 0.05 * rng.standard_normal(ic.size))
        n = length + BURN_POINTS
        with warnings.catch_warnings(), _time_limit(TIMEOUT):
            warnings.simplefilter("ignore")
            if category == "flow":
                if ppp is None:
                    ppp = int(rng.integers(*ppp_range))
                # DOP853 at dysts's tolerance matches its default Radau solver in a fraction of the time
                tr = sysobj.make_trajectory(n, resample=True, pts_per_period=ppp, method="DOP853")
            else:
                tr = sysobj.make_trajectory(n)
        if tr is None:
            return None
        tr = np.asarray(tr, dtype=float)
        if tr.ndim == 1:
            tr = tr[:, None]
        if tr.shape[0] < n:
            return None
        d = tr.shape[1]
        if coord is None:
            coord = int(rng.integers(0, d))
        x = tr[BURN_POINTS:BURN_POINTS + length, coord % d]
        if not np.all(np.isfinite(x)) or x.std() < 1e-8:
            return None
        if np.mean(np.diff(x) == 0) > 0.2:   # a coordinate that barely moves: a map's degenerate axis
            return None
        return x, "map" if category == "map" else ("flow-3d" if d <= 3 else "flow-4d+")
    except (Exception, _Timeout):
        return None


# systems reversible in law (Hamiltonian in dysts's metadata, plus these)
_ALSO_REVERSIBLE = {"NoseHoover", "SprottA", "HenonHeiles", "Torus"}


def reversible_systems() -> set[str]:
    import dysts
    meta = json.loads((Path(dysts.__file__).parent / "data" / "chaotic_attractors.json").read_text())
    return {name for name, m in meta.items() if m.get("hamiltonian")} | _ALSO_REVERSIBLE


def lyapunov_table() -> dict:
    """Largest Lyapunov exponent (Benettin) and period for each dysts system: data/lyapunov_dysts.json."""
    return json.loads((DATA / "lyapunov_dysts.json").read_text())


# ---------------------------------------------------------------------------------------------------
# multifractal sources: standardised increments x = eps * exp(w), and their two factors
# ---------------------------------------------------------------------------------------------------
def fgn(n: int, H: float, rng: np.random.Generator) -> np.ndarray:
    """Fractional Gaussian noise by spectral synthesis, amplitude ~ f^{-(2H-1)/2}."""
    f = np.fft.rfftfreq(n)
    amp = np.zeros_like(f)
    amp[1:] = f[1:] ** (-(2 * H - 1) / 2)
    ph = rng.uniform(0, 2 * np.pi, f.size)
    x = np.fft.irfft(amp * np.exp(1j * ph), n=n)
    return (x - x.mean()) / x.std()


def _log_correlated(n: int, lam2: float, L: int, rng: np.random.Generator) -> np.ndarray:
    """Cov(w_s, w_t) ~ lam2 ln(L/|t-s|) for |t-s| < L: 1/f noise cut off below 1/L, variance lam2 ln L."""
    f = np.fft.rfftfreq(n)
    amp = np.zeros_like(f)
    amp[1:] = np.maximum(f[1:], 1.0 / L) ** -0.5
    ph = rng.uniform(0, 2 * np.pi, f.size)
    w = np.fft.irfft(amp * np.exp(1j * ph), n=n)
    w = (w - w.mean()) / w.std()
    return w * np.sqrt(lam2 * np.log(L))


def _discrete_cascade(n: int, b: int, mult_fn, rng: np.random.Generator) -> np.ndarray:
    """log of a multiplicative cascade (each cell split into b children, multipliers from mult_fn) read
    at a random grid phase."""
    m = np.ones(1)
    while m.size < n:
        m = np.repeat(m, b) * mult_fn(m.size * b)
    idx = (np.arange(n) + rng.integers(m.size)) % m.size
    w = np.log(m[idx])
    return w - w.mean()


def multifractal(kind: str, n: int, p: dict, rng: np.random.Generator, w_scale: float = 1.0):
    """(x, eps, w) for kind in mrw-lognormal, mrw-student, log-poisson, binomial-cascade, lmsv."""
    if kind == "mrw-student":   # heavy-tailed fGn: the fractional filter on Student-t innovations
        innov = rng.standard_t(p["df"], n)
        f = np.fft.rfftfreq(n)
        amp = np.ones_like(f)
        amp[1:] = f[1:] ** (-(2 * p["H"] - 1) / 2)
        eps = np.fft.irfft(amp * np.fft.rfft(innov), n=n)
        eps = (eps - eps.mean()) / eps.std()
    else:
        eps = fgn(n, p["H"], rng)
    if kind in ("mrw-lognormal", "mrw-student"):
        w = _log_correlated(n, p["lam2"], p["L"], rng)
    elif kind == "log-poisson":
        beta, lam = p["beta"], p["lam"]
        w = _discrete_cascade(n, p["b"], lambda k: beta ** rng.poisson(lam, k) * np.exp(lam * (1 - beta)), rng)
    elif kind == "binomial-cascade":
        pm = p["pm"]

        def mult(k):   # conservative: each pair of siblings gets (2pm, 2(1-pm)) in random order
            pair = np.where(rng.random(k // 2) < 0.5, 1, -1)
            return np.stack([1 + pair * (2 * pm - 1), 1 - pair * (2 * pm - 1)], axis=1).ravel()

        w = _discrete_cascade(n, 2, mult, rng)
    elif kind == "lmsv":
        w = fgn(n, p["Hw"], rng) * p["sw"]
    else:
        raise KeyError(kind)
    w = w * w_scale
    vol = np.exp(w)
    x = eps * vol / np.sqrt(np.mean(vol ** 2))
    return (x - x.mean()) / x.std(), eps, w


# ---------------------------------------------------------------------------------------------------
# long-lag autoregression
# ---------------------------------------------------------------------------------------------------
def longlag_simulate(a: np.ndarray, phi: float, L: int, e: np.ndarray) -> np.ndarray:
    """u_t = e_t + phi u_{t-L} on the innovations (white at every lag below L), then a short-range
    AR(p) with coefficients a driven by u."""
    n = e.size
    u = e.copy()
    for t in range(L, n):
        u[t] += phi * u[t - L]
    p = a.size
    if p == 0:
        return u
    x = np.zeros(n)
    for t in range(p, n):
        x[t] = u[t] + np.dot(a, x[t - p:t][::-1])
    return x


# ---------------------------------------------------------------------------------------------------
# replayed segments
# ---------------------------------------------------------------------------------------------------
def replay_series(i: int, length: int, replay_fraction=(0.15, 0.3), seg_range=(20, 60),
                  fidelity_range=(0.05, 0.2), phi_range=(0.3, 0.8)):
    """AR(1)-coloured noise (phi from phi_range) whose innovations replay 15-30% of their own past, in
    segments of 20-60 samples copied from random earlier positions with a little fresh noise."""
    rng = stream("replay-recurrence", "pair", i)
    phi = float(rng.uniform(*phi_range))
    e = rng.standard_normal(length + 200)
    rng.standard_normal(length + 200)   # a second stream of innovations, drawn but unused here
    frac = rng.uniform(*replay_fraction)
    fid = rng.uniform(*fidelity_range)
    e1 = e.copy()
    covered = n_rep = 0
    t = 200 + length // 4               # replays start after the first quarter so sources exist
    while t < e.size - seg_range[1] and covered < frac * length:
        L = int(rng.integers(seg_range[0], seg_range[1] + 1))
        src = int(rng.integers(200, t - L))
        e1[t:t + L] = e1[src:src + L] + fid * rng.standard_normal(L)
        covered += L
        n_rep += 1
        t += L + int(rng.integers(seg_range[0], 3 * seg_range[1]))
    x = np.zeros(e1.size)
    for k in range(1, x.size):
        x[k] = phi * x[k - 1] + e1[k]
    x = x[200:] * np.sqrt(1 - phi ** 2)
    x = (x - x.mean()) / x.std()
    return x, dict(phi=phi, replay_fraction=covered / length, n_replays=n_rep, replay_noise=fid)


# ---------------------------------------------------------------------------------------------------
# phase-amplitude coupling
# ---------------------------------------------------------------------------------------------------
PAC_SYSTEMS = {   # slow period range, fast period range, phase-jitter strength
    "theta-gamma-narrow": dict(slow=(40, 60), fast=(5, 7), jitter=0.03),
    "theta-gamma-broad": dict(slow=(40, 60), fast=(5, 7), jitter=0.10),
    "delta-beta": dict(slow=(70, 90), fast=(8, 11), jitter=0.05),
    "alpha-gamma": dict(slow=(24, 32), fast=(4, 5.5), jitter=0.05),
}


def _narrowband_phase(n: int, period: float, jitter: float, rng: np.random.Generator) -> np.ndarray:
    """Phase of a rhythm whose instantaneous frequency wanders slowly (smoothed multiplicative jitter)."""
    w = rng.standard_normal(n)
    k = max(3, int(period * 3))
    w = np.convolve(w, np.ones(k) / k, mode="same")
    w = w / (w.std() + 1e-12)
    return 2 * np.pi * np.cumsum((1.0 / period) * (1.0 + jitter * w)) + rng.uniform(0, 2 * np.pi)


def pac_series(i: int, length: int, systems: dict | None = None, sigma: float = 0.8, kappa: float = 0.6,
               a_fast: float = 0.5):
    """x = slow + a_fast (1 + kappa cos(phi_slow - phi0)) fast + noise: the fast rhythm's envelope follows
    the slow rhythm's phase. Instance i runs through the systems in turn (instances per system grow
    with i), and the result is rank-remapped onto a reference marginal pooled with an envelope driven
    by an independent slow phase."""
    systems = systems or PAC_SYSTEMS
    names = list(systems)
    n = i + 1
    while len(names) * max(1, n // len(names)) <= i:
        n *= 2
    per = max(1, n // len(names))
    sname, rep = names[i // per], i % per
    cfg = systems[sname]
    rng = stream("pac-bandmatched", sname, rep)
    ps, pf = rng.uniform(*cfg["slow"]), rng.uniform(*cfg["fast"])
    phi = _narrowband_phase(length, ps, cfg["jitter"], rng)
    phi_indep = _narrowband_phase(length, ps, cfg["jitter"], rng)
    psi = _narrowband_phase(length, pf, cfg["jitter"], rng)
    phi0 = rng.uniform(0, 2 * np.pi)
    noise = rng.standard_normal(length)
    slow, carrier = np.cos(phi), np.cos(psi)

    def raw(driver):
        x = slow + a_fast * (1.0 + kappa * np.cos(driver - phi0)) * carrier
        x = x + sigma * x.std() * noise
        return (x - x.mean()) / x.std()

    r1, r0 = raw(phi), raw(phi_indep)
    return rank_remap(r1, np.sort(np.concatenate([r1, r0]))[::2]), dict(
        system=sname, slow_period=ps, fast_period=pf)


# ---------------------------------------------------------------------------------------------------
# quadratic phase coupling
# ---------------------------------------------------------------------------------------------------
# scalar libm for the trig and real per-element arithmetic throughout: numpy's vectorised complex
# arithmetic is not bit-identical between allocations (SIMD/FMA paths depend on alignment)
def _complex_ou(n: int, tau: float, rng: np.random.Generator) -> np.ndarray:
    """Unit-variance complex OU envelope with correlation time tau samples."""
    rho = np.exp(-1.0 / tau)
    z = np.zeros(n + 500, dtype=complex)
    z[0] = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2)
    innov = (rng.standard_normal(n + 500) + 1j * rng.standard_normal(n + 500)) / np.sqrt(2)
    a = np.sqrt(1 - rho ** 2)
    for t in range(1, z.size):
        z[t] = rho * z[t - 1] + a * innov[t]
    return z[500:]


def _cos_sin(f: float, n: int):
    w = 2 * np.pi * f
    return np.array([math.cos(w * t) for t in range(n)]), np.array([math.sin(w * t) for t in range(n)])


def _real_tone(env_abs, phase, c, s_):
    """Re[|env| e^{i phase} (c + i s)] with real arithmetic only."""
    pc = np.array([math.cos(v) for v in phase])
    ps = np.array([math.sin(v) for v in phase])
    return env_abs * (pc * c - ps * s_)


def qpc_series(i: int, length: int, sigma: float = 0.5, f_range=(0.03, 0.18), tau_range=(20, 120),
               coupling_amp: float = 1.0, biphase: float = np.pi / 2):
    """Three narrowband components at f1, f2 and f1 + f2 with complex-OU envelopes (coherence time tau);
    the third's phase is theta1 + theta2 + biphase at every instant, its amplitude independent. The
    result is rank-remapped onto a reference marginal pooled with an uncoupled third component."""
    rng = stream("qpc-bispectral", "pair", i)
    while True:
        f1, f2 = rng.uniform(*f_range, 2)
        if abs(f1 - f2) > 0.02 and f1 + f2 < 0.45:
            break
    tau = float(np.exp(rng.uniform(np.log(tau_range[0]), np.log(tau_range[1]))))
    e1, e2, e3 = (_complex_ou(length, tau, rng) for _ in range(3))
    e1p, e2p = _complex_ou(length, tau, rng), _complex_ou(length, tau, rng)
    noise = rng.standard_normal(length)
    c1, s1 = _cos_sin(f1, length)
    c2, s2 = _cos_sin(f2, length)
    c3, s3 = _cos_sin(f1 + f2, length)
    a1, a2, a3 = (np.array([abs(v) for v in e]) for e in (e1, e2, e3))
    x1c = _real_tone(a1, np.array([cmath.phase(v) for v in e1]), c1, s1)
    x2c = _real_tone(a2, np.array([cmath.phase(v) for v in e2]), c2, s2)
    ph3 = np.array([cmath.phase(a) + cmath.phase(b) + biphase for a, b in zip(e1, e2)])
    ph3u = np.array([cmath.phase(a) + cmath.phase(b) + biphase for a, b in zip(e1p, e2p)])
    x3c, x3u = _real_tone(a3, ph3, c3, s3), _real_tone(a3, ph3u, c3, s3)
    base = x1c + x2c
    x1 = base + coupling_amp * x3c + sigma * noise
    x0 = base + coupling_amp * x3u + sigma * noise
    x1 = rank_remap(x1, np.sort(np.concatenate([x1, x0]))[::2])
    x1 = (x1 - x1.mean()) / x1.std()
    band = "tau20-40" if tau < 40 else "tau40-60" if tau < 60 else "tau60-120"
    return x1, dict(system=band, f1=float(f1), f2=float(f2), tau=tau)
