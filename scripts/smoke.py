"""Generate one or all instances of every family in the given classes, reporting failures and timing."""
import sys, time, traceback
import numpy as np
from s1000.registry import load_all, by_class
from s1000.build import generate

classes = sys.argv[1] if len(sys.argv) > 1 else "ABCDEFGHIJKLMN"
full = "--full" in sys.argv
load_all()
fails = []
for cls, fams in by_class().items():
    if cls not in classes:
        continue
    for fam in fams:
        idx = range(fam.n) if full else sorted({0, fam.n // 2, fam.n - 1})
        t0 = time.time()
        bad = 0
        for i in idx:
            try:
                x, m, ex = generate(fam, i)
                if m["attempt"]:
                    print(f"    {fam.name}[{i}] needed attempt {m['attempt']}", flush=True)
            except Exception as e:
                bad += 1
                fails.append((fam.name, i, repr(e)[:200]))
        print(f"{fam.name:34s} {len(idx):3d} inst  {time.time()-t0:7.1f}s  {'FAIL x%d' % bad if bad else 'ok'}", flush=True)
for f in fails:
    print("FAIL", *f)
