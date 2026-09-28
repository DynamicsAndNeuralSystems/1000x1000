"""Class F: deterministic maps, and deterministic aperiodic non-chaotic sequences."""
from __future__ import annotations

import math

import numpy as np

from ..registry import family
from ..rng import rng_for
from ..util import add_noise, deterministic_noise_sigma

DET = dict(deterministic="yes", linear="no", gaussian="no", stationary="yes", reversible="no")
BURN = 1000


def _finish(x, rng, info):
    """Apply the corpus-wide measurement-noise dial and record it. A clean orbit with fewer than 10
    distinct values is a periodic orbit (a periodic window): kept, and retagged as such."""
    if np.std(x) < 1e-9 * max(1.0, np.abs(x).mean()):
        raise RuntimeError("orbit converged to a fixed point")  # a named retry redraws within the stratum
    from ..registry import profile
    n_clean = np.unique(np.round(x, 12)).size
    if profile() == "stationary1000" and n_clean < 100:
        raise RuntimeError(f"periodic orbit ({n_clean} distinct values): redrawn in the stationary profile")
    if n_clean < 10:
        info = dict(info, periodic="yes", chaotic="no", discrete_valued="yes", n_states=int(n_clean))
    sig = deterministic_noise_sigma(rng)
    info = dict(info, noise_sigma=sig, measurement_noise="yes" if sig > 0 else "no",
                deterministic="partly" if sig > 0 else "yes")
    return add_noise(x, sig, rng), info


def _iterate(f, x0, n, burn=BURN):
    x = np.empty(n + burn)
    v = x0
    for t in range(n + burn):
        v = f(v)
        x[t] = v
    return x[burn:]


def _lyap_1d(f, df, x0, n=4000, burn=500):
    v, s = x0, 0.0
    for t in range(n + burn):
        v = f(v)
        if t >= burn:
            d = abs(df(v))
            s += math.log(d) if d > 0 else -30.0
    return s / n


def _chaos_tag(lam):
    return dict(lyapunov_max=lam, chaotic="yes" if lam > 0.01 else "no", periodic="yes" if lam < -0.01 else "no")


@family("F", "logistic", 8, DET, profiles={"stationary1000": {"indices": [3, 4, 6, 10, 12], "strat_n": 13}})  # over-represented: 5 spanning r
def logistic(i, rng, T, S):
    """Logistic map, r stratified over [3.5, 4] (periodic windows included, retagged by lambda; the
    stationary profile redraws r on [3.57, 4] until lambda > 0.01)."""
    from ..registry import profile
    r = S.draw("r", 3.5, 4.0)
    for _ in range(30):
        f = lambda v, r=r: r * v * (1 - v)
        x = _iterate(f, rng.uniform(0.1, 0.9), T)
        lam = _lyap_1d(f, lambda v, r=r: r * (1 - 2 * v), x[0])
        if profile() != "stationary1000" or lam > 0.01:
            break
        r = rng.uniform(3.57, 4.0)  # periodic window: redraw across the chaotic range
    return _finish(x, rng, dict(r=r, **_chaos_tag(lam)))


@family("F", "classic-1d", 6, DET, profiles={"stationary1000": 11})
def classic_1d(i, rng, T, S):
    """Tent, sine, cubic and Chebyshev maps across their chaotic ranges."""
    kind = ["tent", "sine", "cubic", "chebyshev", "tent", "sine"][i % 6]
    if kind == "tent":
        mu = S.draw("mu", 1.2, 2.0)
        f = lambda v: mu * min(v, 1 - v)
        df = lambda v: mu if v < 0.5 else -mu
        par = dict(mu=mu)
    elif kind == "sine":
        a = S.draw("a", 0.85, 1.0)
        f = lambda v: a * math.sin(math.pi * v)
        df = lambda v: a * math.pi * math.cos(math.pi * v)
        par = dict(a=a)
    elif kind == "cubic":
        a = S.draw("a", 2.4, 3.0)
        f = lambda v: a * v * (1 - v * v)
        df = lambda v: a * (1 - 3 * v * v)
        par = dict(a=a)
    else:
        k = int(rng.integers(2, 5))
        f = lambda v: math.cos(k * math.acos(max(-1.0, min(1.0, v))))
        df = lambda v: k * math.sin(k * math.acos(max(-1.0, min(1.0, v)))) / max(1e-9, math.sqrt(1 - min(v * v, 1 - 1e-12)))
        par = dict(k=k)
    x = _iterate(f, rng.uniform(0.1, 0.9), T)
    lam = _lyap_1d(f, df, x[0])
    return _finish(x, rng, dict(kind=kind, **par, **_chaos_tag(lam)))


@family("F", "circle-map", 6, {**DET, "quasiperiodic": "partly"}, profiles={"stationary1000": 9})
def circle_map(i, rng, T, S):
    """Circle map theta_{n+1} = theta_n + Omega - (K/2pi) sin(2 pi theta_n): mode-locked and
    quasi-periodic (K < 1) and chaotic (K > 1); observed as sin(2 pi theta)."""
    from ..registry import profile
    # the quasi-periodic regime (K < 1) reads as a drifting sinusoid, and H.quasiperiodic covers it
    K = S.draw("K", 1.05, 2.5) if profile() == "stationary1000" else S.draw("K", 0.3, 2.5)
    Om = rng.uniform(0.05, 0.95)
    f = lambda th: (th + Om - K / (2 * math.pi) * math.sin(2 * math.pi * th)) % 1.0
    df = lambda th: 1 - K * math.cos(2 * math.pi * th)
    th = _iterate(f, rng.uniform(), T)
    lam = _lyap_1d(f, df, th[0])
    x = np.sin(2 * np.pi * th)
    info = dict(K=K, Omega=Om, lyapunov_max=lam, chaotic="yes" if lam > 0.01 else "no",
                quasiperiodic="yes" if (K < 1 and abs(lam) < 0.01) else "no",
                periodic="yes" if lam < -0.01 else "no")
    return _finish(x, rng, info)


@family("F", "pomeau-manneville", 6, {**DET, "bursty": "yes", "event_like": "yes"}, profiles={"stationary1000": 8})
def pomeau_manneville(i, rng, T, S):
    """Pomeau-Manneville intermittency x_{n+1} = x_n + x_n^z mod 1, z S[1.3, 1.85] (finite invariant
    measure; laminar phases of tens of samples, many per record)."""
    z = S.draw("z", 1.3, 1.85)  # z -> 2 is the infinite-measure boundary: laminar phases outgrow the record
    f = lambda v: (v + v**z) % 1.0
    df = lambda v: 1 + z * v ** (z - 1)
    x = _iterate(f, rng.uniform(0.05, 0.95), T)
    lam = _lyap_1d(f, df, x[0], n=20000)
    return _finish(x, rng, dict(z=z, **_chaos_tag(lam)))


@family("F", "shift-gauss", 4, DET)
def shift_gauss(i, rng, T, S):
    """Bernoulli (doubling) shift (even i, iterated in exact rational arithmetic) and Gauss map (odd i)."""
    if i % 2 == 0:
        from fractions import Fraction
        # exact doubling map of an irrational-like rational with a huge odd denominator
        v = Fraction(int(rng.integers(1, 2**60)) * 2 + 1, 2**61 * 3**40 + 1)
        for _ in range(200):  # the opening iterates are v, 2v, 4v ...: exponentially small, not yet mixing
            v = (2 * v) % 1
        x = np.empty(T)
        for t in range(T):
            v = (2 * v) % 1
            x[t] = float(v)
        return _finish(x, rng, dict(kind="doubling", lyapunov_max=math.log(2), chaotic="yes"))
    f = lambda v: (1 / v) % 1.0 if v > 1e-12 else 0.5
    x = _iterate(f, rng.uniform(0.1, 0.9), T)
    lam = _lyap_1d(f, lambda v: -1 / (v * v) if v > 1e-9 else 1e9, x[0])
    return _finish(x, rng, dict(kind="gauss", **_chaos_tag(lam)))


@family("F", "piecewise-impact", 3, DET)
def piecewise_impact(i, rng, T, S):
    """Piecewise-linear / square-root (Nordmark impact) maps: x -> a x + b (x<0), x -> -c sqrt(x) + d (x>=0)."""
    a = S.draw("a", 0.5, 0.95)
    for _ in range(30):  # this family is meant to be chaotic: redraw c, d until lambda > 0
        c, d = rng.uniform(1.0, 3.0), rng.uniform(0.2, 0.8)
        f = lambda v, a=a, c=c, d=d: (a * v + d) if v < 0 else (-c * math.sqrt(v) + d)
        df = lambda v, a=a, c=c: a if v < 0 else (-c / (2 * math.sqrt(max(v, 1e-9))))
        x = _iterate(f, rng.uniform(-0.5, 0.5), T)
        lam = _lyap_1d(f, df, x[0])
        if lam > 0.02:
            break
    return _finish(x, rng, dict(a=a, c=c, d=d, **_chaos_tag(lam)))


@family("F", "dysts-map", 22, {**DET, "chaotic": "yes"}, profiles={"stationary1000": {"indices": [0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], "strat_n": 22}})  # no index wraps; slot 8 duplicated Henon
def dysts_map(i, rng, T, S):
    """One trajectory per usable dysts map (22 of 23), one coordinate, perturbed initial condition."""
    from ..sources import catalogue as _catalogue, trajectory as _trajectory
    from ..sources import usable_systems
    from ..registry import profile
    maps = [c for c in usable_systems() if c[2] == "map"]
    if profile() == "stationary1000":  # Circle: unbounded angle; Duffing: drifting; Gingerbreadman: periodic at the default IC
        maps = [c for c in maps if c[0] not in ("Circle", "Duffing", "Gingerbreadman")]
    for shift in range(len(maps)):
        name, ctor, cat = maps[(i + shift) % len(maps)]
        tag = f"s1000-{i}-{int(rng.integers(1 << 30))}"  # memoises this rng stream's trajectory only
        r = _trajectory(name, ctor, cat, T, rng_for("traj", tag), tag=tag)  # own stream: cache hits must not change rng use
        if r is None:
            raise RuntimeError(f"dysts map {name} unusable")
        if profile() != "stationary1000" or np.unique(np.round(r[0], 12)).size >= 100:
            break  # otherwise periodic at its default: fall back to the next map
    if profile() == "stationary1000":
        from .G_flows import _periodicity
        if _periodicity(r[0]) > 0.95:  # a near-regular coordinate: try the map's other coordinate
            r2 = _trajectory(name, ctor, cat, T, rng_for("traj", tag + "-c1"), tag=tag + "-c1", coord=1)
            if r2 is not None and _periodicity(r2[0]) < _periodicity(r[0]):
                r = r2
    return _finish(r[0], rng, dict(system=name))


@family("F", "map-sweep", 16, {**DET, "chaotic": "partly"})
def map_sweep(i, rng, T, S):
    """Regime sweeps of higher-dimensional maps: Henon (a), Lozi, Ikeda (u), Chirikov standard map
    (K across KAM -> chaotic; wrapped and unwrapped), Zaslavskii, Arnold cat, Burgers, coupled logistic pair."""
    kinds = ["henon", "henon", "henon", "lozi", "lozi", "ikeda", "ikeda", "standard", "standard",
             "standard", "standard", "zaslavskii", "cat", "burgers", "coupled-logistic", "standard"]
    kind = kinds[i]
    n = T + BURN
    x = np.empty(n)
    from ..registry import profile
    if profile() == "stationary1000" and kind == "zaslavskii":
        kind = "ikeda"  # this Zaslavskii parameterisation sits on a period-2 orbit
    if kind == "henon":
        a = S.draw("henon_a", 1.0, 1.4)
        for _ in range(30):
            u, v = 0.1, 0.1
            for t in range(n):
                u, v = 1 - a * u * u + v, 0.3 * u
                x[t] = u
            if profile() != "stationary1000" or np.unique(np.round(x[BURN:], 12)).size >= 100:
                break
            a = rng.uniform(1.15, 1.4)  # periodic window: redraw
        par = dict(a=a)
    elif kind == "lozi":
        a = S.draw("lozi_a", 1.55, 1.78)  # the Lozi attractor's chaotic band (b = 0.5)
        for _ in range(30):
            u, v = 0.1, 0.1
            for t in range(n):
                u, v = 1 - a * abs(u) + v, 0.5 * u
                x[t] = u
            if profile() != "stationary1000" or np.unique(np.round(x[BURN:], 12)).size >= 100:
                break
            a = rng.uniform(1.55, 1.78)
        par = dict(a=a)
    elif kind == "ikeda":
        uu = S.draw("ikeda_u", 0.7, 0.9)  # u >= 0.92 converges to a fixed point
        z = 0.1 + 0.1j
        for t in range(n):
            tt = 0.4 - 6 / (1 + abs(z) ** 2)
            z = 1 + uu * z * np.exp(1j * tt)
            x[t] = z.real
        par = dict(u=uu)
    elif kind == "standard":
        K = {7: 0.5, 8: 0.97, 9: 1.5, 10: 3.0, 15: 6.0}[i]
        if profile() == "stationary1000" and i in (8, 9):
            K = {8: 2.5, 9: 4.5}[i]  # the regular (KAM) regimes read as sinusoids
        p, q = rng.uniform(0, 2 * np.pi), rng.uniform(0, 2 * np.pi)
        from ..registry import profile
        unwrapped = i % 2 == 0 and profile() != "stationary1000"  # momentum diffuses: full profile only
        pu = p
        for t in range(n):
            p = p + K * math.sin(q)
            pu += K * math.sin(q)
            q = (q + p) % (2 * math.pi)
            p = p % (2 * math.pi)
            x[t] = pu if unwrapped else (math.sin(q) if profile() == "stationary1000" else q)
        par = dict(K=K, observed="p-unwrapped" if unwrapped else ("sin-theta" if profile() == "stationary1000" else "theta"))
    elif kind == "zaslavskii":
        eps, nu, r = 5.0, 0.2, 2.0
        mu = (1 - math.exp(-r)) / r
        u, v = 0.1, 0.1
        for t in range(n):
            u, v = (u + nu * (1 + mu * v) + eps * nu * mu * math.cos(2 * math.pi * u)) % 1.0, \
                   math.exp(-r) * (v + eps * math.cos(2 * math.pi * u))
            x[t] = v
        par = dict(eps=eps, nu=nu, r=r)
    elif kind == "cat":
        u, v = rng.uniform(), rng.uniform()
        for t in range(n):
            u, v = (2 * u + v) % 1.0, (u + v) % 1.0
            x[t] = u
        par = {}
    elif kind == "burgers":
        a, b = 0.75, 1.75
        u, v = -0.1, 0.1
        for t in range(n):
            u, v = a * u - v * v, b * v + u * v
            x[t] = v
        par = dict(a=a, b=b)
    else:
        r, c = 3.9, S.draw("coupling", 0.05, 0.4)
        u, v = 0.3, 0.6
        for t in range(n):
            fu, fv = r * u * (1 - u), r * v * (1 - v)
            u, v = (1 - c) * fu + c * fv, (1 - c) * fv + c * fu
            x[t] = u
        par = dict(r=r, coupling=c)
    xs = x[BURN:]
    return _finish(xs, rng, dict(kind=kind, **par))


def _pi_digits(n):
    """First n decimal digits of pi after the point (Machin, integer arithmetic)."""
    prec = n + 10
    scale = 10 ** prec

    def arctan_inv(k):
        total, term, sign, i = 0, scale // k, 1, 1
        k2 = k * k
        while term:
            total += sign * (term // i)
            term //= k2
            sign, i = -sign, i + 2
        return total

    pi = 4 * (4 * arctan_inv(5) - arctan_inv(239))
    s = str(pi)[1:1 + n]
    return np.array([int(c) for c in s], dtype=float)


def _ca_row_density(rule: int, width: int, steps: int, rng, burn: int = 500):
    table = [(rule >> k) & 1 for k in range(8)]
    row = rng.integers(0, 2, width)
    for _ in range(burn):  # initial transient of the random start
        idx = 4 * np.roll(row, 1) + 2 * row + np.roll(row, -1)
        row = np.array([table[k] for k in idx])
    out = np.empty(steps)
    for t in range(steps):
        out[t] = row.mean()
        idx = 4 * np.roll(row, 1) + 2 * row + np.roll(row, -1)
        row = np.array([table[k] for k in idx])
    return out


def _ca_column(rule: int, width: int, steps: int):
    table = [(rule >> k) & 1 for k in range(8)]
    row = np.zeros(width, dtype=int)
    row[width // 2] = 1
    out = np.empty(steps)
    for t in range(steps):
        out[t] = row[width // 2]
        idx = 4 * np.roll(row, 1) + 2 * row + np.roll(row, -1)
        row = np.array([table[k] for k in idx])
    return out


@family("F", "aperiodic", 10, {**DET, "chaotic": "no", "periodic": "no", "discrete_valued": "yes", "reversible": "na"}, profiles={"stationary1000": 0})
def aperiodic(i, rng, T, S):
    """Deterministic aperiodic non-chaotic sequences: Thue-Morse, Fibonacci word, Rudin-Shapiro,
    cut-and-project quasicrystal, CA rule 30 / 110 row density, rule 30 centre column, decimal
    digits of pi, binary digits of sqrt 2, Collatz stopping times."""
    kind = ["thue-morse", "fibonacci", "rudin-shapiro", "cut-project", "rule30-density",
            "rule110-density", "rule30-column", "pi-digits", "sqrt2-bits", "collatz"][i]
    N = T
    if kind == "thue-morse":
        x = np.array([bin(n).count("1") % 2 for n in range(N)], dtype=float)
    elif kind == "fibonacci":
        s = "0"
        while len(s) < N:
            s = "".join("01" if c == "0" else "0" for c in s)
        x = np.array([int(c) for c in s[:N]], dtype=float)
    elif kind == "rudin-shapiro":
        x = np.array([bin(n & (n >> 1)).count("1") % 2 for n in range(N)], dtype=float)
    elif kind == "cut-project":
        tau = (1 + 5**0.5) / 2
        n = np.arange(1, N + 1)
        x = (np.floor((n + 1) * tau) - np.floor(n * tau)).astype(float)
    elif kind == "rule30-density":
        x = _ca_row_density(30, 400, N, rng)
        return x, dict(kind=kind, discrete_valued="no")
    elif kind == "rule110-density":
        x = _ca_row_density(110, 400, N, rng)
        return x, dict(kind=kind, discrete_valued="no")
    elif kind == "rule30-column":
        x = _ca_column(30, 2 * N + 11, N)  # the centre column of rule 30: Wolfram's pseudo-random sequence
    elif kind == "pi-digits":
        x = _pi_digits(N)
    elif kind == "sqrt2-bits":
        v = math.isqrt(2 * 4**N)
        b = bin(v)[2:]
        x = np.array([int(c) for c in b[1:N + 1]], dtype=float)
    else:
        def stop(n):
            k = 0
            while n != 1:
                n = n // 2 if n % 2 == 0 else 3 * n + 1
                k += 1
            return k
        x = np.array([stop(n) for n in range(1, N + 1)], dtype=float)
    return x, dict(kind=kind)


@family("F", "aperiodic-real", 0, {**DET, "chaotic": "no", "periodic": "no", "reversible": "na"}, profiles={"stationary1000": 2})
def aperiodic_real(i, rng, T, S):
    """Real-valued deterministic aperiodic sequences: cellular-automaton row density, rule 30 (class 3, i = 0) and
    rule 110 (class 4: a periodic background crossed by gliders, i = 1; until 2026-09-26 a second rule-30
    density at another width, which was redundant with the first)."""
    width = [3000, 8000][i % 2]  # density is quantised to 1/width; rule 110 fluctuates less, so needs wider rows for >= 100 levels
    rule = [30, 110][i % 2]
    return _ca_row_density(rule, width, T, rng), dict(kind=f"rule{rule}-density", width=width)


@family("F", "rulkov", 0, {**DET, "chaotic": "yes", "bursty": "yes"}, profiles={"stationary1000": 3})
def rulkov(i, rng, T, S):
    """Rulkov (2001) map neuron: fast x_{n+1} = alpha / (1 + x_n^2) + y_n and slow
    y_{n+1} = y_n - mu (x_n - sigma). Chaotic bursts of spikes separated by slow silent recovery;
    alpha stratified over [4.1, 4.6], mu LU[0.003, 0.01] sets the burst period (~10 bursts per record)."""
    al = S.draw("alpha", 4.1, 4.6)
    mu = math.exp(rng.uniform(math.log(0.003), math.log(0.01)))
    sig = rng.uniform(-1.3, -0.5)
    x, y = rng.uniform(-1.5, -0.5), -3.0
    out = np.empty(T + 3 * BURN)
    for t in range(out.size):
        x, y = al / (1 + x * x) + y, y - mu * (x - sig)
        out[t] = x
    return _finish(out[3 * BURN:], rng, dict(alpha=al, mu=mu, sigma=sig))


@family("F", "sna", 0, {**DET, "chaotic": "no", "quasiperiodic": "partly"}, profiles={"stationary1000": 2})
def sna(i, rng, T, S):
    """Strange nonchaotic attractor (Grebogi, Ott, Pelikan & Yorke 1984): the quasi-periodically forced
    map x_{n+1} = 2 sigma tanh(x_n) cos(2 pi theta_n), theta_{n+1} = theta_n + omega mod 1, omega the
    golden mean. For sigma > 1 the attractor is fractal but its Lyapunov exponent is negative."""
    sigma = S.draw("sigma", 1.3, 2.0)
    om = (5 ** 0.5 - 1) / 2
    x, th = rng.uniform(0.1, 1.0), rng.uniform()
    out = np.empty(T + BURN)
    for t in range(T + BURN):
        x = 2 * sigma * math.tanh(x) * math.cos(2 * math.pi * th)
        th = (th + om) % 1.0
        out[t] = x
    return _finish(out[BURN:], rng, dict(sigma=sigma, omega=om, lyapunov_max=float("nan")))
