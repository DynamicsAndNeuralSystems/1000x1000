"""Contact sheet: one thumbnail per series (or per family), for eyeballing the corpus."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

data = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
per_family = "--families" in sys.argv
z = np.load(data / "series.npz")
X, ids = z["X"], z["ids"]
df = pd.read_parquet(data / "metadata.parquet")
out = data / "figures"
out.mkdir(exist_ok=True)

for cls, g in df.groupby("cls", sort=True):
    rows = g.index.tolist()
    if per_family:
        rows = [g[g.family == f].index[0] for f in g.family.unique()]
    n = len(rows)
    ncol = 5
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(20, 1.6 * nrow), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for ax, r in zip(axes.ravel(), rows):
        x = X[r]
        ax.plot(x, lw=0.5, color="k")
        ax.set_title(f"{df.id[r].replace('S1000_', '')}", fontsize=7, loc="left", pad=1)
        ax.axis("off")
    fig.suptitle(f"class {cls} ({n} shown)", fontsize=10, y=1.0)
    fig.tight_layout(pad=0.3)
    fig.savefig(out / f"contact_{cls}{'_families' if per_family else ''}.png", dpi=110)
    plt.close(fig)
    print("wrote", cls, n)
