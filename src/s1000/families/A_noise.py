"""Class A: i.i.d. noise. The corpus's zero of dynamics; anchors the marginal axis."""
from __future__ import annotations

import numpy as np

from ..registry import family
from ..util import best_fit, stable_innov

IID = dict(linear="yes", stationary="yes", reversible="yes")


@family("A", "gaussian", 3, {**IID, "gaussian": "yes"}, profiles={"stationary1000": 4})
def gaussian(i, rng, T, S):
    """Standard Gaussian white noise."""
    from scipy import stats
    return best_fit(lambda r: r.standard_normal(T), rng, cdf=stats.norm.cdf), dict(skewness=0.0)


@family("A", "uniform", 2, {**IID, "gaussian": "no"}, profiles={"stationary1000": 3})
def uniform(i, rng, T, S):
    """Uniform white noise on [-1, 1]."""
    from scipy import stats
    return best_fit(lambda r: r.uniform(-1, 1, T), rng, cdf=stats.uniform(-1, 2).cdf), dict(skewness=0.0)


@family("A", "laplace", 2, {**IID, "gaussian": "no", "heavy_tailed": "partly"})
def laplace(i, rng, T, S):
    """Laplace (double-exponential) white noise."""
    from scipy import stats
    return best_fit(lambda r: r.laplace(0, 1, T), rng, cdf=stats.laplace.cdf), dict(skewness=0.0)


@family("A", "student-t", 4, {**IID, "gaussian": "no", "heavy_tailed": "yes"})
def student_t(i, rng, T, S):
    """Student-t white noise, nu in {1.5, 2, 3, 5}; in the stationary profile nu in {3, 4, 5, 7} (finite variance)."""
    from ..registry import profile
    nu = ([3.0, 4.0, 5.0, 7.0] if profile() == "stationary1000" else [1.5, 2.0, 3.0, 5.0])[i % 4]
    from scipy import stats
    return best_fit(lambda r: r.standard_t(nu, T), rng, cdf=stats.t(nu).cdf), dict(nu=nu)


@family("A", "alpha-stable", 5, {**IID, "gaussian": "no", "heavy_tailed": "yes", "skewed": "partly"}, profiles={"stationary1000": 0})
def alpha_stable(i, rng, T, S):
    """Alpha-stable white noise, alpha S[0.8, 1.9], skew beta U[-1, 1]."""
    alpha = S.draw("alpha", 0.8, 1.9)
    beta = rng.uniform(-1, 1)
    ref = np.concatenate([stable_innov(4000, alpha, beta, np.random.Generator(np.random.PCG64(99 + k))) for k in range(5)])
    x = best_fit(lambda r: stable_innov(T, alpha, beta, r), rng, reference=ref)
    return x, dict(alpha=alpha, beta=beta, skewed="yes" if abs(beta) > 0.3 else "no")


@family("A", "skewed", 5, {**IID, "gaussian": "no", "skewed": "yes"}, profiles={"stationary1000": 6})
def skewed(i, rng, T, S):
    """Skewed white noise: gamma (shape LU[0.3, 3]), log-normal (sigma U[0.3, 1.5]), chi-square."""
    kind = S.choice("kind", ["gamma", "lognormal", "chisq"])
    if kind == "gamma":
        k = S.draw("shape", 0.3, 3.0, log=True)
        from scipy import stats
        return best_fit(lambda r: r.gamma(k, 1.0, T), rng, cdf=stats.gamma(k).cdf), dict(kind=kind, shape=k, skewness=2 / np.sqrt(k))
    if kind == "lognormal":
        s = S.draw("sigma_log", 0.3, 1.5)
        sk = (np.exp(s**2) + 2) * np.sqrt(np.exp(s**2) - 1)
        from scipy import stats
        return best_fit(lambda r: r.lognormal(0, s, T), rng, cdf=stats.lognorm(s).cdf), dict(kind=kind, sigma_log=s, skewness=sk)
    k = int(S.integer("df", 1, 4))
    from scipy import stats
    return best_fit(lambda r: r.chisquare(k, T), rng, cdf=stats.chi2(k).cdf), dict(kind=kind, df=k, skewness=np.sqrt(8 / k))


@family("A", "bimodal", 3, {**IID, "gaussian": "no"})
def bimodal(i, rng, T, S):
    """Two-component Gaussian mixture, separation U[2, 5] SD, weight U[0.2, 0.5]."""
    sep = S.draw("sep", 2.0, 5.0)
    w = rng.uniform(0.2, 0.5)
    def draw(r):
        z = r.uniform(size=T) < w
        return np.where(z, sep / 2, -sep / 2) + r.standard_normal(T)
    ref = draw(np.random.Generator(np.random.PCG64(12345)))
    for _ in range(6):  # a long reference sample of the same mixture
        ref = np.concatenate([ref, draw(np.random.Generator(np.random.PCG64(12345 + len(ref))))])
    return best_fit(draw, rng, reference=ref), dict(separation=sep, weight=w)


@family("A", "discrete", 4, {**IID, "gaussian": "no", "discrete_valued": "yes"}, profiles={"stationary1000": 0})
def discrete(i, rng, T, S):
    """Discrete i.i.d.: Bernoulli, Poisson, categorical, integer-uniform."""
    kind = ["bernoulli", "poisson", "categorical", "intuniform"][i % 4]
    if kind == "bernoulli":
        p = rng.uniform(0.05, 0.5)
        return (rng.uniform(size=T) < p).astype(float), dict(kind=kind, p=p, n_states=2)
    if kind == "poisson":
        lam = float(np.exp(rng.uniform(np.log(0.5), np.log(20))))
        return rng.poisson(lam, T).astype(float), dict(kind=kind, lam=lam, skewed="yes" if lam < 4 else "no")
    if kind == "categorical":
        k = int(rng.integers(3, 11))
        p = rng.dirichlet(np.ones(k))
        return rng.choice(k, T, p=p).astype(float), dict(kind=kind, k=k, n_states=k)
    k = int(rng.integers(3, 11))
    return rng.integers(0, k, T).astype(float), dict(kind=kind, k=k, n_states=k)


@family("A", "exponential-pareto", 2, {**IID, "gaussian": "no", "skewed": "yes", "heavy_tailed": "partly"})
def exp_pareto(i, rng, T, S):
    """Exponential (i=0) or Pareto with tail index LU[1.2, 4] (i=1)."""
    if i % 2 == 0:
        from scipy import stats
        return best_fit(lambda r: r.exponential(1.0, T), rng, cdf=stats.expon.cdf), dict(kind="exponential", skewness=2.0)
    from ..registry import profile
    lo = 2.2 if profile() == "stationary1000" else 1.2  # finite variance in the stationary profile
    a = float(np.exp(rng.uniform(np.log(lo), np.log(4))))
    from scipy import stats
    return best_fit(lambda r: 1 + r.pareto(a, T), rng, cdf=stats.pareto(a).cdf), dict(kind="pareto", tail=a, heavy_tailed="yes")


@family("A", "heavy-finite", 0, {**IID, "gaussian": "no", "heavy_tailed": "yes"}, profiles={"stationary1000": 6})
def heavy_finite(i, rng, T, S):
    """Finite-variance heavy-tailed white noise: Student-t nu S[3, 6] (even i) or a scale mixture of
    Gaussians (SD 1 with probability 1-p, SD 5 with probability p, p U[0.02, 0.1]; odd i)."""
    if i % 2 == 0:
        from scipy import stats
        nu = S.draw("nu", 3.0, 6.0)
        return best_fit(lambda r: r.standard_t(nu, T), rng, cdf=stats.t(nu).cdf), dict(kind="student", nu=nu)
    p = rng.uniform(0.02, 0.1)

    def draw(r):
        return np.where(r.uniform(size=T) < p, 5.0, 1.0) * r.standard_normal(T)
    ref = np.concatenate([draw(np.random.Generator(np.random.PCG64(777 + k))) for k in range(8)])
    return best_fit(draw, rng, reference=ref), dict(kind="scale-mixture", p=p)
