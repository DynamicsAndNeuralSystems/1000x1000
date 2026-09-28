"""Time-reversibility audit (on ranks within each segment): regenerate each series at TL = 20000 samples with its own seed stream (same
parameters), split into 20 segments of 1000, and for each segment compute asymmetry statistics that vanish in
expectation for any time-reversible process (whatever its marginal):
  trev(x, L)   = E[(x_{t+L}-x_t)^3] / E[(x_{t+L}-x_t)^2]^1.5
  trev(x^2, L) (catches sign-symmetric irreversibility, e.g. GARCH)
  bic(x, L)    = E[x_t^2 x_{t+L} - x_t x_{t+L}^2]   (x standardised)
Across segments: mean and t = mean / (sd / sqrt(20)). A series is flagged irreversible when some statistic has
|t| > 6 and |mean| > 0.05."""
import json, sys, signal, multiprocessing as mp
import numpy as np
ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
TL, NSEG, LAGS = 20000, 20, (1, 2, 4, 8, 16)

def stats(x):
    # ranks (a monotone transform keeps reversibility) give bounded, robust moments for heavy tails
    u = (np.argsort(np.argsort(x + 1e-12 * np.random.default_rng(0).standard_normal(x.size))) + .5) / x.size
    x = (u - .5) / np.sqrt(1 / 12)
    y = (u - .5) ** 2; y = (y - y.mean()) / (y.std() + 1e-300)
    out = {}
    for L in LAGS:
        for nm, z in (("trev_x", x), ("trev_x2", y)):
            d = z[L:] - z[:-L]; out[f"{nm}@{L}"] = np.mean(d ** 3) / (np.mean(d ** 2) ** 1.5 + 1e-300)
        out[f"bic@{L}"] = np.mean(x[:-L] ** 2 * x[L:] - x[:-L] * x[L:] ** 2)
    return out

def one(args):
    sid, cls, key, i, attempt, manual = args
    from s1000.registry import load_all, set_profile
    from s1000.rng import rng_for
    from s1000.util import Strat
    set_profile("stationary1000")
    fam = {(f.cls, f.key): f for f in load_all().values()}[(cls, key)]
    base = (cls, key, i) if manual == 0 else (cls, key, i, "manual", manual)
    parts = base if attempt == 0 else (*base, "retry", attempt)
    rng = rng_for(*parts)
    S = Strat(fam.name, i, fam.strat_n(), rng)
    signal.alarm(240)
    try:
        x, _ = fam.gen(i, rng, TL, S)
        x = np.asarray(x, float).ravel()
        if x.size < TL or not np.all(np.isfinite(x)):
            return sid, {"error": f"length {x.size} or non-finite"}
        seg = [stats(x[k * 1000:(k + 1) * 1000]) for k in range(NSEG)]
        res = {}
        for s in seg[0]:
            v = np.array([g[s] for g in seg]); m, sd = v.mean(), v.std(ddof=1)
            res[s] = (float(m), float(m / (sd / np.sqrt(NSEG) + 1e-12)))
        return sid, res
    except Exception as e:
        return sid, {"error": f"{type(e).__name__}: {e}"[:200]}
    finally:
        signal.alarm(0)

if __name__ == "__main__":
    import pandas as pd, os
    d = pd.read_csv(ROOT / "data" / "stationary1000" / "metadata.csv")
    out_path = sys.argv[1]
    done = set()
    if os.path.exists(out_path):
        done = {json.loads(l)["id"] for l in open(out_path)}
    jobs = [(r.id, r.cls, r.family, int(r["index"]), int(r.attempt), int(r.manual if r.manual == r.manual else 0))
            for _, r in d.iterrows() if r.id not in done]
    print("to do", len(jobs), flush=True)
    pending = {j[0] for j in jobs}
    with mp.Pool(10, maxtasksperchild=10) as p, open(out_path, "a") as fh:
        it = p.imap_unordered(one, jobs)
        while pending:
            try:
                sid, res = it.next(timeout=400)
            except (mp.TimeoutError, StopIteration):
                break
            pending.discard(sid)
            fh.write(json.dumps({"id": sid, "res": res}) + "\n"); fh.flush()
        p.terminate()
    print("done; unfinished:", sorted(pending), flush=True)
