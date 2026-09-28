# The 1000×1000 collection

1000 simulated time series, each 1000 samples long, from 133 generating mechanisms across 13 classes:
noise and linear processes, long memory and multifractal cascades, nonlinear stochastic processes,
deterministic maps and chaotic flows, oscillators, noise-driven continuous-time dynamics, point processes
and discrete states, composite and coupled systems, observation effects, and models of natural and
engineered systems (hearts, brains, climate, ecosystems, …). It is a simulated companion to the
[Empirical1000](https://doi.org/10.6084/m9.figshare.5436136) dataset (same length, same
[hctsa](https://github.com/benfulcher/hctsa) file formats), with ground truth: every series comes with its
generating process, the parameters drawn for it, property tags and, where known, numerical invariants
(largest Lyapunov exponent, Hurst exponent, period, …).

- **Website:** https://dynamicsandneuralsystems.github.io/1000x1000/ (browse, listen, map, quiz)
- **Data:** [doi:10.6084/m9.figshare.34013331](https://doi.org/10.6084/m9.figshare.34013331) (CC BY 4.0),
  including the full hctsa feature matrix
- **This repository:** the generator code (`s1000`), the website, and documentation (MIT license)

## Reproducibility

The corpus is a pure function of names. Every series is generated from
`rng_for(class, family, index)` (BLAKE2b of the name seeds a PCG64 stream), so regenerating one series,
one family or the whole corpus gives bit-identical values on any platform and in any order. Each series'
metadata records its `seed_name`, the derived 64-bit `seed`, and the retry `attempt` (a series failing a
quality gate is regenerated under `(..., "retry", k)`, also a name). Stratified parameter draws are
addressed by `(family, "lhs", parameter)`, so the assignment of strata to instances never depends on how
many instances are built. `manifest.json` holds a SHA-256 per series and the library versions;
`s1000 verify` regenerates a random subset and checks the hashes.

Every series in this release also passes a **window-stationarity gate** (`qc.stationarity_gate`): over 5
non-overlapping windows the SD of window means is at most 0.5 of the series SD, and (unless the family is
tagged heavy-tailed, bursty, event-like, heteroskedastic or regime-switching) the SD of window SDs is at
most 0.5 and the max/min window variance at most 20. All series have finite variance.

Two reproducibility details are built in: cached dysts trajectories come from their own named child
stream (so a cache hit and a cache miss consume a series' stream identically), and a few chaotic
integrations use scalar arithmetic, since numpy's vectorized complex operations take alignment-dependent
SIMD/FMA paths whose last-ulp differences a chaotic system amplifies. `verify --cold` deletes the sampled
series' cached trajectories first, so the integration itself is exercised.

## Install and build

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,site,figures]"
.venv/bin/s1000 manifest --profile 1000x1000                      # quota table per class
.venv/bin/s1000 build --profile 1000x1000 --export                # -> data/stationary1000/ (series, metadata, hctsa .mat, csvs, catalogue)
.venv/bin/s1000 verify --profile 1000x1000 --fraction 0.25 --cold # regenerate 25% from a cold trajectory cache and compare hashes
.venv/bin/s1000 site --profile 1000x1000                          # website data -> site/data/
```

`--profile 1000x1000` (alias of `stationary1000`) is this release. A second profile, `full`, includes
non-stationary processes and is in development.

Outputs in `data/stationary1000/`: `series.npz` (`X`: 1000 × 1000 float64, and `ids`),
`metadata.parquet` / `.csv` (tags, ground truth, parameters, seeds), `manifest.json`,
`INP_1000x1000.mat` (hctsa input: `timeSeriesData`, `labels`, `keywords`), `timeseries-data.csv`,
`timeseries-info.csv`, `catalogue.md`.

## Layout

| | |
|---|---|
| `src/s1000/rng.py` | the seed contract |
| `src/s1000/registry.py` | classes, quotas, tag vocabulary, `@family` |
| `src/s1000/families/` | one module per class; each family is a generator `gen(i, rng, T, S) -> (x, info)` |
| `src/s1000/sources.py` | shared generators: dysts trajectories, multifractal sources, coupled rhythms |
| `src/s1000/util.py` | stratified draws, filters, integrators, noise |
| `src/s1000/build.py` | generation, quality-gate retries, hashing |
| `src/s1000/qc.py` | per-series gates |
| `src/s1000/reversibility.py` | the time-reversibility tag (see `docs/time_reversibility.md`) |
| `src/s1000/export.py`, `site.py` | hctsa files and csvs; website data |
| `docs/cards.yaml` | the family cards shown on the website (equations, notation, references) |
| `site/` | the website (static; deployed to GitHub Pages by `scripts/deploy_pages.sh`) |
| `scripts/` | audits, figures, the logo and overview figure |
| `tests/` | quotas, determinism, gates |

## Citation

Fulcher, B. D. (2026). *The 1000×1000 collection: 1000 synthetic time series from 133 dynamical
processes.* figshare. Dataset. https://doi.org/10.6084/m9.figshare.34013331

If you use the hctsa features, please also cite B. D. Fulcher and N. S. Jones, *Cell Systems* 5, 527
(2017), doi:10.1016/j.cels.2017.10.001.

Developed by [Ben Fulcher](http://www.benfulcher.com/), [Dynamics and Neural Systems
Group](https://dynamicsandneuralsystems.github.io/), School of Physics, The University of Sydney. The
generator code, the website and much of the documentation were written with Claude Code (Anthropic)
under the author's direction and review.
