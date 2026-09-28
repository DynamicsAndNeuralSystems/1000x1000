"""Build the interactive keep/fix/drop review page for a built corpus + review notes.
usage: review_page.py DATA NOTES.csv OUT.html [--full COLLECTION TAG]
With --full every series is up for decision (default view: all) and choices go to db collection COLLECTION.
Each series is embedded min-max scaled to uint8 (base64), which is exact at plot resolution."""
import base64, json, sys
from pathlib import Path
import numpy as np, pandas as pd

data, notes_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
full = "--full" in sys.argv
collection, tag = (sys.argv[sys.argv.index("--full") + 1:sys.argv.index("--full") + 3]) if full else ("decisions", "")
z = np.load(data / "series.npz"); X, ids = z["X"], list(z["ids"])
m = pd.read_parquet(data / "metadata.parquet").set_index("id")
notes = pd.read_csv(notes_path)
man = json.loads((data / "manifest.json").read_text())

KEEP_IDS = {"S1000_E_stoch-vol_005", "S1000_G_dysts-flow_010", "S1000_C_levy-ou_003", "S1000_J_renewal_007"}
def suggest(sid, cats, texts):
    if full: return None
    if sid in KEEP_IDS: return "keep"
    if set(cats) <= {"banded"}: return "keep"
    if "discrete" in cats and any("point mass" in t for t in texts): return "keep"
    if any("redundant with H.sinusoid" in t or "similar clean limit cycles" in t for t in texts): return "drop"
    return "fix"

order = m.loc[ids].sort_values(["cls", "family", "index"], kind="stable").index
rows = []
for sid in order:
    x = X[ids.index(sid)].astype(float)
    lo, hi = x.min(), x.max()
    u = np.round(255 * (x - lo) / (hi - lo if hi > lo else 1)).astype(np.uint8)
    p = json.loads(m.loc[sid, "params"])
    kind = str(p.get("system") or p.get("kind") or p.get("observation") or "")
    nt = notes[notes.id == sid]
    cats, texts = list(nt.category), list(nt.note)
    rows.append(dict(id=sid, c=m.loc[sid, "cls"], f=m.loc[sid, "family"], i=int(m.loc[sid, "index"]), k=kind,
                     n=[[a, b] for a, b in zip(cats, texts)], s=suggest(sid, cats, texts) if cats else None,
                     x=base64.b64encode(u.tobytes()).decode()))
payload = dict(version=man.get("built", ""), profile=man.get("profile", ""), rows=rows, fullPass=full, collection=collection, tag=tag)
tpl = (Path(__file__).parent / "review_page_template.html").read_text()
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(tpl.replace("__DATA__", json.dumps(payload, separators=(",", ":"))))
print(f"{len(rows)} series, {sum(1 for r in rows if r['n'])} flagged -> {out} ({out.stat().st_size/1e6:.1f} MB)")
