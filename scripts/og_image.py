"""Link-preview (Open Graph) image for the website: site/og.png, 1200 x 630.
Thirteen strips, one series per class in its class colours, under the title."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SITE = Path(__file__).resolve().parents[1] / "site"
COL = {"A": ((146, 58, 55), (255, 237, 234)), "B": ((0, 109, 57), (230, 249, 235)), "C": ((82, 79, 155), (240, 242, 255)),
       "D": ((142, 66, 6), (255, 239, 227)), "E": ((0, 111, 92), (224, 250, 244)), "F": ((109, 69, 142), (249, 239, 255)),
       "G": ((128, 79, 0), (255, 241, 223)), "H": ((0, 108, 123), (223, 249, 252)), "I": ((129, 61, 119), (255, 237, 252)),
       "J": ((105, 92, 0), (247, 245, 223)), "L": ((142, 57, 89), (255, 236, 243)), "M": ((71, 103, 5), (238, 247, 228)),
       "N": ((40, 90, 157), (232, 245, 255))}
PICK = {"A": "S1000_IID_skewed_000", "B": "S1000_LG_narrowband_001", "C": "S1000_LNG_levy-ou_002", "D": "S1000_LRD_mrw_003",
        "E": "S1000_NLS_garch_004", "F": "S1000_MAP_dysts-map_004", "G": "S1000_FLOW_dysts-flow_020", "H": "S1000_OSC_modulated-stationary_000",
        "I": "S1000_SDE_double-well_003", "J": "S1000_EVT_hawkes_001", "L": "S1000_COMP_pac_000", "M": "S1000_OBS_clipped_000",
        "N": "S1000_NAT_ecgsyn_000"}
rgb = lambda c: tuple(v / 255 for v in c)

index = json.loads((SITE / "data/index.json").read_text())
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor="#f7f6f2")
# the logo (scripts/logo.py): the zeros of each 1000 are one orbit over the class pastels; drawn in its viewBox units
sys.path.insert(0, str(Path(__file__).resolve().parent))
import logo as L
from matplotlib.patches import Ellipse
lh = 0.17  # logo height, figure fraction
lx = fig.add_axes([0.05, 0.875 - lh / 2, lh * 532 / 124 * 630 / 1200, lh])
lx.set_xlim(-12, 520); lx.set_ylim(112, -12); lx.axis("off")
fig.canvas.draw()
unit = (lx.transData.transform((1, 0))[0] - lx.transData.transform((0, 0))[0]) * 72 / fig.dpi  # points per unit
def lpl(pts, w, alpha=1.0, cap="round"):
    lx.plot([p[0] for p in pts], [p[1] for p in pts], color="#16150f", lw=w * unit, alpha=alpha, solid_capstyle=cap, solid_joinstyle="round")
x = 0
for side in (0, 1):
    lpl([(x + 4, 20), (x + 20, 2), (x + 20, 100)], 9); x += 44
    for k in range(3):
        rgb_ = [int(v) / 255 for v in L.PAST[3 * side + k][4:-1].split(",")]
        lx.add_patch(Ellipse((x + 27 * (2 * k + 1), 51), 2 * 22.5, 2 * 41.5, color=rgb_, lw=0))
    pts = L.triple_path(x); N = len(pts); st = int(0.27 * N); seq = (pts[st:] + pts[:st])[:int(N * 0.95)]; Ls = len(seq)
    for k in range(10):
        lpl(seq[k * Ls // 10:min(Ls - 1, (k + 1) * Ls // 10) + 1], 8, 0.2 + 0.8 * (k + 1) / 10, "butt")
    hx, hy = pts[st - 1]; lx.add_patch(Ellipse((hx, hy), 13, 13, color="#16150f", lw=0))
    x += 6 * 27
    if side == 0:
        x += 26; c = x + 22
        lpl([(c - 16, 42), (c + 16, 74)], 9); lpl([(c - 16, 74), (c + 16, 42)], 9); x += 44 + 26
fig.text(0.05, 0.73, "1000 simulated time series, 1000 samples each, spanning the dynamical processes scientists model",
         fontsize=17, color="#52514e", family="Helvetica Neue", va="center")
fig.text(0.05, 0.05, "dynamicsandneuralsystems.github.io/1000x1000", fontsize=14, color="#85847d", family="Helvetica Neue")
codes = [c["code"] for c in index["classes"]]
top, bot, gap = 0.66, 0.11, 0.006
h = (top - bot - gap * (len(codes) - 1)) / len(codes)
for k, c in enumerate(codes):
    x = np.asarray(json.loads((SITE / f"data/series/{c}.json").read_text())[PICK[c]], float)[:400]
    ax = fig.add_axes([0.05, top - (k + 1) * h - k * gap, 0.9, h])
    ink, bg = COL[c]
    ax.set_facecolor(rgb(bg))
    ax.plot(x, color=rgb(ink), lw=1.1)
    lo, hi = np.quantile(x, [0.005, 0.995])
    ax.set_ylim(lo - 0.1 * (hi - lo), hi + 0.1 * (hi - lo)); ax.set_xlim(0, len(x) - 1)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
fig.savefig(SITE / "og.png", facecolor=fig.get_facecolor())
print("wrote", SITE / "og.png")
