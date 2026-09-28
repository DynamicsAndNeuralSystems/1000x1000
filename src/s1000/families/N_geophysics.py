"""Class N, geophysics and climate (22)."""
from __future__ import annotations

import math

import numpy as np

from ..registry import family
from ..util import ar2_from_period, ar_filter, bin_events, burn, burstiness, em_sde, ma_filter, rk4

GEO = dict(domain="geophysics", linear="no", gaussian="no", stationary="yes")


def _bartlett_lewis(hours, rng, storm_rate, cell_rate, storm_dur, cell_dur, mean_int):
    """Bartlett-Lewis rectangular pulses: storms (Poisson), cells within each storm (Poisson over
    an exponential storm duration), each cell a rectangular pulse of exponential duration and
    exponential intensity. Returns hourly totals."""
    x = np.zeros(hours)
    t = 0.0
    while t < hours:
        t += rng.exponential(1 / storm_rate)
        dur = rng.exponential(storm_dur)
        c = t
        while c < t + dur:
            L = rng.exponential(cell_dur)
            I = rng.exponential(mean_int)
            a, b = int(c), int(math.ceil(c + L))
            for h in range(max(a, 0), min(b, hours)):
                ov = min(c + L, h + 1) - max(c, h)
                if ov > 0:
                    x[h] += I * ov
            c += rng.exponential(1 / cell_rate)
    return x


@family("N", "rainfall-pulse", 4, {**GEO, "skewed": "yes", "bursty": "yes", "event_like": "yes", "reversible": "no"}, profiles={"stationary1000": 6})
def rainfall_pulse(i, rng, T, S):
    """Bartlett-Lewis rectangular-pulse rainfall, aggregated to hourly (even i) or daily (odd i)
    totals; storm rate S over temperate <-> convective regimes. Zero-inflated, heavily right-skewed."""
    storm_rate = S.draw("storm_rate", 0.02, 0.08, log=True)  # per hour: >= 20 storms per 1000 h
    cell_rate, storm_dur, cell_dur = rng.uniform(0.5, 2.0), rng.uniform(3, 12), rng.uniform(0.5, 3.0)
    mean_int = rng.uniform(1.0, 4.0)
    if i % 2 == 0:
        x = _bartlett_lewis(T, rng, storm_rate, cell_rate, storm_dur, cell_dur, mean_int)
        agg = "hourly"
    else:
        h = _bartlett_lewis(24 * T, rng, storm_rate, cell_rate, storm_dur, cell_dur, mean_int)
        x = h.reshape(T, 24).sum(axis=1)
        agg = "daily"
    from ..registry import profile as _pp
    extra = dict(storm_dur=storm_dur, cell_dur=cell_dur, mean_int=mean_int) if _pp() == "stationary1000" else {}
    return x, dict(storm_rate=storm_rate, cell_rate=cell_rate, aggregation=agg, zero_fraction=float(np.mean(x == 0)), **extra)


@family("N", "richardson-weather", 3, {**GEO, "skewed": "yes", "regime_switching": "yes", "reversible": "yes"}, profiles={"stationary1000": 0})
def richardson(i, rng, T, S):
    """Richardson weather generator: Markov-chain wet/dry days (P(wet|wet) S[0.4, 0.8]) with gamma
    daily amounts (shape S[0.5, 1.2]); i=2 adds an annual cycle in the wet probability."""
    pww = S.draw("p_ww", 0.4, 0.8)
    pwd = rng.uniform(0.1, 0.4)
    shape = S.draw("shape", 0.5, 1.2)
    scale = rng.uniform(3, 12)
    wet = False
    x = np.zeros(T)
    for t in range(T):
        seas = 0.15 * math.sin(2 * math.pi * t / 365.25) if i == 2 else 0.0
        p = (pww if wet else pwd) + seas
        wet = rng.uniform() < p
        x[t] = rng.gamma(shape, scale) if wet else 0.0
    return x, dict(p_ww=pww, p_wd=pwd, shape=shape, seasonal=i == 2, zero_fraction=float(np.mean(x == 0)),
                   stationary="no" if i == 2 else "yes", nonstationary_kind="drift" if i == 2 else "none")


@family("N", "river-discharge", 3, {**GEO, "skewed": "yes", "reversible": "no"}, profiles={"stationary1000": 0})
def river_discharge(i, rng, T, S):
    """Daily river discharge: Nash cascade of n linear reservoirs (n S[2, 5], k U[1, 6] days) driven
    by Richardson-type rainfall, plus slow baseflow; i=2 adds a seasonal snowmelt input."""
    n_res = S.integer("n_res", 2, 5)
    k = rng.uniform(1.0, 6.0)
    pww, pwd, shape, scale = 0.6, 0.25, 0.8, 8.0
    wet = False
    N = T + 400
    rain = np.zeros(N)
    for t in range(N):
        wet = rng.uniform() < (pww if wet else pwd)
        rain[t] = rng.gamma(shape, scale) if wet else 0.0
    if i == 2:
        rain += 6.0 * np.clip(np.sin(2 * np.pi * (np.arange(N) - 80) / 365.25), 0, None) ** 3
    q = rain.copy()
    for _ in range(n_res):
        q = ar_filter(q * (1 / k), [1 - 1 / k])
    base = ar_filter(0.02 * rain, [0.995])
    x = burn(q + base, T)
    return x + 0.02 * x.std() * rng.standard_normal(T), dict(n_res=n_res, k=k, snowmelt=i == 2,
                                                            stationary="no" if i == 2 else "yes", nonstationary_kind="drift" if i == 2 else "none")


def _etas(t_end, mu, K, alpha, c, p, b, m0, rng, m_max=7.0):
    """ETAS by branching: background Poisson events, each event spawning Omori-Utsu aftershocks."""
    beta = math.log(10) * b
    n_bg = rng.poisson(mu * t_end)
    events = [(t, m0 + min(rng.exponential(1 / beta), m_max - m0)) for t in rng.uniform(0, t_end, n_bg)]
    queue = list(events)
    while queue:
        t, m = queue.pop()
        n_off = rng.poisson(K * math.exp(alpha * (m - m0)))
        for _ in range(n_off):
            u = rng.uniform()
            dt = c * ((1 - u) ** (-1 / (p - 1)) - 1)
            tc = t + dt
            if tc < t_end:
                mc = m0 + min(rng.exponential(1 / beta), m_max - m0)
                events.append((tc, mc))
                queue.append((tc, mc))
        if len(events) > 200000:
            break
    return np.array(sorted(e[0] for e in events))


@family("N", "stick-slip", 0, {**GEO, "event_like": "partly", "skewed": "yes", "reversible": "no"},
        profiles={"stationary1000": 2})
def stick_slip(i, rng, T, S):
    """Stress on a fault under steady tectonic loading with stick-slip release: a noisy linear ramp
    that drops at each earthquake, giving an irregular sawtooth. i = 0 is time-predictable (a random
    failure threshold, full drop to a base level); i = 1 is slip-predictable (a fixed threshold, random
    stress drop). Loading rate stratified so ~15-50 cycles fall in the record (Shimazaki & Nakata 1980)."""
    load = S.draw("load", 0.015, 0.05, log=True)
    cv = rng.uniform(0.2, 0.5)
    s, th = rng.uniform(0, 0.5), 1.0
    out = np.empty(T + 200)
    for t in range(out.size):
        s += load * (1 + 0.3 * rng.standard_normal())
        if s >= th:
            if i % 2 == 0:
                s, th = 0.0, max(0.2, 1 + cv * rng.standard_normal())
            else:
                s -= min(s, max(0.05, rng.gamma(1 / cv ** 2, cv ** 2)))
        out[t] = s
    out = out[200:]
    return out + 0.01 * out.std() * rng.standard_normal(T), dict(
        kind="time-predictable" if i % 2 == 0 else "slip-predictable", load=load, cv=cv)


@family("N", "etas", 4, {**GEO, "bursty": "yes", "event_like": "yes", "heavy_tailed": "yes", "discrete_valued": "yes", "reversible": "no"}, profiles={"stationary1000": 5})
def etas(i, rng, T, S):
    """ETAS earthquake model (Ogata): background rate + Omori-Utsu aftershock cascades with
    Gutenberg-Richter magnitudes; branching ratio S[0.5, 0.95], Omori p S[1.05, 1.4]. Daily counts
    (even i) or inter-event times (odd i; the stationary profile uses inter-event times only) — the burstiest thing in the corpus."""
    n_br = S.draw("branching", 0.5, 0.95)
    p = S.draw("omori_p", 1.05, 1.4)
    alpha, b, c, m0 = 1.5, 1.0, 0.01, 3.0
    beta = math.log(10) * b
    # branching ratio n = K * beta/(beta - alpha) for exponential magnitudes -> K
    K = n_br * (beta - alpha) / beta
    mu = rng.uniform(0.3, 0.8)  # background rate per day: >= 300 background events over the record
    t_end = 4 * T
    times = _etas(t_end, mu, K, alpha, c, p, b, m0, rng)
    iv = np.diff(times)
    info = dict(branching=n_br, omori_p=p, mu=mu, K=K, burstiness_B=burstiness(iv), event_rate=times.size / t_end)
    from ..registry import profile
    if (i % 2 == 1 or profile() == "stationary1000") and iv.size >= T:
        return iv[-T:], dict(info, observed="inter-event-times", discrete_valued="no", event_like="no")
    return bin_events(times, t_end)[-T:], info


@family("N", "soc-avalanche", 1, {**GEO, "heavy_tailed": "yes", "skewed": "yes", "discrete_valued": "yes", "reversible": "yes"}, profiles={"stationary1000": 0})
def soc_avalanche(i, rng, T, S):
    """Bak-Tang-Wiesenfeld sandpile (24 x 24, open boundaries): the avalanche-size sequence."""
    L = 24
    z = rng.integers(0, 4, (L, L))
    x = np.empty(T)
    for k in range(T + 500):
        a, b = rng.integers(0, L, 2)
        z[a, b] += 1
        size = 0
        while True:
            over = np.argwhere(z >= 4)
            if over.size == 0:
                break
            for (r, c) in over:
                z[r, c] -= 4
                size += 1
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < L and 0 <= cc < L:
                        z[rr, cc] += 1
        if k >= 500:
            x[k - 500] = size
    return x, dict(L=L)


@family("N", "barnes-sunspot", 1, {**GEO, "linear": "no", "periodic": "partly", "reversible": "no"})
def barnes_sunspot(i, rng, T, S):
    """Barnes-type sunspot model: an ARMA(2,2) with an 11-year pseudo-period (monthly sampling, 132
    samples) passed through a static nonlinearity y = z^2 + 0.03 z^3."""
    from ..registry import profile
    P = 22.0 if profile() == "stationary1000" else 132.0  # stationary: semi-annual sampling, ~45 cycles per record
    a = ar2_from_period(P, 0.985 if P > 100 else 0.93)
    e = rng.standard_normal(T + 3000)
    z = ar_filter(ma_filter(e, [-0.5, 0.2]), a)
    z = burn(z, T)
    z = z / z.std() * 2.0
    return z**2 + 0.03 * z**3, dict(period_samples=P, skewed="yes")


def _stommel(u, eta1, eta2, eta3):
    Tt, Ss = u
    q = abs(Tt - Ss)
    return np.array([eta1 - Tt * (1 + q), eta2 - Ss * (eta3 + q)])


@family("N", "climate-model", 4, {**GEO, "continuous_time": "yes"})
def climate_model(i, rng, T, S):
    """Stochastic climate models: Hasselmann (OU forced by weather noise with an annual cycle),
    the ENSO delayed oscillator (Suarez-Schopf T' = T - T^3 - alpha T(t - delta)), Stommel two-box
    thermohaline circulation with noise (bistable), and Daisyworld with noisy luminosity."""
    kind = ["hasselmann", "enso", "stommel", "daisyworld"][i]
    if kind == "hasselmann":
        tau = S.draw("tau", 20, 200, log=True)
        t = np.arange(T)
        forcing = np.sin(2 * np.pi * t / 12.0)
        e = rng.standard_normal(T + 2000)
        x = burn(ar_filter(e * math.sqrt(1 - math.exp(-2 / tau)), [math.exp(-1 / tau)]), T)
        return x + 0.7 * forcing, dict(kind=kind, tau=tau, linear="yes", gaussian="yes", period_samples=12.0, periodic="partly")
    if kind == "enso":
        from .G_flows import _dde
        alpha, delta = S.draw("alpha", 0.6, 0.95), rng.uniform(1.5, 3.0)
        f = lambda x, xd: x - x**3 - alpha * xd
        dt = 0.01
        from ..registry import profile
        if profile() == "stationary1000":
            # the delayed oscillator on its own is a limit cycle: drive it with weather noise (Euler-Maruyama)
            sig = rng.uniform(0.15, 0.4)
            m = int(round(delta / dt))
            n = int(700 / dt)
            xs = np.empty(n)
            xs[: m + 1] = 0.5 + 0.01 * rng.standard_normal(m + 1)
            dW = rng.standard_normal(n) * math.sqrt(dt)
            for t in range(m, n - 1):
                xs[t + 1] = xs[t] + dt * f(xs[t], xs[t - m]) + sig * dW[t]
            xf = xs[int(100 / dt):]
        else:
            xf = _dde(f, delta, dt, int(600 / dt), 0.5, int(100 / dt), rng)
        step = max(1, xf.size // T)
        x = xf[::step][:T]
        return x + 0.02 * x.std() * rng.standard_normal(T), dict(kind=kind, alpha=alpha, delta=delta, periodic="partly",
                                                                 **({"sigma": sig} if profile() == "stationary1000" else {}))
    if kind == "stommel":
        eta1, eta2, eta3 = 3.0, S.draw("eta2", 0.6, 1.3), 0.3
        dt, k = 0.02, 10
        out = em_sde(lambda u: _stommel(u, eta1, eta2, eta3), lambda u: np.array([0.0, 0.25]), [1.0, 1.0], dt, T * k, rng, k, 5000)
        q = out[:, 0] - out[:, 1]
        return q, dict(kind=kind, eta2=eta2, regime_switching="yes", reversible="partly")
    # Daisyworld with fluctuating luminosity
    Lum = S.draw("luminosity", 0.8, 1.2)  # habitable range: outside it the daisies go extinct (absorbing)

    def dw(u):
        aw, ab, Lt = u
        ag = 1 - aw - ab
        A = aw * 0.75 + ab * 0.25 + ag * 0.5
        Te = (Lt * 917 / 5.67e-8 * (1 - A)) ** 0.25 if Lt > 0 else 250.0
        Tw, Tb = 20 * (A - 0.75) + Te, 20 * (A - 0.25) + Te
        bw = max(0.0, 1 - 0.003265 * (295.5 - Tw) ** 2)
        bb = max(0.0, 1 - 0.003265 * (295.5 - Tb) ** 2)
        return np.array([aw * (ag * bw - 0.3) + 1e-3 * (aw < 0.01), ab * (ag * bb - 0.3) + 1e-3 * (ab < 0.01), -(Lt - Lum) / 50.0])  # seed bank: no absorbing extinction
    dt, k = 0.1, 10
    out = em_sde(dw, lambda u: np.array([0.0, 0.0, 0.05]), [0.2, 0.2, Lum], dt, T * k, rng, k, 20000)
    return out[:, 0], dict(kind=kind, luminosity=Lum)


def _sabra_scalar(N, nu, f1, u0, dt, n_steps, burn_n, sub, shell):
    """Sabra shell model integrated in scalar Python complex arithmetic (bit-reproducible across
    processes: numpy's vectorised complex ops pick alignment-dependent SIMD/FMA paths whose last-ulp
    differences a chaotic system amplifies). du_n/dt = i[k_{n+1} u_{n+2} u*_{n+1} - (1/2) k_n u_{n+1} u*_{n-1}
    + (1/2) k_{n-1} u_{n-1} u_{n-2}] - nu k_n^2 u_n + f_n (energy-conserving triad coefficients), Heun step
    with an exact integrating factor for the viscous term."""
    import cmath
    k = [2.0 ** n for n in range(N)]
    decay = [cmath.exp(-nu * kn * kn * dt) for kn in k]
    u = list(u0)
    out = []

    def rhs(v):
        r = [0j] * N
        for n in range(N):
            a = k[n + 1] * v[n + 2] * v[n + 1].conjugate() if n + 2 < N else 0j
            b = 0.5 * k[n] * v[n + 1] * v[n - 1].conjugate() if 1 <= n < N - 1 else 0j
            c = 0.5 * k[n - 1] * v[n - 1] * v[n - 2] if n >= 2 else 0j
            r[n] = 1j * (a - b + c)
        r[1] += f1
        return r
    for s in range(burn_n + n_steps):
        k1 = rhs(u)
        up = [u[n] + dt * k1[n] for n in range(N)]
        k2 = rhs(up)
        u = [(u[n] + 0.5 * dt * (k1[n] + k2[n])) * decay[n] for n in range(N)]
        if s >= burn_n and (s - burn_n) % sub == 0:
            v = u[shell].real
            if v != v or abs(v) > 1e3:
                raise RuntimeError("shell model diverged")
            out.append(v)
    return out


@family("N", "turbulence", 2, {**GEO, "bursty": "yes", "heavy_tailed": "yes", "heteroskedastic": "yes", "continuous_time": "yes", "reversible": "no"})
def turbulence(i, rng, T, S):
    """Turbulence: Sabra shell-model velocity at a mid-inertial shell (intermittent), and a point
    velocity of the randomly forced viscous Burgers equation (spectral, 128 modes)."""
    if i == 0:
        N, nu, dt = 16, 1e-6, 2e-5
        u0 = [1e-2 * complex(rng.standard_normal(), rng.standard_normal()) * (2.0 ** n) ** (-1 / 3) for n in range(N)]
        from ..registry import profile
        sub = 500 if profile() == "stationary1000" else 200  # coarser sampling: more eddy turnovers per record
        out = _sabra_scalar(N, nu, 0.5 * (1 + 1j), u0, dt, n_steps=sub * T, burn_n=300000, sub=sub, shell=7)
        return np.array(out[:T]), dict(kind="sabra-shell", shell=7, nu=nu)
    M = 128
    L = 2 * np.pi
    kx = np.fft.fftfreq(M, d=L / M) * 2 * np.pi
    nu = 0.01
    u = np.zeros(M)
    dt = 0.005
    out = np.empty(T)
    from ..registry import profile
    sub = 150 if profile() == "stationary1000" else 60
    for s in range(sub * T + 4000):
        uh = np.fft.fft(u)
        force = np.zeros(M, dtype=complex)
        for m in (1, 2, 3):
            force[m] = 2.0 * (rng.standard_normal() + 1j * rng.standard_normal()) / math.sqrt(dt)
            force[-m] = np.conj(force[m])
        nonlin = np.fft.fft(u * np.fft.ifft(1j * kx * uh).real)
        uh = (uh - dt * nonlin + dt * force) / (1 + dt * nu * kx**2)
        u = np.fft.ifft(uh).real
        if s >= 4000 and (s - 4000) % sub == 0:
            out[(s - 4000) // sub] = u[M // 3]
    return out, dict(kind="burgers-point", nu=nu)


@family("N", "richardson-weather-stationary", 0, {**GEO, "skewed": "yes", "regime_switching": "yes", "reversible": "yes"}, profiles={"stationary1000": 3})
def richardson_stationary(i, rng, T, S):
    """Richardson weather generator without the annual cycle: Markov wet/dry days (P(wet|wet) S[0.4, 0.8]) with gamma amounts."""
    pww, pwd = S.draw("p_ww", 0.4, 0.8), rng.uniform(0.1, 0.4)
    shape, scale = S.draw("shape", 0.5, 1.2), rng.uniform(3, 12)
    wet = False
    x = np.zeros(T)
    for t in range(T):
        wet = rng.uniform() < (pww if wet else pwd)
        x[t] = rng.gamma(shape, scale) if wet else 0.0
    return x, dict(p_ww=pww, p_wd=pwd, shape=shape, scale=scale, zero_fraction=float(np.mean(x == 0)))


@family("N", "river-discharge-stationary", 0, {**GEO, "skewed": "yes", "reversible": "no"}, profiles={"stationary1000": 3})
def river_stationary(i, rng, T, S):
    """Daily discharge from a Nash cascade (n S[2, 5], k U[1, 6] days) driven by Markov-gamma rainfall, plus baseflow; no seasonal input."""
    n_res, k = S.integer("n_res", 2, 5), rng.uniform(1.0, 6.0)
    wet = False
    N = T + 400
    rain = np.zeros(N)
    for t in range(N):
        wet = rng.uniform() < (0.6 if wet else 0.25)
        rain[t] = rng.gamma(0.8, 8.0) if wet else 0.0
    q = rain.copy()
    for _ in range(n_res):
        q = ar_filter(q * (1 / k), [1 - 1 / k])
    x = burn(q + ar_filter(0.02 * rain, [0.98]), T)  # baseflow memory ~50 days
    return x + 0.02 * x.std() * rng.standard_normal(T), dict(n_res=n_res, k=k)
