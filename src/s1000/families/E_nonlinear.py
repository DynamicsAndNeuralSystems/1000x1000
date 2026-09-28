"""Class E: nonlinear stochastic, discrete time."""
from __future__ import annotations

import numpy as np

from ..registry import family
from ..util import burn, skew_innov

NS = dict(linear="no", gaussian="no", stationary="yes")
BURN = 500


@family("E", "setar", 12, {**NS, "reversible": "no"}, profiles={"stationary1000": 21})
def setar(i, rng, T, S):
    """SETAR with 2 (even i) or 3 (odd i) regimes, delay d in {1, 2, 3}; regime AR coefficients
    phi+ S[0.4, 0.9], phi- U[-0.6, 0.2] (third regime U[-0.3, 0.7]); threshold 0 (2 regimes) or two U[-1, 1] (3 regimes)."""
    d = S.integer("delay", 1, 3)
    k = 2 if i % 2 == 0 else 3
    phis = [S.draw("phi_plus", 0.4, 0.9), rng.uniform(-0.6, 0.2)] + ([rng.uniform(-0.3, 0.7)] if k == 3 else [])
    thr = [0.0] if k == 2 else sorted(rng.uniform(-1.0, 1.0, 2))
    n = T + BURN
    e = rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(d, n):
        z = x[t - d]
        r = int(np.searchsorted(thr, z))
        x[t] = phis[r] * x[t - 1] + e[t]
    return burn(x, T), dict(delay=d, regimes=k, phis=phis, thresholds=thr)


@family("E", "expar", 6, {**NS, "reversible": "no"})
def expar(i, rng, T, S):
    """Exponential AR (Haggan-Ozaki): x_t = (a + b exp(-x_{t-1}^2)) x_{t-1} + e_t."""
    a = S.draw("a", 0.2, 0.6)
    b = rng.uniform(0.2, 0.95 - a)
    n = T + BURN
    e = rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = (a + b * np.exp(-x[t - 1] ** 2)) * x[t - 1] + e[t]
    return burn(x, T), dict(a=a, b=b)


@family("E", "bilinear", 6, {**NS, "reversible": "no"})
def bilinear(i, rng, T, S):
    """Bilinear MA x_t = e_t + c e_{t-1} e_{t-2}, c S[0.4, 1]; Gaussian (even i: irreversible only
    above third order) or skewed (odd i) innovations."""
    c = S.draw("c", 0.4, 1.0)
    n = T + BURN
    if i % 2 == 0:
        e = rng.standard_normal(n)
        k = None
    else:
        k = rng.uniform(0.4, 3.0)
        e = skew_innov(n, k, rng)
    x = e[2:] + c * e[1:-1] * e[:-2]
    return burn(x, T), dict(c=c, shape=k, skewed="yes" if k else "no")


@family("E", "random-coef-ar", 4, {**NS, "heteroskedastic": "yes"}, profiles={"stationary1000": 5})
def rcar(i, rng, T, S):
    """Random-coefficient AR(1): phi_t = phi + sigma_phi eps_t, sigma_phi S[0.1, 0.4]."""
    phi = rng.uniform(0.3, 0.8)
    sp = S.draw("sigma_phi", 0.1, 0.4)
    n = T + BURN
    e = rng.standard_normal(n)
    ph = phi + sp * rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = ph[t] * x[t - 1] + e[t]
    return burn(x, T), dict(phi=phi, sigma_phi=sp)


@family("E", "garch", 12, {**NS, "heteroskedastic": "yes", "bursty": "yes", "heavy_tailed": "yes"}, profiles={"stationary1000": 19})
def garch(i, rng, T, S):
    """ARCH(1) / GARCH(1,1) / GJR-GARCH / EGARCH returns with Gaussian or Student-t innovations;
    persistence S[0.6, 0.99]."""
    kind = S.choice("kind", ["arch", "garch", "gjr", "egarch"])
    pers = S.draw("persistence", 0.6, 0.99)
    tdist = i % 3 == 0
    nu = rng.uniform(3, 8) if tdist else None
    n = T + BURN
    z = rng.standard_t(nu, n) / np.sqrt(nu / (nu - 2)) if tdist else rng.standard_normal(n)
    r = np.zeros(n)
    omega = 0.05
    if kind == "arch":
        # ARCH(1) above alpha ~ 0.6 has an infinite fourth moment: the record is a few huge
        # excursions on a quiet floor, which reads as non-stationary however long it runs
        alpha, beta, gamma = min(pers, 0.6), 0.0, 0.0
    elif kind == "garch":
        alpha = rng.uniform(0.03, 0.2)
        beta, gamma = pers - alpha, 0.0
    elif kind == "gjr":
        alpha, gamma = rng.uniform(0.02, 0.1), rng.uniform(0.1, 0.3)
        beta = pers - alpha - gamma / 2
    else:
        alpha, gamma, beta = rng.uniform(0.1, 0.3), rng.uniform(-0.3, -0.05), pers
    if kind == "egarch":
        lh = np.log(omega)
        for t in range(1, n):
            lh = omega * (1 - beta) + beta * lh + alpha * (abs(z[t - 1]) - np.sqrt(2 / np.pi)) + gamma * z[t - 1]
            r[t] = np.exp(lh / 2) * z[t]
    else:
        h = omega / max(1 - pers, 0.01)
        for t in range(1, n):
            h = omega + (alpha + gamma * (r[t - 1] < 0)) * r[t - 1] ** 2 + beta * h
            r[t] = np.sqrt(h) * z[t]
    return burn(r, T), dict(kind=kind, persistence=pers, alpha=alpha, beta=beta, gamma=gamma, nu=nu,
                            reversible="no" if kind in ("gjr", "egarch") else "yes")


@family("E", "stoch-vol", 6, {**NS, "heteroskedastic": "yes", "bursty": "partly"}, profiles={"stationary1000": 8})
def stoch_vol(i, rng, T, S):
    """Stochastic volatility: r_t = exp(h_t/2) z_t, h_t = phi h_{t-1} + sigma eta_t, phi S[0.8, 0.95], sigma S[0.15, 0.4]."""
    phi, sv = S.draw("phi", 0.8, 0.95), S.draw("sigma", 0.15, 0.4)
    n = T + BURN
    h = np.zeros(n)
    eta = rng.standard_normal(n)
    for t in range(1, n):
        h[t] = phi * h[t - 1] + sv * eta[t]
    return burn(np.exp(h / 2) * rng.standard_normal(n), T), dict(phi=phi, sigma=sv, timescale_samples=-1 / np.log(phi))


@family("E", "markov-switching-ar", 8, {**NS, "regime_switching": "yes"}, profiles={"stationary1000": 10})
def ms_ar(i, rng, T, S):
    """Markov-switching AR(1) with 2-4 regimes (dwell LU[8, 60]); regimes differ in a drawn
    subset of {phi, mean, variance}."""
    k = S.integer("k", 2, 4)
    dwell = S.draw("dwell", 8, 60, log=True)  # >= ~15 regime changes per record
    stay = 1 - 1 / dwell
    P = np.full((k, k), (1 - stay) / (k - 1))
    np.fill_diagonal(P, stay)
    which = rng.choice(["phi", "mean", "var", "phi+mean", "all"])
    phi = rng.uniform(-0.5, 0.9, k) if "phi" in which or which == "all" else np.full(k, rng.uniform(0.2, 0.8))
    mu = rng.uniform(-2, 2, k) if "mean" in which or which == "all" else np.zeros(k)
    sd = np.exp(rng.uniform(np.log(0.3), np.log(3), k)) if "var" in which or which == "all" else np.ones(k)
    n = T + BURN
    s = np.zeros(n, dtype=int)
    for t in range(1, n):
        s[t] = rng.choice(k, p=P[s[t - 1]])
    e = rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = mu[s[t]] + phi[s[t]] * (x[t - 1] - mu[s[t - 1]]) + sd[s[t]] * e[t]
    return burn(x, T), dict(k=k, dwell=dwell, which=which, phi=phi, mu=mu, sd=sd, n_states=k)


@family("E", "hmm", 6, {**NS, "regime_switching": "yes"}, profiles={"stationary1000": 8})
def hmm(i, rng, T, S):
    """Hidden Markov: 2-state Gaussian (i%3==0), cyclic 3-state Gaussian (i%3==1, detailed balance
    violated), or categorical emissions from a 3-5 state chain (i%3==2)."""
    from ..registry import profile
    kind = (["gauss2", "cyclic3"] if profile() == "stationary1000" else ["gauss2", "cyclic3", "categorical"])[i % (2 if profile() == "stationary1000" else 3)]
    dwell = S.draw("dwell", 4, 50, log=True)  # >= ~20 transitions per record
    stay = 1 - 1 / dwell
    n = T + BURN
    if kind == "gauss2":
        P = np.array([[stay, 1 - stay], [1 - stay, stay]])
        means, sd, k = np.array([-1.0, 1.0]) * rng.uniform(0.5, 2.0), rng.uniform(0.3, 1.0), 2
    elif kind == "cyclic3":
        fwd = rng.uniform(0.7, 0.95)
        P = np.array([[stay, (1 - stay) * fwd, (1 - stay) * (1 - fwd)],
                      [(1 - stay) * (1 - fwd), stay, (1 - stay) * fwd],
                      [(1 - stay) * fwd, (1 - stay) * (1 - fwd), stay]])
        means, sd, k = np.sort(rng.standard_normal(3)) * rng.uniform(1.0, 2.5), rng.uniform(0.3, 0.8), 3
    else:
        k = int(rng.integers(3, 6))
        P = np.full((k, k), (1 - stay) / (k - 1))
        np.fill_diagonal(P, stay)
        means, sd = None, None
    s = np.zeros(n, dtype=int)
    for t in range(1, n):
        s[t] = rng.choice(k, p=P[s[t - 1]])
    if kind == "categorical":
        E = rng.dirichlet(np.ones(k) * 0.5, size=k)
        x = np.array([rng.choice(k, p=E[st]) for st in s], dtype=float)
        return burn(x, T), dict(kind=kind, k=k, dwell=dwell, n_states=k, discrete_valued="yes",
                                reversible="yes")
    x = means[s] + sd * rng.standard_normal(n)
    info = dict(kind=kind, k=k, dwell=dwell, n_states=k, reversible="no" if kind == "cyclic3" else "yes")
    if profile() == "stationary1000":  # record the emission levels and noise (and the cycle bias), so each series' card can give them
        info.update(mu=[float(m) for m in means], sd=float(sd), **({"fwd": float(fwd)} if kind == "cyclic3" else {}))
    return burn(x, T), info


@family("E", "stochastic-map", 12, {**NS, "deterministic": "partly", "chaotic": "partly"}, profiles={"stationary1000": {"indices": [0, 1, 2, 3, 5, 6, 8, 10, 11, 15, 17, 18], "strat_n": 19}})
def stochastic_map(i, rng, T, S):
    """Logistic, tent, Henon or Ricker map with dynamical noise LU[0.001, 0.1] (scaled per map; multiplicative
    for Ricker); parameter drawn in chaotic *and* periodic regimes (noisy periodicity, noise-induced chaos),
    except in the stationary profile, where it is redrawn until the noise-free map is chaotic."""
    from ..registry import profile
    kind = S.choice("kind", ["logistic", "tent", "henon", "ricker"])
    eps = S.draw("noise", 0.001, 0.1, log=True)
    n = T + BURN
    stat = profile() == "stationary1000"
    if stat:  # floor 0.01: below it a noisy map sat on its clean twin in hctsa space (2026-09-26); same strata
        eps = 0.01 * (eps / 0.001) ** 0.5

    def chaotic(step, x0, deriv=None):
        """Clean map has >= 100 distinct values over 1000 iterates (not a periodic orbit)."""
        v, seen = x0, set()
        for t in range(1500):
            v = step(v)
            if t >= 500:
                seen.add(round(float(v[0]) if np.ndim(v) else float(v), 10))
        return len(seen) >= 100
    if kind == "logistic":
        r = rng.uniform(3.57, 4.0) if stat else rng.uniform(3.5, 4.0)
        if stat:
            for _ in range(30):
                if chaotic(lambda v, r=r: r * v * (1 - v), 0.3):
                    break
                r = rng.uniform(3.57, 4.0)
        x = np.empty(n)
        x[0] = rng.uniform(0.1, 0.9)
        for t in range(1, n):
            x[t] = np.clip(r * x[t - 1] * (1 - x[t - 1]) + eps * 0.3 * rng.standard_normal(), 0.0, 1.0)
        par = dict(r=r)
    elif kind == "tent":
        mu = rng.uniform(1.2, 2.0)
        x = np.empty(n)
        x[0] = rng.uniform(0.1, 0.9)
        for t in range(1, n):
            v = x[t - 1]
            x[t] = np.clip(mu * min(v, 1 - v) + eps * 0.3 * rng.standard_normal(), 0.0, 1.0)
        par = dict(mu=mu)
    elif stat and i == 15:
        # the seventh Hénon series in the collection was redundant at any a (2026-09-26): a noisy Holmes (Duffing)
        # map instead, which has no clean twin here (dysts' Duffing map is excluded as drifting). a = 2.7 is
        # chaotic (lambda ~ 0.29) and does not escape under this noise; y observed.
        a_h, b_h = 2.7, 0.2
        u, v = 0.1, 0.1
        x = np.empty(n)
        for t in range(n):
            u, v = v + eps * 0.3 * rng.standard_normal(), -b_h * u + a_h * v - v ** 3 + eps * 0.3 * rng.standard_normal()
            if abs(v) > 10:
                raise RuntimeError("noisy Holmes map escaped: redrawn")
            x[t] = v
        kind, par = "holmes", dict(a=a_h, b=b_h)
    elif kind == "henon":
        a, b = (rng.uniform(1.2, 1.4) if stat else rng.uniform(1.0, 1.4)), 0.3
        if stat:
            for _ in range(30):
                if chaotic(lambda u, a=a: np.array([1 - a * u[0] ** 2 + u[1], 0.3 * u[0]]), np.array([0.1, 0.1])):
                    break
                a = rng.uniform(1.2, 1.4)
            # 006 and 015 drew a ~ 1.21, next to the clean Hénon at a = 1.217 (F.map-sweep 000): at small noise the
            # three were hctsa near-duplicates whatever the noise level (2026-09-26). Move them into the gaps
            # between the collection's other Hénon parameters (1.115, 1.217, 1.291, 1.364, 1.4); both chaotic.
            a = {6: 1.16}.get(i, a)
        x = np.empty(n)
        u, v = 0.1, 0.1
        escaped = False
        for t in range(n):
            u, v = 1 - a * u * u + v + eps * 0.7 * rng.standard_normal(), b * u
            if abs(u) > 3:  # dynamical noise has kicked the orbit off the attractor
                escaped = True
                u, v = 0.1, 0.1
            x[t] = u
        if stat and escaped:
            raise RuntimeError("noisy Henon escaped the attractor: redrawn in the stationary profile")
        par = dict(a=a, b=b)
    else:
        r = rng.uniform(2.7, 3.6) if stat else rng.uniform(2.0, 3.6)
        if stat:
            for _ in range(30):
                if chaotic(lambda v, r=r: v * np.exp(r * (1 - v)), 0.5):
                    break
                r = rng.uniform(2.7, 3.6)
        x = np.empty(n)
        x[0] = 0.5
        for t in range(1, n):
            x[t] = x[t - 1] * np.exp(r * (1 - x[t - 1]) + eps * rng.standard_normal())
        par = dict(r=r)
    return burn(x, T), dict(kind=kind, noise=eps, **par)


@family("E", "star", 8, {**NS, "reversible": "no"}, profiles={"stationary1000": 14})
def star(i, rng, T, S):
    """Smooth-transition AR (LSTAR / ESTAR) or additive nonlinear AR (sin / tanh); transition
    steepness LU[1, 20]."""
    kind = S.choice("kind", ["lstar", "estar", "sin", "tanh"])
    g = S.draw("gamma", 1, 20, log=True)
    p1, p2 = rng.uniform(0.2, 0.8), rng.uniform(-0.8, 0.2)
    n = T + BURN
    e = rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(1, n):
        v = x[t - 1]
        if kind == "lstar":
            G = 1 / (1 + np.exp(-g * v))
            x[t] = (p1 * (1 - G) + p2 * G) * v + e[t]
        elif kind == "estar":
            G = 1 - np.exp(-g * v * v / 4)
            x[t] = (p1 * (1 - G) + p2 * G) * v + e[t]
        elif kind == "sin":
            x[t] = p1 * v + 1.5 * np.sin(g / 5 * v) + e[t]
        else:
            x[t] = p1 * v + 2.0 * np.tanh(g / 5 * v) - 1.0 * v + e[t]
    return burn(x, T), dict(kind=kind, gamma=g, p1=p1, p2=p2)


@family("E", "volterra", 4, {**NS, "reversible": "no"})
def volterra(i, rng, T, S):
    """Second-order Volterra (nonlinear MA): linear MA(3) plus quadratic lag products, weight S[0.3, 1]."""
    w = S.draw("w", 0.3, 1.0)
    n = T + BURN
    e = rng.standard_normal(n)
    th = rng.uniform(-0.8, 0.8, 3)
    x = e.copy()
    for j in range(3):
        x[j + 1:] += th[j] * e[: n - j - 1]
    q = rng.uniform(-1, 1, (3, 3))
    for a in range(3):
        for b in range(a, 3):
            x[b + 1:] += w * q[a, b] * e[b - a: n - a - 1] * e[: n - b - 1]
    from ..registry import profile as _pp
    extra = dict(q_kernel=[float(q[a, b]) for a in range(3) for b in range(a, 3)]) if _pp() == "stationary1000" else {}  # h_jk, j <= k
    return burn(x, T), dict(w=w, theta=th, **extra)


@family("E", "count", 8, {**NS, "discrete_valued": "yes", "skewed": "yes"}, profiles={"stationary1000": 0})
def count(i, rng, T, S):
    """Count processes: INAR(1) (thinning S[0.2, 0.9]), Poisson autoregression (INGARCH), or
    negative-binomial INGARCH; mean LU[1, 30]."""
    kind = S.choice("kind", ["inar", "poisson-ar", "nb-ingarch"])
    mean = S.draw("mean", 1, 30, log=True)
    n = T + BURN
    x = np.zeros(n)
    if kind == "inar":
        a = S.draw("alpha", 0.2, 0.9)
        lam = mean * (1 - a)
        x[0] = rng.poisson(mean)
        for t in range(1, n):
            x[t] = rng.binomial(int(x[t - 1]), a) + rng.poisson(lam)
        par = dict(alpha=a)
    else:
        a, b = rng.uniform(0.2, 0.6), rng.uniform(0.1, 0.5)
        if a + b > 0.95:
            b = 0.95 - a
        om = mean * (1 - a - b)
        lam = mean
        r_nb = rng.uniform(1, 10)
        for t in range(1, n):
            lam = om + a * x[t - 1] + b * lam
            x[t] = rng.poisson(lam) if kind == "poisson-ar" else rng.negative_binomial(r_nb, r_nb / (r_nb + lam))
        par = dict(a=a, b=b, r_nb=r_nb if kind == "nb-ingarch" else None)
    return burn(x, T), dict(kind=kind, mean=mean, **par, bursty="yes" if kind != "inar" else "partly")


@family("E", "bistable-map", 4, {**NS, "regime_switching": "yes", "deterministic": "partly"}, profiles={"stationary1000": 5})
def bistable_map(i, rng, T, S):
    """Noisy double-well map x_t = x_{t-1} + h(x_{t-1} - x_{t-1}^3) + sigma e_t; h = 0.1, sigma
    S[0.22, 0.4]: >= ~40 well crossings per record."""
    h = 0.1
    sig = S.draw("sigma", 0.22, 0.4)  # >= ~40 well crossings per record
    n = T + BURN
    e = rng.standard_normal(n)
    x = np.zeros(n)
    x[0] = 1.0
    for t in range(1, n):
        v = x[t - 1]
        x[t] = v + h * (v - v**3) + sig * e[t]
    xs = burn(x, T)
    crossings = int(np.sum(np.diff(np.sign(xs)) != 0))
    return xs, dict(sigma=sig, crossings=crossings)


@family("E", "latent-ar-observed", 4, {**NS, "discrete_valued": "yes", "linear": "partly"}, profiles={"stationary1000": 0})
def latent_ar_observed(i, rng, T, S):
    """Binary (probit) or ordinal (k U{3..5}) observation of a latent AR(1), phi S[0.5, 0.98]."""
    phi = S.draw("phi", 0.5, 0.95)
    k = 2 if i % 2 == 0 else int(rng.integers(3, 6))
    n = T + BURN
    e = rng.standard_normal(n) * np.sqrt(1 - phi**2)
    z = np.zeros(n)
    for t in range(1, n):
        z[t] = phi * z[t - 1] + e[t]
    cuts = np.quantile(z, np.linspace(0, 1, k + 1)[1:-1]) if k > 2 else np.array([0.0])
    return burn(np.searchsorted(cuts, z).astype(float), T), dict(phi=phi, k=k, n_states=k)


@family("E", "cubic-crisis", 0, {**NS, "deterministic": "partly", "chaotic": "yes", "regime_switching": "yes",
                                 "reversible": "no"}, profiles={"stationary1000": 2})
def cubic_crisis(i, rng, T, S):
    """Noise-induced switching between chaotic attractors: the symmetric cubic map x -> a x - x^3 just
    below its attractor-merging crisis (a < 3 sqrt(3)/2 ~ 2.598) has two mirror-image chaotic bands;
    dynamical noise LU[0.03, 0.06] kicks the orbit between them, so chaotic motion within a band is
    broken by switches at irregular times. a stratified over [2.50, 2.58]."""
    a = S.draw("a", 2.50, 2.58)
    eps = rng.uniform(0.03, 0.06)
    x = rng.uniform(0.3, 1.2) * rng.choice([-1, 1])
    out = np.empty(T + BURN)
    for t in range(T + BURN):
        x = a * x - x ** 3 + eps * rng.standard_normal()
        if abs(x) > 1.95:  # beyond the basin boundary the orbit escapes to infinity: redraw
            raise RuntimeError("orbit escaped")
        out[t] = x
    return out[BURN:], dict(a=a, noise=eps)


@family("E", "kesten", 0, {**NS, "heavy_tailed": "yes", "bursty": "yes", "skewed": "yes", "reversible": "no"},
        profiles={"stationary1000": 2})
def kesten(i, rng, T, S):
    """Kesten random multiplicative process x_{n+1} = a_n x_n + b_n, ln a_n ~ N(m, s^2) with m < 0 and
    b_n > 0: occasional runs of a_n > 1 give bursts of exponential growth, and the stationary law has a
    power-law tail with exponent kappa = -2m/s^2, stratified over [2.3, 4] (finite variance)."""
    kappa = S.draw("kappa", 2.3, 4.0)
    s_ = rng.uniform(0.3, 0.5)
    m = -kappa * s_ * s_ / 2
    n = T + 3000
    a = np.exp(m + s_ * rng.standard_normal(n))
    b = rng.exponential(1.0, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = a[t] * x[t - 1] + b[t]
    return x[3000:], dict(kappa=kappa, s=s_, m=m)
