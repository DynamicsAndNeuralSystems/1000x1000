"""Explicit equations for the named variants of non-dysts families, written from the generators' code.

``variant_equations(family, params)`` returns {'lines': [LaTeX lines with & alignment], 'params': {symbol: value},
'note': str} for one series, or None when the family card's equations already are the series' equations.
Constants are those in the code; drawn values come from the series' parameters.
"""
from __future__ import annotations

W = r"\,\xi(t)"  # white-noise forcing, written as dW/dt


def _p(params, **sym):
    """{latex symbol: value} for the drawn parameters present in params."""
    return {s: float(params[k]) for s, k in sym.items() if isinstance(params.get(k), (int, float))}


LORENZ = [r"\dot x &= 10\,(y - x)", r"\dot y &= x\,(28 - z) - y", r"\dot z &= x y - \tfrac{8}{3} z"]
CHUA = [r"\dot x &= 15.6\,\left(y - x - h(x)\right)", r"\dot y &= x - y + z", r"\dot z &= -28\, y",
        r"h(x) &= -\tfrac{5}{7} x - \tfrac{3}{14}\left(|x + 1| - |x - 1|\right)"]


def variant_equations(family: str, params: dict):
    k = params.get("kind") or params.get("system")
    f = family

    if f == "I.noisy-chaos":
        if k == "lorenz":
            L = [l + r" + 8\epsilon\,\xi_%s(t)" % v for l, v in zip(LORENZ, "xyz")]
            return dict(lines=L, params=_p(params, **{r"\epsilon": "noise"}), note="Lorenz flow with dynamical noise; x observed.")
        if k == "rossler":
            L = [r"\dot x &= -y - z + 5\epsilon\,\xi_x(t)", r"\dot y &= x + 0.2\, y + 5\epsilon\,\xi_y(t)", r"\dot z &= 0.2 + z\,(x - 5.7)"]
            return dict(lines=L, params=_p(params, **{r"\epsilon": "noise"}), note="Rössler flow with dynamical noise on x and y; x observed.")
        if k == "chua":
            L = [CHUA[0] + r" + 1.5\epsilon\,\xi_x(t)", CHUA[1] + r" + 1.5\epsilon\,\xi_y(t)", CHUA[2], CHUA[3]]
            return dict(lines=L, params=_p(params, **{r"\epsilon": "noise"}), note="Chua circuit with dynamical noise on x and y (ε capped at 0.06); x observed.")

    if f == "I.noisy-limit-cycle":
        if k == "vdp":
            return dict(lines=[r"\dot x &= y + \sigma\,\xi_x(t)", r"\dot y &= \mu\,(1 - x^2)\, y - x + \sigma\,\xi_y(t)"],
                        params=_p(params, **{r"\mu": "mu", r"\sigma": "sigma"}), note="van der Pol oscillator; x observed.")
        if k == "vdp-relaxation":
            return dict(lines=[r"\dot x &= \mu\left(x - x^3/3 - y\right) + \sigma\,\xi_x(t)", r"\dot y &= x/\mu + \sigma\,\xi_y(t)"],
                        params=_p(params, **{r"\mu": "mu", r"\sigma": "sigma"}), note="van der Pol oscillator in Liénard form (relaxation regime); x observed.")

    if f == "I.near-critical":
        kap = _p(params, **{r"\kappa": "kappa"})
        forms = {
            "pitchfork": ([r"\dot x &= \kappa\, x - x^3 + \xi(t)"], "x observed."),
            "hopf-radial": ([r"\dot r &= \kappa\, r - r^3 + \xi(t)"], "|r| observed (the amplitude of a Hopf normal form)."),
            "hopf-planar": ([r"\dot x &= \kappa\, x - (x^2 + y^2)\, x - \omega y + \xi_x(t)", r"\dot y &= \kappa\, y - (x^2 + y^2)\, y + \omega x + \xi_y(t)"], "x observed; ω drawn in [0.3, 1.5]."),
            "saddle-node": ([r"\dot x &= -\kappa - x^2 + 0.3\,\xi(t)"], "x observed (a soft wall at x = −2 stops escape past the fold)."),
            "transcritical": ([r"\dot x &= -\kappa\, x - x^2 + 0.3\,\xi(t)"], "x observed (soft walls keep x on the stable branch)."),
        }
        if k in forms:
            L, note = forms[k]
            return dict(lines=L, params=kap, note=note)

    if f == "E.stochastic-map":
        e = {r"\epsilon": "noise"}
        forms = {
            "logistic": ([r"x_{n+1} &= \mathrm{clip}_{[0,1]}\!\left(r\, x_n (1 - x_n) + 0.3\,\epsilon\, \eta_n\right)"], {r"r": "r"}),
            "tent": ([r"x_{n+1} &= \mathrm{clip}_{[0,1]}\!\left(\mu \min(x_n, 1 - x_n) + 0.3\,\epsilon\, \eta_n\right)"], {r"\mu": "mu"}),
            "henon": ([r"x_{n+1} &= 1 - a\, x_n^2 + y_n + 0.7\,\epsilon\, \eta_n", r"y_{n+1} &= 0.3\, x_n"], {r"a": "a"}),
            "ricker": ([r"x_{n+1} &= x_n \exp\!\left(r\,(1 - x_n) + \epsilon\, \eta_n\right)"], {r"r": "r"}),
            "holmes": ([r"x_{n+1} &= y_n + 0.3\,\epsilon\, \eta_n", r"y_{n+1} &= -0.2\, x_n + 2.7\, y_n - y_n^3 + 0.3\,\epsilon\, \eta'_n"], {}),
        }
        if k in forms:
            L, s = forms[k]
            return dict(lines=L, params=_p(params, **s, **e), note="x observed.")

    if f == "F.classic-1d":
        forms = {"tent": ([r"x_{n+1} &= \mu \min(x_n, 1 - x_n)"], {r"\mu": "mu"}),
                 "sine": ([r"x_{n+1} &= a \sin(\pi x_n)"], {"a": "a"}),
                 "cubic": ([r"x_{n+1} &= a\, x_n\,(1 - x_n^2)"], {"a": "a"}),
                 "chebyshev": ([r"x_{n+1} &= \cos\!\left(k \arccos x_n\right)"], {"k": "k"})}
        if k in forms:
            L, s = forms[k]
            return dict(lines=L, params=_p(params, **s), note="")

    if f == "F.map-sweep":
        forms = {
            "henon": ([r"x_{n+1} &= 1 - a\, x_n^2 + y_n", r"y_{n+1} &= 0.3\, x_n"], {"a": "a"}, "x observed."),
            "lozi": ([r"x_{n+1} &= 1 - a\, |x_n| + y_n", r"y_{n+1} &= 0.5\, x_n"], {"a": "a"}, "x observed."),
            "ikeda": ([r"z_{n+1} &= 1 + u\, z_n\, e^{i \vartheta_n}", r"\vartheta_n &= 0.4 - \frac{6}{1 + |z_n|^2}"], {"u": "u"}, "Re z observed."),
            "standard": ([r"p_{n+1} &= p_n + K \sin\theta_n \pmod{2\pi}", r"\theta_{n+1} &= \theta_n + p_{n+1} \pmod{2\pi}"], {"K": "K"}, "sin θ observed."),
            "cat": ([r"x_{n+1} &= 2 x_n + y_n \pmod 1", r"y_{n+1} &= x_n + y_n \pmod 1"], {}, "x observed."),
            "burgers": ([r"x_{n+1} &= 0.75\, x_n - y_n^2", r"y_{n+1} &= 1.75\, y_n + x_n y_n"], {}, "y observed."),
            "coupled-logistic": ([r"u_{n+1} &= (1 - c)\, f(u_n) + c\, f(v_n)", r"v_{n+1} &= (1 - c)\, f(v_n) + c\, f(u_n)", r"f(u) &= 3.9\, u (1 - u)"], {"c": "coupling"}, "u observed."),
        }
        if k in forms:
            L, s, note = forms[k]
            return dict(lines=L, params=_p(params, **s), note=note)

    if f == "G.canonical-sweep":
        forms = {
            "lorenz-rho24.5": ([r"\dot x &= 10\,(y - x)", r"\dot y &= x\,(24.5 - z) - y", r"\dot z &= x y - \tfrac{8}{3} z"], "x observed (ρ = 24.5: chaos coexists with stable fixed points)."),
            "lorenz-rho160": ([r"\dot x &= 10\,(y - x)", r"\dot y &= x\,(160 - z) - y", r"\dot z &= x y - \tfrac{8}{3} z"], "x observed."),
            "lorenz-rho130": ([r"\dot x &= 10\,(y - x)", r"\dot y &= x\,(130 - z) - y", r"\dot z &= x y - \tfrac{8}{3} z"], "x observed (ρ = 130: strongly chaotic, far above the classic ρ = 28)."),
            "rossler-funnel": ([r"\dot x &= -y - z", r"\dot y &= x + 0.3\, y", r"\dot z &= 0.1 + z\,(x - 14)"], "x observed (the screw-type funnel attractor)."),
            "chen": ([r"\dot x &= 35\,(y - x)", r"\dot y &= -7 x - x z + 28 y", r"\dot z &= x y - 3 z"], "x observed."),
            "rossler-c8.5": ([r"\dot x &= -y - z", r"\dot y &= x + 0.1\, y", r"\dot z &= 0.1 + z\,(x - 8.5)"], "z observed (the funnel's spikes)."),
            "chua": (CHUA, "x observed."),
            "duffing-forced": ([r"\ddot x &= x - x^3 - 0.3\, \dot x + 0.5 \cos(1.2\, t)"], "x observed."),
            "driven-pendulum": ([r"\ddot\theta &= -\sin\theta - 0.5\, \dot\theta + 1.2 \cos\!\left(\tfrac{2}{3} t\right)"], "sin θ observed (θ is unbounded when the pendulum rotates)."),
            "double-pendulum": ([r"\dot\theta_1 &= \frac{p_1 - p_2 \cos\Delta}{1 + \sin^2\Delta}, \quad \dot\theta_2 = \frac{2 p_2 - p_1 \cos\Delta}{1 + \sin^2\Delta}",
                                 r"\dot p_1 &= -2 \sin\theta_1 - \dot\theta_1 \dot\theta_2 \sin\Delta, \quad \dot p_2 = -\sin\theta_2 + \dot\theta_1 \dot\theta_2 \sin\Delta",
                                 r"\Delta &= \theta_1 - \theta_2"], "sin θ₁ observed (equal masses and lengths, g = 1)."),
            "lorenz84": ([r"\dot x &= -y^2 - z^2 - 0.25\, x + 0.25 \cdot 8", r"\dot y &= x y - 4 x z - y + 1", r"\dot z &= 4 x y + x z - z"], "x observed."),
        }
        if k in forms:
            L, note = forms[k]
            return dict(lines=L, params={}, note=note)

    if f == "G.dde-stationary":
        forms = {"mackey-glass": ([r"\dot x &= 0.2\, \frac{x(t - \tau)}{1 + x(t - \tau)^{10}} - 0.1\, x"], {r"\tau": "tau"}),
                 "ikeda-dde": ([r"\dot x &= -x + \mu \sin\!\left(x(t - 2)\right)"], {r"\mu": "mu"}),
                 "hutchinson": ([r"\dot x &= r\, x \left(1 - x(t - 1)\right)"], {"r": "r"}),
                 "ucar": ([r"\dot x &= x(t - \tau) - x(t - \tau)^3"], {r"\tau": "tau"}),
                 "bandpass-ikeda": ([r"0.01\, \dot x &= -x - \tfrac{1}{50}\, y + \beta \sin^2\!\left(x(t - 1) - \tfrac{\pi}{4}\right)", r"\dot y &= x"], {r"\beta": "beta"})}
        if k in forms:
            L, s = forms[k]
            return dict(lines=L, params=_p(params, **s), note="")

    if f == "H.limit-cycle":
        forms = {"vdp": ([r"\dot x &= y", r"\dot y &= \mu\,(1 - x^2)\, y - x"], {r"\mu": "mu"}, "van der Pol; x observed."),
                 "stuart-landau": ([r"\dot x &= (\mu - x^2 - y^2)\, x - y", r"\dot y &= (\mu - x^2 - y^2)\, y + x"], {r"\mu": "mu"}, "x observed."),
                 "brusselator": ([r"\dot x &= a + x^2 y - (b + 1)\, x", r"\dot y &= b\, x - x^2 y"], {"a": "a", "b": "b"}, "x observed."),
                 "fhn": ([r"\dot v &= v - v^3/3 - w + I", r"\dot w &= 0.08\,(v + 0.7 - 0.8\, w)"], {"I": "I"}, "FitzHugh–Nagumo (oscillatory); v observed.")}
        if k in forms:
            L, s, note = forms[k]
            return dict(lines=L, params=_p(params, **s), note=note)

    if f == "H.period-doubled-flows":
        if k == "rossler-p2":
            return dict(lines=[r"\dot x &= -y - z", r"\dot y &= x + 0.1\, y", r"\dot z &= 0.1 + z\,(x - 3.5)"], params={}, note="x observed (a period-1 orbit).")
        if k == "rossler-p4":
            return dict(lines=[r"\dot x &= -y - z", r"\dot y &= x + 0.1\, y", r"\dot z &= 0.1 + z\,(x - 8.5)"], params={}, note="z observed: a spike train whose heights repeat every four spikes (a period-4 orbit of the period-doubling cascade).")
        if k == "lorenz-periodic":
            return dict(lines=[r"\dot x &= 10\,(y - x)", r"\dot y &= x\,(350 - z) - y", r"\dot z &= x y - \tfrac{8}{3} z"], params={}, note="z observed (a periodic window).")

    if f == "H.cycle-shapes":
        forms = {"hr-bursting": ([r"\dot x &= y - x^3 + 3 x^2 - z + I", r"\dot y &= 1 - 5 x^2 - y", r"\dot z &= 0.006\,\left(4\,(x + 1.6) - z\right)"], {"I": "I"}, "Hindmarsh–Rose; x observed."),
                 "rayleigh": ([r"\dot x &= v", r"\dot v &= \mu\,(1 - v^2)\, v - x"], {r"\mu": "mu"}, "x observed."),
                 "lotka-volterra": ([r"\dot x &= x\,(1 - y)", r"\dot y &= y\,(x - 1)"], {"x_0": "x0"}, "x observed, started at (x₀, 1)."),
                 "pendulum-separatrix": ([r"\ddot\theta &= -\sin\theta"], {}, "θ observed; released from rest just below the separatrix energy.")}
        if k in forms:
            L, s, note = forms[k]
            return dict(lines=L, params=_p(params, **s), note=note)

    if f == "L.coupled-systems":
        eps = _p(params, **{r"\varepsilon": "coupling"})
        if k == "lorenz-rossler":
            return dict(lines=[r"\dot{\mathbf{u}}_L &= 0.15\, \mathbf{f}_{\text{Lorenz}}(\mathbf{u}_L)",
                               r"\dot x_R &= -y_R - z_R + \varepsilon\left(\tfrac{5}{8} x_L - x_R\right)",
                               r"\dot y_R &= x_R + 0.2\, y_R, \quad \dot z_R = 0.2 + z_R\,(x_R - 5.7)"], params=eps,
                        note=f"A time-rescaled Lorenz flow drives a Rössler flow; Rössler {params.get('observed', 'x')} observed.")
        if k == "rossler-rossler":
            return dict(lines=[r"\dot x_i &= -\omega_i y_i - z_i + \varepsilon\,(x_j - x_i)",
                               r"\dot y_i &= \omega_i x_i + 0.165\, y_i, \quad \dot z_i = 0.2 + z_i\,(x_i - 10)",
                               r"\omega_{1,2} &= 1 \pm 0.02"], params=eps,
                        note=f"Two diffusively coupled Rössler flows (i, j = 1, 2); second oscillator's {params.get('observed', 'x')} observed.")
        if k.startswith("cml-"):
            return dict(lines=[r"x_{n+1}(i) &= (1 - \varepsilon)\, f\big(x_n(i)\big) + \tfrac{\varepsilon}{2}\big[f\big(x_n(i-1)\big) + f\big(x_n(i+1)\big)\big]",
                               r"f(x) &= 1 - a x^2, \quad i = 1, \dots, 100 \text{ (periodic ring)}"],
                        params=_p(params, **{r"\varepsilon": "coupling", "a": "a"}),
                        note=("Kaneko coupled map lattice in its spatiotemporal-intermittency regime" if k == "cml-intermittency"
                              else "Kaneko coupled map lattice in its fully developed spatiotemporal-chaos regime") + "; one site observed.")
        if k == "delayed-master-slave":
            return dict(lines=[r"m_{n+1} &= r\, m_n (1 - m_n)", r"s_{n+1} &= (1 - \varepsilon)\, r\, s_n (1 - s_n) + \varepsilon\, m_n"],
                        params=_p(params, **{r"\varepsilon": "coupling", "r": "r"}), note="A logistic master drives a logistic slave; s observed.")
    return None
