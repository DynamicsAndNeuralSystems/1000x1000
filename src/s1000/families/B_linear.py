"""Class B: linear Gaussian, short memory. What varies is the spectrum."""
from __future__ import annotations

import numpy as np
from scipy import signal

from ..registry import family
from ..util import ar2_from_period, ar_filter, burn, ma_filter, stable_ar

LG = dict(linear="yes", gaussian="yes", stationary="yes", reversible="yes")
BURN = 2000


def _e(rng, T):
    return rng.standard_normal(T + BURN)


@family("B", "ar1", 10, LG, profiles={"stationary1000": 11})
def ar1(i, rng, T, S):
    """AR(1), phi stratified over (-0.98, 0.98); negative phi included."""
    phi = S.draw("phi", -0.98, 0.98)
    x = burn(ar_filter(_e(rng, T), [phi]), T)
    return x, dict(phi=phi, timescale_samples=-1 / np.log(abs(phi)) if abs(phi) > 0 else 0.0)


@family("B", "ar2", 14, LG, profiles={"stationary1000": 16})
def ar2(i, rng, T, S):
    """AR(2): half with complex roots (pseudo-period S[3, 80] samples, modulus
    S[0.5, 0.99]), half with two real roots."""
    if i % 2 == 0:
        P = S.draw("period", 3, 80, log=True)
        r = S.draw("modulus", 0.5, 0.99)
        a = ar2_from_period(P, r)
        info = dict(pseudo_period=P, modulus=r, period_samples=P, a=a)
    else:
        r1, r2 = S.draw("r1", -0.95, 0.95), rng.uniform(-0.95, 0.95)
        a = np.array([r1 + r2, -r1 * r2])
        info = dict(roots=[r1, r2], a=a)
    return burn(ar_filter(_e(rng, T), a), T), info


@family("B", "arp", 10, LG, profiles={"stationary1000": 11})
def arp(i, rng, T, S):
    """AR(p), p in 3..12, coefficients from reflection coefficients U(-0.8, 0.8)."""
    p = S.integer("p", 3, 12)
    for _ in range(50):  # keep the slowest mode under ~30 samples (spectral radius <= 0.97)
        a = stable_ar(p, rng, 0.8)
        comp = np.diag(np.ones(p - 1), -1)
        comp[0] = a
        if np.abs(np.linalg.eigvals(comp)).max() <= 0.97:
            break
    return burn(ar_filter(_e(rng, T), a), T), dict(p=p, a=a)


@family("B", "maq", 8, LG, profiles={"stationary1000": 9})
def maq(i, rng, T, S):
    """MA(q), q in 1..10, theta_j = U(-1, 1) r^j, r U[0.5, 0.95]; non-invertible cases allowed."""
    q = S.integer("q", 1, 10)
    r = rng.uniform(0.5, 0.95)
    th = rng.uniform(-1, 1, q) * r ** np.arange(1, q + 1)
    return burn(ma_filter(_e(rng, T), th), T), dict(q=q, theta=th)


@family("B", "arma", 10, LG, profiles={"stationary1000": 12})
def arma(i, rng, T, S):
    """ARMA(p, q), p, q <= 4."""
    p, q = S.integer("p", 1, 4), int(rng.integers(1, 5))
    a = stable_ar(p, rng, 0.8)
    th = rng.uniform(-1, 1, q) * rng.uniform(0.5, 0.95) ** np.arange(1, q + 1)
    return burn(ar_filter(ma_filter(_e(rng, T), th), a), T), dict(p=p, q=q, a=a, theta=th)


@family("B", "seasonal-arma", 8, {**LG, "periodic": "partly"}, profiles={"stationary1000": 9})
def seasonal_arma(i, rng, T, S):
    """Multiplicative seasonal AR: (1 - phi B)(1 - Phi B^s) x_t = e_t, s S[4, 60], Phi U[0.5, 0.95], phi U[-0.5, 0.5]."""
    s = S.integer("season", 4, 60)
    Phi = rng.uniform(0.5, 0.95)
    phi = rng.uniform(-0.5, 0.5)
    a = np.zeros(s + 1)
    a[0] = phi
    a[s - 1] += Phi
    a[s] += -phi * Phi
    return burn(ar_filter(_e(rng, T), a), T), dict(season=s, Phi=Phi, phi=phi, period_samples=s)


@family("B", "narrowband", 8, LG, profiles={"stationary1000": 9})
def narrowband(i, rng, T, S):
    """Butterworth band-pass (order 2) filtered noise: centre LU[0.05, 0.4] cycles/sample, Q LU[2, 30]."""
    fc = S.draw("fc", 0.05, 0.4, log=True)  # >= 50 cycles per record
    Q = S.draw("Q", 2, 30, log=True)
    bw = fc / Q
    lo, hi = max(fc - bw / 2, 1e-3), min(fc + bw / 2, 0.499)
    sos = signal.butter(2, [2 * lo, 2 * hi], btype="band", output="sos")
    x = signal.sosfilt(sos, _e(rng, T))
    return burn(x, T), dict(fc=fc, Q=Q, period_samples=1 / fc)


@family("B", "lowhigh-pass", 4, LG)
def lowhigh(i, rng, T, S):
    """Low-pass (even i) or high-pass (odd i) Butterworth-filtered noise, cutoff LU[0.02, 0.4], order U{2..8}."""
    fc = S.draw("fc", 0.02, 0.4, log=True)
    order = int(rng.integers(2, 9))
    sos = signal.butter(order, 2 * fc, btype="low" if i % 2 == 0 else "high", output="sos")
    return burn(signal.sosfilt(sos, _e(rng, T)), T), dict(fc=fc, order=order, kind="low" if i % 2 == 0 else "high")


@family("B", "random-spectrum", 4, LG)
def random_spectrum(i, rng, T, S):
    """A spectrum nobody named: log-PSD is a smooth Gaussian process in log-frequency, phases random."""
    f = np.fft.rfftfreq(T)
    u = np.zeros_like(f)
    u[1:] = np.log(f[1:])
    u[1:] = (u[1:] - u[1]) / (u[-1] - u[1])
    ell = S.draw("ell", 0.05, 0.4, log=True)
    amp_sd = rng.uniform(1.0, 3.0)
    K = np.exp(-0.5 * ((u[:, None] - u[None, :]) / ell) ** 2) + 1e-6 * np.eye(f.size)
    logA = amp_sd * np.linalg.cholesky(K) @ rng.standard_normal(f.size)
    A = np.exp(logA)
    A[0] = 0
    ph = rng.uniform(0, 2 * np.pi, f.size)
    x = np.fft.irfft(A * np.exp(1j * ph), n=T)
    return x / x.std(), dict(ell=ell, amp_sd=amp_sd)
