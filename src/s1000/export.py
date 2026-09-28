"""Export in the Empirical1000 file set: an hctsa INP .mat, timeseries csvs,
and a generated family catalogue."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import T
from .registry import CLASSES, by_class, load_all

# hctsa input file per profile: stage 1 is published as "1000x1000"; the frozen full profile keeps its name
INP_NAMES = {"full": "INP_Synthetic1000.mat", "stationary1000": "INP_1000x1000.mat"}


def inp_name(prof: str) -> str:
    return INP_NAMES.get(prof, f"INP_{prof}.mat")


def to_hctsa_mat(X: np.ndarray, df: pd.DataFrame, path: Path):
    from scipy.io import savemat
    n = X.shape[0]
    ts = np.empty((n, 1), dtype=object)
    labels = np.empty((n, 1), dtype=object)
    keywords = np.empty((n, 1), dtype=object)
    for k in range(n):
        ts[k, 0] = X[k].reshape(-1, 1)
        labels[k, 0] = str(df["id"].iloc[k])
        keywords[k, 0] = str(df["keywords"].iloc[k])
    savemat(str(path), dict(timeSeriesData=ts, labels=labels, keywords=keywords), do_compression=True)


def to_csvs(X: np.ndarray, df: pd.DataFrame, out: Path):
    np.savetxt(out / "timeseries-data.csv", X, delimiter=",", fmt="%.10g")
    df[["id", "keywords"]].rename(columns={"id": "Name", "keywords": "Keywords"}).assign(Length=T) \
        .to_csv(out / "timeseries-info.csv", index=False)


def catalogue_md(df: pd.DataFrame | None = None) -> str:
    from .registry import PROFILES, profile
    load_all()
    prof = profile()
    lines = [f"# Synthetic1000 family catalogue — profile `{prof}`", "",
             "Generated from the registry; one row per family. Quotas are the profile's.", ""]
    for cls, fams in by_class().items():
        title, quota = CLASSES[cls][0], PROFILES[prof][cls]
        if not fams:
            continue
        lines += [f"## {cls}. {title} — {sum(f.quota() for f in fams)} of {quota}", "",
                  "| family | n | tags (yes) | description |", "|---|---|---|---|"]
        for f in fams:
            yes = ", ".join(k for k, v in f.tags.items() if v == "yes")
            doc = " ".join(f.doc.split())
            lines.append(f"| `{f.key}` | {f.quota()} | {yes} | {doc} |")
        lines.append("")
    return "\n".join(lines)


def export_all(data: Path):
    import json
    from .registry import set_profile
    set_profile(json.loads((data / "manifest.json").read_text()).get("profile", "full"))
    z = np.load(data / "series.npz")
    X = z["X"]
    df = pd.read_parquet(data / "metadata.parquet")
    prof = json.loads((data / "manifest.json").read_text()).get("profile", "full")
    to_hctsa_mat(X, df, data / inp_name(prof))
    to_csvs(X, df, data)
    (data / "catalogue.md").write_text(catalogue_md(df))


def subset(src: Path, out: Path, where: list[str], name: str = "Synthetic1000-subset") -> int:
    """Filter a built corpus by tag values (``stationary=yes``, ``cls=A,B,G``) and write the same
    file set (series.npz, metadata, csvs, hctsa .mat) for the subset. The manifest of the source
    corpus still applies: every series keeps its id and seed."""
    import json
    z = np.load(src / "series.npz")
    X, ids = z["X"], z["ids"]
    df = pd.read_parquet(src / "metadata.parquet")
    keep = np.ones(len(df), dtype=bool)
    for w in where:
        key, val = w.split("=", 1)
        keep &= df[key].astype(str).isin(val.split(",")).values
    out.mkdir(parents=True, exist_ok=True)
    Xs, ds = X[keep], df[keep].reset_index(drop=True)
    np.savez_compressed(out / "series.npz", X=Xs, ids=ids[keep])
    ds.to_parquet(out / "metadata.parquet", index=False)
    ds.to_csv(out / "metadata.csv", index=False)
    to_hctsa_mat(Xs, ds, out / f"INP_{name}.mat")
    to_csvs(Xs, ds, out)
    man = json.loads((src / "manifest.json").read_text())
    man.update(subset_of=str(src), where=where, n=int(keep.sum()),
               hashes={k: v for k, v in man["hashes"].items() if k in set(ids[keep])})
    (out / "manifest.json").write_text(json.dumps(man, indent=1))
    return int(keep.sum())
