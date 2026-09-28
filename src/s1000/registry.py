"""The family registry: the design's quota table, as code.

A *family* is one generating mechanism with a parameter prior and a fixed
quota ``n``. ``@family(...)`` registers a generator ``gen(i, rng, T, S) ->
(x, info)`` where ``i`` indexes the instance within the family, ``rng`` is the
instance's named generator, ``S`` a ``util.Strat`` for stratified draws, and ``info`` is a dict of parameters and any
ground-truth numerics (``lyapunov_max``, ``hurst_H``, ``period_samples``, ...)
the generator knows. Tags declared in the decorator are the family's defaults;
``info`` may override any of them per instance (e.g. a logistic-map draw that
lands in a periodic window sets ``chaotic="no"``).

The quota is the single source of truth: ``s1000 manifest`` exports it, the
design document is prose about it, and a test checks every class sums to the
design's number.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# Profiles: a profile is a quota table over the same families and the same seed names. "full" is
# the design's corpus; "stationary1000" drops class K and every non-stationary instance and gives
# the 147 slots back to stationary families (plus stationary-only variants of a few mixed families).
# A series is bit-identical across profiles when its family has the same quota in both (the
# stratified draw is binned by the profile's quota).
PROFILES = {
    "full": dict(A=30, B=76, C=46, D=74, E=100, F=81, G=150, H=41, I=72, J=58, K=82, L=40, M=40, N=110),
    "stationary1000": dict(A=30, B=85, C=52, D=62, E=122, F=81, G=181, H=32, I=104, J=48, K=0, L=43, M=40, N=120),
}
ACTIVE = ["full"]
# Published names: stage 1 is released as "1000 x 1000"; the CLI accepts either spelling.
RELEASE_NAMES = {"stationary1000": "1000x1000"}
PROFILE_ALIASES = {v: k for k, v in RELEASE_NAMES.items()}


def canonical_profile(name: str) -> str:
    return PROFILE_ALIASES.get(name, name)


def set_profile(name: str):
    name = canonical_profile(name)
    if name not in PROFILES:
        raise KeyError(name)
    ACTIVE[0] = name


def profile() -> str:
    return ACTIVE[0]


CLASSES = {
    "A": ("i.i.d. noise", 30),
    "B": ("linear Gaussian, short memory", 76),
    "C": ("linear non-Gaussian", 46),
    "D": ("long memory, self-similar, multifractal", 74),
    "E": ("nonlinear stochastic, discrete time", 100),
    "F": ("deterministic maps", 81),
    "G": ("chaotic flows", 150),
    "H": ("periodic, quasi-periodic, oscillatory", 41),
    "I": ("noise-driven continuous-time dynamics", 72),
    "J": ("events, point processes, discrete states", 58),
    "K": ("non-stationary", 82),
    "L": ("structured, composite, coupled", 40),
    "M": ("observation effects", 40),
    "N": ("named models of natural and engineered processes", 110),
}

# Human-facing class codes (the web resource, figures). Display only: the letters above stay in series ids
# and seed names, so renaming a code never changes a series.
CLASS_CODES = {
    "A": "IID", "B": "LG", "C": "LNG", "D": "LRD", "E": "NLS", "F": "MAP", "G": "FLOW",
    "H": "OSC", "I": "SDE", "J": "EVT", "K": "NST", "L": "COMP", "M": "OBS", "N": "NAT",
}
# Short full names, for places too small for the class title (e.g. the landing-page zoo).
CLASS_NAMES = {
    "A": "i.i.d. noise", "B": "Linear Gaussian", "C": "Linear non-Gaussian", "D": "Long memory", "E": "Nonlinear stochastic",
    "F": "Deterministic maps", "G": "Chaotic flows", "H": "Oscillators", "I": "Noisy continuous time", "J": "Events and states",
    "K": "Non-stationary", "L": "Composite and coupled", "M": "Observation effects", "N": "Natural and engineered",
}

TAG_NAMES = (
    "deterministic", "chaotic", "linear", "gaussian", "stationary", "long_memory",
    "periodic", "quasiperiodic", "reversible", "discrete_valued", "continuous_time",
    "heavy_tailed", "heteroskedastic", "regime_switching", "event_like", "bursty",
    "skewed", "nonstationary_kind", "measurement_noise", "domain",
)
TAG_VALUES = {"yes", "no", "partly", "na"}
NONSTAT_KINDS = {"trend", "break", "drift", "walk", "ramp", "transient", "none"}
DOMAINS = {"abstract", "physiology", "geophysics", "ecology", "engineering", "economics"}
NUMERIC_NAMES = (
    "lyapunov_max", "hurst_H", "arfima_d", "spectral_beta", "period_samples",
    "timescale_samples", "noise_sigma", "n_states", "event_rate", "burstiness_B", "skewness",
)

DEFAULT_TAGS = {name: "na" for name in TAG_NAMES}
DEFAULT_TAGS.update(nonstationary_kind="none", measurement_noise="no", domain="abstract",
                    stationary="yes", deterministic="no", discrete_valued="no",
                    continuous_time="no", periodic="no", quasiperiodic="no")


@dataclass
class Family:
    cls: str
    key: str
    n: int                      # quota in the "full" profile
    gen: Callable
    tags: dict = field(default_factory=dict)
    doc: str = ""
    order: int = 0
    profiles: dict = field(default_factory=dict)   # quota overrides per profile

    @property
    def name(self) -> str:
        return f"{self.cls}.{self.key}"

    def _spec(self, prof: str | None = None):
        prof = prof or profile()
        return self.n if prof == "full" else self.profiles.get(prof, self.n)

    def indices(self, prof: str | None = None) -> list[int]:
        """Instance indices built in this profile. A profile override is either a count (instances
        0..n-1) or {"indices": [...], "strat_n": N}: keep only those instances of an N-instance
        family, each byte-identical to its N-instance self (stratified draws stay binned by N)."""
        v = self._spec(prof)
        return list(v["indices"]) if isinstance(v, dict) else list(range(int(v)))

    def quota(self, prof: str | None = None) -> int:
        return len(self.indices(prof))

    def strat_n(self, prof: str | None = None) -> int:
        v = self._spec(prof)
        return int(v.get("strat_n", len(v["indices"]))) if isinstance(v, dict) else int(v)


FAMILIES: dict[str, Family] = {}
_ORDER = [0]


def family(cls: str, key: str, n: int, tags: dict | None = None, doc: str = "", profiles: dict | None = None):
    """Register a generator under class ``cls`` with key ``key`` and quota ``n`` in the full profile;
    ``profiles`` overrides the quota per profile (0 excludes the family from that profile)."""
    if cls not in CLASSES:
        raise KeyError(cls)
    tags = dict(tags or {})
    for k, v in tags.items():
        if k not in TAG_NAMES:
            raise KeyError(f"unknown tag {k!r} in {cls}.{key}")
        if k == "nonstationary_kind":
            assert v in NONSTAT_KINDS, (cls, key, v)
        elif k == "domain":
            assert v in DOMAINS, (cls, key, v)
        else:
            assert v in TAG_VALUES, (cls, key, k, v)

    def deco(fn):
        fam = Family(cls=cls, key=key, n=n, gen=fn, tags=tags, doc=doc or (fn.__doc__ or "").strip(),
                     order=_ORDER[0], profiles=dict(profiles or {}))
        _ORDER[0] += 1
        if fam.name in FAMILIES:
            raise KeyError(f"duplicate family {fam.name}")
        FAMILIES[fam.name] = fam
        return fn

    return deco


def load_all():
    """Import every family module (registration is an import side effect)."""
    from .families import (A_noise, B_linear, C_nongaussian, D_longmemory, E_nonlinear,  # noqa: F401
                           F_maps, G_flows, H_oscillatory, I_sde, J_events, K_nonstationary,
                           L_structured, M_observation, N_named)
    return FAMILIES


def by_class(prof: str | None = None) -> dict[str, list[Family]]:
    """Families with a non-zero quota in the profile, by class, in registration order."""
    prof = prof or profile()
    out: dict[str, list[Family]] = {c: [] for c in CLASSES}
    for fam in sorted(FAMILIES.values(), key=lambda f: f.order):
        if fam.quota(prof) > 0:
            out[fam.cls].append(fam)
    return out


def quota_check(prof: str | None = None) -> dict[str, tuple[int, int]]:
    """{class: (declared, registered)} for the profile."""
    prof = prof or profile()
    reg = by_class(prof)
    return {c: (PROFILES[prof][c], sum(f.quota(prof) for f in reg[c])) for c in CLASSES}
