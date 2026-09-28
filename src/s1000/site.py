"""``s1000 site``: export a built corpus as the data files of the static web resource.

Writes ``<site>/data/``: ``index.json`` (corpus, classes, families with their cards, tag vocabulary),
``meta.json`` (one record per series: tags, numerics, drawn parameters, seed), ``series/<cls>.json``
(the samples of one class, 4 significant figures, loaded on demand) and ``embed.json`` (PCA and t-SNE coordinates
from full hctsa features when ``<out>/hctsa/HCTSA_*.mat`` exists, else catch22), ``neighbours.json`` (each
series' nearest neighbours in the same space). The front end in ``site/`` is plain
files; ``python -m http.server -d site`` serves it.

Family cards (description, LaTeX equations, simulation notes, references) live in ``docs/cards.yaml``
keyed by family name; a family without a card falls back to its generator's docstring.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .build import class_label
from .registry import CLASS_CODES, CLASS_NAMES, CLASSES, NUMERIC_NAMES, RELEASE_NAMES, PROFILES, TAG_NAMES, by_class, load_all, set_profile
from .names import FAMILY as FAMILY_NAMES, series_labels, series_name
from .util import dominant_period

CODE_CLASS = {v: k for k, v in CLASS_CODES.items()}  # series IDs and `cls` carry class codes (FLOW) in stationary1000

# Binary tags shown as filter chips (value "yes"; "partly" counts as a softer yes).
CHIP_TAGS = ("chaotic", "deterministic", "linear", "gaussian", "long_memory", "periodic", "quasiperiodic",
             "continuous_time", "heavy_tailed", "heteroskedastic", "regime_switching", "event_like",
             "bursty", "skewed", "reversible", "measurement_noise")
ONE_LINERS = {
    "A": "Independent draws: the null against which all structure is measured.",
    "B": "Gaussian processes fully described by a short-memory autocorrelation.",
    "C": "Linear filters driven by skewed, heavy-tailed or bounded innovations.",
    "D": "Power-law correlations, fractional processes and multiplicative cascades.",
    "E": "Thresholds, volatility clustering, hidden regimes and random coefficients.",
    "F": "Iterated maps, from the logistic map to strange nonchaotic attractors.",
    "G": "Strange attractors of ordinary and delay differential equations.",
    "H": "Limit cycles, tori and shaped oscillations.",
    "I": "Stochastic differential equations: wells, resonance, excitability, noisy chaos.",
    "J": "Renewal, self-exciting and Markov processes, read out as real values.",
    "K": "Trends, breaks and drifts.",
    "L": "Couplings, mixtures, cross-frequency and cyclostationary structure.",
    "M": "What measurement does to a process: clipping, aliasing, gaps, readouts.",
    "N": "Models of hearts, brains, climate, ecosystems, lasers and markets.",
}


# One line per class about its mascot (site/icons/<letter>-<animal>.svg), shown in italics on the class page.
MOTTOS = {
    "A": "A memory like a goldfish: every draw forgets the last.",
    "B": "The jellyfish drifts in a Gaussian bell, forever relaxing back to rest.",
    "C": "The stingray glides in a straight line, trailing a long, heavy tail.",
    "D": "An elephant never forgets.",
    "E": "The chameleon changes with its surroundings: new conditions, new regime.",
    "F": "The frog travels in discrete hops, one iterate at a time.",
    "G": "One flap of a butterfly's wings, and the future is a different place.",
    "H": "Fireflies flash in rhythm, and whole trees of them fall into step.",
    "I": "Busy as a bee, buzzing along a jittery, noise-driven path.",
    "J": "The woodpecker drums in bursts: rat-a-tat, silence, rat-a-tat-tat.",
    "K": "The caterpillar becomes a butterfly: the process itself changes.",
    "L": "Eight arms, one animal: coupled parts moving as a whole.",
    "M": "The owl reminds us that what we see depends on how we look.",
    "N": "The beaver, nature's own engineer.",
}


def _sig(v: float, n: int = 4):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    return float(f"{v:.{n}g}")


# Series whose samples are successive iterations of a discrete-time rule: the phase portrait uses the rule's
# own step (tau = 1), so x_{t+1} against x_t is the graph of the map. Everything else uses the ACF delay.
UNIT_STEP_CLASSES = {"E", "F"}
UNIT_STEP_KINDS = {("L", "on-off"): None, ("L", "coupled-systems"): {"cml-intermittency", "cml-turbulence"},
                   ("N", "blowflies-ricker"): {"ricker-env"}, ("N", "deboer"): None}
UNIT_STEP_OBS = {"clipped", "missing-data", "irregular-sampling", "nonlinear-readout", "outliers", "heavy-noise"}


def _unit_step(cls: str, family: str, p: dict, all_params: dict) -> bool:
    if cls in UNIT_STEP_CLASSES:
        return True
    if (cls, family) in UNIT_STEP_KINDS:
        kinds = UNIT_STEP_KINDS[(cls, family)]
        return kinds is None or p.get("kind") in kinds
    if cls == "M" and p.get("observation") in UNIT_STEP_OBS and p.get("base_id"):
        b = p["base_id"].split("_")
        return _unit_step(CODE_CLASS.get(b[1], b[1]), b[2], all_params.get(p["base_id"], {}), all_params)
    return False


def _load_cards(root: Path) -> dict:
    p = root / "docs" / "cards.yaml"
    if not p.exists():
        return {}
    import yaml
    return yaml.safe_load(p.read_text()) or {}


def _embed(F: np.ndarray, n_pc: int | None = None):
    """Robust-sigmoid normalise the features (as hctsa's scaledRobustSigmoid, so a few extreme series do
    not set the axes) and standardise; PCA for the PCA view; t-SNE and neighbours on the normalised
    features, or on their first ``n_pc`` principal components (for thousands of hctsa features). UMAP on the same."""
    med = np.median(F, 0)
    iqr = np.subtract(*np.percentile(F, [75, 25], 0))
    iqr[iqr == 0] = F.std(0)[iqr == 0] + 1e-12
    Z = 1 / (1 + np.exp(-np.clip((F - med) / (iqr / 1.35), -50, 50)))
    Z = (Z - Z.mean(0)) / (Z.std(0) + 1e-12)
    U, s, Vt = np.linalg.svd(Z, full_matrices=False)
    R = U[:, :n_pc] * s[:n_pc] if n_pc else Z
    from sklearn.manifold import TSNE
    T = TSNE(n_components=2, perplexity=30, init="pca", random_state=0).fit_transform(R)
    import umap
    M = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=0).fit_transform(R)
    return U[:, :2] * s[:2], (s**2 / np.sum(s**2))[:2], T, M, R


def _hctsa_features(path: Path, catch22: np.ndarray):
    """The usable part of an hctsa feature matrix (rows in the corpus order): operations with no NaN/Inf
    that are not constant. The row order is checked against catch22, whose features hctsa contains."""
    import io
    import h5py
    # one sequential read, then parse in memory: h5py's many small reads are very slow on cloud-synced folders
    with h5py.File(io.BytesIO(Path(path).read_bytes()), "r") as f:
        H = np.array(f["TS_DataMat"]).T
    H = H[:, np.isfinite(H).all(0) & (H.std(0) > 0)]
    rank = lambda A: np.argsort(np.argsort(A, 0), 0).astype(float)
    a, b = rank(catch22[:, :1]), rank(H)
    rho = np.abs(((a - a.mean(0)) / a.std(0)).T @ ((b - b.mean(0)) / b.std(0)) / len(a)).max()
    if rho < 0.99:
        raise ValueError(f"{path}: rows do not line up with the corpus (best catch22 match rho = {rho:.2f})")
    return H


def export_site(out: Path, site: Path, prof: str, hctsa: Path | None = None):
    set_profile(prof)
    load_all()
    reg = by_class(prof)
    cards = _load_cards(Path.cwd())
    dd = site / "data"
    (dd / "series").mkdir(parents=True, exist_ok=True)

    manifest = json.loads((out / "manifest.json").read_text())
    meta = pd.read_parquet(out / "metadata.parquet")
    meta["cls"] = meta["cls"].map(lambda c: CODE_CLASS.get(c, c))  # the site keys classes by letter internally
    z = np.load(out / "series.npz")
    X, ids = z["X"], [str(s) for s in z["ids"]]
    row = {s: k for k, s in enumerate(ids)}

    # --- per-series records
    recs = []
    all_params = {r.id: json.loads(r.params or "{}") for r in meta.itertuples(index=False)}
    # explicit equations for dysts systems (one symbolic evaluation per system; None keeps the generic card)
    from .equations import system_equations
    DYSTS = {"dysts-flow": "flow", "dysts-flow-coarse": "flow", "dysts-flow-extra": "flow", "dysts-map": "map"}
    eq_cache = {}
    from .variant_eqs import variant_equations

    def eqs_for(r):
        """{'lines': aligned LaTeX lines, 'params': {symbol: value}, 'note': str} or None."""
        p = all_params[r.id]
        kind, name = DYSTS.get(r.family), p.get("system")
        if r.cls in ("F", "G") and kind and name:
            if (name, kind) not in eq_cache:
                try:
                    eq_cache[(name, kind)] = system_equations(name, kind)
                except Exception:
                    eq_cache[(name, kind)] = None
            e = eq_cache[(name, kind)]
            if not e:
                return None
            obs = e["state"][p["coord"] % len(e["state"])] if isinstance(p.get("coord"), int) else None
            return dict(lines=[f"{l} &= {rr}" for l, rr in zip(e["lhs"], e["rhs"])], params=e["params"],
                        note=f"\\({obs}\\) observed." if obs else "")
        return variant_equations(f"{r.cls}.{r.family}", p)
    for r in meta.itertuples(index=False):
        x = X[row[r.id]]
        tags = {t: getattr(r, t) for t in TAG_NAMES if getattr(r, t) not in ("na", "none", "no")}
        nums = {k: _sig(getattr(r, k)) for k in NUMERIC_NAMES if pd.notna(getattr(r, k))}
        P = nums.get("period_samples") or dominant_period(x)
        # is there a clear spectral peak? share of (non-DC) power within +-2 bins of the largest peak
        F = np.abs(np.fft.rfft(x - x.mean())) ** 2
        F[0] = 0
        k = int(np.argmax(F))
        peak = bool(F.sum() > 0 and F[max(1, k - 2):k + 3].sum() / F.sum() > 0.25)
        peak = peak or tags.get("periodic") in ("yes", "partly") or tags.get("quasiperiodic") in ("yes", "partly")
        recs.append(dict(id=r.id, name=series_name(f"{r.cls}.{r.family}", all_params[r.id], all_params),
                         labels=series_labels(tags), eqs=eqs_for(r), cls=r.cls, family=r.family, index=int(r.index), seed_name=r.seed_name,
                         seed=str(r.seed), tags=tags, nums=nums, params=json.loads(r.params or "{}"),
                         period=_sig(P if math.isfinite(P) else 0.0, 3), peak=peak,
                         step=1 if _unit_step(r.cls, r.family, all_params[r.id], all_params) else None,
                         mean=_sig(float(x.mean())), sd=_sig(float(x.std()))))
    (dd / "meta.json").write_text(json.dumps(recs, separators=(",", ":")))

    # --- samples, one file per class
    for c in CLASSES:
        cid = [r["id"] for r in recs if r["cls"] == c]
        if not cid:
            continue
        rows = {i: [_sig(float(v)) for v in X[row[i]]] for i in cid}
        (dd / "series" / f"{c}.json").write_text(json.dumps(rows, separators=(",", ":")))

    # --- landing-page ticker: a few random series per class, full length, 3 significant figures
    rs = np.random.default_rng(1000)
    tick = []
    for c in CLASSES:
        cid = [r["id"] for r in recs if r["cls"] == c]
        tick += [str(i) for i in rs.choice(cid, min(7, len(cid)), replace=False)] if cid else []
    rs.shuffle(tick)
    (dd / "ticker.json").write_text(json.dumps({i: [_sig(float(v), 3) for v in X[row[i]]] for i in tick},
                                               separators=(",", ":")))

    # --- class mascots: site/icons/<letter>-<animal>.svg, embedded so pages can draw them in the class colour
    icons = {}
    for p in sorted((site / "icons").glob("?-*.svg")):
        icons[p.name[0]] = (p.stem.split("-", 1)[1], p.read_text().strip())

    # --- classes and families
    reg_idx = {f.name: f.indices(prof) for fams in reg.values() for f in fams}
    classes = []
    for c, fams in reg.items():
        if not fams:
            continue
        fl = []
        for f in fams:
            card = dict(cards.get(f.name) or {})
            card.setdefault("description", " ".join(f.doc.split()))
            fl.append(dict(key=f.key, name=f.name, label=FAMILY_NAMES.get(f.name, f.key), labels=series_labels(f.tags), n=f.quota(prof), tags=f.tags, card=card,
                           has_card=f.name in cards,
                           source=f"src/s1000/families/{f.gen.__module__.rsplit('.', 1)[-1]}.py"))
        # landing-page preview: the first 250 samples of three series from different families
        picks = [f"S1000_{class_label(c)}_{f['key']}_{int(reg_idx[f['name']][0]):03d}" for f in fl[:: max(1, len(fl) // 3)]][:3]
        preview = {i: [_sig(float(v), 3) for v in X[row[i]][:250]] for i in picks if i in row}
        mascot, icon = icons.get(c, ("", ""))
        classes.append(dict(code=c, short=CLASS_CODES[c], name=CLASS_NAMES[c], mascot=mascot, icon=icon, motto=MOTTOS.get(c, ""), title=CLASSES[c][0], blurb=ONE_LINERS.get(c, ""),
                            n=PROFILES[prof][c], families=fl, preview=preview))
    from .export import inp_name
    index = dict(corpus="1000×1000", profile=prof, release=RELEASE_NAMES.get(prof, prof), inp=inp_name(prof), T=manifest["T"], n=manifest["n"],
                 built=manifest["built"], versions=manifest["versions"], chip_tags=CHIP_TAGS,
                 numeric_names=NUMERIC_NAMES, classes=classes)
    (dd / "index.json").write_text(json.dumps(index, separators=(",", ":")))

    # --- embedding: full hctsa if a feature matrix exists (data/<profile>/hctsa/HCTSA_*.mat), else catch22
    cp = out / "catch24.npz"
    if not cp.exists() or cp.stat().st_mtime < (out / "series.npz").stat().st_mtime:
        # a stale cache silently misaligns the hctsa row check below: recompute when the series are newer
        import pycatch22
        np.savez_compressed(cp, F=np.array([pycatch22.catch22_all(list(r), catch24=True)["values"] for r in X], float),
                            ids=np.array(ids))
    fz = np.load(cp)
    # catch22, not catch24: catch24's mean and SD are in each generator's arbitrary units, not dynamics
    C, fids = fz["F"][:, :22], [str(s) for s in fz["ids"]]
    hp = hctsa or next(iter(sorted((out / "hctsa").glob("HCTSA_*.mat"))), None)
    if hp is not None:
        H = _hctsa_features(Path(hp), C)
        # all clean features, not PCA-50: 50 components keep 71% of the variance and blur the close end (only 79% of
        # 8-nearest neighbours matched the full space, 2026-09-26), which is what 'similar dynamics' shows
        P, ev, T, M, R = _embed(H, n_pc=None)
        feats, n_feats = "hctsa", H.shape[1]
    else:
        P, ev, T, M, R = _embed(C)
        feats, n_feats = "catch22", C.shape[1]
    pts = lambda M: {i: [_sig(a, 4), _sig(b, 4)] for i, (a, b) in zip(fids, M)}
    emb = dict(features=feats, n_features=int(n_feats), explained=[_sig(v, 3) for v in ev], pca=pts(P), tsne=pts(T), umap=pts(M))
    (dd / "embed.json").write_text(json.dumps(emb, separators=(",", ":")))

    # --- nearest neighbours in the same space as the t-SNE (the "similar dynamics" pane)
    sq = (R**2).sum(1)
    D = np.sqrt(np.maximum(sq[:, None] + sq[None, :] - 2 * R @ R.T, 0))
    np.fill_diagonal(D, np.inf)
    K = 8
    nn = np.argsort(D, 1)[:, :K]
    nbrs = dict(features=feats, k=K,
                nn={fids[i]: [[fids[j], _sig(float(D[i, j]), 3)] for j in nn[i]] for i in range(len(fids))})
    (dd / "neighbours.json").write_text(json.dumps(nbrs, separators=(",", ":")))

    # --- quiz look-alikes: each series' nearest series from other families (hard-mode distractors), as
    # [row index into ids, distance]; dysts families count as one (same systems, different sampling)
    by_id = {r["id"]: r for r in recs}
    grp = ["dysts" if by_id[i]["family"].startswith("dysts") else f'{by_id[i]["cls"]}.{by_id[i]["family"]}' for i in fids]
    look = []
    for i in range(len(fids)):
        row = []
        for j in np.argsort(D[i]):
            if grp[j] != grp[i]:
                row.append([int(j), _sig(float(D[i, j]), 3)])
                if len(row) == 16:
                    break
        look.append(row)
    quiz = dict(features=feats, ids=fids, median_nn=_sig(float(np.median(D.min(1))), 3), look=look)
    (dd / "quiz.json").write_text(json.dumps(quiz, separators=(",", ":")))

    size = sum(p.stat().st_size for p in dd.rglob("*.json"))
    n_cards = sum(f["has_card"] for c in classes for f in c["families"])
    n_fams = sum(len(c["families"]) for c in classes)
    print(f"wrote {dd}: {len(recs)} series, {n_fams} families ({n_cards} with cards), {size / 1e6:.1f} MB")
