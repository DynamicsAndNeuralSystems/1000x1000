"""Shared generator machinery: stratified parameter draws, filters,
integrators, fGn, event binning, measurement noise."""
from __future__ import annotations

import math

import numpy as np
from scipy import signal
from scipy.integrate import solve_ivp

from .rng import rng_for

# --------------------------------------------------------------------------
# stratified draws
# --------------------------------------------------------------------------


class Strat:
    """Latin-hypercube draws for instance ``i`` of ``n`` in a family.

    ``draw(name, lo, hi)`` returns a value in bin ``perm[i]`` of ``n`` equal
    bins over [lo, hi] (log-spaced with ``log=True``), jittered uniformly within
    the bin. The permutation is addressed by (family, name) so each parameter
    is stratified independently and the assignment never depends on how many
    instances are generated or in what order. ``choice`` stratifies a discrete
    set the same way (each value appears ~n/k times).
    """

    def __init__(self, fam_name: str, i: int, n: int, rng: np.random.Generator):
        self.fam, self.i, self.n, self.rng = fam_name, i, n, rng

    def _bin(self, name: str) -> int:
        perm = rng_for(self.fam, "lhs", name).permutation(self.n)
        return int(perm[self.i])

    def draw(self, name: str, lo: float, hi: float, log: bool = False) -> float:
        b = self._bin(name)
        u = (b + self.rng.uniform()) / self.n
        if log:
            return float(math.exp(math.log(lo) + u * (math.log(hi) - math.log(lo))))
        return float(lo + u * (hi - lo))

    def choice(self, name: str, values):
        values = list(values)
        b = self._bin(name)
        return values[int(b * len(values) / self.n)]

    def integer(self, name: str, lo: int, hi: int) -> int:
        """Inclusive integer range, stratified."""
        return int(min(hi, math.floor(self.draw(name, lo, hi + 1))))


# --------------------------------------------------------------------------
# linear filters
# --------------------------------------------------------------------------


def ar_filter(e: np.ndarray, a) -> np.ndarray:
    """x_t = sum_k a_k x_{t-k} + e_t (a = [a_1..a_p]); zero initial state."""
    a = np.atleast_1d(np.asarray(a, dtype=float))
    return signal.lfilter([1.0], np.concatenate([[1.0], -a]), e)


def ma_filter(e: np.ndarray, theta) -> np.ndarray:
    """x_t = e_t + sum_j theta_j e_{t-j}."""
    theta = np.atleast_1d(np.asarray(theta, dtype=float))
    return signal.lfilter(np.concatenate([[1.0], theta]), [1.0], e)


def stable_ar(p: int, rng: np.random.Generator, kmax: float = 0.8) -> np.ndarray:
    """AR(p) coefficients from reflection coefficients in (-kmax, kmax): stable
    by construction (Levinson recursion)."""
    a = np.zeros(0)
    for k in range(1, p + 1):
        kk = rng.uniform(-kmax, kmax)
        a_new = np.empty(k)
        a_new[: k - 1] = a - kk * a[::-1]
        a_new[k - 1] = kk
        a = a_new
    return a


def ar2_from_period(period: float, modulus: float) -> np.ndarray:
    """AR(2) with complex roots of modulus r and pseudo-period P samples."""
    th = 2 * np.pi / period
    return np.array([2 * modulus * np.cos(th), -(modulus**2)])


def burn(x: np.ndarray, T: int) -> np.ndarray:
    return np.asarray(x, dtype=float)[-T:]


# --------------------------------------------------------------------------
# innovations
# --------------------------------------------------------------------------


def skew_innov(n: int, shape: float, rng: np.random.Generator) -> np.ndarray:
    """Centred, unit-variance gamma innovations: skewness 2/sqrt(shape)."""
    return (rng.gamma(shape, 1.0, n) - shape) / np.sqrt(shape)


def stable_innov(n: int, alpha: float, beta: float, rng: np.random.Generator) -> np.ndarray:
    """Alpha-stable draws (Chambers-Mallows-Stuck), scale 1, location 0."""
    U = rng.uniform(-np.pi / 2, np.pi / 2, n)
    W = rng.exponential(1.0, n)
    if abs(alpha - 1.0) < 1e-6:
        X = (2 / np.pi) * ((np.pi / 2 + beta * U) * np.tan(U)
                           - beta * np.log((np.pi / 2) * W * np.cos(U) / (np.pi / 2 + beta * U)))
        return X
    zeta = -beta * np.tan(np.pi * alpha / 2)
    xi = np.arctan(-zeta) / alpha
    X = ((1 + zeta**2) ** (1 / (2 * alpha)) * np.sin(alpha * (U + xi)) / np.cos(U) ** (1 / alpha)
         * (np.cos(U - alpha * (U + xi)) / W) ** ((1 - alpha) / alpha))
    return X


# --------------------------------------------------------------------------
# long memory
# --------------------------------------------------------------------------


def fgn(n: int, H: float, rng: np.random.Generator) -> np.ndarray:
    """Exact fractional Gaussian noise by Davies-Harte circulant embedding.
    Falls back to a spectral synthesis when the embedding is not positive
    (only happens for H very close to 1 at small n)."""
    k = np.arange(n + 1)
    gamma = 0.5 * (np.abs(k + 1) ** (2 * H) - 2 * np.abs(k) ** (2 * H) + np.abs(k - 1) ** (2 * H))
    row = np.concatenate([gamma[:n], gamma[n:0:-1]])  # length 2n circulant
    lam = np.fft.fft(row).real
    if np.min(lam) < 0:
        f = np.fft.rfftfreq(n)
        amp = np.zeros_like(f)
        amp[1:] = f[1:] ** (-(2 * H - 1) / 2)
        ph = rng.uniform(0, 2 * np.pi, f.size)
        x = np.fft.irfft(amp * np.exp(1j * ph), n=n)
        return (x - x.mean()) / x.std()
    m = 2 * n
    Z = rng.standard_normal(m) + 1j * rng.standard_normal(m)
    Z[0] = Z[0].real * np.sqrt(2)
    Z[n] = Z[n].real * np.sqrt(2)
    Z[n + 1:] = np.conj(Z[1:n][::-1])
    x = np.fft.ifft(np.sqrt(lam) * Z).real[:n] * np.sqrt(m / 2)
    return x / x.std() if x.std() > 0 else x


def arfima(n: int, d: float, rng: np.random.Generator, ar=(), ma=(), burn_in: int = 2000) -> np.ndarray:
    """ARFIMA(p, d, q) by truncated fractional-difference MA(inf) weights."""
    m = n + burn_in
    j = np.arange(1, m)
    w = np.concatenate([[1.0], np.cumprod((j - 1 + d) / j)])  # psi weights of (1-B)^-d
    e = rng.standard_normal(m)
    x = signal.fftconvolve(e, w)[:m]
    if len(ma):
        x = ma_filter(x, ma)
    if len(ar):
        x = ar_filter(x, ar)
    return x[-n:]


def powerlaw_noise(n: int, beta: float, rng: np.random.Generator) -> np.ndarray:
    """1/f^beta noise by spectral synthesis (unit variance)."""
    f = np.fft.rfftfreq(n)
    amp = np.zeros_like(f)
    amp[1:] = f[1:] ** (-beta / 2)
    ph = rng.uniform(0, 2 * np.pi, f.size)
    x = np.fft.irfft(amp * np.exp(1j * ph), n=n)
    return (x - x.mean()) / x.std()


# --------------------------------------------------------------------------
# continuous time
# --------------------------------------------------------------------------


def em_sde(drift, diffusion, x0, dt: float, n_steps: int, rng: np.random.Generator,
           obs_every: int = 1, burn_steps: int = 0):
    """Euler-Maruyama for dx = drift(x) dt + diffusion(x) dW (vector state).
    ``diffusion`` may return a scalar, a vector (diagonal) or None (=0).
    Returns the observed states, shape (n_obs, dim)."""
    x = np.array(x0, dtype=float)
    dim = x.size
    total = burn_steps + n_steps
    out = np.empty(((n_steps + obs_every - 1) // obs_every, dim))
    sq = np.sqrt(dt)
    k = 0
    for s in range(total):
        g = diffusion(x)
        dW = rng.standard_normal(dim) * sq if g is not None else 0.0
        x = x + np.asarray(drift(x), dtype=float) * dt + (g * dW if g is not None else 0.0)
        if s >= burn_steps and (s - burn_steps) % obs_every == 0:
            out[k] = x
            k += 1
    return out[:k]


def best_fit(sampler, rng: np.random.Generator, cdf=None, reference=None, n_tries: int = 12) -> np.ndarray:
    """Draw ``n_tries`` realisations and keep the one whose empirical distribution best matches the
    process's own law (smallest Kolmogorov-Smirnov distance to ``cdf``, or to a large reference
    sample when the law has no closed form). Without this an i.i.d. family of three is at the mercy
    of one unlucky draw; with it, each realisation is a fair picture of its marginal. Deterministic:
    every candidate comes from the instance's own stream."""
    from scipy import stats
    best, best_d = None, np.inf
    if cdf is None and reference is not None:
        reference = np.sort(np.asarray(reference, dtype=float))
    for _ in range(n_tries):
        x = np.asarray(sampler(rng), dtype=float)
        if cdf is not None:
            d = stats.kstest(x, cdf).statistic
        else:
            d = stats.ks_2samp(x, reference).statistic
        if d < best_d:
            best, best_d = x, d
    return best


def acf_time(x: np.ndarray, maxlag: int = 500) -> int:
    """First lag at which the autocorrelation drops below 1/e (samples)."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    v = x @ x
    if v == 0:
        return maxlag
    for k in range(1, maxlag):
        if (x[:-k] @ x[k:]) / v < np.exp(-1):
            return k
    return maxlag


def dominant_period(x: np.ndarray) -> float:
    """Period (samples) of the largest spectral peak, excluding DC; inf if flat."""
    x = np.asarray(x, dtype=float)
    F = np.abs(np.fft.rfft(x - x.mean()))
    F[0] = 0.0
    f = np.fft.rfftfreq(x.size)
    i = int(np.argmax(F))
    return float(1.0 / f[i]) if f[i] > 0 else float("inf")


def flow_series(f, x0, T: int, ppp: float, coord: int = 0, dt_probe: float = 0.01,
                t_probe: float = 200.0, burn_periods: float = 30.0, rtol: float = 1e-8,
                args=(), method: str = "DOP853", max_period: float | None = None):
    """One coordinate of an ODE flow resampled to ``ppp`` points per dominant
    period. A probe integration estimates the period; the main integration
    then covers ``burn_periods`` + T/ppp periods. Returns (x, period_time)."""
    probe_t = np.arange(0, t_probe, dt_probe)
    sol = solve_ivp(f, (0, t_probe), np.asarray(x0, float), t_eval=probe_t, method=method,
                    rtol=rtol, atol=rtol * 1e-2, args=args)
    if not sol.success or sol.y.shape[1] < probe_t.size:
        raise RuntimeError("probe integration failed")
    y = sol.y[coord, probe_t.size // 4:]
    per = dominant_period(y) * dt_probe
    if not np.isfinite(per) or per <= 0:
        per = t_probe / 20
    if max_period is not None:
        per = min(per, max_period)
    dt_obs = per / ppp
    n_burn = int(burn_periods * ppp)
    t_end = dt_obs * (n_burn + T)
    t_eval = np.arange(n_burn + T) * dt_obs
    sol = solve_ivp(f, (0, t_end), sol.y[:, -1], t_eval=t_eval, method=method,
                    rtol=rtol, atol=rtol * 1e-2, args=args)
    if not sol.success or sol.y.shape[1] < t_eval.size:
        raise RuntimeError("main integration failed")
    return sol.y[coord, n_burn:], per


def rk4(f, x0, dt: float, n_steps: int, args=()):
    """Fixed-step RK4 (for maps of ODEs where solve_ivp overhead is wasteful)."""
    x = np.array(x0, dtype=float)
    out = np.empty((n_steps, x.size))
    for i in range(n_steps):
        k1 = f(x, *args)
        k2 = f(x + 0.5 * dt * k1, *args)
        k3 = f(x + 0.5 * dt * k2, *args)
        k4 = f(x + dt * k3, *args)
        x = x + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        out[i] = x
    return out


# --------------------------------------------------------------------------
# events
# --------------------------------------------------------------------------


def bin_events(times: np.ndarray, T: int) -> np.ndarray:
    """Integer counts per unit bin over [0, T)."""
    times = np.asarray(times, dtype=float)
    times = times[(times >= 0) & (times < T)]
    return np.bincount(times.astype(int), minlength=T)[:T].astype(float)


def burstiness(intervals: np.ndarray) -> float:
    """Goh-Barabasi B = (sigma - mu) / (sigma + mu) of inter-event intervals."""
    iv = np.asarray(intervals, dtype=float)
    if iv.size < 3:
        return float("nan")
    s, m = iv.std(), iv.mean()
    return float((s - m) / (s + m)) if (s + m) > 0 else float("nan")


def renewal_times(interval_sampler, T: int, rng: np.random.Generator, n_max: int | None = None) -> np.ndarray:
    """Event times of a renewal process on [0, T): draws intervals until T."""
    t, out = 0.0, []
    n_max = n_max or 50 * T
    while t < T and len(out) < n_max:
        t += float(interval_sampler(rng))
        out.append(t)
    return np.array(out)[:-1] if out and out[-1] >= T else np.array(out)


# --------------------------------------------------------------------------
# measurement noise
# --------------------------------------------------------------------------


def deterministic_noise_sigma(rng: np.random.Generator) -> float:
    """The corpus-wide dial for deterministic families: 1/3 exactly zero,
    2/3 log-uniform on [0.005, 0.5] in units of the clean SD."""
    if rng.uniform() < 1 / 3:
        return 0.0
    return float(np.exp(rng.uniform(np.log(0.005), np.log(0.5))))


def add_noise(x: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if sigma <= 0:
        return x
    return x + sigma * x.std() * rng.standard_normal(x.size)


def zscore(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    s = x.std()
    return (x - x.mean()) / (s if s > 0 else 1.0)
