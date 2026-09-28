"""``s1000 build|manifest|verify|export``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="s1000")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="generate series + metadata into --out")
    b.add_argument("--out", default=None, type=Path, help="default data/<profile>")
    b.add_argument("--class", dest="classes", nargs="*", help="restrict to these classes (A..N)")
    b.add_argument("--family", dest="families", nargs="*", help="restrict to these families (e.g. K.pinup)")
    b.add_argument("--export", action="store_true", help="also write the hctsa .mat / csv / catalogue")
    b.add_argument("--keep-going", action="store_true", help="collect generator failures instead of stopping (development only)")
    b.add_argument("--profile", default="full", help="quota profile: full | stationary1000 (alias 1000x1000)")
    b.add_argument("--force", nargs="*", help="with --refresh: families to regenerate regardless (e.g. A.student-t)")
    b.add_argument("--refresh", action="store_true", help="update the existing corpus in --out: regenerate only changed families, gate failures and manual_flags.csv retries")
    m = sub.add_parser("manifest", help="print the quota table and registered families")
    m.add_argument("--profile", default="full")
    v = sub.add_parser("verify", help="regenerate a random subset and compare hashes")
    v.add_argument("--out", default=None, type=Path, help="built corpus; default data/<profile> with --profile, else data")
    v.add_argument("--profile", default=None, help="stationary1000 (alias 1000x1000) | full")
    v.add_argument("--fraction", type=float, default=0.05)
    v.add_argument("--cold", action="store_true", help="clear the sampled series' cached dysts trajectories first (exercises the integration)")
    e = sub.add_parser("export", help="write the hctsa INP_*.mat (INP_1000x1000.mat for stationary1000), csvs and catalogue.md from --out")
    e.add_argument("--out", default="data", type=Path)
    s_ = sub.add_parser("subset", help="write a filtered copy of a built corpus, e.g. --where stationary=yes")
    s_.add_argument("--src", default="data", type=Path)
    s_.add_argument("--out", required=True, type=Path)
    s_.add_argument("--where", nargs="+", required=True, help="tag=value filters (all must hold); value may be a comma list")
    s_.add_argument("--name", default="Synthetic1000-subset", help="name used in the .mat filename")
    w = sub.add_parser("site", help="export a built corpus as the web resource's data files (site/data/)")
    w.add_argument("--profile", default="stationary1000", help="stationary1000 (alias 1000x1000) | full")
    w.add_argument("--out", default=None, type=Path, help="built corpus; default data/<profile>")
    w.add_argument("--site", default="site", type=Path)
    w.add_argument("--hctsa", default=None, type=Path, help="HCTSA .mat for the map and neighbours; default <out>/hctsa/HCTSA_*.mat if present, else catch22")
    a = ap.parse_args(argv)
    from .registry import canonical_profile
    if getattr(a, "profile", None):
        a.profile = canonical_profile(a.profile)

    if a.cmd == "site":
        from .site import export_site
        export_site(a.out or Path("data") / a.profile, a.site, a.profile, a.hctsa)
        return 0

    if a.cmd == "manifest":
        from .registry import CLASSES, by_class, load_all, quota_check, set_profile
        set_profile(a.profile)
        load_all()
        reg = by_class()
        total_decl = total_reg = 0
        print(f"profile: {a.profile}")
        for c, (decl, got) in quota_check().items():
            flag = "" if decl == got else f"   <-- {got - decl:+d}"
            print(f"{c}  {CLASSES[c][0]:50s} {got:4d} / {decl:4d}{flag}")
            for f in reg[c]:
                print(f"     {f.key:28s} {f.quota():3d}")
            total_decl += decl
            total_reg += got
        print(f"total {total_reg} / {total_decl}")
        return 0
    if a.cmd == "build":
        from .build import build
        a.out = a.out or Path("data") / a.profile
        build(a.out, classes=a.classes, families=a.families, keep_going=a.keep_going, prof=a.profile, refresh=a.refresh, force=a.force)
        if a.export:
            from .export import export_all
            export_all(a.out)
        return 0
    if a.cmd == "verify":
        from .build import verify
        bad = verify(a.out or (Path("data") / a.profile if a.profile else Path("data")), a.fraction, cold=a.cold)
        print("all regenerated series match the manifest" if not bad else f"MISMATCH: {bad}")
        return 0 if not bad else 1
    if a.cmd == "export":
        from .export import export_all
        export_all(a.out)
        return 0
    if a.cmd == "subset":
        from .export import subset
        n = subset(a.src, a.out, a.where, a.name)
        print(f"wrote {n} series to {a.out}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
