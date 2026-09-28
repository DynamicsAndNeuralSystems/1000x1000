# Time-reversibility: the `reversible` tag

Decided 2026-09-28 (Ben). This applies to the stationary1000 / 1000×1000 release. The full profile is frozen and keeps its older tags.

## The criterion

A series is tagged `reversible: yes` if the process that generated it, **as seen through the recorded variable**, is time-reversible in the time-series sense (Weiss 1975). For every k, the joint distribution of (x₁, …, xₖ) must equal that of (xₖ, …, x₁).

- **Population property.** This is a property of the observed process in the limit of an infinitely long record. It is not a property of the finite series, and it is not a statistical test result. A 1000-sample `yes` series can still look slightly asymmetric by chance.
- **Two requirements.** Time-reversibility needs two things:
  1. **Reversible dynamics.** Played backwards, the motion is also a valid motion, once any velocity-like variables have their signs flipped.
  2. **A reversal-even observable.** The recorded variable must be one that some reversing symmetry leaves unchanged (or whose statistics are symmetric when flipped). The trajectory must also sit on an invariant set that the reversal maps onto itself.
- **Not the physics sense.** The tag is *not* "the equations are reversible". That was the earlier, process-level meaning. It was dropped because it describes the model, whereas users read tags as statements about the series they are looking at.

Values:
- `yes`: time-reversible.
- `no`: not time-reversible.
- `na`: not determined (theory does not settle it and the check below cannot confirm it).

## The worked example: Nosé–Hoover

The equations are x′ = y, y′ = −x + yz, z′ = a − y². They have two reversing symmetries:

| reversing symmetry | leaves unchanged |
|---|---|
| (x, y, z, t) → (x, −y, −z, −t) | x |
| (x, y, z, t) → (−x, y, −z, −t) | y |

So a long x or y record is time-reversible. The thermostat variable z flips sign under *both* symmetries, so z run backwards is distributed like −z. z is also lopsided in time: z′ ≤ a, so it rises slowly but can fall arbitrarily fast. So z is **not** time-reversible at any record length. Its marginal distribution is still symmetric (skewness 0), so only the time ordering reveals the asymmetry.

In 400,000-sample runs from three initial conditions, the lag-1 increment skewness came out as follows:
- **z:** ≈ −3.2, the same in every half-run.
- **x and y:** ≈ 0, with sign-changing noise.

`S1000_FLOW_dysts-flow_075` (formerly `S1000_G_dysts-flow_075`) observes z, so it is `no`.

## How tags are set

1. **Theory decides.** A rule is written per family, or per variant within a family, in `src/s1000/reversibility.py`. It is applied in `build.generate` for stationary1000 only, and each rule carries its reasoning. Families without a rule keep their generator's tag. Typical cases:
   - **`yes`:**
     - i.i.d. noise;
     - Gaussian linear and long-memory processes;
     - any 1D diffusion (detailed balance);
     - two-state Markov chains (and HMMs built on one);
     - stochastic volatility, i.e. an i.i.d. sign times a function of a reversible Gaussian log-volatility;
     - Poisson / Cox trains read out through a symmetric kernel;
     - sinusoids, beats, AM/FM with sinusoidal modulation, and quasi-periodic sums;
     - conservative flows observed through a reversal-even variable.
   - **`no`:**
     - linear processes with non-Gaussian innovations (Weiss 1975);
     - (G)ARCH, where the squared series has an arrow of time;
     - nonlinear or random-coefficient autoregressions and noisy maps;
     - Markov chains on 3+ states with random or cyclic transitions;
     - dissipative chaos;
     - relaxation, bursting and other time-asymmetric periodic waveforms (sawtooth, Van der Pol, FitzHugh–Nagumo, Brusselator, Hindmarsh–Rose, Lotka–Volterra);
     - Hawkes / ETAS self-excitation;
     - zero-order-hold gap filling.
   - **Observation transforms (M class)** keep their base series' tag. Static readouts, additive i.i.d. noise or outliers, zero-phase decimation and linear interpolation all preserve reversibility. The exception is zero-order hold, which is `no`.
2. **Finite data checks.** `scripts/audit_reversibility.py` does the following:
   - It regenerates every series at 20× length (20,000 samples) with its own seed stream, so the parameters are the same.
   - It splits the run into 20 segments and computes three statistics on ranks: trev(x), trev(x²) and the bicovariance E[x_t² x_{t+L} − x_t x_{t+L}²], at lags 1–16.
   - It flags a consistent asymmetry (|t| > 6 across segments and |effect| > 0.02).

   Ranks make it robust to heavy tails, and the x² statistic catches sign-symmetric irreversibility such as GARCH. The check can only **rule reversibility out**. It is used to catch theory mistakes and to decide cases theory leaves open.
   - It decided Hénon–Heiles (`G.dysts-flow_041`) as `no`. The observed orbit lies on a regular torus that the reversal maps to a *different* torus, giving a strong asymmetry that holds at infinite length. Theory alone had suggested `yes`.
   - The only `yes` it flags is `J.compound-poisson-increments_000` (effect 0.04, t = −6.1). That series is i.i.d. by construction; its many exact zeros are ties that rank statistics handle poorly.
   - It could not regenerate `D.mrw`, `D.lmsv`, the M observations or the double pendulum at 20× length, so their tags rest on theory.

## Not determined (`na`)

| family | why |
|---|---|
| G: Bickley jet, blinking rotlet (and the `G.blinking-rotlet` family), blinking vortex, interior squirmer | forced or blinking 2D incompressible flows: reversible in law through a reflection, but whether the observed tracer coordinate is even under it is not established |
| I.stochastic-resonance | periodically forced double well: the forcing breaks detailed balance, but whether x alone shows it is unclear (a linear analogue would be reversible) |
| N.climate-model (Stommel) | 2D nonlinear noisy box model, not a gradient system |
| N.rr-af | atrial-fibrillation RR intervals through a refractory AV node |
| N.gait-emg-tremor | not assessed |
| D.discrete-cascade | not assessed (dyadic cascade structure) |

## History

- **Before 2026-09-28.** The tags came from family-level defaults. For dysts flows they came from dysts' "Hamiltonian" flag plus a short list of other systems known to be reversible in law (`sources.reversible_systems()`). That tagged the dynamics, not the observed series, and gave chaotic flows a `reversible` tag, which prompted the review.
- **2026-09-28, first pass.** Nosé–Hoover and the lid-driven cavity were moved to `no`, and the site labelled the tag "reversible dynamics". An early check used Gaussian (phase-randomised) surrogates. That was the wrong null: it raises false alarms on heavy-tailed but reversible series and is blind to GARCH.
- **2026-09-28, convention adopted.** The tag switched to the time-series convention: the site label is now "time-reversible", with a tooltip and an FAQ entry. The full retag changed 187 tags, giving 314 `yes` / 645 `no` / 41 `na`. All series stayed byte-identical. The hctsa keywords were updated; `data/stationary1000/hctsa/README.md` has the md5s.
