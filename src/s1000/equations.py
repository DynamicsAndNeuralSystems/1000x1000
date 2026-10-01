"""Explicit equations for dysts systems, for the web resource.

Each dysts system defines its right-hand side (flows) or update (maps) as a small Python function. Calling
that function with SymPy symbols in place of numbers gives the system's equations exactly as integrated,
which are rendered as LaTeX. Systems whose code is not symbolic-friendly (vectorised or with branches on
the state) return None and keep the family card's generic form.
"""
from __future__ import annotations

import inspect
import types


def _shim(np, sp):
    """A stand-in for numpy inside a dysts module: elementary functions map to SymPy."""
    table = dict(sin=sp.sin, cos=sp.cos, tan=sp.tan, tanh=sp.tanh, sinh=sp.sinh, cosh=sp.cosh, exp=sp.exp,
                 log=sp.log, sqrt=sp.sqrt, abs=sp.Abs, sign=sp.sign, arctan=sp.atan, arcsin=sp.asin,
                 arccos=sp.acos, power=sp.Pow, pi=sp.pi, maximum=sp.Max, minimum=sp.Min, e=sp.E,
                 heaviside=lambda x, *_: sp.Heaviside(x))
    mod = types.SimpleNamespace(**table)

    def __getattr__(name):  # anything else is not symbolic-friendly
        raise AttributeError(name)
    mod.__getattr__ = __getattr__
    return mod


# dysts names some variables and parameters with several letters (lam, px, pth, ...), which LaTeX would
# typeset as a product of single-letter symbols: give them their usual notation instead
TEX_NAMES = {"eps": r"\varepsilon", "lam": r"\lambda", "lamb": r"\lambda", "th": r"\theta",
             "px": "p_x", "py": "p_y", "pr": "p_r", "pth": r"p_\theta", "tx": r"\tau_x", "tz": r"\tau_z",
             "vs": "v_s", "vsw": r"v_{\mathrm{sw}}", "zs": "z_s", "curr": "I"}


def _sym(sp, name: str):
    """A SymPy symbol for a dysts variable or parameter, printed in conventional notation."""
    import re
    tex = TEX_NAMES.get(name)
    if tex is None and re.fullmatch(r"[A-Za-z]{2,}", sp.latex(sp.Symbol(name))):
        tex = r"\mathrm{%s}" % name  # any other multi-letter name reads as one symbol, upright
    return sp.Symbol(tex or name)


def system_equations(name: str, kind: str = "flow"):
    """{'lhs': [...], 'rhs': [...], 'params': {name: value}} as LaTeX strings, or None."""
    import numpy as np
    import sympy as sp
    import dysts.flows as FL
    import dysts.maps as MP
    module = FL if kind == "flow" else MP
    cls = getattr(module, name, None)
    if cls is None or not hasattr(cls, "_rhs"):
        return None
    fn = getattr(cls._rhs, "py_func", cls._rhs)
    try:
        inst = cls()
        pnames = list(inst.params)
    except Exception:
        return None
    try:  # vector-style systems implement rhs(X, t) instead of _rhs(x, y, ..., params)
        fn(*([0.0] * len(inspect.signature(fn).parameters)))
    except NotImplementedError:
        return _vector_system(module, inst, kind, np, sp)
    except Exception:
        pass
    args = list(inspect.signature(fn).parameters)
    state = [a for a in args if a not in pnames and a != "t"]
    if not state or len(state) > 12:
        return None
    S = {a: _sym(sp, a) for a in state}
    P = {p: _sym(sp, p) for p in pnames}
    call = [S[a] if a in S else (sp.Symbol("t") if a == "t" else P[a]) for a in args]
    saved = module.np
    module.np = _shim(np, sp)
    try:
        out = fn(*call)
    except Exception:
        return None
    finally:
        module.np = saved
    out = list(out) if isinstance(out, (tuple, list)) else [out]
    if len(out) != len(state):
        return None
    lat = lambda e: sp.latex(e, mul_symbol=" ") if isinstance(e, sp.Basic) else str(e)
    if kind == "flow":
        lhs = [r"\dot{%s}" % sp.latex(S[a]) for a in state]
    else:
        lhs = [r"%s_{n+1}" % sp.latex(S[a]) for a in state]
    rhs = [lat(e) for e in out]
    if any(len(r) > 400 for r in rhs):
        return None
    params = {sp.latex(P[p]): float(v) for p, v in inst.params.items() if isinstance(v, (int, float))}
    return dict(lhs=lhs, rhs=rhs, state=[sp.latex(S[a]) for a in state], params=params)


def _vector_system(module, inst, kind, np, sp):
    """Systems written as rhs(X, t) with X a state vector: pass a list of symbols x_1..x_d."""
    d = len(np.atleast_1d(inst.ic))
    if d > 8:
        return None
    X = [sp.Symbol(f"x_{i + 1}") for i in range(d)]
    saved = module.np
    module.np = _shim(np, sp)
    try:
        out = inst.rhs(X, sp.Symbol("t")) if kind == "flow" else inst.rhs(X)
        out = list(out)
    except Exception:
        return None
    finally:
        module.np = saved
    if len(out) != d or not all(isinstance(e, sp.Basic) for e in out):
        return None
    # parameters are attributes on the instance: show them symbolically where SymPy kept them as numbers
    lhs = [(r"\dot{%s}" if kind == "flow" else r"%s_{n+1}") % sp.latex(x) for x in X]
    rhs = [sp.latex(e, mul_symbol=" ") for e in out]
    if any(len(r) > 400 for r in rhs):
        return None
    return dict(lhs=lhs, rhs=rhs, state=[sp.latex(x) for x in X], params={})
