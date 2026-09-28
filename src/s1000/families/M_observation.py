"""Class M: observation effects. Each instance takes a base series that exists elsewhere in the
corpus (its id is recorded as ``base_id``; tags are inherited) and applies one transform.
Aliasing and oversampling integrate a flow directly at the extreme sampling rate."""
from __future__ import annotations

import math

import numpy as np
from scipy.integrate import solve_ivp

from ..registry import TAG_NAMES, family
from ..rng import rng_for

BASE_CLASSES = "ABCDEFGHIJKLN"


def _base(i, rng, exclude=("M",), skip=()):
    """A base series drawn from the corpus: class cycles through A..N (skipping M), family and index
    random within it. Returns (x, base_meta)."""
    from ..build import generate
    from ..registry import by_class, load_all, profile
    load_all()
    stationary_only = profile() == "stationary1000"
    reg = by_class()
    classes = [c for c in BASE_CLASSES if any(f.cls != "M" for f in reg[c])]  # K is empty in stationary1000
    for _ in range(20):
        cls = classes[i % len(classes)]
        if cls in skip:
            i += 1
            continue
        fams = [f for f in reg[cls] if f.cls != "M"]
        if stationary_only:
            fams = [f for f in fams if f.tags.get("stationary", "yes") != "no"]
        fam = fams[int(rng.integers(0, len(fams)))]
        idx = fam.indices()
        j = idx[int(rng.integers(0, len(idx)))]
        x, meta, _ = generate(fam, j)
        if not stationary_only or meta["stationary"] != "no":
            return x, meta
        i += 1
    raise RuntimeError("no stationary base found")


def _inherit(meta, transform, **extra):
    info = {k: meta[k] for k in TAG_NAMES}
    info.update(base_id=meta["id"], observation=transform, **extra)
    return info


@family("M", "quantised", 6, {}, profiles={"stationary1000": 0})
def quantised(i, rng, T, S):
    """Base series quantised to k in {2, 3, 4, 8, 16} equal-probability levels."""
    x, m = _base(i, rng)
    k = S.choice("k", [2, 3, 4, 8, 16])
    cuts = np.quantile(x, np.linspace(0, 1, k + 1)[1:-1])
    return np.searchsorted(cuts, x).astype(float), _inherit(m, "quantised", k=k, discrete_valued="yes", n_states=k)


@family("M", "clipped", 4, {})
def clipped(i, rng, T, S):
    """Base series clipped (saturated) at +-c SD about the mean, c S[0.5, 1.5]."""
    x, m = _base(i + 3, rng)
    c = S.draw("c", 0.5, 1.5)
    mu, sd = x.mean(), x.std()
    return np.clip(x, mu - c * sd, mu + c * sd), _inherit(m, "clipped", c=c)


@family("M", "missing-data", 4, {})
def missing_data(i, rng, T, S):
    """Missing fraction U[0.05, 0.4] in gaps of mean length LU[1, 30], filled by zero-order hold
    (even i) or linear interpolation (odd i)."""
    x, m = _base(i + 6, rng)
    frac = S.draw("fraction", 0.05, 0.4)
    gap = S.draw("gap", 1, 30, log=True)
    miss = np.zeros(T, dtype=bool)
    n_gaps = max(1, int(frac * T / gap))
    for s in rng.choice(T, n_gaps, replace=False):
        L = max(1, int(rng.exponential(gap)))
        miss[s:s + L] = True
    miss[0] = False
    y = x.copy()
    idx = np.arange(T)
    if i % 2 == 0:
        last = np.maximum.accumulate(np.where(~miss, idx, 0))
        y = x[last]
        fill = "zero-order-hold"
    else:
        y = np.interp(idx, idx[~miss], x[~miss])
        fill = "linear"
    return y, _inherit(m, "missing-data", fraction=float(miss.mean()), gap=gap, fill=fill)


@family("M", "irregular-sampling", 3, {})
def irregular_sampling(i, rng, T, S):
    """Base series sampled at jittered times (jitter U[0.1, 0.8] of the interval) and linearly
    re-interpolated to the grid."""
    from ..registry import profile
    if profile() == "stationary1000":
        return _irregular_times(i, rng, T, S)
    x, m = _base(i + 9, rng)
    jit = S.draw("jitter", 0.1, 0.8)
    t_obs = np.sort(np.arange(T) + jit * rng.uniform(-0.5, 0.5, T))
    y_obs = np.interp(t_obs, np.arange(T), x)
    return np.interp(np.arange(T), t_obs, y_obs), _inherit(m, "irregular-sampling", jitter=jit)


def _irregular_times(i, rng, T, S):
    """Irregular sampling as an instrument does it: a continuous-time base process is generated at k times
    the record length and read at T random times (a Poisson sampler, mean interval k samples); the values
    are recorded in sequence, with no re-gridding. Replaced jitter-and-re-interpolate (2026-09-26), which
    was nearly the identity on smooth bases."""
    from ..build import DEFAULT_TAGS
    from ..registry import by_class, load_all
    from ..rng import rng_for
    from ..util import Strat
    load_all()
    k = S.integer("mean_interval", 3, 6)
    reg = by_class()
    fams = [f for c in BASE_CLASSES for f in reg[c] if f.cls != "M" and f.tags.get("stationary", "yes") != "no"
            and f.tags.get("continuous_time") == "yes"]
    for attempt in range(20):
        fam = fams[int(rng.integers(0, len(fams)))]
        idx = fam.indices()
        j = idx[int(rng.integers(0, len(idx)))]
        sub = rng_for("irregular", fam.cls, fam.key, j, k)
        try:
            xb, info = fam.gen(j, sub, k * T, Strat(fam.name, j, fam.strat_n(), sub))
        except Exception:
            continue
        xb = np.asarray(xb, dtype=float)
        if xb.size != k * T or not np.all(np.isfinite(xb)) or xb.std() == 0:
            continue
        tags = dict(DEFAULT_TAGS, **fam.tags, **{t: info[t] for t in TAG_NAMES if t in info})
        if tags["stationary"] == "no" or tags.get("continuous_time") != "yes":
            continue
        gaps = 1 + rng.poisson(k - 1, T)  # intervals >= 1, mean k
        t_idx = np.cumsum(gaps)
        t_idx = t_idx[t_idx < k * T]
        if t_idx.size < T:
            continue
        out = dict(tags, base_family=fam.name, base_index=j, observation="irregular-sampling", mean_interval=k,
                   interval_cv=float(gaps.std() / gaps.mean()))
        return xb[t_idx[:T]], out
    raise RuntimeError("no continuous-time base could be generated at length k*T")


def _lorenz(t, u):
    x, y, z = u
    return [10 * (y - x), x * (28 - z) - y, x * y - 8 / 3 * z]


def _rossler(t, u):
    x, y, z = u
    return [-y - z, x + 0.2 * y, 0.2 + z * (x - 5.7)]


def _flow_at_ppp(kind, ppp, T, rng):
    f, x0, per = (_lorenz, [1.0, 1.0, 20.0], 0.75) if kind == "lorenz" else (_rossler, [1.0, 1.0, 0.0], 6.1)
    x0 = np.array(x0) * (1 + 0.05 * rng.standard_normal(3))
    dt = per / ppp
    n_burn = int(max(400, 30 * ppp))
    te = np.arange(n_burn + T) * dt
    sol = solve_ivp(f, (0, te[-1]), x0, t_eval=te, method="DOP853", rtol=1e-8, atol=1e-10)
    return sol.y[0, n_burn:]


FLOWTAGS = dict(deterministic="yes", chaotic="yes", linear="no", gaussian="no", stationary="yes",
                continuous_time="yes", reversible="no")


@family("M", "aliased", 4, FLOWTAGS)
def aliased(i, rng, T, S):
    """A chaotic flow undersampled: ppp U[2.5, 6] points per period."""
    ppp = S.draw("ppp", 2.5, 6.0)
    kind = "lorenz" if i % 2 == 0 else "rossler"
    return _flow_at_ppp(kind, ppp, T, rng), dict(observation="aliased", system=kind, ppp=ppp, period_samples=ppp)


@family("M", "oversampled", 3, FLOWTAGS)
def oversampled(i, rng, T, S):
    """A chaotic flow oversampled: ppp U[150, 400] (2.5-7 periods per series; stationary: U[40, 70], 14-25 periods)."""
    from ..registry import profile
    ppp = S.draw("ppp", 40, 70) if profile() == "stationary1000" else S.draw("ppp", 150, 400)  # 14-25 periods per record when stationary
    kind = "lorenz" if i % 2 == 0 else "rossler"
    return _flow_at_ppp(kind, ppp, T, rng), dict(observation="oversampled", system=kind, ppp=ppp, period_samples=ppp)


@family("M", "nonlinear-readout", 5, {})
def nonlinear_readout(i, rng, T, S):
    """Base series observed through x^2, |x|, exp(x), sign(x) or x * x_{t-1}."""
    x, m = _base(i + 12, rng)
    from ..registry import profile
    kind = ["square", "abs", "exp", "sign", "lagproduct"][i]
    if kind == "exp" and (m["heavy_tailed"] == "yes" or m["heteroskedastic"] == "yes"):
        kind = "abs"  # exp of a heavy-tailed base is a single spike
    if kind == "sign" and profile() == "stationary1000":
        kind = "cube"  # real-valued corpus
    z = (x - x.mean()) / x.std()
    if kind == "square":
        y = z * z
    elif kind == "abs":
        y = np.abs(z)
    elif kind == "exp":
        y = np.exp(z)
    elif kind == "sign":
        y = np.sign(z)
    elif kind == "cube":
        y = z**3
    else:
        y = np.concatenate([[0.0], z[1:] * z[:-1]])
    info = _inherit(m, "nonlinear-readout", readout=kind, gaussian="no", linear="no")
    if kind == "sign":
        info.update(discrete_valued="yes", n_states=2)
    if kind in ("square", "abs", "exp"):
        info.update(skewed="yes")
    return y, info


@family("M", "outliers", 4, {})
def outliers(i, rng, T, S):
    """Additive outliers at rate U[0.005, 0.05], size U[4, 10] SD, random sign."""
    x, m = _base(i + 15, rng)
    rate, size = S.draw("rate", 0.005, 0.05, log=True), rng.uniform(4, 10)
    hit = rng.uniform(size=T) < rate
    y = x + hit * size * x.std() * rng.choice([-1.0, 1.0], T)
    return y, _inherit(m, "outliers", rate=rate, size=size, heavy_tailed="yes", event_like="partly")


@family("M", "integrated", 3, {}, profiles={"stationary1000": 0})
def integrated(i, rng, T, S):
    """Cumulative sum of a stationary base series."""
    x, m = _base(i + 18, rng)
    return np.cumsum(x - x.mean()), _inherit(m, "integrated", stationary="no", nonstationary_kind="walk")


@family("M", "heavy-noise", 4, {}, profiles={"stationary1000": 7})
def heavy_noise(i, rng, T, S):
    """Base series under heavy white measurement noise, SNR U[-6, 0] dB."""
    from ..registry import profile
    # white noise under white noise is still white noise: skip i.i.d. (class A) bases in the stationary profile
    x, m = _base(i + 21, rng, skip=("A",) if profile() == "stationary1000" else ())
    snr = S.draw("snr_db", -6.0, 0.0)
    s = 10 ** (-snr / 20)
    return x + s * x.std() * rng.standard_normal(T), _inherit(m, "heavy-noise", snr_db=snr, noise_sigma=s,
                                                             measurement_noise="yes", deterministic="partly" if m["deterministic"] == "yes" else m["deterministic"])


@family("M", "downsampled", 0, {}, profiles={"stationary1000": 6})
def downsampled(i, rng, T, S):
    """A stationary base process generated at k x the record length (k S{2..5}) and decimated
    (anti-aliased) by k: the same process observed at a coarser sampling interval. Class A (i.i.d.) bases
    are skipped: decimating white noise yields only the anti-aliasing filter's band-limited noise. For the same reason a
    linear-Gaussian base whose decimated lag-1 autocorrelation is below 0.3 (e.g. AR(1) with |phi| small) is redrawn."""
    from scipy.signal import decimate
    from ..build import DEFAULT_TAGS, _keywords
    from ..registry import by_class, load_all, profile
    from ..rng import rng_for
    from ..util import Strat
    load_all()
    k = S.integer("factor", 2, 5)
    reg = by_class()
    classes = [c for c in BASE_CLASSES if any(f.cls != "M" for f in reg[c])]
    for attempt in range(20):
        cls = classes[(i + attempt) % len(classes)]
        if cls == "A":  # decimated i.i.d. noise only shows the anti-aliasing filter (band-limited noise): skip class A
            continue
        fams = [f for f in reg[cls] if f.cls != "M" and f.tags.get("stationary", "yes") != "no"]
        fam = fams[int(rng.integers(0, len(fams)))]
        idx = fam.indices()
        j = idx[int(rng.integers(0, len(idx)))]
        sub = rng_for("downsampled", fam.cls, fam.key, j, k)
        try:
            xb, info = fam.gen(j, sub, k * T, Strat(fam.name, j, fam.strat_n(), sub))
        except Exception:
            continue
        xb = np.asarray(xb, dtype=float)
        if xb.size != k * T or not np.all(np.isfinite(xb)) or xb.std() == 0:
            continue
        tags = dict(DEFAULT_TAGS, **fam.tags, **{t: info[t] for t in TAG_NAMES if t in info})
        if tags["stationary"] == "no":
            continue
        y = decimate(xb - xb.mean(), k, zero_phase=True) + xb.mean()
        yc = y[:T] - y[:T].mean()
        if tags["linear"] == "yes" and tags["gaussian"] == "yes" and abs(yc[1:] @ yc[:-1]) < 0.3 * (yc @ yc):
            continue  # a linear-Gaussian base with no memory left at the coarse scale is just filtered white noise
        out = dict(tags, base_family=fam.name, base_index=j, observation="downsampled", factor=k)
        return y[:T], out
    raise RuntimeError("no stationary base could be generated at length k*T")
