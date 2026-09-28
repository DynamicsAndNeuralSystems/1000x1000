import numpy as np

from s1000 import T
from s1000.build import generate, sha
from s1000.registry import CLASSES, load_all, quota_check


def test_quotas_match_design():
    from s1000.registry import PROFILES
    load_all()
    for prof in PROFILES:
        for c, (decl, got) in quota_check(prof).items():
            assert decl == got, f"{prof} class {c}: {got} registered vs {decl} designed"
        assert sum(PROFILES[prof].values()) == 1000


def test_determinism_and_gates():
    fams = load_all()
    picks = ["A.gaussian", "B.ar2", "D.fgn", "E.garch", "F.logistic", "J.hawkes", "K.pinup", "N.rr-ipfm"]
    for name in picks:
        fam = fams[name]
        x1, m1, e1 = generate(fam, 0)
        x2, m2, e2 = generate(fam, 0)
        assert x1.shape == (T,)
        assert sha(x1) == sha(x2)
        assert np.all(np.isfinite(x1)) and x1.std() > 0
        assert m1["seed"] == m2["seed"] and m1["seed_name"].startswith("synthetic1000/")


def test_tvp_vector_present():
    fams = load_all()
    x, m, extras = generate(fams["K.pinup"], 3)
    assert "tvp" in extras and extras["tvp"].shape == (T,)
