"""The `reversible` tag in stationary1000: time-reversibility in the time-series sense (criterion, worked
example and audit: docs/time_reversibility.md).

A series is time-reversible if its joint statistics are the same run backwards (Weiss 1975), in theory, for an
infinitely long record. That needs reversible dynamics *and* an observed variable that the reversal leaves
unchanged (the Nose-Hoover thermostat variable z, say, flips sign under every reversing symmetry of its
equations, so it is not). `yes` / `no` are set from theory for each family (and variant) below; `na` marks
cases that are not determined. Families not listed keep their generator's tag.

Checked (2026-09-28) against a 20x-longer realisation of every series with its own seed stream, on ranks, over
20 segments: trev(x), trev(x^2) and E[x_t^2 x_{t+L} - x_t x_{t+L}^2] at lags 1-16. No series tagged `yes` shows
a consistent asymmetry (|t| > 6, |effect| > 0.02) except J.compound-poisson-increments 000
(|effect| 0.04, t = -6.1: i.i.d. by construction; its many exact zeros are ties that the rank statistics
handle poorly). D.mrw, D.lmsv and the M observations could not be regenerated at 20x length and rest on theory. The test can only reveal irreversibility,
so a `yes` rests on the theory.
"""
from __future__ import annotations

import numpy as np

YES, NO, NA = "yes", "no", "na"

# conservative (Hamiltonian / volume-preserving) flows whose observed series is time-reversible: an observable that
# some reversing symmetry leaves unchanged, on a symmetric invariant set (and no asymmetry in the long-run check)
_G_YES = {"DoublePendulum", "double-pendulum", "SwingingAtwood", "NuclearQuadrupole", "ArnoldWeb", "SprottA", "Torus"}
# periodically forced or blinking 2D incompressible flows: reversible in law through a reflection, but whether the
# observed tracer coordinate is even under it is not established
_G_NA = {"BickleyJet", "BlinkingRotlet", "BlinkingVortex", "InteriorSquirmer"}
# reversible in law but not as observed: Henon-Heiles' orbit here lies on a regular torus that the reversal maps to
# a different torus (strong asymmetry in the long-run check); Nose-Hoover observes z; the lid-driven cavity is forced


def _dysts(tags, info):
    s = info.get("system")
    return YES if s in _G_YES else NA if s in _G_NA else NO


def _shot_noise(tags, info):
    # Poisson times and iid amplitudes through a symmetric pulse are reversible; the sampled Gaussian pulse is
    # symmetric only when its centre 3w falls on the sampling grid's midpoint
    if info.get("kind") != "gaussian":
        return NO
    w = info["width"]
    t = np.arange(int(6 * w) + 1)
    h = np.exp(-0.5 * ((t - 3 * w) / w) ** 2)
    return YES if np.allclose(h, h[::-1], rtol=1e-3, atol=1e-6) else NO


RULES = {
    # linear processes with non-Gaussian innovations are irreversible (Weiss 1975)
    "C.ar-bounded": NO,
    "C.arma-heavy": NO,
    "C.shot-noise": _shot_noise,
    # stochastic volatility: an iid sign times a function of a reversible Gaussian log-volatility
    "D.lmsv": YES,
    "D.mrw": YES,
    "D.discrete-cascade": NA,
    "E.stoch-vol": YES,
    # (G)ARCH: volatility jumps after a shock and decays, so x^2 has an arrow of time
    "E.garch": NO,
    # nonlinear or random-coefficient autoregressions and noisy maps
    "E.random-coef-ar": NO,
    "E.markov-switching-ar": NO,
    "E.bistable-map": NO,
    "E.stochastic-map": NO,
    "F.aperiodic-real": NO,
    "G.dysts-flow": _dysts,
    "G.dysts-flow-coarse": _dysts,
    "G.dysts-flow-extra": _dysts,
    "G.canonical-sweep": _dysts,
    "G.blinking-rotlet": NA,
    # periodic waveforms: reversible only if the waveform is symmetric in time (sinusoids, beats, AM/FM with
    # sinusoidal modulation, incommensurate sums); sawtooth, random harmonics, relaxation and dissipative cycles are not
    "H.harmonic": lambda tags, info: NO if info.get("kind") in ("random", "sawtooth") else tags.get("reversible"),
    "H.limit-cycle": NO,
    "H.period-doubled-flows": NO,
    "H.cycle-shapes": lambda tags, info: YES if info.get("kind") == "pendulum-separatrix" else NO,
    # any 1D diffusion (additive noise in a potential) satisfies detailed balance
    "I.double-well": YES,
    "I.stochastic-resonance": NA,
    # a two-state Markov chain is always reversible; random transition matrices on 3+ states are not
    "J.markov-chain-emitted": lambda tags, info: YES if info.get("kind") != "cyclic" and info.get("k") == 2 else NO,
    "J.compound-poisson-increments": YES,  # iid
    "L.longlag-comb": lambda tags, info: YES if info.get("kind") == "linear" else NO,
    "L.mixture": lambda tags, info: YES if info.get("kind") == "ar+telegraph" else NO,
    "N.climate-model": lambda tags, info: {"hasselmann": YES, "stommel": NA}.get(info.get("kind"), NO),
    "N.collective": lambda tags, info: YES if info.get("kind") == "ising" else NO,  # Glauber dynamics: detailed balance
    "N.kirman": YES,  # a birth-death chain
    "N.rr-af": NA,
    # an observation of a base series keeps its tag, except a zero-order-hold gap fill (flat, then a jump)
    "M.missing-data": lambda tags, info: NO if info.get("fill") == "zero-order-hold" else tags.get("reversible"),
    # decimation with a zero-phase (symmetric) filter keeps reversibility; the base is generated directly, so apply
    # its family's rule here (a family-wide value; variant rules fall back to the base's own tag)
    "M.downsampled": lambda tags, info: RULES[info["base_family"]] if isinstance(RULES.get(info.get("base_family")), str)
    else tags.get("reversible"),
}


def time_reversible(fam, tags: dict, info: dict) -> str:
    rule = RULES.get(f"{fam.cls}.{fam.key}")
    if rule is None:
        return tags.get("reversible")
    return rule(tags, info) if callable(rule) else rule
