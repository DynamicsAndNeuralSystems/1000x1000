"""Overview figures of the built corpus, written to data/figures/:

  carpet.png      the full 1000 x 1000 heat map, rows ordered by class / family, z-scored per row
  examples.png    one instance per family (first 250 samples), grouped by class
  embedding.png   catch24 feature space, PCA, one facet per class (all series grey, class in blue)
  joint.png       the same feature space with Empirical1000 (first 1000 samples of each) overlaid
  tags.png        fraction of each class tagged 'yes' for each property
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import numpy as np
import pandas as pd

from s1000.registry import CLASSES, TAG_NAMES

data = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
out = data / "figures"
out.mkdir(exist_ok=True)
z = np.load(data / "series.npz")
X, ids = z["X"], z["ids"]
df = pd.read_parquet(data / "metadata.parquet")
assert (df.id.values == ids).all()

INK, INK2, MUTED, SURFACE = "#0b0b0b", "#52514e", "#a09f98", "#fcfcfb"
BLUE, RED, GREY_MID = "#2a78d6", "#e34948", "#f0efec"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
diverging = LinearSegmentedColormap.from_list("bgr", [BLUE, GREY_MID, RED])
sequential = LinearSegmentedColormap.from_list("seq", ["#ffffff"] + SEQ)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})

classes = [c for c in CLASSES if (df.cls == c).any()]  # classes present in this profile
order = df.sort_values(["cls", "family", "index"], kind="stable").index.values
prof = json.loads((data / "manifest.json").read_text()).get("profile", "full")
bounds = [0]
for c in classes:
    bounds.append(bounds[-1] + int((df.cls == c).sum()))


def zrows(A):
    A = A - A.mean(axis=1, keepdims=True)
    s = A.std(axis=1, keepdims=True)
    return A / np.where(s > 0, s, 1)


# ---------------------------------------------------------------- carpet
Z = np.clip(zrows(X[order]), -2.5, 2.5)
fig = plt.figure(figsize=(11, 14))
gs = fig.add_gridspec(1, 2, width_ratios=[1, 40], wspace=0.01)
axb, ax = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
ax.imshow(Z, aspect="auto", cmap=diverging, vmin=-2.5, vmax=2.5, interpolation="nearest")
ax.set_xlabel("sample")
ax.set_yticks([])
ax.set_xticks([0, 250, 500, 750, 999])
for b in bounds[1:-1]:
    ax.axhline(b - 0.5, color=INK, lw=0.6)
band = np.zeros((len(order), 1))
for k in range(len(classes)):
    band[bounds[k]:bounds[k + 1]] = k % 2
axb.imshow(band, aspect="auto", cmap=ListedColormap(["#cde2fb", "#6da7ec"]), interpolation="nearest")
axb.set_xticks([])
axb.set_yticks([(bounds[k] + bounds[k + 1]) / 2 for k in range(len(classes))])
axb.set_yticklabels([f"{c}  ({bounds[k + 1] - bounds[k]})" for k, c in enumerate(classes)], fontsize=8)
axb.tick_params(length=0)
for s in axb.spines.values():
    s.set_visible(False)
ax.set_title(f"Synthetic1000 [{prof}]: every series, z-scored and clipped to ±2.5 SD (blue low, red high); rows grouped by class",
             loc="left", fontsize=10, color=INK)
fig.savefig(out / "carpet.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------- examples: one per family
fam_rows = []
for c in classes:
    g = df[df.cls == c]
    for f in g.family.unique():
        fam_rows.append(g[g.family == f].index[0])
n = len(fam_rows)
ncol = 10
nrow = int(np.ceil(n / ncol))
fig, axes = plt.subplots(nrow, ncol, figsize=(20, 1.35 * nrow), squeeze=False)
for a in axes.ravel():
    a.axis("off")
for a, r in zip(axes.ravel(), fam_rows):
    x = X[r, :250]
    a.plot(x, lw=0.7, color=INK)
    a.text(0.0, 1.02, f"{df.cls[r]} · {df.family[r]}", transform=a.transAxes, fontsize=7, color=INK2, va="bottom")
    a.axis("off")
fig.suptitle("One instance per family (first 250 samples), classes A–N in order", fontsize=11, color=INK, x=0.01, ha="left")
fig.tight_layout(pad=0.4, rect=(0, 0, 1, 0.985))
fig.savefig(out / "examples.png", dpi=130)
plt.close(fig)

# ---------------------------------------------------------------- features
import pycatch22

def feats(A):
    F = np.array([pycatch22.catch22_all(list(row), catch24=True)["values"] for row in A], dtype=float)
    return F

fpath = data / "catch24.npz"
if fpath.exists():
    F = np.load(fpath)["F"]
else:
    F = feats(X)
    np.savez_compressed(fpath, F=F, ids=ids)
def robust_sigmoid(A, ref=None):
    """hctsa's robust sigmoid: 1 / (1 + exp(-(x - median) / (1.35 IQR))), fitted on ``ref``."""
    R = A if ref is None else ref
    med = np.nanmedian(R, 0)
    iqr = np.nanpercentile(R, 75, 0) - np.nanpercentile(R, 25, 0)
    iqr = np.where(iqr > 0, iqr, np.nanstd(R, 0) + 1e-12)
    return np.nan_to_num(1 / (1 + np.exp(-(A - med) / (1.35 * iqr))), nan=0.5)

Fz = robust_sigmoid(F)
U, S, Vt = np.linalg.svd(Fz - Fz.mean(0), full_matrices=False)
P = (Fz - Fz.mean(0)) @ Vt[:2].T
ev = S[:2] ** 2 / (S**2).sum()

fig, axes = plt.subplots(3, 5, figsize=(17, 10.5), squeeze=False)
for a in axes.ravel():
    a.axis("off")
for a, c in zip(axes.ravel(), classes):
    m = (df.cls == c).values
    a.axis("on")
    a.scatter(P[~m, 0], P[~m, 1], s=5, color="#d9d8d3", linewidths=0)
    a.scatter(P[m, 0], P[m, 1], s=12, color=BLUE, linewidths=0.5, edgecolors=SURFACE)
    a.set_title(f"{c} · {CLASSES[c][0]}  (n = {m.sum()})", fontsize=9, loc="left", color=INK)
    a.set_xticks([])
    a.set_yticks([])
    for s in a.spines.values():
        s.set_color("#d9d8d3")
fig.suptitle(f"[{prof}] catch24 feature space (robust-sigmoid normalised), first two principal components ({100*ev[0]:.0f}% + {100*ev[1]:.0f}% of variance): each class highlighted against the corpus",
             fontsize=11, color=INK, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.97))
fig.savefig(out / "embedding.png", dpi=130)
plt.close(fig)

# ---------------------------------------------------------------- joint with Empirical1000
emp = next((d / "INP_1000ts.mat" for d in data.resolve().parents if (d / "INP_1000ts.mat").exists()), Path("/nonexistent"))  # Empirical1000 input file, somewhere above this repo
if emp.exists():
    from scipy.io import loadmat
    m = loadmat(str(emp), squeeze_me=True)
    E = np.array([np.ravel(t)[:1000] for t in m["timeSeriesData"] if np.ravel(t).size >= 1000], dtype=float)
    epath = data / "catch24_empirical1000.npz"
    if epath.exists():
        FE = np.load(epath)["F"]
    else:
        FE = feats(E)
        np.savez_compressed(epath, F=FE)
    both = np.vstack([F, FE])
    B = robust_sigmoid(both)
    Ub, Sb, Vtb = np.linalg.svd(B - B.mean(0), full_matrices=False)
    Pb = (B - B.mean(0)) @ Vtb[:2].T
    ns = F.shape[0]
    # nearest-neighbour distance from each empirical series to the synthetic corpus, in z-feature space
    from scipy.spatial import cKDTree
    d_emp, _ = cKDTree(B[:ns]).query(B[ns:])
    d_syn, _ = cKDTree(B[:ns]).query(B[:ns], k=2)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
    a = axes[0]
    a.scatter(Pb[:ns, 0], Pb[:ns, 1], s=9, color=BLUE, linewidths=0, alpha=0.8, label="Synthetic1000")
    a.scatter(Pb[ns:, 0], Pb[ns:, 1], s=9, color="#eb6834", linewidths=0, alpha=0.8, label="Empirical1000 (first 1000 samples)")
    a.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8)
    a.set_title("Joint catch24 PCA of both corpora (robust-sigmoid normalised)", loc="left", fontsize=10, color=INK, pad=22)
    a.set_xticks([]); a.set_yticks([])
    a = axes[1]
    bins = np.linspace(0, max(d_emp.max(), d_syn[:, 1].max()), 40)
    a.hist(d_syn[:, 1], bins=bins, color=BLUE, alpha=0.8, label="synthetic → nearest other synthetic")
    a.hist(d_emp, bins=bins, color="#eb6834", alpha=0.8, label="empirical → nearest synthetic")
    a.legend(frameon=False)
    a.set_xlabel("nearest-neighbour distance (robust-sigmoid catch24)")
    a.set_ylabel("count")
    a.set_title("Coverage: empirical series far from every synthetic one are the gaps", loc="left", fontsize=10, color=INK)
    for s in a.spines.values():
        s.set_color("#d9d8d3")
    fig.tight_layout()
    fig.savefig(out / "joint.png", dpi=130)
    plt.close(fig)
    q = np.quantile(d_syn[:, 1], 0.95)
    far = np.flatnonzero(d_emp > q)
    print(f"joint: {len(far)} of {len(d_emp)} empirical series lie beyond the synthetic 95% NN distance ({q:.2f})")
    names = np.array([str(l) for l, t in zip(m["labels"], m["timeSeriesData"]) if np.ravel(t).size >= 1000])
    kws = np.array([str(k) for k, t in zip(m["keywords"], m["timeSeriesData"]) if np.ravel(t).size >= 1000])
    pd.DataFrame(dict(name=names[far], keywords=kws[far], nn_distance=d_emp[far])).sort_values("nn_distance", ascending=False) \
        .to_csv(data / "coverage_gaps.csv", index=False)

# ---------------------------------------------------------------- tags
tags = [t for t in TAG_NAMES if t not in ("nonstationary_kind", "domain")]
M = np.array([[(df[df.cls == c][t] == "yes").mean() for t in tags] for c in classes])
fig, ax = plt.subplots(figsize=(13, 6))
ax.imshow(M, cmap=sequential, vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(tags)))
ax.set_xticklabels(tags, rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(len(classes)))
ax.set_yticklabels([f"{c}  {CLASSES[c][0]}" for c in classes], fontsize=8)
for i in range(len(classes)):
    for j in range(len(tags)):
        v = M[i, j]
        if v > 0:
            ax.text(j, i, f"{100*v:.0f}", ha="center", va="center", fontsize=6.5, color="#ffffff" if v > 0.55 else INK2)
ax.set_title("Percent of each class tagged 'yes' for each property", loc="left", fontsize=10, color=INK)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
fig.tight_layout()
fig.savefig(out / "tags.png", dpi=150)
plt.close(fig)
print("figures written to", out)
