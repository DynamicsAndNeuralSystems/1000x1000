"""Every series as its own full-width row, 25 rows per page, class-ordered: data/figures/all_series.pdf.

usage: all_series.py DATA [ROWS_PER_PAGE] [--notes NOTES.csv]
With --notes (columns id, category, note) writes all_series_annotated.pdf instead: flagged rows get a
background tinted by category and their notes printed beside the row, with a legend/summary on page 1."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from s1000.registry import CLASSES

args = [a for a in sys.argv[1:] if not a.startswith("--")]
notes_path = sys.argv[sys.argv.index("--notes") + 1] if "--notes" in sys.argv else None
if notes_path:
    args = [a for a in args if a != notes_path]
data = Path(args[0] if args else "data")
rows_per_page = int(args[1]) if len(args) > 1 else 25
NOTES = {}
CAT_COLOR = {"slow": "#cde2fb", "nonstationary": "#fbd9c2", "onset": "#f7c6c6", "periodic": "#e1d9f7",
             "duplicate": "#d3f0dc", "spiky": "#f8ecb8", "discrete": "#e3e2dd", "banded": "#c9ece8", "other": "#f0e0f0"}
CAT_INK = {"slow": "#184f95", "nonstationary": "#a3470e", "onset": "#a61b1b", "periodic": "#4a3aa7",
           "duplicate": "#1d6b3a", "spiky": "#7a5a00", "discrete": "#52514e", "banded": "#11695f", "other": "#7a3a7a"}
if notes_path:
    nt = pd.read_csv(notes_path)
    for r in nt.itertuples():
        NOTES.setdefault(r.id, []).append((r.category, r.note))
z = np.load(data / "series.npz")
X, ids = z["X"], z["ids"]
df = pd.read_parquet(data / "metadata.parquet")
order = df.sort_values(["cls", "family", "index"], kind="stable").index.values
INK, INK2, MUTED, BLUE = "#0b0b0b", "#52514e", "#a09f98", "#2a78d6"
plt.rcParams.update({"font.family": "DejaVu Sans"})

TAGS = ["deterministic", "chaotic", "linear", "gaussian", "stationary", "long_memory", "periodic",
        "discrete_valued", "bursty", "skewed", "heavy_tailed", "regime_switching", "event_like"]


def tagline(m):
    yes = [t for t in TAGS if m[t] == "yes"]
    extra = []
    if m["nonstationary_kind"] not in ("none", None):
        extra.append(f"nonstat:{m['nonstationary_kind']}")
    if m["domain"] != "abstract":
        extra.append(m["domain"])
    return "  ".join(yes + extra)


pdf_path = data / "figures" / ("all_series_annotated.pdf" if notes_path else "all_series.pdf")
pdf_path.parent.mkdir(exist_ok=True)
id_col = df["id"].values
with PdfPages(pdf_path) as pdf:
    if notes_path:  # summary page
        fig = plt.figure(figsize=(16, 0.42 * rows_per_page + 0.6))
        fig.text(0.06, 0.94, "Synthetic1000 stationary1000 — review notes", fontsize=16, color=INK, weight="bold")
        fig.text(0.06, 0.905, f"{len(NOTES)} of {len(order)} series flagged; tinted rows carry notes to the right. Categories:", fontsize=10, color=INK2)
        cats = pd.read_csv(notes_path).groupby("category").id.nunique().sort_values(ascending=False)
        y = 0.86
        desc = {"slow": "too slow: too few independent stretches / events per record",
                "nonstationary": "looks non-stationary: slow envelope, intermittency, drift",
                "onset": "initial transient / initial-condition artefact",
                "periodic": "periodic or near-sinusoidal outside the designed-periodic class H",
                "duplicate": "near-duplicate of another series / over-represented behaviour",
                "spiky": "a few extreme points dominate the plot",
                "discrete": "quasi-discrete (few distinct values or a point mass)",
                "banded": "banded chaos: genuine, but reads as a solid band",
                "other": "other"}
        for c, n in cats.items():
            fig.patches.append(plt.Rectangle((0.06, y - 0.008), 0.03, 0.022, transform=fig.transFigure, color=CAT_COLOR.get(c, "#eee")))
            fig.text(0.1, y, f"{c}  ({n})", fontsize=10, color=CAT_INK.get(c, INK), weight="bold")
            fig.text(0.24, y, desc.get(c, ""), fontsize=10, color=INK2)
            y -= 0.04
        # index of flagged series by page
        y -= 0.02
        fig.text(0.06, y, "Flagged series per page:", fontsize=10, color=INK)
        per_page = {}
        for k, r in enumerate(order):
            if id_col[r] in NOTES:
                per_page.setdefault(k // rows_per_page + 2, []).append(id_col[r])
        line = "   ".join(f"p{pg}: {len(v)}" for pg, v in sorted(per_page.items()))
        import textwrap
        for ln in textwrap.wrap(line, 150):
            y -= 0.03
            fig.text(0.06, y, ln, fontsize=8.5, color=INK2, family="monospace")
        pdf.savefig(fig)
        plt.close(fig)
    for p0 in range(0, len(order), rows_per_page):
        rows = order[p0:p0 + rows_per_page]
        fig, axes = plt.subplots(rows_per_page, 1, figsize=(16, 0.42 * rows_per_page + 0.6), squeeze=False)
        axes = axes.ravel()
        for a in axes:
            a.axis("off")
        pos = {r: k for k, r in enumerate(order)}
        for a, r in zip(axes, rows):
            m = df.loc[r]
            x = X[r]
            a.plot(x, lw=0.55, color=INK)
            a.set_xlim(0, len(x) - 1)
            a.axis("off")
            new_cls = pos[r] == 0 or df.loc[order[pos[r] - 1], "cls"] != m["cls"]
            par = json.loads(m["params"])
            hint = par.get("system") or par.get("kind") or par.get("observation") or ""
            label = f"{m['cls']}·{m['family']}·{m['index']:03d}" + (f"  {hint}" if hint else "")
            a.text(-0.005, 0.5, label, transform=a.transAxes, ha="right", va="center",
                   fontsize=6.3, color=BLUE if new_cls else INK2, family="monospace")
            sid = m["id"]
            if sid in NOTES:
                cats = [c for c, _ in NOTES[sid]]
                a.axis("on")
                a.set_xticks([]); a.set_yticks([])
                for sp in a.spines.values():
                    sp.set_visible(False)
                a.set_facecolor(CAT_COLOR.get(cats[0], "#eee"))
                a.set_xlim(-8, len(x) + 7)
                import textwrap
                txt = "\n".join(textwrap.fill(f"[{c}] {n}", 62, subsequent_indent="   ") for c, n in NOTES[sid])
                a.text(1.003, 0.5, txt, transform=a.transAxes, ha="left", va="center", fontsize=5.6,
                       color=CAT_INK.get(cats[0], INK), linespacing=1.05)
                a.texts[-2].set_color(CAT_INK.get(cats[0], INK))
                a.texts[-2].set_fontweight("bold")
            else:
                a.text(1.003, 0.5, tagline(m), transform=a.transAxes, ha="left", va="center", fontsize=5.5, color=MUTED)
            if new_cls:
                a.text(0.0, 1.05, f"class {m['cls']} — {CLASSES[m['cls']][0]}", transform=a.transAxes, ha="left", va="bottom",
                       fontsize=7.5, color=BLUE, weight="bold")
        page = p0 // rows_per_page + 1
        fig.text(0.5, 0.005, f"Synthetic1000 — series {p0 + 1}–{p0 + len(rows)} of {len(order)} — page {page + (1 if notes_path else 0)} of {int(np.ceil(len(order) / rows_per_page)) + (1 if notes_path else 0)}",
                 ha="center", fontsize=7, color=INK2)
        fig.subplots_adjust(left=0.17, right=0.74 if notes_path else 0.80, top=0.965, bottom=0.025, hspace=0.35)
        pdf.savefig(fig)
        plt.close(fig)
print("wrote", pdf_path)
