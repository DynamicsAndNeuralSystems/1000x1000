"""Automated screen for the issue types Ben has flagged by eye (review rounds 1-3), so a corpus is only
handed over for manual review once none remain. One row per series, one boolean column per issue.

  slow        too few independent stretches: autocorrelation time > 6 samples, or < 35 dominant
              periods in the record (for oscillatory series)          ["could be faster"]
  drift       non-stationary to the eye: 10-window mean spread > 0.35 SD, or 10-window SD spread
              > 0.35, or max/min window variance > 8 (not for event-like families)
  onset       opening differs from the rest: first 50 samples' mean > 1 SD from the rest's mean,
              their SD < 0.3x or > 3x the rest's, or a flat run at the start
  ending      same test on the last 50 samples                        [onoff-traffic drop-off]
  flat        a run of > 30 near-constant samples anywhere (not for zero-inflated event families)
  periodic    exact or near-exact repetition: autocorrelation at the dominant period > 0.95
              (outside class H, where periodicity is designed)       [limit cycles, trivial orbits]
  sinusoid    near-pure sinusoid: > 80% of spectral power in the 5 bins around the peak
  spiky       a handful of points dominate the plot: range / (1st-99th percentile range) > 3
  jumps       sudden resets in continuous-time families: max |dx| > 12x the 99th percentile |dx|
  levels      fewer than 200 distinct values or one value > 40% of samples (quasi-discrete)
  few_events  event-like families with fewer than 25 excursions above median + 3 MAD
  duplicate   within-family pairs whose catch24 profiles are near-identical (distance < 15% of the
              family's median pairwise distance)                      [circle maps 005/006]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from s1000.util import acf_time, dominant_period  # noqa: E402

data = Path(sys.argv[1] if len(sys.argv) > 1 else "data/stationary1000")
z = np.load(data / "series.npz")
X, ids = z["X"], list(z["ids"])
m = pd.read_parquet(data / "metadata.parquet").set_index("id").loc[ids]
F = np.load(data / "catch24.npz")["F"] if (data / "catch24.npz").exists() else None


def windows(x, k):
    w = x[: (x.size // k) * k].reshape(k, -1)
    s = x.std() or 1.0
    return w.mean(1).std() / s, w.std(1).std() / s, (w.std(1).max() ** 2) / max(w.std(1).min() ** 2, 1e-12)


def longest_flat(x, tol):
    d = np.abs(np.diff(x)) < tol
    best = run = 0
    for v in d:
        run = run + 1 if v else 0
        best = max(best, run)
    return best


rows = []
for k, sid in enumerate(ids):
    x = X[k].astype(float)
    r = m.loc[sid]
    cls, fam = r["cls"], r["family"]
    s = x.std() or 1.0
    ev = r["event_like"] == "yes" or r["bursty"] == "yes"
    ct = r["continuous_time"] == "yes"
    tau = acf_time(x)
    P = dominant_period(x)
    xc = x - x.mean()
    Pi = int(round(P)) if np.isfinite(P) else 0
    ac_P = float(xc[:-Pi] @ xc[Pi:] / (xc @ xc)) if 2 <= Pi < 300 else 0.0
    spec = np.abs(np.fft.rfft(xc)) ** 2
    spec[0] = 0
    pk = int(np.argmax(spec))
    conc = spec[max(0, pk - 2): pk + 3].sum() / max(spec.sum(), 1e-12)
    n_periods = x.size / P if np.isfinite(P) and P > 0 else np.inf
    sm, ss, vr = windows(x, 10)
    head, tail, mid = x[:50], x[-50:], x[50:-50]
    ms, mm = mid.std() or 1.0, mid.mean()
    q01, q99 = np.percentile(x, [1, 99])
    dx = np.abs(np.diff(x))
    vals, counts = np.unique(x, return_counts=True)
    med = np.median(x)
    mad = np.median(np.abs(x - med)) or s
    exc = np.abs(x - med) > 3 * mad
    n_exc = int(np.sum(exc[1:] & ~exc[:-1]))
    flat = longest_flat(x, 1e-6 * s)
    zero_inflated = counts.max() / x.size > 0.2
    rows.append(dict(
        id=sid, cls=cls, family=fam, tau=tau, n_periods=round(n_periods, 1), ac_at_period=round(ac_P, 3),
        spec_conc=round(conc, 3), sm10=round(sm, 3), ss10=round(ss, 3), vr10=round(vr, 1),
        slow=bool(tau > 6 or (conc > 0.3 and n_periods < 35)),
        drift=bool(not ev and (sm > 0.35 or ss > 0.35 or vr > 8)),
        onset=bool(abs(head.mean() - mm) > 1.0 * ms or not (0.3 < head.std() / ms < 3) or longest_flat(head, 1e-6 * s) > 15),
        ending=bool(abs(tail.mean() - mm) > 1.0 * ms or not (0.3 < tail.std() / ms < 3)),
        flat=bool(flat > 30 and not zero_inflated),
        periodic=bool(cls != "H" and ac_P > 0.95),
        sinusoid=bool(conc > 0.8),
        spiky=bool((x.max() - x.min()) / max(q99 - q01, 1e-12) > 3),
        jumps=bool(ct and dx.max() > 12 * max(np.percentile(dx, 99), 1e-12)),
        levels=bool(vals.size < 200 or counts.max() / x.size > 0.4),
        few_events=bool(r["event_like"] == "yes" and n_exc < 25),
        duplicate=False,
    ))
out = pd.DataFrame(rows)

if F is not None:
    from scipy.spatial.distance import pdist, squareform
    Fz = (F - np.nanmedian(F, 0)) / (np.nanpercentile(F, 75, 0) - np.nanpercentile(F, 25, 0) + 1e-9)
    Fz = np.nan_to_num(np.clip(Fz, -10, 10))
    for fam, g in out.groupby("family"):
        idx = g.index.values
        if idx.size < 3:
            continue
        D = squareform(pdist(Fz[idx]))
        medD = np.median(D[np.triu_indices(idx.size, 1)])
        for a in range(idx.size):
            for b in range(a + 1, idx.size):
                if D[a, b] < 0.15 * medD:
                    out.loc[idx[a], "duplicate"] = True
                    out.loc[idx[b], "duplicate"] = True

issues = ["slow", "drift", "onset", "ending", "flat", "periodic", "sinusoid", "spiky", "jumps", "levels", "few_events", "duplicate"]
out["n_issues"] = out[issues].sum(1)
out.to_csv(data / "screen.csv", index=False)
print(f"{int((out.n_issues > 0).sum())} of {len(out)} series flagged")
print(out[issues].sum().to_string())
print()
print(out[out.n_issues > 0].groupby(["cls", "family"])[issues].sum().loc[lambda d: d.sum(1) > 0].astype(int).to_string())
