"""Design §4.3 audit: is each series long enough to express its process?
tau_acf  = first lag at which the autocorrelation falls below 1/e (samples)
n_events = threshold crossings (|x - median| > 4 MAD), for event-like / bursty families
n_dist   = distinct values (periodic orbits, saturation)
Flags: T/tau_acf < 20, or n_events < 20 for event-like families."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from s1000 import T

data = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
X = np.load(data / "series.npz")["X"]; df = pd.read_parquet(data / "metadata.parquet")

def tau_acf(x, maxlag=500):
    x = x - x.mean(); v = x @ x
    if v == 0: return np.inf
    for k in range(1, maxlag):
        if (x[:-k] @ x[k:]) / v < np.exp(-1): return k
    return maxlag

rows = []
for r in range(len(df)):
    x = X[r]; med = np.median(x); mad = np.median(np.abs(x - med)) or x.std() or 1
    dev = np.abs(x - med) > 4 * mad
    n_ev = int(np.sum(dev[1:] & ~dev[:-1]))
    rows.append(dict(id=df.id[r], cls=df.cls[r], family=df.family[r], tau=tau_acf(x), n_events=n_ev,
                     n_dist=int(np.unique(x).size), event_like=df.event_like[r]))
a = pd.DataFrame(rows); a["T_over_tau"] = T / a.tau
a.to_csv(data / "audit_length.csv", index=False)
g = a.groupby(["cls", "family"]).agg(n=("id", "size"), tau_med=("tau", "median"), tau_max=("tau", "max"),
                                    T_over_tau_min=("T_over_tau", "min"), events_min=("n_events", "min"), dist_min=("n_dist", "min"))
short = g[(g.T_over_tau_min < 20)]
print("families with some instance having T/tau < 20:"); print(short.round(1).to_string())
ev = a[a.event_like == "yes"].groupby(["cls", "family"]).n_events.agg(["min", "median"])
print("\nevent-like families with < 20 events in some instance:"); print(ev[ev["min"] < 20].to_string())
