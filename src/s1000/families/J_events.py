"""Class J: events, point processes, discrete states."""
from __future__ import annotations

import math

import numpy as np

from ..registry import family
from ..util import ar_filter, bin_events, burn, burstiness, renewal_times

EV = dict(linear="no", gaussian="no", stationary="yes", event_like="yes", discrete_valued="yes", skewed="yes")


@family("J", "poisson", 6, {**EV, "reversible": "yes", "bursty": "no"}, profiles={"stationary1000": 0})
def poisson(i, rng, T, S):
    """Poisson counts per bin, homogeneous (even i) or rate-modulated (sinusoid / ramp, odd i);
    mean count LU[0.1, 20]."""
    mean = S.draw("mean", 0.1, 20, log=True)
    t = np.arange(T)
    if i % 2 == 0:
        lam = np.full(T, mean)
        kind = "homogeneous"
    elif i % 4 == 1:
        P = rng.uniform(40, 300)
        lam = mean * (1 + 0.8 * np.sin(2 * np.pi * t / P))
        kind = "sinusoidal"
    else:
        lam = mean * np.linspace(0.3, 1.7, T)
        kind = "ramp"
    x = rng.poisson(lam).astype(float)
    return x, dict(kind=kind, mean=mean, event_rate=mean, stationary="yes" if kind == "homogeneous" else "no",
                   nonstationary_kind="none" if kind == "homogeneous" else ("trend" if kind == "ramp" else "drift"),
                   burstiness_B=0.0)


@family("J", "renewal", 8, {**EV, "bursty": "partly"}, profiles={"stationary1000": 9})
def renewal(i, rng, T, S):
    """Renewal process with gamma, log-normal, Weibull or Pareto intervals, mean interval S[5, 60];
    burstiness stratified over [-0.5, 0.8]; observed as a 0/1 event train (even i) or the interval sequence (odd i); the stationary profile uses intervals only."""
    mean = S.draw("mean_interval", 5, 60, log=True)
    B = S.draw("B", -0.5, 0.8)
    cv = (1 + B) / (1 - B)  # sigma/mu
    kind = S.choice("kind", ["gamma", "lognormal", "weibull", "pareto"])
    if kind == "gamma":
        k = 1 / cv**2
        samp = lambda r: r.gamma(k, mean / k)
    elif kind == "lognormal":
        s2 = math.log(1 + cv**2)
        samp = lambda r: r.lognormal(math.log(mean) - s2 / 2, math.sqrt(s2))
    elif kind == "weibull":
        from scipy.optimize import brentq
        from scipy.special import gamma as G
        f = lambda kk: math.sqrt(G(1 + 2 / kk) / G(1 + 1 / kk) ** 2 - 1) - cv
        kk = brentq(f, 0.15, 20.0) if f(0.15) * f(20.0) < 0 else 1.0
        scale = mean / G(1 + 1 / kk)
        samp = lambda r: scale * r.weibull(kk)
    else:
        a = max(2.05, 1 + math.sqrt(1 + 1 / cv**2))  # variance finite
        xm = mean * (a - 1) / a
        samp = lambda r: xm * (1 + r.pareto(a))
    from ..registry import profile
    if i % 2 == 0 and profile() != "stationary1000":
        times = renewal_times(samp, 4 * T, rng)
        x = bin_events(times, 4 * T)[-T:]
        iv = np.diff(times)
        return x, dict(kind=kind, mean_interval=mean, target_B=B, burstiness_B=burstiness(iv),
                       event_rate=1 / mean, bursty="yes" if B > 0.3 else "no")
    iv = np.array([samp(rng) for _ in range(T)])
    return iv, dict(kind=kind, mean_interval=mean, target_B=B, burstiness_B=burstiness(iv), observed="intervals",
                    event_like="no", discrete_valued="no", bursty="yes" if B > 0.3 else "no", reversible="yes")


def _bw() -> dict:
    """The smoothing bandwidth just drawn by _smoothed_rate, for the series' metadata (stationary profile)."""
    from ..registry import profile
    return {"smooth_bw": _smoothed_rate.last_bw} if profile() == "stationary1000" else {}


def _smoothed_rate(counts: np.ndarray, rng: np.random.Generator, bw_range=(2.0, 6.0)) -> np.ndarray:
    """Gaussian-kernel-smoothed event rate (bandwidth U[2, 6] samples) plus 2% white noise: the
    real-valued readout of a point process."""
    bw = rng.uniform(*bw_range)
    _smoothed_rate.last_bw = bw  # read back by the caller (_bw) so each series records its bandwidth
    k = np.arange(-int(4 * bw), int(4 * bw) + 1)
    ker = np.exp(-0.5 * (k / bw) ** 2)
    ker /= ker.sum()
    y = np.convolve(counts, ker, mode="same")
    return y + 0.02 * (y.std() or 1.0) * rng.standard_normal(y.size)


def _hawkes(T, mu, n_br, kernel, rng, decay=10.0, alpha_pl=1.5):
    """Ogata thinning with exponential (decay) or power-law kernel; returns event times on [0, T)."""
    times = []
    t = 0.0
    if kernel == "exp":
        lam_max = mu + n_br / decay * 50  # crude bound refreshed per step
    while t < T:
        rec = [s for s in times[-2000:] if t - s < 20 * decay]
        if kernel == "exp":
            lam_now = mu + sum(n_br / decay * math.exp(-(t - s) / decay) for s in rec)
        else:
            c = 1.0
            lam_now = mu + sum(n_br * (alpha_pl - 1) / c * (1 + (t - s) / c) ** (-alpha_pl) for s in rec)
        lam_bar = lam_now
        w = rng.exponential(1 / max(lam_bar, 1e-9))
        t += w
        if t >= T:
            break
        rec = [s for s in times[-2000:] if t - s < 20 * decay]
        if kernel == "exp":
            lam_t = mu + sum(n_br / decay * math.exp(-(t - s) / decay) for s in rec)
        else:
            c = 1.0
            lam_t = mu + sum(n_br * (alpha_pl - 1) / c * (1 + (t - s) / c) ** (-alpha_pl) for s in rec)
        if rng.uniform() * lam_bar <= lam_t:
            times.append(t)
    return np.array(times)


@family("J", "hawkes", 8, {**EV, "bursty": "yes", "reversible": "no"}, profiles={"stationary1000": 9})
def hawkes(i, rng, T, S):
    """Hawkes self-exciting process, branching ratio S[0.2, 0.98] (upper quarter near-critical),
    exponential (even i) or power-law (odd i) kernel; binned counts, or inter-event intervals (i % 4 == 3);
    the stationary profile reads every instance out as a kernel-smoothed rate."""
    n_br = S.draw("branching", 0.2, 0.98)
    kernel = "exp" if i % 2 == 0 else "powerlaw"
    from ..registry import profile
    stat = profile() == "stationary1000"
    mean_rate = S.draw("rate", 0.2, 1.0, log=True) if stat else S.draw("rate", 0.05, 0.5, log=True)
    mu = mean_rate * (1 - n_br)
    decay = rng.uniform(2, 10) if stat else rng.uniform(2, 50)  # stationary: short kernels, many clusters per record
    times = _hawkes(4 * T, mu, n_br, kernel, rng, decay=decay)
    iv = np.diff(times)
    info = dict(branching=n_br, kernel=kernel, base_rate=mu, decay=decay, event_rate=mean_rate,
                burstiness_B=burstiness(iv))
    from ..registry import profile
    if profile() == "stationary1000":
        # one readout for the whole family: a kernel-smoothed rate. (Interval sequences, which live
        # on a different scale, are the readout of J.renewal, where every instance is one.)
        return _smoothed_rate(bin_events(times, 4 * T)[-T:], rng), dict(info, observed="smoothed-rate", discrete_valued="no", **_bw())
    if i % 4 == 3 and iv.size >= T:
        return iv[-T:], dict(info, observed="intervals", event_like="no", discrete_valued="no")
    return bin_events(times, 4 * T)[-T:], info


@family("J", "cox", 5, {**EV, "bursty": "yes", "reversible": "yes"}, profiles={"stationary1000": 0})
def cox(i, rng, T, S):
    """Doubly stochastic Poisson: rate = mean exp(s OU) (even i) or mean abs(OU) (odd i), OU tau LU[5, 100]."""
    tau = S.draw("tau", 5, 40, log=True)
    mean = S.draw("mean", 0.2, 10, log=True)
    n = T + 2000
    ou = ar_filter(rng.standard_normal(n) * math.sqrt(1 - math.exp(-2 / tau)), [math.exp(-1 / tau)])[-T:]
    if i % 2 == 0:
        s = rng.uniform(0.5, 1.5)
        lam = mean * np.exp(s * ou - s * s / 2)
        kind = "log-gaussian"
    else:
        lam = mean * np.abs(ou) / math.sqrt(2 / math.pi)
        kind = "abs-ou"
    return rng.poisson(lam).astype(float), dict(kind=kind, tau=tau, mean=mean, event_rate=mean, timescale_samples=tau)


@family("J", "markov-chain", 6, {**EV, "event_like": "no", "skewed": "na", "regime_switching": "yes"}, profiles={"stationary1000": 0})
def markov_chain(i, rng, T, S):
    """Markov chain with 2-6 states, dwell LU[2, 100]; reversible (random symmetric-ish) or cyclic
    (odd i, detailed balance violated); emission = state index."""
    k = S.integer("k", 2, 6)
    dwell = S.draw("dwell", 2, 40, log=True)  # >= 25 transitions per record
    stay = 1 - 1 / dwell
    if i % 2 == 0 or k == 2:
        off = rng.dirichlet(np.ones(k - 1), size=k)
        P = np.zeros((k, k))
        for a in range(k):
            P[a, [b for b in range(k) if b != a]] = (1 - stay) * off[a]
            P[a, a] = stay
        kind = "random"
    else:
        P = np.full((k, k), 0.0)
        for a in range(k):
            P[a, a] = stay
            P[a, (a + 1) % k] = (1 - stay) * 0.9
            P[a, (a - 1) % k] = (1 - stay) * 0.1
        kind = "cyclic"
    n = T + 500
    s = np.zeros(n, dtype=int)
    for t in range(1, n):
        s[t] = rng.choice(k, p=P[s[t - 1]])
    return burn(s.astype(float), T), dict(k=k, dwell=dwell, kind=kind, n_states=k, timescale_samples=dwell,
                                           reversible="no" if kind == "cyclic" else "partly")


@family("J", "telegraph", 4, {**EV, "event_like": "no", "skewed": "no", "reversible": "yes", "regime_switching": "yes"}, profiles={"stationary1000": 0})
def telegraph(i, rng, T, S):
    """Random telegraph (dichotomous) noise, switching rate LU[0.01, 0.3] per sample, +-1."""
    rate = S.draw("rate", 0.03, 0.3, log=True)  # >= 30 flips per record
    flips = rng.uniform(size=T) < rate
    x = np.cumprod(np.where(flips, -1.0, 1.0)) * rng.choice([-1.0, 1.0])
    return x, dict(rate=rate, n_states=2, event_rate=rate, timescale_samples=1 / rate)


@family("J", "spike-signs", 4, {**EV, "discrete_valued": "no", "skewed": "no", "reversible": "no"}, profiles={"stationary1000": 5})
def spike_signs(i, rng, T, S):
    """Marked point process on an AR floor: spikes 4-7 SD at gamma(4) intervals (mean tau S[10, 40]),
    sign rule s_n = -s_{n-1} s_{n-2} r_n (third-order, sign-balanced, no pairwise correlation)."""
    tau = S.draw("tau", 10, 40, log=True)
    p_plus = rng.uniform(0.7, 0.85)
    phi = rng.choice([0.0, 0.5, 0.8])
    n = T + 500
    floor = ar_filter(rng.standard_normal(n) * math.sqrt(1 - phi**2), [phi]) if phi > 0 else rng.standard_normal(n)
    x = floor.copy()
    t = rng.gamma(4, tau / 4)
    s1, s2 = 1.0, 1.0
    k = 0
    while t < n:
        r = 1.0 if rng.uniform() < p_plus else -1.0
        s = -s1 * s2 * r
        x[int(t)] += s * rng.uniform(4, 7)
        s2, s1 = s1, s
        t += rng.gamma(4, tau / 4)
        k += 1
    return burn(x, T), dict(tau=tau, p_plus=p_plus, phi=phi, event_rate=1 / tau)


@family("J", "queue-branching", 5, {**EV, "event_like": "no", "reversible": "partly"}, profiles={"stationary1000": 0})
def queue_branching(i, rng, T, S):
    """M/M/1 queue length (load S[0.5, 0.98]), Galton-Watson branching with immigration, or a
    birth-death population."""
    kind = ["mm1", "mm1", "galton-watson", "birth-death", "mm1"][i]
    n = T + 2000
    x = np.zeros(n)
    if kind == "mm1":
        rho = S.draw("load", 0.5, 0.8)  # above ~0.8 the queue's relaxation time approaches the record
        lam, mu = rho, 1.0
        q = 0
        for t in range(n):
            q += rng.poisson(lam) - min(q, rng.poisson(mu))
            x[t] = q
        par = dict(load=rho, reversible="yes")
    elif kind == "galton-watson":
        m = rng.uniform(0.7, 0.98)
        imm = rng.uniform(0.5, 3.0)
        z = 5
        for t in range(n):
            z = rng.poisson(m * z) + rng.poisson(imm)
            x[t] = z
        par = dict(mean_offspring=m, immigration=imm, reversible="no")
    else:
        b, d, K = 0.05, 0.02, 100.0
        N = 50
        for t in range(n):
            births = rng.poisson(b * N)
            deaths = rng.poisson(d * N + b * N * N / K)
            N = max(1, N + births - deaths)
            x[t] = N
        par = dict(b=b, d=d, K=K, reversible="partly")
    return burn(x, T), dict(kind=kind, **par)


@family("J", "random-walk-lattice", 4, {**EV, "event_like": "no", "skewed": "no", "stationary": "no",
                                       "nonstationary_kind": "walk", "reversible": "yes"}, profiles={"stationary1000": 0})
def random_walk_lattice(i, rng, T, S):
    """Simple random walk on Z (i=0), one coordinate of a 2-D lattice walk (i=1), a reflected walk
    on {0..L} (i=2, stationary), a walk on a small random graph (node index, i=3, stationary)."""
    kind = ["z", "z2", "reflected", "graph"][i]
    if kind == "z":
        return np.cumsum(rng.choice([-1.0, 1.0], T)), dict(kind=kind)
    if kind == "z2":
        step = rng.choice(4, T)
        dx = np.where(step == 0, 1.0, np.where(step == 1, -1.0, 0.0))
        return np.cumsum(dx), dict(kind=kind)
    if kind == "reflected":
        L = int(rng.integers(5, 30))
        x = np.zeros(T)
        v = L // 2
        for t in range(T):
            v = min(L, max(0, v + int(rng.choice([-1, 1]))))
            x[t] = v
        return x, dict(kind=kind, L=L, stationary="yes", nonstationary_kind="none", n_states=L + 1)
    k = int(rng.integers(6, 15))
    A = (rng.uniform(size=(k, k)) < 0.3).astype(float)
    A = np.maximum(A, A.T)
    np.fill_diagonal(A, 0)
    for a in range(k):
        A[a, (a + 1) % k] = A[(a + 1) % k, a] = 1  # ring guarantees connectivity
    x = np.zeros(T)
    v = 0
    for t in range(T):
        nb = np.flatnonzero(A[v])
        v = int(rng.choice(nb))
        x[t] = v
    return x, dict(kind=kind, k=k, stationary="yes", nonstationary_kind="none", n_states=k)


@family("J", "symbolic", 4, {**EV, "event_like": "no", "skewed": "no", "deterministic": "yes", "chaotic": "yes", "reversible": "no"}, profiles={"stationary1000": 0})
def symbolic(i, rng, T, S):
    """Symbolic dynamics: binary partition of the logistic (r=4, r=3.8), tent, or Lorenz (sign of x)."""
    kind = ["logistic4", "logistic3.8", "tent", "lorenz-sign"][i]
    if kind.startswith("logistic"):
        r = 4.0 if kind == "logistic4" else 3.8
        v = rng.uniform(0.1, 0.9)
        x = np.empty(T)
        for t in range(T + 500):
            v = r * v * (1 - v)
            if t >= 500:
                x[t - 500] = 1.0 if v > 0.5 else 0.0
        return x, dict(kind=kind, r=r, n_states=2)
    if kind == "tent":
        # exact rational iteration of the tent map with slope 2 (a binary shift)
        from fractions import Fraction
        v = Fraction(int(rng.integers(1, 2**60)) * 2 + 1, 2**61 * 3**40 + 1)
        x = np.empty(T)
        for t in range(T):
            v = 2 * v if v < Fraction(1, 2) else 2 - 2 * v
            x[t] = 1.0 if v > Fraction(1, 2) else 0.0
        return x, dict(kind=kind, n_states=2)
    from ..util import flow_series
    def lor(t, u):
        xx, yy, zz = u
        return [10 * (yy - xx), xx * (28 - zz) - yy, xx * yy - 8 / 3 * zz]
    x, per = flow_series(lor, [1.0 + rng.uniform(), 1.0, 20.0], T, 8, t_probe=100.0)
    return (x > 0).astype(float), dict(kind=kind, n_states=2, continuous_time="yes")


@family("J", "compound-poisson", 4, {**EV, "event_like": "partly", "heavy_tailed": "yes", "bursty": "yes"}, profiles={"stationary1000": 0})
def compound_poisson(i, rng, T, S):
    """Compound Poisson with Pareto jumps (tail S[1.2, 3]): increments (even i; zero-inflated, the
    shape of a rainfall total) or the cumulative sum (odd i)."""
    a = S.draw("tail", 1.2, 3.0)
    rate = S.draw("rate", 0.05, 0.5, log=True)
    n_ev = rng.poisson(rate, T)
    inc = np.array([np.sum(1 + rng.pareto(a, k)) if k else 0.0 for k in n_ev])
    if i % 2 == 0:
        return inc, dict(tail=a, rate=rate, event_rate=rate, discrete_valued="no")
    return np.cumsum(inc), dict(tail=a, rate=rate, event_rate=rate, discrete_valued="no", stationary="no",
                                nonstationary_kind="walk", event_like="no")


@family("J", "poisson-stationary", 0, {**EV, "reversible": "yes", "bursty": "no"}, profiles={"stationary1000": 0})
def poisson_stationary(i, rng, T, S):
    """Homogeneous Poisson counts per bin, mean count LU[0.1, 20]."""
    mean = S.draw("mean", 0.1, 20, log=True)
    return rng.poisson(mean, T).astype(float), dict(kind="homogeneous", mean=mean, event_rate=mean, burstiness_B=0.0)


@family("J", "lattice-bounded", 0, {**EV, "event_like": "no", "skewed": "no", "reversible": "yes"}, profiles={"stationary1000": 0})
def lattice_bounded(i, rng, T, S):
    """Bounded random walks: reflected on {0..L} (even i) or on a small random graph (odd i)."""
    if i % 2 == 0:
        L = int(rng.integers(5, 30))
        x = np.zeros(T)
        v = L // 2
        for t in range(T):
            v = min(L, max(0, v + int(rng.choice([-1, 1]))))
            x[t] = v
        return x, dict(kind="reflected", L=L, n_states=L + 1)
    k = int(rng.integers(6, 15))
    A = (rng.uniform(size=(k, k)) < 0.3).astype(float)
    A = np.maximum(A, A.T)
    np.fill_diagonal(A, 0)
    for a in range(k):
        A[a, (a + 1) % k] = A[(a + 1) % k, a] = 1
    x = np.zeros(T)
    v = 0
    for t in range(T):
        v = int(rng.choice(np.flatnonzero(A[v])))
        x[t] = v
    return x, dict(kind="graph", k=k, n_states=k)


@family("J", "compound-poisson-increments", 0, {**EV, "event_like": "partly", "heavy_tailed": "yes", "bursty": "yes", "discrete_valued": "no"},
        profiles={"stationary1000": 2})
def compound_poisson_increments(i, rng, T, S):
    """Compound Poisson increments with Pareto jumps (tail S[2.2, 3.5], finite variance): zero-inflated, rainfall-total shape."""
    a = S.draw("tail", 2.2, 3.5)
    rate = S.draw("rate", 0.05, 0.5, log=True)
    n_ev = rng.poisson(rate, T)
    return np.array([np.sum(1 + rng.pareto(a, k)) if k else 0.0 for k in n_ev]), dict(tail=a, rate=rate, event_rate=rate)


@family("J", "poisson-smoothed", 0, {**EV, "discrete_valued": "no", "skewed": "partly", "reversible": "yes", "bursty": "no"}, profiles={"stationary1000": 6})
def poisson_smoothed(i, rng, T, S):
    """Homogeneous Poisson event train (rate LU[0.05, 0.5]) read out as a kernel-smoothed rate."""
    rate = S.draw("rate", 0.05, 0.5, log=True)
    return _smoothed_rate(rng.poisson(rate, T).astype(float), rng), dict(rate=rate, event_rate=rate, burstiness_B=0.0, **_bw())


@family("J", "cox-smoothed", 0, {**EV, "discrete_valued": "no", "bursty": "yes", "reversible": "yes"}, profiles={"stationary1000": 6})
def cox_smoothed(i, rng, T, S):
    """Doubly stochastic Poisson (rate = mean exp(s OU), OU tau LU[2, 10], mean LU[0.5, 3]) read out as a kernel-smoothed rate."""
    tau = S.draw("tau", 2, 10, log=True)
    mean = S.draw("mean", 0.5, 3.0, log=True)
    ou = ar_filter(rng.standard_normal(T + 2000) * math.sqrt(1 - math.exp(-2 / tau)), [math.exp(-1 / tau)])[-T:]
    s_ = rng.uniform(0.3, 0.8)
    lam = mean * np.exp(s_ * ou - s_ * s_ / 2)
    from ..registry import profile as _pp
    return _smoothed_rate(rng.poisson(lam).astype(float), rng), dict(tau=tau, mean=mean, event_rate=mean, timescale_samples=tau, **_bw(),
                                                                   **({"s": s_} if _pp() == "stationary1000" else {}))


@family("J", "markov-chain-emitted", 0, {**EV, "event_like": "no", "skewed": "na", "discrete_valued": "no", "regime_switching": "yes"}, profiles={"stationary1000": 7})
def markov_chain_emitted(i, rng, T, S):
    """Markov chain with 2-6 states (dwell LU[2, 40]; random or cyclic transitions) read out through
    state-dependent Gaussian emissions (means = state index, SD U[0.15, 0.4])."""
    k = S.integer("k", 2, 6)
    dwell = S.draw("dwell", 2, 40, log=True)
    stay = 1 - 1 / dwell
    if i % 2 == 0 or k == 2:
        off = rng.dirichlet(np.ones(k - 1), size=k)
        P = np.zeros((k, k))
        for a in range(k):
            P[a, [b for b in range(k) if b != a]] = (1 - stay) * off[a]
            P[a, a] = stay
        kind = "random"
    else:
        P = np.zeros((k, k))
        for a in range(k):
            P[a, a], P[a, (a + 1) % k], P[a, (a - 1) % k] = stay, (1 - stay) * 0.9, (1 - stay) * 0.1
        kind = "cyclic"
    n = T + 500
    s = np.zeros(n, dtype=int)
    for t in range(1, n):
        s[t] = rng.choice(k, p=P[s[t - 1]])
    sd = rng.uniform(0.15, 0.4)
    from ..registry import profile as _pp
    extra = {"transitions": [float(v) for v in P.ravel()]} if _pp() == "stationary1000" else {}  # row-major transition matrix
    return burn(s + sd * rng.standard_normal(n), T), dict(k=k, dwell=dwell, kind=kind, n_states=k, emission_sd=sd, **extra,
                                                          reversible="no" if kind == "cyclic" else "partly")


@family("J", "telegraph-noisy", 0, {**EV, "event_like": "no", "skewed": "no", "discrete_valued": "no", "reversible": "yes", "regime_switching": "yes"}, profiles={"stationary1000": 4})
def telegraph_noisy(i, rng, T, S):
    """Random telegraph noise (+-1, switching rate LU[0.03, 0.3]) in Gaussian noise of SD U[0.1, 0.4]."""
    rate = S.draw("rate", 0.03, 0.3, log=True)
    sd = rng.uniform(0.1, 0.4)
    x = np.cumprod(np.where(rng.uniform(size=T) < rate, -1.0, 1.0)) * rng.choice([-1.0, 1.0])
    return x + sd * rng.standard_normal(T), dict(rate=rate, n_states=2, event_rate=rate, noise_sd=sd)
