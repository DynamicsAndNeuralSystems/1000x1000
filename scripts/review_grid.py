"""Render a set of series as a compact review grid with screen metrics annotated.
usage: review_grid.py DATA OUTPREFIX [--issue NAME | --ids id1,id2 | --family F.x] [--per 48]"""
import argparse, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("data"); ap.add_argument("out")
ap.add_argument("--issue"); ap.add_argument("--ids"); ap.add_argument("--family"); ap.add_argument("--cls")
ap.add_argument("--per", type=int, default=48); ap.add_argument("--all", action="store_true")
a = ap.parse_args()
data = Path(a.data)
z = np.load(data / "series.npz"); X, ids = z["X"], list(z["ids"])
m = pd.read_parquet(data / "metadata.parquet").set_index("id")
s = pd.read_csv(data / "screen.csv").set_index("id")
sel = list(s.index)
if a.issue: sel = [i for i in sel if s.loc[i, a.issue]]
if a.ids: sel = a.ids.split(",")
if a.family: sel = [i for i in sel if f"{m.loc[i,'cls']}.{m.loc[i,'family']}" == a.family]
if a.cls: sel = [i for i in sel if m.loc[i, "cls"] in a.cls]
issues = ["slow", "drift", "onset", "ending", "flat", "periodic", "sinusoid", "spiky", "jumps", "levels", "few_events", "duplicate"]
for p0 in range(0, len(sel), a.per):
    chunk = sel[p0:p0 + a.per]
    ncol = 3; nrow = int(np.ceil(len(chunk) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(18, 0.95 * nrow + 0.3), squeeze=False)
    for ax in axes.ravel(): ax.axis("off")
    for ax, i in zip(axes.ravel(), chunk):
        x = X[ids.index(i)]; r = s.loc[i]; p = json.loads(m.loc[i, "params"])
        hint = p.get("system") or p.get("kind") or p.get("observation") or ""
        ax.plot(x, lw=0.45, color="k"); ax.set_xlim(0, 999)
        fl = ",".join(k for k in issues if r[k])
        ax.set_title(f"{i.replace('S1000_','')} {hint} | tau {r.tau} sm {r.sm10:.2f} ss {r.ss10:.2f} vr {r.vr10:.0f} | {fl}", fontsize=6, loc="left", pad=1)
    fig.tight_layout(pad=0.2, h_pad=0.4)
    fig.savefig(f"{a.out}_{p0 // a.per + 1:02d}.png", dpi=80); plt.close(fig)
print(len(sel), "series ->", int(np.ceil(len(sel) / a.per)), "images")
