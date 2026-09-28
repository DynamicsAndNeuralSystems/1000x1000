"""Window stationarity audit: 5 non-overlapping windows of T/5.
statav_mean = SD of window means / SD of series      (hctsa SY_StatAv, 'mean')
statav_std  = SD of window SDs   / SD of series      (hctsa SY_StatAv, 'std')
var_ratio   = max window variance / min window variance
For i.i.d. noise statav_mean ~ 1/sqrt(200) = 0.07; strongly correlated stationary series reach ~0.3;
a drifting mean pushes it well above."""
import sys
from pathlib import Path
import numpy as np, pandas as pd

data = Path(sys.argv[1] if len(sys.argv) > 1 else "data/stationary1000")
X = np.load(data / "series.npz")["X"]; df = pd.read_parquet(data / "metadata.parquet")
W = 5
rows = []
for r in range(len(df)):
    x = X[r]; s = x.std() or 1.0
    w = x[: (len(x) // W) * W].reshape(W, -1)
    m, sd = w.mean(1), w.std(1)
    rows.append(dict(id=df.id[r], cls=df.cls[r], family=df.family[r], statav_mean=m.std() / s,
                     statav_std=sd.std() / s, var_ratio=(sd.max() ** 2) / max(sd.min() ** 2, 1e-12)))
a = pd.DataFrame(rows)
a.to_csv(data / "audit_stationarity.csv", index=False)
print("quantiles of statav_mean:", np.round(a.statav_mean.quantile([.5, .9, .95, .99]).values, 3))
print("quantiles of statav_std: ", np.round(a.statav_std.quantile([.5, .9, .95, .99]).values, 3))
print("quantiles of var_ratio:  ", np.round(a.var_ratio.quantile([.5, .9, .95, .99]).values, 2))
flag = a[(a.statav_mean > 0.5) | (a.statav_std > 0.35) | (a.var_ratio > 10)]
print(f"\nflagged {len(flag)} of {len(a)} (statav_mean > 0.5 or statav_std > 0.35 or var_ratio > 10)")
print(flag.groupby(["cls", "family"]).agg(n=("id", "size"), statav_mean=("statav_mean", "max"), statav_std=("statav_std", "max"), var_ratio=("var_ratio", "max")).round(2).to_string())
