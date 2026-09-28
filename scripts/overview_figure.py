"""Overview figure for the figshare deposit, in the format of the Empirical1000 overview
of the Empirical1000 dataset: all 1000 series as small panels, ordered so neighbouring
panels share dynamics (optimal-leaf-ordered Ward clustering of hctsa PCA-25), each a short window at its own
timescale, coloured by class in the website's class colours. Writes 1000x1000_overview.png/.pdf into the figshare
folder.

usage: python scripts/overview_figure.py [FIGSHARE_DIR]"""
import csv, os, sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from scipy.cluster.hierarchy import linkage, leaves_list, optimal_leaf_ordering

DDIR = sys.argv[1] if len(sys.argv) > 1 else "data/stationary1000/figshare_1000x1000"
names, kws = [], []
with open(f"{DDIR}/hctsa_timeseries-info.csv") as f:
    for row in csv.DictReader(f):
        names.append(row["Name"]); kws.append(row["Keywords"])
N = len(names)

series = []
with open(f"{DDIR}/hctsa_timeseries-data.csv") as f:
    for line in f:
        series.append(np.fromstring(line, sep=","))
assert len(series) == N

X = np.loadtxt(f"{DDIR}/hctsa_datamatrix.csv", delimiter=",")
with open(f"{DDIR}/hctsa_features.csv") as f:
    fnames = [row["Name"] for row in csv.DictReader(f)]
TAU  = X[:, fnames.index("firstZero_acf_tau")].copy()   # CO_FirstCrossing_acf_0
FMIN = X[:, fnames.index("firstMin_acf")].copy()        # CO_FirstMin_ac
col_ok = ~np.all(np.isnan(X), axis=0)
X = X[:, col_ok]
cm = np.nanmean(X, axis=0)
inds = np.where(np.isnan(X))
X[inds] = np.take(cm, inds[1])
X = (X - X.mean(0)) / (X.std(0) + 1e-12)
X = np.clip(X, -8, 8)
P = PCA(n_components=25, random_state=0).fit_transform(X)
Z = optimal_leaf_ordering(linkage(P, method="ward"), P)
order = leaves_list(Z)

# ---- classes (the class code is the second part of each ID), in the website's class colours ----
CLASSES = [("IID", "i.i.d. noise"), ("LG", "linear Gaussian"), ("LNG", "linear non-Gaussian"),
           ("LRD", "long memory"), ("NLS", "nonlinear stochastic"), ("MAP", "maps"), ("FLOW", "chaotic flows"),
           ("OSC", "oscillatory"), ("SDE", "noise-driven continuous time"), ("EVT", "events and states"),
           ("COMP", "composite and coupled"), ("OBS", "observation effects"), ("NAT", "natural and engineered")]
PALETTE = ["#e2726b", "#44b16f", "#8c8cec", "#db7c3f", "#00b39a", "#b07fda", "#c88b0d",
           "#00b0c1", "#cb75bc", "#aa9a0d", "#dc7096", "#7fa840", "#5c99ed"]
code = [n.split("_")[1] for n in names]
cidx = np.array([[c for c, _ in CLASSES].index(k) for k in code])
colors = [PALETTE[c] for c in cidx]

# ---- characteristic-timescale windowing -------------------------------------
# Primary rule: show a central window of ~K_TAU * tau samples, tau = hctsa's
# firstZero_acf_tau (first zero-crossing of the ACF).  Secondary rule: if that
# window would still show many clean cycles of a dominant oscillation, trim it
# to ~CYC_MAX periods so chaotic flows read clearly instead of as a dense band.
K_TAU   = float(os.environ.get("K_TAU", 22))
WMIN    = int(os.environ.get("WMIN", 60))
CYC_MAX = float(os.environ.get("CYC_MAX", 6))
SUF     = os.environ.get("SUF", "")

def best_start(x, W):
    n = x.size
    starts = sorted({int(round(f * (n - W))) for f in np.linspace(0, 1, 9)})
    return max(starts, key=lambda s: np.std(x[s:s + W]))

def spectral_period(w):
    """Dominant period if the window has a clear spectral peak, else None."""
    n = w.size
    if n < 32:
        return None
    ps = np.abs(np.fft.rfft((w - w.mean()) * np.hanning(n))) ** 2
    f  = np.fft.rfftfreq(n)
    lo = np.searchsorted(f, 2.0 / n)
    seg = ps[lo:]
    if seg.size == 0:
        return None
    k = int(np.argmax(seg))
    pos = seg[seg > 0]
    if pos.size == 0 or seg[k] / np.median(pos) < 5:
        return None
    P = 1.0 / f[lo + k]
    return P if 3 <= P <= n / 2.5 else None

def window_of(x, tau, fmin):
    n = x.size
    if n <= WMIN or not np.isfinite(tau) or tau < 1:
        w = x
    else:
        W = int(np.clip(K_TAU * tau, WMIN, n))
        w = x if W >= n else x[best_start(x, W):][:W]
        if np.std(w) < 1e-9 * (np.std(x) + 1e-12):
            w = x
    # secondary: cap the number of visible pseudo-periods so dense flows clear up.
    # pseudo-period = clean spectral peak if present, else 2 x firstMin_acf (a
    # real hctsa timescale, defined for every series).
    P = spectral_period(w)
    if P is None and np.isfinite(fmin) and fmin >= 1:
        P = 2.0 * fmin
    if P is not None:
        W2 = int(np.clip(CYC_MAX * P, WMIN, w.size))
        if W2 < w.size:
            w = w[best_start(w, W2):][:W2]
    return w

clean = [series[i][np.isfinite(series[i])].astype(float) for i in range(N)]
windows = [window_of(clean[i], TAU[i], FMIN[i]) for i in range(N)]
wl = np.array([w.size for w in windows])
print(f"K_TAU={K_TAU} WMIN={WMIN} CYC_MAX={CYC_MAX} | window len "
      f"min {wl.min()} median {int(np.median(wl))} max {wl.max()} "
      f"| whole series: {sum(wl[i] == clean[i].size for i in range(N))}")

# ---- layout ----
NCOL, NROW = 40, 25
BG = "#0f1116"
fig = plt.figure(figsize=(26, 17), dpi=200)
fig.patch.set_facecolor(BG)
ax = fig.add_axes([0.012, 0.034, 0.976, 0.79])   # grid area only
ax.set_facecolor(BG); ax.set_xlim(0, NCOL); ax.set_ylim(0, NROW); ax.axis("off")

# faint panel scaffold
for rr in range(NROW):
    if rr % 2 == 0:
        ax.add_patch(plt.Rectangle((0, rr), NCOL, 1, color="#ffffff", alpha=0.022, lw=0))
for cc in range(1, NCOL):
    ax.axvline(cc, color="#ffffff", alpha=0.03, lw=0.4)

px, py = 0.05, 0.09
NB = 150            # envelope bins (used only for windows still longer than this)
LINE_MAX = 1400    # plot as a line up to this many samples, else min/max envelope
for k, si in enumerate(order):
    r, c = divmod(k, NCOL)
    y0 = NROW - 1 - r
    x = windows[si]
    if x.size < 2: continue
    lo_c, hi_c = np.percentile(x, [0.5, 99.5])
    if hi_c <= lo_c: hi_c = x.max(); lo_c = x.min()
    if hi_c <= lo_c: continue
    xn = (np.clip(x, lo_c, hi_c) - lo_c) / (hi_c - lo_c)
    col = colors[si]
    if xn.size > LINE_MAX:
        nb = NB
        idx = np.linspace(0, xn.size, nb + 1).astype(int)
        lo = np.array([xn[idx[j]:idx[j+1]].min() for j in range(nb)])
        hi = np.array([xn[idx[j]:idx[j+1]].max() for j in range(nb)])
        tt = np.linspace(c + px, c + 1 - px, nb)
        y_lo = y0 + py + lo * (1 - 2 * py)
        y_hi = y0 + py + hi * (1 - 2 * py)
        ax.fill_between(tt, y_lo, y_hi, color=col, lw=0, alpha=0.92)
        ax.plot(tt, y_hi, lw=0.4, color=col); ax.plot(tt, y_lo, lw=0.4, color=col)
    else:
        tt = np.linspace(c + px, c + 1 - px, xn.size)
        yy = y0 + py + xn * (1 - 2 * py)
        lw = 0.9 if xn.size < 300 else (0.7 if xn.size < 700 else 0.55)
        ax.plot(tt, yy, lw=lw, color=col, alpha=1.0, solid_capstyle="round")

# ---- header ----
fig.text(0.012, 0.958, "The 1000×1000 collection",
         color="#f6f7f9", fontsize=40, fontweight="bold", ha="left", va="top")
fig.text(0.012, 0.912,
         "Every series in the 1000×1000 collection (1000 simulated series, 1000 samples each), ordered so "
         f"neighbouring panels share dynamics (1-D layout of {X.shape[1]} hctsa features).",
         color="#9aa0a8", fontsize=13.5, ha="left", va="top")
fig.text(0.012, 0.888,
         "Each panel is a short window — ≈22τ (τ = first ACF zero-crossing), trimmed to ≲6 cycles "
         "of the dominant oscillation — robust-scaled to its own frame.",
         color="#9aa0a8", fontsize=13.5, ha="left", va="top")

handles = [plt.Line2D([0],[0], color=PALETTE[i], lw=6, label=f"{c}  {lab}") for i,(c,lab) in enumerate(CLASSES)]
fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.012, 0.855),
           ncol=7, frameon=False, fontsize=12, labelcolor="#cfd3d9",
           handlelength=1.5, columnspacing=1.8, borderaxespad=0)
fig.text(0.988, 0.010,
         "hctsa b1759834  ·  MATLAB R2025a  ·  doi:10.6084/m9.figshare.34013331",
         color="#5f656c", fontsize=10, ha="right", va="bottom")

out = f"{DDIR}/1000x1000_overview{SUF}"
fig.savefig(out + ".png", facecolor=BG, dpi=200)
if not SUF:
    fig.savefig(out + ".pdf", facecolor=BG)
print("wrote", out + ".png")
