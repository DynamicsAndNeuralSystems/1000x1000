"""Generate the corpus (or any part of it) from names alone."""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
import time
from pathlib import Path

import numpy as np

from . import CORPUS, T
from .qc import gate, real_valued_gate, stationarity_gate
from .registry import CLASS_CODES, DEFAULT_TAGS, NUMERIC_NAMES, PROFILES, TAG_NAMES, Family, load_all, profile, set_profile
from .rng import name_of, rng_for, seed_of
from .util import Strat

MAX_ATTEMPTS = 8


def class_label(cls: str) -> str:
    """How a class appears in series IDs, the `cls` column and keywords: its three-letter code in stationary1000
    (e.g. FLOW), its letter in the frozen full profile. Seed streams always use the letter, so relabelling never
    changes a series."""
    return CLASS_CODES[cls] if profile() == "stationary1000" else cls


def series_id(fam: Family, i: int) -> str:
    return f"S1000_{class_label(fam.cls)}_{fam.key}_{i:03d}"


def family_source_sha(fam: Family) -> str:
    """Hash of the generator's source: a refresh regenerates a family when this changes.
    (Changes to shared helpers in util.py are not detected: rebuild fully after those.)"""
    return hashlib.sha256(inspect.getsource(fam.gen).encode()).hexdigest()[:16]


def generate(fam: Family, i: int, manual: int = 0):
    """(x, meta, extras) for instance i of a family. ``extras`` holds any
    per-series vectors (the PINUP row's time-varying parameter). ``manual`` > 0 selects the
    n-th manually requested redraw (a reviewer flagged the series): its own named stream."""
    last_reason = None
    for attempt in range(MAX_ATTEMPTS):
        base = (fam.cls, fam.key, i) if manual == 0 else (fam.cls, fam.key, i, "manual", manual)
        parts = base if attempt == 0 else (*base, "retry", attempt)
        rng = rng_for(*parts)
        S = Strat(fam.name, i, fam.strat_n(), rng)
        try:
            x, info = fam.gen(i, rng, T, S)
        except Exception as e:  # a generator that blew up is a failed attempt, not a crash
            last_reason = f"exception: {type(e).__name__}: {e}"
            continue
        x = np.asarray(x, dtype=float).ravel()
        if x.size != T:
            last_reason = f"length {x.size} != {T}"
            continue
        info = dict(info or {})
        tags = dict(DEFAULT_TAGS)
        tags.update(fam.tags)
        tags.update({k: info.pop(k) for k in list(info) if k in TAG_NAMES})
        numerics = {k: float(info.pop(k)) for k in list(info) if k in NUMERIC_NAMES}
        extras = {k: np.asarray(info.pop(k), dtype=float) for k in list(info)
                  if isinstance(info[k], np.ndarray) and info[k].size == T}
        if profile() == "stationary1000":  # time-reversibility set from theory per family (reversibility.py)
            from .reversibility import time_reversible
            tags["reversible"] = time_reversible(fam, tags, info)
        reason = gate(x, tags)
        if reason is None and profile() == "stationary1000":
            reason = real_valued_gate(x, tags, fam.cls) or (stationarity_gate(x, tags, fam.cls) if tags.get("stationary") != "no" else None)
        if reason is None:
            meta = dict(id=series_id(fam, i), cls=class_label(fam.cls), family=fam.key, index=i,
                        seed_name=name_of(CORPUS, *parts), seed=str(seed_of(CORPUS, *parts)),
                        attempt=attempt, manual=manual, **tags, **{k: numerics.get(k, np.nan) for k in NUMERIC_NAMES},
                        params=json.dumps(_jsonable(info), sort_keys=True),
                        keywords=_keywords(fam, tags))
            return x, meta, extras
        last_reason = reason
    raise RuntimeError(f"{series_id(fam, i)}: no valid series in {MAX_ATTEMPTS} attempts ({last_reason})")


def _keywords(fam: Family, tags: dict) -> str:
    kw = [f"class-{class_label(fam.cls)}", fam.key, tags["domain"]]
    kw += [k for k in TAG_NAMES if tags.get(k) == "yes"]
    if tags.get("nonstationary_kind") not in (None, "none"):
        kw.append(f"nonstat-{tags['nonstationary_kind']}")
    return ",".join(kw)


def _jsonable(d):
    out = {}
    for k, v in d.items():
        if isinstance(v, np.ndarray):
            out[k] = v.tolist() if v.size <= 64 else f"<array {v.shape}>"
        elif isinstance(v, (np.floating, np.integer)):
            out[k] = v.item()
        elif isinstance(v, dict):
            out[k] = _jsonable(v)
        else:
            out[k] = v
    return out


def sha(x: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(x, dtype=np.float64).tobytes()).hexdigest()


def _int0(v) -> int:
    """int(v) with NaN/None (older metadata without the column) as 0."""
    try:
        return 0 if v is None or v != v else int(v)
    except (TypeError, ValueError):
        return 0


def _gates_pass(x: np.ndarray, tags: dict, cls: str = "") -> str | None:
    reason = gate(x, tags)
    if reason is None and profile() == "stationary1000":
        reason = real_valued_gate(x, tags, cls) or (stationarity_gate(x, tags, cls) if tags.get("stationary") != "no" else None)
    return reason


def _load_existing(out: Path):
    """Existing corpus in ``out`` as {id: (x, meta_row, extras)} plus its manifest, or None."""
    if not (out / "manifest.json").exists() or not (out / "series.npz").exists():
        return None, None
    import pandas as pd
    man = json.loads((out / "manifest.json").read_text())
    z = np.load(out / "series.npz")
    df = pd.read_parquet(out / "metadata.parquet")
    ex = {}
    for k in ("tvp",):
        if (out / f"{k}.npz").exists():
            zz = np.load(out / f"{k}.npz")
            ex[k] = {sid: zz[sid] for sid in zz.files}
    rows = {}
    for x, (_, m) in zip(z["X"], df.iterrows()):
        m = m.to_dict()
        rows[m["id"]] = (x, m, {k: v[m["id"]] for k, v in ex.items() if m["id"] in v})
    return rows, man


def _manual_flags(out: Path) -> dict:
    """{id: action} from out/manual_flags.csv (columns id, action[, note]); action in {retry, drop}."""
    p = out / "manual_flags.csv"
    if not p.exists():
        return {}
    import pandas as pd
    df = pd.read_csv(p)
    return {str(r.id): str(r.action).strip() for r in df.itertuples() if str(r.action).strip() in ("retry", "drop")}


def build(out: Path, classes: list[str] | None = None, families: list[str] | None = None,
          verbose: bool = True, keep_going: bool = False, prof: str = "full", refresh: bool = False,
          force: list[str] | None = None):
    """``keep_going`` collects generator failures instead of stopping at the first, writes whatever
    succeeded, and lists the failures (for iterating on generators; a release build must not use it).
    ``refresh`` updates an existing corpus in ``out``: families whose generator source or quota changed
    are regenerated; every other stored series is re-checked against the current gates and only the
    failing instances (and any flagged ``retry`` in manual_flags.csv) are regenerated."""
    failures = []
    set_profile(prof)
    fams = load_all()
    selected = [f for f in sorted(fams.values(), key=lambda f: f.order) if f.quota(prof) > 0
                and (classes is None or f.cls in classes) and (families is None or f.name in families)]
    old, old_man = _load_existing(out) if refresh else (None, None)
    old_fams = (old_man or {}).get("families", {})
    old_manual = (old_man or {}).get("manual", {})
    flags = _manual_flags(out) if refresh else {}
    manual_counter = dict(old_manual)
    X, meta, extras, hashes = [], [], {}, {}
    t_start = time.time()
    n_reused = n_regen = 0
    for fam in selected:
        t0 = time.time()
        src = family_source_sha(fam)
        if old is None:
            fam_changed = True
        elif fam.name in old_fams:
            of = old_fams[fam.name]
            old_strat = of.get("strat_n", of.get("n"))
            fam_changed = of.get("source") != src or old_strat != fam.strat_n(prof)
            # dropping instances (same strat_n) keeps the survivors: only new indices are generated
        else:  # manifest predates source hashes: trust the stored series unless forced
            fam_changed = not all(series_id(fam, i) in old for i in fam.indices(prof))
        if force and fam.name in force:
            fam_changed = True
        if refresh and fam.cls == "M":
            fam_changed = True  # observation effects depend on base series from other families: always regenerate
        for i in fam.indices(prof):
            sid = series_id(fam, i)
            manual = int(manual_counter.get(sid, 0))
            if flags.get(sid) == "retry":  # a reviewer asked for a fresh draw of this series
                manual += 1
                manual_counter[sid] = manual
            reuse = None
            if not fam_changed and sid in old and flags.get(sid) != "retry":
                x0, m0, ex0 = old[sid]
                tags0 = {k: m0[k] for k in TAG_NAMES}
                if _gates_pass(x0, tags0, fam.cls) is None and _int0(m0.get("manual", 0)) == manual:
                    reuse = (x0, m0, ex0)
            if reuse is not None:
                x, m, ex = reuse
                n_reused += 1
            else:
                try:
                    x, m, ex = generate(fam, i, manual=manual)
                    n_regen += 1
                except Exception as e:
                    if not keep_going:
                        raise
                    failures.append(f"{fam.name}[{i}]: {e}")
                    continue
            X.append(x)
            meta.append(m)
            hashes[m["id"]] = sha(x)
            for k, v in ex.items():
                extras.setdefault(k, {})[m["id"]] = v
        if verbose:
            print(f"  {fam.name:32s} n={fam.quota(prof):3d}  {time.time() - t0:6.1f}s{'  (changed)' if fam_changed and refresh else ''}",
                  file=sys.stderr, flush=True)
    if verbose and refresh:
        print(f"refresh: {n_reused} series reused, {n_regen} regenerated", file=sys.stderr)
    if flags and not failures:  # retries are applied once: archive the request so a later refresh doesn't redraw again
        fp = out / "manual_flags.csv"
        fp.rename(out / f"manual_flags_applied_{time.strftime('%Y%m%d-%H%M%S')}.csv")
        fp.write_text("id,action,note\n")
    X = np.stack(X)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "series.npz", X=X, ids=np.array([m["id"] for m in meta]))
    import pandas as pd
    df = pd.DataFrame(meta)
    df.to_parquet(out / "metadata.parquet", index=False)
    df.to_csv(out / "metadata.csv", index=False)
    for k, d in extras.items():
        np.savez_compressed(out / f"{k}.npz", **d)
    (out / "manifest.json").write_text(json.dumps(dict(
        corpus=CORPUS, profile=prof, T=T, n=int(X.shape[0]), built=time.strftime("%Y-%m-%d %H:%M:%S"),
        versions=_versions(),
        families={f.name: dict(n=f.quota(prof), strat_n=f.strat_n(prof), indices=f.indices(prof),
                               source=family_source_sha(f)) for f in selected},
        manual={k: v for k, v in manual_counter.items() if v},
        hashes=hashes), indent=1))
    if verbose:
        print(f"built {X.shape[0]} series in {time.time() - t_start:.0f}s -> {out}", file=sys.stderr)
        for f in failures:
            print("FAILED", f, file=sys.stderr)
    return X, df


def _versions() -> dict:
    import platform
    import numpy, scipy
    v = dict(python=platform.python_version(), numpy=numpy.__version__, scipy=scipy.__version__,
             platform=platform.platform())
    try:
        import dysts
        v["dysts"] = getattr(dysts, "__version__", "unknown")
    except ImportError:
        pass
    return v


def _clear_trajectory_cache(sid: str, meta_row: dict | None):
    """Delete the cached trajectories of a dysts-based series so it regenerates cold."""
    import glob, os
    if meta_row is None:
        return 0
    try:
        sysname = json.loads(meta_row.get("params", "{}")).get("system")
    except Exception:
        sysname = None
    if not sysname:
        return 0
    from .sources import CACHE
    n = 0
    for f in glob.glob(str(CACHE / f"{sysname}_*_s1000*.npz")):
        os.remove(f)
        n += 1
    return n


def verify(out: Path, fraction: float = 0.05, seed: int = 0, cold: bool = False) -> list[str]:
    """Regenerate a random subset and compare hashes against the manifest. ``cold`` first deletes
    the cached dysts trajectories of the sampled series, so the integration itself is exercised
    (a warm cache can mask a stale or non-reproducible trajectory). Returns the ids that differ."""
    man = json.loads((out / "manifest.json").read_text())
    set_profile(man.get("profile", "full"))
    fams = load_all()
    ids = sorted(man["hashes"])
    pick = np.random.default_rng(seed).choice(len(ids), max(1, int(fraction * len(ids))), replace=False)
    by_id = {series_id(f, i): (f, i) for f in fams.values() for i in f.indices()}
    meta_by_id = {}
    if cold:
        import pandas as pd
        df = pd.read_parquet(out / "metadata.parquet")
        meta_by_id = {r["id"]: r for r in df.to_dict("records")}
    bad = []
    for j in pick:
        sid = ids[j]
        fam, i = by_id[sid]
        if cold:
            _clear_trajectory_cache(sid, meta_by_id.get(sid))
        x, _, _ = generate(fam, i, manual=int(man.get("manual", {}).get(sid, 0)))
        if sha(x) != man["hashes"][sid]:
            bad.append(sid)
    return bad
