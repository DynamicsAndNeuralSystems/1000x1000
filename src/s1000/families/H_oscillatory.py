"""Class H: periodic, quasi-periodic, oscillatory deterministic."""
from __future__ import annotations

import math

import numpy as np

from ..registry import family
from ..util import add_noise, deterministic_noise_sigma, flow_series

PER = dict(deterministic="yes", chaotic="no", linear="na", gaussian="no", stationary="yes",
           periodic="yes", reversible="yes")


def _finish(x, rng, info):
    sig = deterministic_noise_sigma(rng)
    info = dict(info, noise_sigma=sig, measurement_noise="yes" if sig > 0 else "no",
                deterministic="partly" if sig > 0 else "yes")
    return add_noise(x, sig, rng), info


@family("H", "sinusoid", 5, {**PER, "linear": "yes"}, profiles={"stationary1000": 3})
def sinusoid(i, rng, T, S):
    """Pure sinusoid, points per period LU[2.2, 300] (near-Nyquist and very slow both present;
    the stationary profile stops at 60)."""
    from ..registry import profile
    # the stationary profile stops at 60 points per period (>= 16 cycles): 300 left ~3 cycles
    ppp = S.draw("ppp", 2.2, 60, log=True) if profile() == "stationary1000" else S.draw("ppp", 2.2, 300, log=True)
    ph = rng.uniform(0, 2 * np.pi)
    return _finish(np.sin(2 * np.pi * np.arange(T) / ppp + ph), rng, dict(period_samples=ppp))


@family("H", "harmonic", 7, PER, profiles={"stationary1000": 5})
def harmonic(i, rng, T, S):
    """Square, sawtooth, triangle, pulse train, or a random set of 2-20 harmonics with random phases."""
    from ..registry import profile
    kind = S.choice("kind", ["sawtooth", "triangle", "random"] if profile() == "stationary1000" else ["square", "sawtooth", "triangle", "pulse", "random"])
    P = S.draw("period", 8, 120, log=True)
    t = np.arange(T)
    ph = (t / P + rng.uniform()) % 1.0
    if kind == "triangle" and profile() == "stationary1000":
        kind = "random"  # the triangle wave duplicated the Rayleigh oscillator (H.cycle-shapes) in hctsa space
    if kind == "square":
        x = np.where(ph < 0.5, 1.0, -1.0)
    elif kind == "sawtooth":
        x = 2 * ph - 1
    elif kind == "triangle":
        x = 4 * np.abs(ph - 0.5) - 1
    elif kind == "pulse":
        duty = rng.uniform(0.05, 0.3)
        x = np.where(ph < duty, 1.0, 0.0)
    else:
        nh = int(rng.integers(2, 21))
        a0 = rng.uniform(0.2, 1.0, nh)  # same draws, same order as before: the raw amplitudes, then the decay exponent
        decay = rng.uniform(0.3, 1.5)
        amps = a0 / np.arange(1, nh + 1) ** decay
        phs = rng.uniform(0, 2 * np.pi, nh)
        x = sum(a * np.sin(2 * np.pi * (k + 1) * ph + p) for k, (a, p) in enumerate(zip(amps, phs)))
    info = dict(kind=kind, period_samples=P)
    if kind == "random" and profile() == "stationary1000":  # record the harmonic count and amplitude decay for the card
        info.update(n_harmonics=nh, decay=float(decay))
    if kind in ("square", "pulse"):
        info["discrete_valued"] = "yes"
    return _finish(x, rng, info)


@family("H", "quasiperiodic", 7, {**PER, "periodic": "no", "quasiperiodic": "yes", "linear": "yes"})
def quasiperiodic(i, rng, T, S):
    """2-torus (even i) or 3-torus (odd i): incommensurate frequencies (ratios near the golden mean
    and sqrt 2), random amplitudes."""
    P = S.draw("period", 6, 60, log=True)
    f1 = 1 / P
    g = (1 + 5**0.5) / 2
    fs = [f1, f1 * g ** rng.choice([-1, 1])]
    if i % 2 == 1:
        fs.append(f1 * 2**0.5 * rng.uniform(0.8, 1.2))
    fs = [f for f in fs if f < 0.45]
    amps = rng.uniform(0.4, 1.0, len(fs))
    t = np.arange(T)
    x = sum(a * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)) for a, f in zip(amps, fs))
    from ..registry import profile as _pp
    return _finish(x, rng, dict(frequencies=fs, period_samples=P, **({"amplitudes": [float(a) for a in amps]} if _pp() == "stationary1000" else {})))


@family("H", "modulated", 7, {**PER, "periodic": "partly", "stationary": "partly"}, profiles={"stationary1000": 0})
def modulated(i, rng, T, S):
    """AM, FM, linear chirp, exponential chirp, or beats."""
    kind = S.choice("kind", ["am", "fm", "chirp-linear", "chirp-exp", "beats"])
    P = S.draw("period", 8, 60, log=True)
    t = np.arange(T)
    f0 = 1 / P
    if kind == "am":
        fm = f0 / rng.uniform(5, 40)
        depth = rng.uniform(0.3, 1.0)
        x = (1 + depth * np.sin(2 * np.pi * fm * t)) * np.sin(2 * np.pi * f0 * t)
        par = dict(mod_period=1 / fm, depth=depth)
    elif kind == "fm":
        fm = f0 / rng.uniform(5, 40)
        dev = rng.uniform(0.2, 0.8) * f0
        ph = 2 * np.pi * np.cumsum(f0 + dev * np.sin(2 * np.pi * fm * t))
        x = np.sin(ph)
        par = dict(mod_period=1 / fm, deviation=dev)
    elif kind == "chirp-linear":
        f1 = min(0.45, f0 * rng.uniform(2, 6))
        ph = 2 * np.pi * np.cumsum(f0 + (f1 - f0) * t / T)
        x = np.sin(ph)
        par = dict(f_end=f1, stationary="no", nonstationary_kind="drift")
    elif kind == "chirp-exp":
        f1 = min(0.45, f0 * rng.uniform(2, 6))
        ph = 2 * np.pi * np.cumsum(f0 * (f1 / f0) ** (t / T))
        x = np.sin(ph)
        par = dict(f_end=f1, stationary="no", nonstationary_kind="drift")
    else:
        df = f0 / rng.uniform(8, 40)
        x = np.sin(2 * np.pi * f0 * t) + np.sin(2 * np.pi * (f0 + df) * t)
        par = dict(beat_period=1 / df)
    return _finish(x, rng, dict(kind=kind, period_samples=P, **par))


def _vdp(t, u, mu):
    x, v = u
    return [v, mu * (1 - x * x) * v - x]


def _stuart_landau(t, u, mu, w):
    x, y = u
    r2 = x * x + y * y
    return [(mu - r2) * x - w * y, (mu - r2) * y + w * x]


def _brusselator(t, u, a, b):
    x, y = u
    return [a + x * x * y - (b + 1) * x, b * x - x * x * y]


def _fhn(t, u, a, b, eps, I):
    v, w = u
    return [v - v**3 / 3 - w + I, eps * (v + a - b * w)]


def _duffing_periodic(t, u, d, g, w):
    x, v, th = u
    return [v, x - x**3 - d * v + g * math.cos(th), w]


@family("H", "limit-cycle", 10, {**PER, "continuous_time": "yes", "linear": "no"}, profiles={"stationary1000": {"indices": [0, 3, 6, 8, 16], "strat_n": 17}})  # one per distinct waveform (review 2026-09-25)
def limit_cycle(i, rng, T, S):
    """Limit cycles: van der Pol (mu S[0.1, 10], sinusoidal to relaxation), Stuart-Landau,
    Brusselator, FitzHugh-Nagumo (oscillatory), integrated and resampled to ppp S[15, 40]."""
    kind = ["vdp", "vdp", "vdp", "vdp", "stuart-landau", "brusselator", "brusselator", "fhn", "fhn", "vdp",
            "vdp", "brusselator", "fhn", "stuart-landau", "vdp", "brusselator", "fhn"][i % 17]
    ppp = S.integer("ppp", 15, 40)
    if kind == "vdp":
        mu = S.draw("mu", 0.1, 10.0, log=True)
        x, per = flow_series(_vdp, [0.5 + rng.uniform(), 0.0], T, ppp, args=(mu,), t_probe=400.0)
        par = dict(mu=mu)
    elif kind == "stuart-landau":
        mu, w = rng.uniform(0.5, 2.0), 1.0
        x, per = flow_series(_stuart_landau, [0.1, 0.0], T, ppp, args=(mu, w))
        par = dict(mu=mu)
    elif kind == "brusselator":
        a = rng.uniform(0.8, 1.2)
        b = rng.uniform(1 + a * a + 0.3, 1 + a * a + 2.0)
        x, per = flow_series(_brusselator, [a * 1.5, b / a * 0.5], T, ppp, args=(a, b))
        par = dict(a=a, b=b)
    else:
        I = rng.uniform(0.5, 1.2)
        x, per = flow_series(_fhn, [-1.0, -0.5], T, ppp, args=(0.7, 0.8, 0.08, I), t_probe=600.0)
        par = dict(I=I)
    return _finish(x, rng, dict(kind=kind, ppp=ppp, period_time=per, period_samples=ppp, **par))


def _logistic_orbit(r, T, rng):
    v = rng.uniform(0.1, 0.9)
    for _ in range(2000):
        v = r * v * (1 - v)
    x = np.empty(T)
    for t in range(T):
        v = r * v * (1 - v)
        x[t] = v
    return x


def _rossler(t, u, a, b, c):
    x, y, z = u
    return [-y - z, x + a * y, b + z * (x - c)]


def _lorenz(t, u, s, r, b):
    x, y, z = u
    return [s * (y - x), x * (r - z) - y, x * y - b * z]


@family("H", "period-doubled", 5, {**PER, "linear": "no"}, profiles={"stationary1000": 0})
def period_doubled(i, rng, T, S):
    """Period-doubled orbits: logistic map at period 2, 4, 8 (r in the cascade), Rossler c = 3.5
    (period-2 orbit), Lorenz rho = 350 (periodic)."""
    kind = ["logistic-p2", "logistic-p4", "logistic-p8", "rossler-p2", "lorenz-periodic"][i]
    if kind.startswith("logistic"):
        r = dict(**{"logistic-p2": 3.2, "logistic-p4": 3.5, "logistic-p8": 3.555})[kind]
        x = _logistic_orbit(r, T, rng)
        return _finish(x, rng, dict(kind=kind, r=r, period_samples=int(kind[-1]), discrete_valued="yes"))
    ppp = S.integer("ppp", 15, 40)
    if kind == "rossler-p2":
        x, per = flow_series(_rossler, [1.0, 1.0, 0.0], T, ppp, args=(0.1, 0.1, 3.5), t_probe=400.0)
    else:
        x, per = flow_series(_lorenz, [1.0, 1.0, 1.0], T, ppp, args=(10.0, 350.0, 8 / 3), coord=2, t_probe=100.0)
    return _finish(x, rng, dict(kind=kind, ppp=ppp, period_time=per, period_samples=ppp, continuous_time="yes"))


@family("H", "modulated-stationary", 0, {**PER, "periodic": "partly"}, profiles={"stationary1000": 6})
def modulated_stationary(i, rng, T, S):
    """AM, FM or beats (the stationary modulations; chirps are left to the full profile)."""
    kind = S.choice("kind", ["am", "fm", "beats"])
    P = S.draw("period", 8, 60, log=True)
    t = np.arange(T)
    f0 = 1 / P
    if kind == "am":
        fm = f0 / rng.uniform(5, 40)
        depth = rng.uniform(0.3, 1.0)
        # visible but slow envelope: >= 1.5 modulation cycles per record and depth >= 0.5 (000 had two-thirds of a cycle at
        # depth 0.31). Deeper slow envelopes fail the stationarity gate (window-variance ratio > 6 for class H) and get redrawn
        fm, depth = max(fm, 1.5 / T), max(depth, 0.5)
        x = (1 + depth * np.sin(2 * np.pi * fm * t)) * np.sin(2 * np.pi * f0 * t)
        par = dict(mod_period=1 / fm, depth=depth)
    elif kind == "fm":
        fm = f0 / rng.uniform(5, 40)
        dev = rng.uniform(0.2, 0.8) * f0
        x = np.sin(2 * np.pi * np.cumsum(f0 + dev * np.sin(2 * np.pi * fm * t)))
        par = dict(mod_period=1 / fm, deviation=dev)
    else:
        df_ = 1 / rng.uniform(40, 150)  # beat period 40-150 samples: >= 6 beats per record
        x = np.sin(2 * np.pi * f0 * t) + np.sin(2 * np.pi * (f0 + df_) * t)
        par = dict(beat_period=1 / df_)
    return _finish(x, rng, dict(kind=kind, period_samples=P, **par))


@family("H", "period-doubled-flows", 0, {**PER, "linear": "no", "continuous_time": "yes"}, profiles={"stationary1000": 2})
def period_doubled_flows(i, rng, T, S):
    """Periodic orbits of chaotic flows: Rossler c = 8.5 (a period-4 orbit of the doubling cascade; c = 3.5,
    a plain period-1 cycle, until 2026-09-26) and Lorenz rho = 350 (periodic)."""
    ppp = S.integer("ppp", 15, 40)
    if i % 2 == 0:
        x, per = flow_series(_rossler, [1.0, 1.0, 0.0], T, ppp, args=(0.1, 0.1, 8.5), coord=2, t_probe=400.0)  # z: a spike train of four heights
        kind = "rossler-p4"
    else:
        x, per = flow_series(_lorenz, [1.0, 1.0, 1.0], T, ppp, args=(10.0, 350.0, 8 / 3), coord=2, t_probe=100.0)
        kind = "lorenz-periodic"
    return _finish(x, rng, dict(kind=kind, ppp=ppp, period_time=per, period_samples=ppp))


def _hr_det(t, u, I, r=0.006, s_=4.0, xr=-1.6):
    x, y, z = u
    return [y - x**3 + 3 * x**2 - z + I, 1 - 5 * x**2 - y, r * (s_ * (x - xr) - z)]


def _rayleigh(t, u, mu):
    x, v = u
    return [v, mu * (1 - v * v) * v - x]


def _lv(t, u):
    x, y = u
    return [x * (1 - y), y * (x - 1)]


def _pendulum_free(t, u):
    th, w = u
    return [w, -math.sin(th)]


@family("H", "cycle-shapes", 0, {**PER, "continuous_time": "yes", "linear": "no"}, profiles={"stationary1000": 4})
def cycle_shapes(i, rng, T, S):
    """Periodic orbits with waveforms not otherwise in H: Hindmarsh-Rose periodic bursting (a train of
    spikes in every cycle), the Rayleigh oscillator (triangle-like), a conservative Lotka-Volterra
    orbit far from equilibrium (sharp pulses on a flat floor), and a pendulum librating just inside its
    separatrix (flat-topped, lingering at the turning points)."""
    kind = ["hr-bursting", "rayleigh", "lotka-volterra", "pendulum-separatrix"][i % 4]
    ppp = S.integer("ppp", 20, 35)
    if kind == "hr-bursting":
        I = rng.uniform(1.8, 2.3)
        x, per = flow_series(_hr_det, [-1.0, -5.0, 2.0], T, ppp * 3, args=(I,), t_probe=4000.0, burn_periods=5)
        par = dict(I=I, samples_per_burst_cycle=ppp * 3)
    elif kind == "rayleigh":
        mu = rng.uniform(2.0, 4.0)
        x, per = flow_series(_rayleigh, [0.5, 0.0], T, ppp, args=(mu,), t_probe=400.0)
        par = dict(mu=mu)
    elif kind == "lotka-volterra":
        x0 = rng.uniform(4.0, 6.0)
        x, per = flow_series(_lv, [x0, 1.0], T, ppp, t_probe=400.0)
        par = dict(x0=x0, reversible="yes")
    else:
        E = rng.uniform(0.97, 0.995) * 2.0  # separatrix energy is 2
        th0 = math.acos(1 - E)  # turning point, released from rest
        x, per = flow_series(_pendulum_free, [th0, 0.0], T, ppp, t_probe=400.0)
        par = dict(energy_fraction=E / 2.0, reversible="yes")
    return _finish(x, rng, dict(kind=kind, ppp=ppp, period_time=per, **par))
