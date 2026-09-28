"""Class K: non-stationary processes, including the PINUP row (Owens, Tamaki & Fulcher 2026)."""
from __future__ import annotations

import math

import numpy as np
from scipy.integrate import solve_ivp

from ..registry import family
from ..util import add_noise, ar_filter, burn, deterministic_noise_sigma, dominant_period, stable_ar

NS = dict(stationary="no", gaussian="no", linear="no")


@family("K", "random-walk", 8, {**NS, "nonstationary_kind": "walk", "linear": "yes", "gaussian": "yes", "reversible": "yes"}, profiles={"stationary1000": 0})
def random_walk(i, rng, T, S):
    """Random walk (i%4==0), ARIMA(p,1,q) (i%4 in {1,2}), near-unit-root AR(1) with phi S[0.99, 0.9999] (i%4==3)."""
    kind = ["rw", "arima", "arima", "near-unit"][i % 4]
    if kind == "rw":
        return np.cumsum(rng.standard_normal(T)), dict(kind=kind)
    if kind == "arima":
        p = int(rng.integers(1, 3))
        a = stable_ar(p, rng, 0.7)
        e = ar_filter(rng.standard_normal(T + 500), a)
        return np.cumsum(burn(e, T)), dict(kind=kind, p=p, a=a)
    phi = S.draw("phi", 0.99, 0.9999, log=True)
    return burn(ar_filter(rng.standard_normal(T + 200), [phi]), T), dict(kind=kind, phi=phi)


@family("K", "trend", 8, {**NS, "nonstationary_kind": "trend", "linear": "yes", "gaussian": "yes"}, profiles={"stationary1000": 0})
def trend(i, rng, T, S):
    """Deterministic trend + stationary AR(1) noise: linear, quadratic, exponential or logistic growth;
    trend-to-noise ratio LU[0.5, 10]."""
    kind = ["linear", "quadratic", "exponential", "logistic"][i % 4]
    snr = S.draw("trend_ratio", 0.5, 10, log=True)
    t = np.linspace(0, 1, T)
    if kind == "linear":
        m = t
    elif kind == "quadratic":
        m = (t - rng.uniform(0.2, 0.8)) ** 2
    elif kind == "exponential":
        m = np.exp(rng.uniform(2, 5) * t)
    else:
        k, t0 = rng.uniform(8, 25), rng.uniform(0.3, 0.7)
        m = 1 / (1 + np.exp(-k * (t - t0)))
    m = (m - m.mean()) / m.std() * snr
    phi = rng.uniform(0.0, 0.8)
    e = burn(ar_filter(rng.standard_normal(T + 500) * math.sqrt(1 - phi**2), [phi]), T)
    return m + e, dict(kind=kind, trend_ratio=snr, phi=phi)


@family("K", "structural-break", 8, {**NS, "nonstationary_kind": "break", "linear": "yes", "gaussian": "yes"}, profiles={"stationary1000": 0})
def structural_break(i, rng, T, S):
    """AR(1) noise with 1-5 breakpoints in mean, variance or spectrum (phi)."""
    what = ["mean", "variance", "spectrum", "mean+variance"][i % 4]
    nb = S.integer("n_breaks", 1, 5)
    cuts = np.sort(rng.choice(np.arange(50, T - 50), nb, replace=False))
    bounds = np.concatenate([[0], cuts, [T]])
    x = np.zeros(T)
    for a, b in zip(bounds[:-1], bounds[1:]):
        phi = rng.uniform(-0.5, 0.9) if "spectrum" in what else 0.5
        sd = math.exp(rng.uniform(math.log(0.3), math.log(3))) if "variance" in what else 1.0
        mu = rng.uniform(-3, 3) if "mean" in what else 0.0
        seg = ar_filter(rng.standard_normal(b - a + 300) * math.sqrt(1 - phi**2), [phi])[-(b - a):]
        x[a:b] = mu + sd * seg
    return x, dict(what=what, n_breaks=nb, breakpoints=cuts)


@family("K", "drifting-parameter", 8, {**NS, "nonstationary_kind": "drift", "linear": "yes", "gaussian": "yes"}, profiles={"stationary1000": 0})
def drifting_parameter(i, rng, T, S):
    """Time-varying AR(2) (pseudo-period or damping sweeping), tilted blend of a random spectrum
    (sources.tilted_blend), or a sweeping band-pass centre frequency."""
    kind = ["tvar", "tilted-blend", "sweep-centre", "tvar"][i % 4]
    if kind == "tvar":
        P0, P1 = S.draw("P0", 4, 60, log=True), rng.uniform(4, 60)
        r = rng.uniform(0.85, 0.98)
        n = T + 300
        Pt = np.concatenate([np.full(300, P0), np.linspace(P0, P1, T)])
        e = rng.standard_normal(n)
        x = np.zeros(n)
        for t in range(2, n):
            th = 2 * math.pi / Pt[t]
            x[t] = 2 * r * math.cos(th) * x[t - 1] - r * r * x[t - 2] + e[t]
        return burn(x, T), dict(kind=kind, P0=P0, P1=P1, modulus=r)
    if kind == "tilted-blend":
        from ..sources import tilted_blend
        base = burn(ar_filter(rng.standard_normal(T + 500), stable_ar(3, rng, 0.7)), T)
        tilt = S.draw("tilt", 0.6, 1.5)
        return tilted_blend(base, rng, tilt, n_sweeps=rng.uniform(1, 3)), dict(kind=kind, tilt=tilt)
    f0, f1 = S.draw("f0", 0.02, 0.3, log=True), rng.uniform(0.02, 0.3)
    n = T + 300
    ft = np.concatenate([np.full(300, f0), np.linspace(f0, f1, T)])
    r = 0.95
    e = rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(2, n):
        x[t] = 2 * r * math.cos(2 * math.pi * ft[t]) * x[t - 1] - r * r * x[t - 2] + e[t]
    return burn(x, T), dict(kind=kind, f0=f0, f1=f1)


@family("K", "bifurcation-ramp", 12, {**NS, "nonstationary_kind": "ramp", "deterministic": "partly"}, profiles={"stationary1000": 0})
def bifurcation_ramp(i, rng, T, S):
    """Slow passage through a bifurcation: logistic r ramped through the period-doubling cascade;
    noisy pitchfork / Hopf with mu ramped through 0 (critical slowing down); saddle-node tipping;
    Rossler c ramped through the cascade."""
    kind = ["logistic-ramp", "pitchfork-ramp", "hopf-ramp", "saddle-node-tip"][i % 4]
    t = np.linspace(0, 1, T)
    if kind == "logistic-ramp":
        r0, r1 = S.draw("r0", 2.8, 3.4), rng.uniform(3.6, 4.0)
        eps = math.exp(rng.uniform(math.log(1e-4), math.log(1e-2)))
        r = r0 + (r1 - r0) * t
        x = np.empty(T)
        v = 0.5
        for k in range(T):
            v = np.clip(r[k] * v * (1 - v) + eps * rng.standard_normal(), 1e-6, 1 - 1e-6)
            x[k] = v
        return x, dict(kind=kind, r0=r0, r1=r1, noise=eps, chaotic="partly")
    if kind == "pitchfork-ramp":
        mu0, mu1 = -1.0, S.draw("mu1", 0.3, 1.5)
        sig = math.exp(rng.uniform(math.log(0.02), math.log(0.2)))
        dt, k = 0.02, 10
        mu = mu0 + (mu1 - mu0) * np.linspace(0, 1, T * k)
        v = 0.0
        x = np.empty(T)
        for s in range(T * k):
            v += (mu[s] * v - v**3) * dt + sig * math.sqrt(dt) * rng.standard_normal()
            if s % k == 0:
                x[s // k] = v
        return x, dict(kind=kind, mu1=mu1, sigma=sig)
    if kind == "hopf-ramp":
        mu0, mu1 = -1.0, S.draw("mu1_h", 0.3, 1.5)
        w = rng.uniform(0.2, 0.6)
        sig = math.exp(rng.uniform(math.log(0.02), math.log(0.2)))
        dt, k = 0.02, 10
        mu = mu0 + (mu1 - mu0) * np.linspace(0, 1, T * k)
        u = np.array([0.0, 0.0])
        x = np.empty(T)
        for s in range(T * k):
            r2 = u @ u
            du = np.array([mu[s] * u[0] - r2 * u[0] - w * u[1], mu[s] * u[1] - r2 * u[1] + w * u[0]])
            u = u + du * dt + sig * math.sqrt(dt) * rng.standard_normal(2)
            if s % k == 0:
                x[s // k] = u[0]
        return x, dict(kind=kind, mu1=mu1, omega=w, sigma=sig, period_samples=2 * math.pi / w / (dt * k))
    a0, a1 = 1.0, S.draw("a1", -0.3, -0.05)
    sig = math.exp(rng.uniform(math.log(0.05), math.log(0.3)))
    dt, k = 0.02, 10
    a = a0 + (a1 - a0) * np.linspace(0, 1, T * k)
    v = 1.0
    x = np.empty(T)
    for s in range(T * k):
        v += (a[s] - v * v) * dt + sig * math.sqrt(dt) * rng.standard_normal()
        v = max(v, -3.0)
        if s % k == 0:
            x[s // k] = v
    return x, dict(kind=kind, a1=a1, sigma=sig)


@family("K", "heteroskedastic-bursts", 6, {**NS, "nonstationary_kind": "break", "heteroskedastic": "yes", "bursty": "yes",
                                          "linear": "yes", "gaussian": "partly"}, profiles={"stationary1000": 0})
def hetero_bursts(i, rng, T, S):
    """Locally stationary AR(1) with the variance switching in blocks (dwell LU[20, 200]) or with a
    smooth log-variance random walk (odd i)."""
    phi = rng.uniform(0.0, 0.8)
    e = burn(ar_filter(rng.standard_normal(T + 500) * math.sqrt(1 - phi**2), [phi]), T)
    if i % 2 == 0:
        dwell = S.draw("dwell", 20, 200, log=True)
        sd = np.empty(T)
        t = 0
        while t < T:
            L = max(5, int(rng.exponential(dwell)))
            sd[t:t + L] = math.exp(rng.uniform(math.log(0.2), math.log(4)))
            t += L
        return e * sd, dict(kind="block-variance", dwell=dwell, phi=phi)
    s = S.draw("vol_step", 0.02, 0.1, log=True)
    logsd = np.cumsum(s * rng.standard_normal(T))
    return e * np.exp(logsd - logsd.mean()), dict(kind="log-variance-walk", vol_step=s, phi=phi, nonstationary_kind="walk")


@family("K", "explosive", 4, {**NS, "nonstationary_kind": "break", "linear": "yes", "skewed": "yes"}, profiles={"stationary1000": 0})
def explosive(i, rng, T, S):
    """Bubble-and-crash: AR(1) with phi > 1 (phi S[1.005, 1.03]) that resets when |x| exceeds a
    threshold; several episodes per series."""
    phi = S.draw("phi", 1.005, 1.03)
    thr = rng.uniform(20, 60)
    x = np.zeros(T)
    v = 0.0
    for t in range(T):
        v = phi * v + rng.standard_normal()
        if abs(v) > thr:
            v = rng.standard_normal()
        x[t] = v
    return x, dict(phi=phi, threshold=thr)


@family("K", "brownian-variants", 4, {**NS, "nonstationary_kind": "walk", "linear": "yes", "gaussian": "yes"}, profiles={"stationary1000": 0})
def brownian_variants(i, rng, T, S):
    """Brownian bridge, reflected Brownian motion, Brownian motion with drift, jump-diffusion."""
    kind = ["bridge", "reflected", "drift", "jump-diffusion"][i]
    w = np.cumsum(rng.standard_normal(T))
    t = np.arange(T) / (T - 1)
    if kind == "bridge":
        return w - t * w[-1], dict(kind=kind)
    if kind == "reflected":
        return np.abs(w), dict(kind=kind, skewed="yes")
    if kind == "drift":
        mu = S.draw("drift", 0.05, 0.5, log=True)
        return w + mu * np.arange(T), dict(kind=kind, drift=mu)
    rate = rng.uniform(0.005, 0.03)
    jumps = (rng.uniform(size=T) < rate) * rng.standard_normal(T) * rng.uniform(5, 15)
    return w + np.cumsum(jumps), dict(kind=kind, jump_rate=rate, heavy_tailed="yes")


@family("K", "seasonal-trend", 5, {**NS, "nonstationary_kind": "trend", "linear": "yes", "gaussian": "yes", "periodic": "partly"}, profiles={"stationary1000": 0})
def seasonal_trend(i, rng, T, S):
    """Classic decomposition: trend + seasonal (period S[12, 120], 1-3 harmonics) + AR(1) noise;
    multiplicative seasonality for odd i."""
    P = S.draw("period", 12, 120, log=True)
    nh = int(rng.integers(1, 4))
    t = np.arange(T)
    seas = sum(rng.uniform(0.3, 1.0) / (h + 1) * np.sin(2 * np.pi * (h + 1) * t / P + rng.uniform(0, 2 * np.pi)) for h in range(nh))
    trend_ = rng.uniform(0.5, 3.0) * np.linspace(0, 1, T) ** rng.uniform(0.7, 1.5)
    phi = rng.uniform(0.0, 0.7)
    e = 0.3 * burn(ar_filter(rng.standard_normal(T + 500) * math.sqrt(1 - phi**2), [phi]), T)
    if i % 2 == 0:
        return trend_ + seas + e, dict(kind="additive", period_samples=P, n_harmonics=nh)
    return (1 + trend_) * (1 + 0.5 * seas) + e, dict(kind="multiplicative", period_samples=P, n_harmonics=nh)


def _lorenz(t, u, s, r, b):
    x, y, z = u
    return [s * (y - x), x * (r - z) - y, x * y - b * z]


def _rossler(t, u, a, b, c):
    x, y, z = u
    return [-y - z, x + a * y, b + z * (x - c)]


def _flow_fixed_dt(f, x0, dt_obs, n, args=(), burn_n=0):
    t_eval = np.arange(n + burn_n) * dt_obs
    sol = solve_ivp(f, (0, t_eval[-1]), np.asarray(x0, float), t_eval=t_eval, method="DOP853",
                    rtol=1e-8, atol=1e-10, args=args)
    if not sol.success or sol.y.shape[1] < t_eval.size:
        raise RuntimeError("integration failed")
    return sol.y[:, burn_n:]


@family("K", "switched-system", 4, {**NS, "nonstationary_kind": "break", "deterministic": "yes", "chaotic": "yes", "continuous_time": "yes"}, profiles={"stationary1000": 0})
def switched_system(i, rng, T, S):
    """The generating system switches at 1-3 breakpoints between Lorenz and Rossler (rescaled to a
    common amplitude and 20 points per period), or between two Lorenz parameter regimes."""
    nb = S.integer("n_breaks", 1, 3)
    cuts = np.sort(rng.choice(np.arange(100, T - 100), nb, replace=False))
    bounds = np.concatenate([[0], cuts, [T]])
    segs = []
    for k, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        L = b - a
        if i % 2 == 0:
            if k % 2 == 0:
                y = _flow_fixed_dt(_lorenz, [1.0, 1.0, 20.0], 0.75 / 20, L, (10.0, 28.0, 8 / 3), 400)[0]
            else:
                y = _flow_fixed_dt(_rossler, [1.0, 1.0, 0.0], 6.1 / 20, L, (0.2, 0.2, 5.7), 400)[0]
        else:
            rho = 28.0 if k % 2 == 0 else 100.0
            y = _flow_fixed_dt(_lorenz, [1.0, 1.0, 20.0], 0.75 / 20, L, (10.0, rho, 8 / 3), 400)[0]
        segs.append((y - y.mean()) / y.std())
    x = np.concatenate(segs)
    sig = deterministic_noise_sigma(rng)
    return add_noise(x, sig, rng), dict(n_breaks=nb, breakpoints=cuts, kind="lorenz-rossler" if i % 2 == 0 else "lorenz-rho",
                                        noise_sigma=sig, measurement_noise="yes" if sig > 0 else "no")


@family("K", "transient", 5, {**NS, "nonstationary_kind": "transient", "linear": "partly"}, profiles={"stationary1000": 0})
def transient(i, rng, T, S):
    """Transients: relaxation to a fixed point with noise, decaying oscillation, approach to the
    Lorenz attractor from far away, damped chaotic transient (Lorenz rho = 22), overdamped step response."""
    kind = ["relaxation", "ringing", "lorenz-approach", "lorenz-transient-chaos", "step"][i]
    t = np.arange(T)
    if kind == "relaxation":
        tau = S.draw("tau", 50, 400, log=True)
        return 10 * np.exp(-t / tau) + 0.3 * rng.standard_normal(T), dict(kind=kind, tau=tau, linear="yes", gaussian="yes")
    if kind == "ringing":
        tau, P = S.draw("tau_r", 50, 400, log=True), rng.uniform(10, 60)
        return np.exp(-t / tau) * np.sin(2 * np.pi * t / P) + 0.05 * rng.standard_normal(T), dict(kind=kind, tau=tau, period_samples=P, linear="yes")
    if kind == "lorenz-approach":
        y = _flow_fixed_dt(_lorenz, [80.0, -60.0, 300.0], 0.75 / 25, T, (10.0, 28.0, 8 / 3), 0)[2]
        return y, dict(kind=kind, deterministic="yes", continuous_time="yes")
    if kind == "lorenz-transient-chaos":
        y = _flow_fixed_dt(_lorenz, [1.0, 1.0, 1.0], 0.75 / 20, T, (10.0, 22.0, 8 / 3), 0)[0]
        return y, dict(kind=kind, deterministic="yes", continuous_time="yes")
    tau = S.draw("tau_s", 20, 200, log=True)
    step = (t > T // 3).astype(float)
    y = np.zeros(T)
    for k in range(1, T):
        y[k] = y[k - 1] + (step[k] - y[k - 1]) / tau
    return y + 0.05 * rng.standard_normal(T), dict(kind=kind, tau=tau, linear="yes")


# --------------------------------------------------------------------------
# PINUP processes (Owens, Tamaki & Fulcher 2026, arXiv:2609.01651)
# --------------------------------------------------------------------------


def _phi_single(u):
    return np.sin(2 * np.pi * u)


def _phi_wiskott(u):
    return np.sin(2 * np.pi * 5 * u) + np.sin(2 * np.pi * 11 * u) + np.sin(2 * np.pi * 13 * u)


def _blasius(t, u, a, a1, a2, b, c, k1, k2, zs):
    x, y, z = u
    return [a * x - a1 * x * y / (1 + k1 * x),
            -b * y + a1 * x * y / (1 + k1 * x) - a2 * y * z / (1 + k2 * y),
            -c * (z - zs) + a2 * y * z / (1 + k2 * y)]


def _langford(t, u, al, be, la, om, rho, ep):
    x, y, z = u
    return [(z - be) * x - om * y, (z - be) * y + om * x,
            la + al * z - z**3 / 3 - (x * x + y * y) * (1 + rho * z) + ep * z * x**3]


def _pinup_map(step, x0, theta0, alpha, phi_fn, T, burn_n=500):
    """Iterate a map whose parameter follows theta_t = theta0 (1 + alpha phi(t/T)) over the record."""
    u = np.concatenate([np.zeros(burn_n), np.arange(T) / T])
    theta = theta0 * (1 + alpha * np.where(np.arange(burn_n + T) < burn_n, 0.0, phi_fn(u)))
    x = np.array(x0, dtype=float)
    out = np.empty(T)
    for t in range(burn_n + T):
        x = step(x, theta[t])
        if t >= burn_n:
            out[t - burn_n] = x[0] if x.ndim else x
    return out, theta[burn_n:]


def _pinup_flow(f, x0, args, idx, theta0, alpha, phi_fn, T, ppp, period, extra=None):
    """Integrate a flow whose parameter ``idx`` of ``args`` follows theta(t) over the observed record
    (constant during the burn-in of 30 periods). ``extra`` = list of (idx, theta0, alpha, phi_fn) for
    additional parameters. Returns (x, tvp[T] for the primary parameter)."""
    if period is None:  # probe at theta0 for the dominant period
        tp = np.arange(0, 400.0, 0.01)
        sp = solve_ivp(f, (0, tp[-1]), np.asarray(x0, float), t_eval=tp, method="DOP853", rtol=1e-8, atol=1e-10, args=args)
        period = dominant_period(sp.y[0, tp.size // 4:]) * 0.01
        x0 = sp.y[:, -1]
    dt_obs = period / ppp
    burn_n = int(30 * ppp)
    t_start, t_end = burn_n * dt_obs, (burn_n + T) * dt_obs
    mods = [(idx, theta0, alpha, phi_fn)] + (extra or [])

    def params(t):
        a = list(args)
        u = 0.0 if t < t_start else (t - t_start) / (t_end - t_start)
        for j, th0, al, fn in mods:
            a[j] = th0 * (1 + al * (0.0 if t < t_start else float(fn(u))))
        return a

    def rhs(t, y):
        return f(t, y, *params(t))
    t_eval = np.arange(burn_n + T) * dt_obs
    sol = solve_ivp(rhs, (0, t_end), np.asarray(x0, float), t_eval=t_eval, method="DOP853", rtol=1e-8, atol=1e-10)
    if not sol.success or sol.y.shape[1] < t_eval.size:
        raise RuntimeError("PINUP integration failed")
    u = np.arange(T) / T
    tvp = theta0 * (1 + alpha * phi_fn(u))
    return sol.y[0, burn_n:], tvp


@family("K", "pinup", 10, {**NS, "nonstationary_kind": "drift", "deterministic": "yes", "chaotic": "partly",
                          "reversible": "no"}, profiles={"stationary1000": 0})
def pinup(i, rng, T, S):
    """PINUP processes: a chaotic system with one parameter modulated within its regime,
    theta(t) = theta0 [1 + alpha phi(t)] over the record. i = 0..5: logistic (r=3.6), sine map (r=3),
    predator-prey map (r=3), Lorenz (rho=28), Blasius (alpha1=0.2), Langford/Aizawa (omega=3.5) with a
    single sinusoid, alpha = 0.1; 6, 7: Lorenz and Langford with Wiskott's three-sinusoid phi;
    8: Lorenz with rho, beta, sigma all modulated (1, 2, 3 cycles); 9: Langford at alpha = 0.5.
    The parameter time course is stored as the per-series vector ``tvp``."""
    ppp = S.integer("ppp", 15, 40)
    sysname = ["logistic", "sine", "predator-prey", "lorenz", "blasius", "langford", "lorenz", "langford", "lorenz", "langford"][i]
    phi_fn = _phi_wiskott if i in (6, 7) else _phi_single
    form = "wiskott3" if i in (6, 7) else ("multi" if i == 8 else "sinusoid")
    alpha = 0.5 if i == 9 else 0.1
    info = dict(system=sysname, tvp_form=form, tvp_alpha=alpha)
    if sysname == "logistic":
        x, tvp = _pinup_map(lambda v, r: r * v * (1 - v), 0.6 + 0.01 * rng.standard_normal(), 3.6, alpha, phi_fn, T)
        info.update(parameter="r", theta0=3.6)
    elif sysname == "sine":
        x, tvp = _pinup_map(lambda v, r: r * np.sin(np.pi * v), 0.6 + 0.01 * rng.standard_normal(), 3.0, alpha, phi_fn, T)
        info.update(parameter="r", theta0=3.0)
    elif sysname == "predator-prey":
        def step(u, r):
            x_, y_ = u
            return np.array([x_ * np.exp(r * (1 - x_) - 5.0 * y_), 5.0 * x_ * (1 - np.exp(-5.0 * y_))])
        x, tvp = _pinup_map(step, [0.5, 0.5] + 0.01 * rng.standard_normal(2), 3.0, alpha, phi_fn, T)
        info.update(parameter="r", theta0=3.0)
    elif sysname == "lorenz":
        x0 = np.array([-9.79, -15.04, 20.53]) * (1 + 0.02 * rng.standard_normal(3))
        extra = [(2, 8 / 3, alpha, lambda u: np.sin(2 * np.pi * 2 * u)), (0, 10.0, alpha, lambda u: np.sin(2 * np.pi * 3 * u))] if i == 8 else None
        x, tvp = _pinup_flow(_lorenz, x0, (10.0, 28.0, 8 / 3), 1, 28.0, alpha, phi_fn, T, ppp, 0.75, extra)
        info.update(parameter="rho" if i != 8 else "rho,beta,sigma", theta0=28.0, ppp=ppp, period_samples=ppp, continuous_time="yes")
    elif sysname == "blasius":
        x0 = np.array([4.03, 5.11, 0.0165]) * (1 + 0.02 * rng.standard_normal(3))
        x, tvp = _pinup_flow(_blasius, x0, (1.0, 0.2, 1.0, 1.0, 10.0, 0.05, 0.0, 0.006), 1, 0.2, alpha, phi_fn, T, ppp, None)
        info.update(parameter="alpha1", theta0=0.2, ppp=ppp, period_samples=ppp, continuous_time="yes")
    else:
        x0 = np.array([-0.78, -0.63, -0.18]) * (1 + 0.02 * rng.standard_normal(3))
        x, tvp = _pinup_flow(_langford, x0, (0.95, 0.7, 0.6, 3.5, 0.25, 0.1), 3, 3.5, alpha, phi_fn, T, ppp, 1.8)
        info.update(parameter="omega", theta0=3.5, ppp=ppp, period_samples=ppp, continuous_time="yes")
    sig = deterministic_noise_sigma(rng)
    info.update(noise_sigma=sig, measurement_noise="yes" if sig > 0 else "no", deterministic="partly" if sig > 0 else "yes",
                tvp=np.asarray(tvp, dtype=float))
    return add_noise(x, sig, rng), info
