"""Class N, physiology: named models of physiological processes (55)."""
from __future__ import annotations

import math

import numpy as np

from ..registry import family
from ..util import ar_filter, bin_events, burn, burstiness, em_sde, fgn, powerlaw_noise, rk4

PHYS = dict(domain="physiology", linear="no", gaussian="no", stationary="yes")


# --------------------------------------------------------------------------
# heart
# --------------------------------------------------------------------------


def _rr_ipfm(n_beats, rng, lf=0.1, hf=0.25, a_lf=0.05, a_hf=0.03, beta=1.0, a_1f=0.03, T0=0.9, white=0.01):
    """Integral pulse frequency modulation: beats fire when the integral of a modulating signal
    crosses multiples of T0. Modulator = LF (Mayer) + HF (respiratory) sinusoids + 1/f^beta + white."""
    dt = 0.05
    n = int(n_beats * T0 / dt * 1.3) + 100
    t = np.arange(n) * dt
    m = (1 + a_lf * np.sin(2 * np.pi * lf * t + rng.uniform(0, 2 * np.pi))
         + a_hf * np.sin(2 * np.pi * hf * t + rng.uniform(0, 2 * np.pi))
         + a_1f * powerlaw_noise(n, beta, rng) + white * rng.standard_normal(n))
    integ = np.cumsum(m) * dt
    targets = T0 * np.arange(1, n_beats + 2)
    targets = targets[targets < integ[-1]]
    beats = np.interp(targets, integ, t)  # linear interpolation of the crossing time
    return np.diff(beats)


@family("N", "rr-ipfm", 6, {**PHYS, "reversible": "no"}, profiles={"stationary1000": 9})
def rr_ipfm(i, rng, T, S):
    """RR intervals from an IPFM model driven by LF (0.1 Hz) and HF (0.25 Hz) modulation, 1/f^beta
    (beta S[0.8, 1.3]) and white noise; LF/HF power ratio S[0.3, 4]; 1000 beats."""
    beta = S.draw("beta", 0.8, 1.3)
    ratio = S.draw("lf_hf", 0.3, 4.0, log=True)
    a_hf = rng.uniform(0.02, 0.05)
    a_lf = a_hf * math.sqrt(ratio)
    T0 = rng.uniform(0.7, 1.1)
    rr = _rr_ipfm(T + 50, rng, a_lf=a_lf, a_hf=a_hf, beta=beta, T0=T0)
    from ..registry import profile as _pp
    return rr[-T:], dict(beta=beta, lf_hf=ratio, T0=T0, spectral_beta=beta, observed="RR-intervals-s", **({"a_hf": a_hf} if _pp() == "stationary1000" else {}))


@family("N", "rr-ectopic", 3, {**PHYS, "event_like": "yes", "bursty": "yes", "heavy_tailed": "yes", "reversible": "no"})
def rr_ectopic(i, rng, T, S):
    """RR intervals with premature ectopic beats (rate LU[1, 6]% of beats): a short coupling
    interval followed by a compensatory pause."""
    rate = S.draw("ectopy_rate", 0.01, 0.06, log=True)  # >= ~10 ectopic beats per record
    T0 = rng.uniform(0.7, 1.1)
    rr = _rr_ipfm(T + 50, rng, T0=T0)[-T:]
    hit = np.flatnonzero(rng.uniform(size=T - 1) < rate)
    for k in hit:
        c = rng.uniform(0.5, 0.7)
        rr[k], rr[k + 1] = c * rr[k], rr[k] * (2 - c)
    from ..registry import profile as _pp
    return rr, dict(ectopy_rate=rate, n_ectopic=int(hit.size), event_rate=rate, observed="RR-intervals-s", **({"T0": T0} if _pp() == "stationary1000" else {}))


@family("N", "rr-af", 3, {**PHYS, "reversible": "partly"})
def rr_af(i, rng, T, S):
    """RR intervals in atrial fibrillation: atrial impulses arrive as a Poisson stream (rate S[4, 9]/s)
    at an AV node with a refractory period (0.25-0.45 s) that lengthens after each conducted beat
    (concealed conduction) — the 'irregularly irregular' rhythm."""
    lam = S.draw("atrial_rate", 4.0, 9.0)
    tau_r = rng.uniform(0.25, 0.45)
    prol = rng.uniform(0.05, 0.2)
    t, last, rr, ref = 0.0, 0.0, [], tau_r
    while len(rr) < T:
        t += rng.exponential(1 / lam)
        if t - last >= ref:
            rr.append(t - last)
            last = t
            ref = tau_r + prol * rng.uniform()
        else:
            ref += 0.02 * prol  # concealed conduction lengthens refractoriness
    rr = np.array(rr[:T])
    return rr, dict(atrial_rate=lam, tau_r=tau_r, prolongation=prol, observed="RR-intervals-s", burstiness_B=burstiness(rr))


@family("N", "deboer", 3, {**PHYS, "reversible": "no"})
def deboer(i, rng, T, S):
    """DeBoer-type beat-to-beat baroreflex model: systolic pressure S_n, RR interval I_n and
    peripheral resistance coupled through a fast vagal and a slow sympathetic baroreflex, a
    Windkessel diastolic decay, and respiratory modulation of pressure; observe RR (i<2) or SBP."""
    resp_T = rng.uniform(3.0, 5.0)
    gain = S.draw("gain", 6.0, 18.0)
    n = T + 300
    S_, I_, R_ = np.full(n, 120.0), np.full(n, 0.9), np.full(n, 1.0)
    tt = 0.0
    f = lambda s: 18 * np.arctan((s - 120) / 18)
    for k in range(6, n):
        tt += I_[k - 1]
        D = S_[k - 1] * math.exp(-I_[k - 1] / (R_[k - 1] * 1.5))
        S_[k] = D + 40 * I_[k - 1] / 0.9 * 0.5 + 3.0 * math.sin(2 * math.pi * tt / resp_T) + 1.0 * rng.standard_normal()
        vag = gain * 0.4 * f(S_[k]) / 1000
        symp = gain * 0.6 * sum(f(S_[k - j]) for j in range(2, 6)) / 4 / 1000
        I_[k] = 0.9 + vag + symp + 0.01 * rng.standard_normal()
        I_[k] = min(1.6, max(0.4, I_[k]))
        R_[k] = 1.0 - 0.3 * sum(f(S_[k - j]) for j in range(2, 6)) / 4 / 100 + 0.01 * rng.standard_normal()
    x = I_ if i < 2 else S_
    return burn(x, T), dict(resp_period=resp_T, gain=gain, observed="RR" if i < 2 else "SBP")


# --------------------------------------------------------------------------
# ECG waveform
# --------------------------------------------------------------------------


@family("N", "ecgsyn", 4, {**PHYS, "periodic": "partly", "reversible": "no", "continuous_time": "yes"})
def ecgsyn(i, rng, T, S):
    """ECGSYN (McSharry et al. 2003): a trajectory around a limit cycle in (x, y) with Gaussian
    PQRST events in z; RR variability from Mayer (0.1 Hz) + respiratory (0.25 Hz) modulation;
    n_beats S[20, 40] in the 1000-sample record; R peak normalised to 1 mV, then 0.05 mV respiratory
    baseline wander and 0.03 mV noise added."""
    n_beats = S.draw("n_beats", 20, 40, log=True)  # >= 5 respiratory cycles of baseline wander per record
    hr = rng.uniform(55, 85)
    rr_mean = 60 / hr
    fs = T / (n_beats * rr_mean)
    th_i = np.array([-np.pi / 3, -np.pi / 12, 0, np.pi / 12, np.pi / 2])
    a_i = np.array([1.2, -5.0, 30.0, -7.5, 0.75])
    b_i = np.array([0.25, 0.1, 0.1, 0.1, 0.4])
    rr = _rr_ipfm(int(n_beats) + 40, rng, T0=rr_mean, a_lf=0.04, a_hf=0.03)
    beat_t = np.concatenate([[0.0], np.cumsum(rr)])
    dt = 1 / (fs * 8)
    n = int(T * 8) + int(8 * fs * rr_mean * 2)
    x, y, z = 1.0, 0.0, 0.0
    out = np.empty(n)
    t = 0.0
    for k in range(n):
        j = min(np.searchsorted(beat_t, t) - 1, rr.size - 1)
        w = 2 * np.pi / rr[max(j, 0)]
        th = math.atan2(y, x)
        al = 1 - math.sqrt(x * x + y * y)
        dth = (th - th_i + np.pi) % (2 * np.pi) - np.pi
        dz = -np.sum(a_i * dth * np.exp(-dth * dth / (2 * b_i * b_i))) - z
        x += dt * (al * x - w * y)
        y += dt * (al * y + w * x)
        z += dt * dz
        out[k] = z
        t += dt
    sig = out[int(8 * fs * rr_mean * 2)::8][:T]
    sig = sig / max(np.abs(sig).max(), 1e-9)  # R peak ~ 1 mV
    tt = np.arange(T) / fs
    sig = sig + 0.05 * np.sin(2 * np.pi * 0.25 * tt + rng.uniform(0, 2 * np.pi)) + 0.03 * rng.standard_normal(T)
    return sig, dict(n_beats=n_beats, hr=hr, fs=fs, period_samples=fs * rr_mean, measurement_noise="yes", noise_sigma=0.03)


# --------------------------------------------------------------------------
# respiration
# --------------------------------------------------------------------------


@family("N", "periodic-breathing", 3, {**PHYS, "continuous_time": "yes", "periodic": "partly", "reversible": "no"})
def periodic_breathing(i, rng, T, S):
    """Chemoreflex loop with circulatory delay (Mackey-Glass form): dC/dt = P - V(C(t - tau)) C,
    V = Vmax C^n / (theta^n + C^n); the ventilation drive V(t) is observed as a breathing
    waveform whose amplitude it modulates. Delay stratified from stable to periodic breathing
    (Cheyne-Stokes)."""
    from .G_flows import _dde
    tau = S.draw("tau", 5.0, 25.0)
    n_hill = 6.0
    f = lambda c, cd: 1.0 - (cd**n_hill / (1 + cd**n_hill)) * c * 1.5
    dt = 0.05
    C = _dde(f, tau, dt, int(T * 0.5 / dt) + 200, 1.0, int(200 / dt), rng)
    V = C**n_hill / (1 + C**n_hill)
    V = V[: int(T * 0.5 / dt)]
    Vs = V[:: max(1, V.size // T)][:T]
    t = np.arange(T)
    from ..registry import profile
    if profile() == "stationary1000":  # breath-to-breath variability in rate and depth
        ph = np.cumsum(2 * np.pi / 8.0 * (1 + 0.1 * rng.standard_normal(T)))
        breath = np.sin(ph) * (1 + 0.08 * rng.standard_normal(T))
    else:
        breath = np.sin(2 * np.pi * t / 8.0)
    return (0.2 + Vs) * breath, dict(tau=tau, period_samples=8.0, hill_n=n_hill)


# --------------------------------------------------------------------------
# neural mass / EEG
# --------------------------------------------------------------------------


def _sigm(v, e0=2.5, r=0.56, v0=6.0):
    return 2 * e0 / (1 + np.exp(r * (v0 - v)))


def _jansen_rit(u, A, B, a, b, C, p):
    y0, y1, y2, y3, y4, y5 = u
    return np.array([y3, y4, y5,
                     A * a * _sigm(y1 - y2) - 2 * a * y3 - a * a * y0,
                     A * a * (p + 0.8 * C * _sigm(C * y0)) - 2 * a * y4 - a * a * y1,
                     B * b * 0.25 * C * _sigm(0.25 * C * y0) - 2 * b * y5 - b * b * y2])


def _epileptor(u, x0, tau0):
    x1, y1, z, x2, y2, g = u
    f1 = x1**3 - 3 * x1**2 if x1 < 0 else (x2 - 0.6 * (z - 4) ** 2) * x1
    f2 = 0.0 if x2 < -0.25 else 6 * (x2 + 0.25)
    return np.array([y1 - f1 - z + 3.1, 1 - 5 * x1**2 - y1, (4 * (x1 - x0) - z) / tau0,
                     -y2 + x2 - x2**3 + 0.45 + 0.002 * g - 0.3 * (z - 3.5), (-y2 + f2) / 10.0, -0.01 * (g - 0.1 * x1)])


@family("N", "neural-mass", 8, {**PHYS, "continuous_time": "yes", "reversible": "no"}, profiles={"stationary1000": 11})
def neural_mass(i, rng, T, S):
    """Neural-mass EEG models: Jansen-Rit (input p stratified: noise-driven alpha, 3 Hz spike-wave,
    high-input), Wilson-Cowan with noise, Epileptor (Jirsa et al. 2014: seizure onset/offset cycles,
    bursty by construction). Sampled at ~250 Hz equivalent."""
    kind = ["jansen-rit", "jansen-rit", "jansen-rit", "wilson-cowan", "wilson-cowan", "epileptor", "epileptor", "epileptor", "jansen-rit", "epileptor"][i % 10]
    if kind == "jansen-rit":
        p_mean = S.draw("p", 60.0, 320.0)
        C = rng.uniform(120, 140)
        dt, k = 0.001, 4
        drift = lambda u: _jansen_rit(u, 3.25, 22.0, 100.0, 50.0, C, p_mean)
        out = em_sde(drift, lambda u: np.array([0, 0, 0, 0, 3.25 * 100 * 30.0, 0]), np.zeros(6), dt, T * k, rng, k, 3000)
        x = out[:, 1] - out[:, 2]
        return x, dict(kind=kind, p=p_mean, C=C, fs=1 / (dt * k))
    if kind == "wilson-cowan":
        P = S.draw("P_wc", 0.5, 1.5)
        sg = lambda v: 1 / (1 + np.exp(-v))
        c1, c2, c3, c4, Q = 16, 12, 15, 3, 0.0

        def drift(u):
            E, I = u
            return np.array([-E + sg(c1 * E - c2 * I + P - 5), (-I + sg(c3 * E - c4 * I + Q - 12)) / 1.0]) * 10
        dt, k = 0.002, 5
        out = em_sde(drift, lambda u: 0.15, [0.1, 0.1], dt, T * k, rng, k, 3000)
        return out[:, 0], dict(kind=kind, P=P)
    x0 = S.draw("x0", -2.1, -1.4)
    from ..registry import profile
    if profile() == "stationary1000" and i == 9:
        # just below the seizure threshold: sustained interictal spiking with no seizure cycles (the two seizing
        # Epileptors 006 and 009 were near-duplicates, 2026-09-26)
        x0 = -2.08
    tau0 = rng.uniform(100, 300)  # slow variable ~100 samples: several seizure cycles per record
    dt, k = 0.02, 100
    out = em_sde(lambda u: _epileptor(u, x0, tau0), lambda u: np.array([0.025, 0.025, 0, 0.25, 0.25, 0]),
                 [0.0, -5.0, 3.0, 0.0, 0.0, 0.0], dt, T * k, rng, k, 20000)
    x = -out[:, 0] + out[:, 3]
    if x0 == -2.08:
        return x, dict(kind="epileptor-interictal", x0=x0, tau0=tau0, bursty="yes", event_like="yes")
    return x, dict(kind=kind, x0=x0, tau0=tau0, bursty="yes", regime_switching="yes", event_like="partly")


# --------------------------------------------------------------------------
# neurons
# --------------------------------------------------------------------------


def _hh(u, I):
    V, m, h, n = u
    am = 0.1 * (V + 40) / (1 - np.exp(-(V + 40) / 10)) if abs(V + 40) > 1e-6 else 1.0
    bm = 4 * np.exp(-(V + 65) / 18)
    ah = 0.07 * np.exp(-(V + 65) / 20)
    bh = 1 / (1 + np.exp(-(V + 35) / 10))
    an = 0.01 * (V + 55) / (1 - np.exp(-(V + 55) / 10)) if abs(V + 55) > 1e-6 else 0.1
    bn = 0.125 * np.exp(-(V + 65) / 80)
    INa = 120 * m**3 * h * (V - 50)
    IK = 36 * n**4 * (V + 77)
    IL = 0.3 * (V + 54.387)
    return np.array([(I - INa - IK - IL) / 1.0, am * (1 - m) - bm * m, ah * (1 - h) - bh * h, an * (1 - n) - bn * n])


def _hr(u, I, r=0.005, s=4.0, xr=-1.6):
    x, y, z = u
    return np.array([y - x**3 + 3 * x**2 - z + I, 1 - 5 * x**2 - y, r * (s * (x - xr) - z)])


def _ml(u, I):
    V, w = u
    m_inf = 0.5 * (1 + np.tanh((V + 1.2) / 18))
    w_inf = 0.5 * (1 + np.tanh((V - 2) / 30))
    tau_w = 1 / np.cosh((V - 2) / 60)
    dV = (I - 4.4 * m_inf * (V - 120) - 8 * w * (V + 84) - 2 * (V + 60)) / 20
    return np.array([dV, 0.04 * (w_inf - w) / tau_w])


@family("N", "neuron", 8, {**PHYS, "continuous_time": "yes", "event_like": "partly", "reversible": "no"}, profiles={"stationary1000": 10})
def neuron(i, rng, T, S):
    """Neuron models with noisy input current: Hodgkin-Huxley (V; binned spikes), Izhikevich regular
    / chattering / intrinsically bursting, Morris-Lecar, Hindmarsh-Rose bursting (V; binned spikes)."""
    from ..registry import profile
    kinds = (["hh-V", "izh-RS", "izh-CH", "morris-lecar", "hr-V", "hh-irregular", "izh-RS", "izh-TC", "hr-V", "morris-lecar"] if profile() == "stationary1000"
             else ["hh-V", "hh-spikes", "izh-RS", "izh-CH", "izh-IB-spikes", "morris-lecar", "hr-V", "hr-spikes", "izh-CH", "hh-V"])
    kind = kinds[i % 10]
    if kind == "hh-irregular":  # just below rheobase: irregular noise-induced spikes between subthreshold oscillations
        I = rng.uniform(5.8, 6.2)
        out = em_sde(lambda u: _hh(u, I), lambda u: np.array([1.5, 0, 0, 0]), [-65.0, 0.05, 0.6, 0.32], 0.01, T * 50, rng, 50, 20000)
        return out[:, 0], dict(kind=kind, I=I, fs_kHz=2.0)
    if kind.startswith("hh"):
        I = S.draw("I_hh", 6.5, 14.0)  # above rheobase: tonic spiking, >= 20 spikes per record
        stat = profile() == "stationary1000"
        dt, k = 0.01, (50 if stat else 20)
        out = em_sde(lambda u: _hh(u, I), lambda u: np.array([3.0, 0, 0, 0]), [-65.0, 0.05, 0.6, 0.32], dt, T * k * (1 if kind == "hh-V" else 4), rng, k, 20000 if stat else 2000)
        V = out[:, 0]
        if kind == "hh-V":
            return V, dict(kind=kind, I=I, fs_kHz=1 / (dt * k))
        sp = np.flatnonzero((V[1:] > 0) & (V[:-1] <= 0))
        x = bin_events(sp / 4.0, T)
        return x, dict(kind=kind, I=I, discrete_valued="yes", event_like="yes", event_rate=sp.size / T)
    if kind.startswith("izh"):
        a, b, c, d = {"izh-RS": (0.02, 0.2, -65, 8), "izh-CH": (0.02, 0.2, -50, 2), "izh-IB-spikes": (0.02, 0.2, -55, 4),
                      "izh-TC": (0.02, 0.25, -65, 0.05)}[kind]
        I = S.draw("I_izh", 6.0, 14.0)  # above threshold for all three cell types
        if kind == "izh-TC":  # thalamo-cortical cell near threshold: sparse, irregular spikes and rebound bursts
            I = rng.uniform(1.5, 2.5)
        dt = 0.25
        n = T * (1 if kind != "izh-IB-spikes" else 8)
        v, u = -65.0, -13.0
        V = np.empty(n)
        for t in range(n):
            for _ in range(4):
                Ii = I + (3.0 if kind == "izh-TC" else 2.0) * rng.standard_normal()
                v += dt * (0.04 * v * v + 5 * v + 140 - u + Ii)
                u += dt * a * (b * v - u)
                if v >= 30:
                    v, u = c, u + d
            V[t] = min(v, 30.0)
        if kind != "izh-IB-spikes":
            return V, dict(kind=kind, I=I, bursty="yes" if kind == "izh-CH" else "no")
        sp = np.flatnonzero((V[1:] >= 29.9) & (V[:-1] < 29.9))
        return bin_events(sp / 8.0, T), dict(kind=kind, I=I, discrete_valued="yes", event_like="yes", bursty="yes", event_rate=sp.size / T)
    if kind == "morris-lecar":
        I = S.draw("I_ml", 80.0, 110.0)
        dt, k = 0.05, (50 if profile() == "stationary1000" else 20)
        out = em_sde(lambda u: _ml(u, I), lambda u: np.array([2.0, 0.0]), [-20.0, 0.1], dt, T * k, rng, k, 2000)
        return out[:, 0], dict(kind=kind, I=I)
    I = S.draw("I_hr", 1.5, 3.5)
    dt, k = 0.02, ((60 if profile() == "stationary1000" else 20) if kind == "hr-V" else 80)
    out = em_sde(lambda u: _hr(u, I), lambda u: np.array([0.05, 0, 0]), [-1.0, -5.0, 2.0], dt, T * k, rng, k, 20000)
    V = out[:, 0]
    if kind == "hr-V":
        return V, dict(kind=kind, I=I, bursty="yes")
    sp = np.flatnonzero((V[1:] > 1.0) & (V[:-1] <= 1.0))
    return bin_events(sp, T), dict(kind=kind, I=I, discrete_valued="yes", event_like="yes", bursty="yes", event_rate=sp.size / T)


# --------------------------------------------------------------------------
# metabolism, endocrine, circadian
# --------------------------------------------------------------------------


@family("N", "glucose-insulin", 3, {**PHYS, "continuous_time": "yes", "stationary": "partly", "reversible": "no"})
def glucose_insulin(i, rng, T, S):
    """Bergman minimal model with meals as gamma-shaped glucose appearance pulses at irregular
    times (bursty input) plus a Sturis-type ultradian oscillation from delayed insulin action;
    glucose sampled every 5 min over ~3.5 days."""
    from ..registry import profile
    stat = profile() == "stationary1000"
    p1, p2, p3, n_ = 0.03, 0.02, S.draw("p3", 5e-6, 2e-5, log=True), 0.14
    resistant = stat and i == 1
    if resistant:  # insulin resistance and reduced glucose effectiveness: large, slow post-meal excursions
        p1, p3 = 0.015, 3e-6
    Gb, Ib = 90.0, 10.0
    dt, k = 0.5, 10
    burn = int(1440 / dt)  # one day of meals before the record starts
    n = T * k + burn
    t = np.arange(n) * dt
    meal_times = []
    tm = rng.uniform(300, 500)
    while tm < t[-1]:
        meal_times.append(tm)
        tm += rng.uniform(180, 420)
    Ra = np.zeros(n)
    for m in meal_times:
        s = rng.uniform(2, 5) if stat else rng.uniform(20, 60)  # stationary: realistic appearance (peaks ~150-250 mg/dL)
        a = (t - m) / 30.0
        Ra += s * np.where(a > 0, a * np.exp(1 - a), 0.0)
    G, X, I = Gb, 0.0, Ib
    delay = [Ib] * int(30 / dt)
    x = np.empty(T)
    for s_ in range(n):
        Id = delay.pop(0)
        dG = -p1 * (G - Gb) - X * G + Ra[s_]
        dX = -p2 * X + p3 * (Id - Ib)
        dI = -n_ * (I - Ib) + 0.005 * max(G - 80, 0) * 1.0 + 0.3 * rng.standard_normal()
        G, X, I = G + dt * dG, X + dt * dX, max(0.0, I + dt * dI)
        delay.append(I)
        if s_ >= burn and (s_ - burn) % k == 0:
            x[(s_ - burn) // k] = G
    return x, dict(p3=p3, n_meals=len(meal_times), event_like="partly", bursty="partly", skewed="yes",
                   **({"kind": "insulin-resistant", "p1": p1} if resistant else {}))


@family("N", "circadian-hormone", 4, {**PHYS, "reversible": "no"})
def circadian_hormone(i, rng, T, S):
    """Kronauer circadian oscillator (the higher-order revised model of Jewett, Forger & Kronauer 1999) driven by a light-dark cycle, sampled hourly (i<2; the
    process is a forced van-der-Pol-type limit cycle with tau_x S[23.5, 25]) and pulsatile hormone
    secretion (Keenan-Veldhuis: renewal pulses of gamma mass through exponential clearance, sampled
    every 10 min; i>=2)."""
    if i < 2:
        tau_x = S.draw("tau_x", 23.5, 25.0)
        mu, q, kk = 0.13, 1 / 3, 0.55
        dt, k = 0.1, 10
        burn_h = 240
        n = T * k + int(burn_h / dt)
        x, xc = 0.5, 0.5
        out = np.empty(T)
        from ..registry import profile as _pf
        # day-to-day light exposure varies (weather, behaviour): the rhythm is entrained but not periodic
        daylight = rng.uniform(0.25, 1.0, int(n * dt / 24) + 2) if _pf() == "stationary1000" else None
        # i = 1 (stationary): irregular schedule, lights-on jittered +-4 h day to day, read out as a
        # melatonin-like nocturnal pulse instead of the oscillator state (review 2026-09-25: 000/001 too alike)
        melatonin = _pf() == "stationary1000" and i == 1
        onset = 7 + (4 * rng.uniform(-1, 1, daylight.size) if melatonin else np.zeros(daylight.size if daylight is not None else 1))
        for s in range(n):
            th = (s * dt) % 24
            L = daylight[int(s * dt // 24)] if daylight is not None else 1.0
            on = onset[int(s * dt // 24)] if melatonin else 7
            B = 0.3 * L * (1 if on < th < on + 16 else 0.0) * (1 - 0.4 * x) * (1 - 0.4 * xc)
            dx = (math.pi / 12) * (xc + mu * (x / 3 + 4 * x**3 / 3 - 256 * x**7 / 105) + B)
            dxc = (math.pi / 12) * (q * B * xc - x * ((24 / (0.99669 * tau_x)) ** 2 + kk * B))
            x += dt * dx + 0.01 * math.sqrt(dt) * rng.standard_normal()
            xc += dt * dxc
            s2 = s - int(burn_h / dt)
            if s2 >= 0 and s2 % k == 0:
                out[s2 // k] = x
        if melatonin:
            out = np.maximum(0.0, -out - 0.3) ** 1.5
            out += 0.02 * out.std() * rng.standard_normal(T)
            return out, dict(kind="kronauer-forger-melatonin", tau_x=tau_x, period_samples=24.0, periodic="partly",
                             continuous_time="yes", skewed="yes")
        return out, dict(kind="kronauer-forger", tau_x=tau_x, period_samples=24.0, periodic="partly", continuous_time="yes")
    rate = S.draw("pulses_per_series", 20, 60, log=True)
    mean_iv = T / rate
    half_life = rng.uniform(3, 10)
    times = []
    tt = 0.0
    while tt < T:
        tt += rng.weibull(2.5) * mean_iv / 0.887
        times.append(tt)
    t = np.arange(T)
    conc = np.zeros(T)
    for tm in times:
        mass = rng.gamma(2.0, 1.0)
        conc += mass * np.where(t >= tm, np.exp(-(t - tm) * math.log(2) / half_life), 0.0)
    conc += 0.05 * conc.std() * rng.standard_normal(T)
    return conc, dict(kind="keenan-veldhuis", n_pulses=len(times), half_life=half_life, event_like="yes",
                      bursty="partly", skewed="yes", event_rate=len(times) / T)


# --------------------------------------------------------------------------
# gene regulation and cell signalling
# --------------------------------------------------------------------------


def _goodwin(u, n, a, b, c):
    x, y, z = u
    return np.array([1 / (1 + z**n) - a * x, x - b * y, y - c * z])


def _repressilator(u, alpha, alpha0, beta, n):
    m1, m2, m3, p1, p2, p3 = u
    return np.array([-m1 + alpha / (1 + p3**n) + alpha0, -m2 + alpha / (1 + p1**n) + alpha0, -m3 + alpha / (1 + p2**n) + alpha0,
                     -beta * (p1 - m1), -beta * (p2 - m2), -beta * (p3 - m3)])


def _goldbeter(u, beta, v0=1.0, v1=7.3, k=10.0, kf=1.0, VM2=65.0, VM3=500.0, K2=1.0, KR=2.0, KA=0.9, m=2, n=2, p=4):
    Z, Y = u
    v2 = VM2 * Z**n / (K2**n + Z**n)
    v3 = VM3 * Y**m / (KR**m + Y**m) * Z**p / (KA**p + Z**p)
    return np.array([v0 + v1 * beta - v2 + v3 + kf * Y - k * Z, v2 - v3 - kf * Y])


@family("N", "gene-cell", 6, {**PHYS, "reversible": "no"})
def gene_cell(i, rng, T, S):
    """Goodwin oscillator (n = 10), the repressilator (Elowitz-Leibler), telegraph-model
    transcription by Gillespie SSA (bursty integer mRNA counts sampled at fixed intervals, x2),
    Goldbeter calcium-induced calcium release oscillations (x2, stimulation beta stratified)."""
    from ..registry import profile
    kind = (["telegraph-ssa", "telegraph-ssa", "telegraph-ssa", "telegraph-ssa", "goldbeter", "goldbeter"] if profile() == "stationary1000"
            else ["goodwin", "repressilator", "telegraph-ssa", "telegraph-ssa", "goldbeter", "goldbeter"])[i]
    if kind == "goodwin":
        n = 10.0
        out = rk4(lambda u: _goodwin(u, n, 0.5, 0.5, 0.5), [0.1, 0.1, 0.1], 0.05, 40 * T + 40000)[40000::40]
        x = out[:T, 0]
        return x + 0.01 * x.std() * rng.standard_normal(T), dict(kind=kind, n=n, periodic="yes", continuous_time="yes", measurement_noise="yes", noise_sigma=0.01)
    if kind == "repressilator":
        alpha = S.draw("alpha_rep", 100.0, 1000.0, log=True)
        out = rk4(lambda u: _repressilator(u, alpha, 1.0, 5.0, 2.0), [0.1, 0.2, 0.3, 0.0, 0.0, 0.0], 0.02, 30 * T + 20000)[20000::30]
        x = out[:T, 3]
        return x + 0.01 * x.std() * rng.standard_normal(T), dict(kind=kind, alpha=alpha, periodic="yes", continuous_time="yes", measurement_noise="yes", noise_sigma=0.01)
    if kind == "telegraph-ssa":
        from ..registry import profile as _pf
        kon = S.draw("k_on", 0.05, 0.3, log=True) if _pf() == "stationary1000" else S.draw("k_on", 0.02, 0.2, log=True)
        koff = rng.uniform(0.1, 0.5)
        km, gam = rng.uniform(5, 30), 0.1
        state, m, t = 0, 0, 0.0
        sample_dt = 1.0
        x = np.empty(T)
        nxt = 0.0
        j = 0
        while j < T:
            rates = np.array([kon if state == 0 else koff, km * state, gam * m])
            tot = rates.sum()
            tau = rng.exponential(1 / tot) if tot > 0 else 1e9
            while nxt < t + tau and j < T:
                x[j] = m
                nxt += sample_dt
                j += 1
            t += tau
            r = rng.uniform() * tot
            if r < rates[0]:
                state = 1 - state
            elif r < rates[0] + rates[1]:
                m += 1
            else:
                m = max(0, m - 1)
        from ..registry import profile
        if profile() == "stationary1000":  # protein readout: translation and dilution of the bursty mRNA count
            kp, gp = 2.0, 0.2  # protein lifetime ~5 samples: bursts stay distinct
            prot = np.zeros(T)
            p = kp * float(np.mean(x)) / gp  # start at the steady state, not at zero
            for t in range(T):
                p += kp * x[t] - gp * p
                prot[t] = p
            return prot, dict(kind="telegraph-ssa-protein", k_on=kon, k_off=koff, k_m=km, bursty="yes", skewed="yes", regime_switching="yes")
        return x, dict(kind=kind, k_on=kon, k_off=koff, k_m=km, discrete_valued="yes", bursty="yes", skewed="yes", regime_switching="yes")
    beta = S.draw("beta_ca", 0.3, 0.9)
    from ..registry import profile as _pf
    if _pf() == "stationary1000":  # intrinsic (channel) noise: a noisy calcium oscillator, not a clean limit cycle
        out = em_sde(lambda u: _goldbeter(u, beta), lambda u: 0.3 * np.sqrt(np.abs(u)), [0.5, 1.0], 0.001, 40 * T, rng, 40, 5000)
        out = np.abs(out)
    else:
        out = rk4(lambda u: _goldbeter(u, beta), [0.5, 1.0], 0.001, 40 * T + 5000)[5000::40]
    x = out[:T, 0]
    return x + 0.02 * x.std() * rng.standard_normal(T), dict(kind=kind, beta=beta, periodic="yes", continuous_time="yes", event_like="partly", measurement_noise="yes", noise_sigma=0.02)


# --------------------------------------------------------------------------
# movement
# --------------------------------------------------------------------------


@family("N", "gait-emg-tremor", 4, {**PHYS})
def gait_emg_tremor(i, rng, T, S):
    """Stride-interval series with fractal fluctuations (Hausdorff: 1.1 s + 0.03 fGn_H, H S[0.6, 0.9];
    x2), surface EMG (Gaussian carrier gated by a bursting envelope at the gait cycle), and
    physiological tremor (8-12 Hz narrowband at 100 Hz sampling)."""
    kind = ["gait", "gait", "emg", "tremor"][i]
    if kind == "gait":
        H = S.draw("H", 0.6, 0.9)
        return 1.1 + 0.03 * fgn(T, H, rng), dict(kind=kind, hurst_H=H, long_memory="yes", linear="yes", gaussian="yes")
    if kind == "emg":
        P = rng.uniform(80, 140)
        t = np.arange(T)
        env = 0.1 + np.clip(np.sin(2 * np.pi * t / P), 0, None) ** 2
        return env * rng.standard_normal(T), dict(kind=kind, period_samples=P, heteroskedastic="yes", bursty="yes")
    f = rng.uniform(0.08, 0.12)
    r = 0.97
    e = rng.standard_normal(T + 500)
    x = np.zeros(T + 500)
    for t in range(2, T + 500):
        x[t] = 2 * r * math.cos(2 * math.pi * f) * x[t - 1] - r * r * x[t - 2] + e[t]
    return burn(x, T) + 0.5 * rng.standard_normal(T), dict(kind=kind, period_samples=1 / f, linear="yes", gaussian="yes")
