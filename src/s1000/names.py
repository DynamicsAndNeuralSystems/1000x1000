"""Human-readable series names and property labels for the web resource.

``series_name`` says what a series' process is called, from its family and, where an instance draws a
named variant (a dysts system, a GARCH type, a neuron model), that variant. No parameter values.
``series_labels`` picks up to three property labels from the series' tags.
"""
from __future__ import annotations

import re

from .registry import CLASS_CODES

FAMILY = {
    "A.gaussian": "Gaussian white noise", "A.uniform": "Uniform white noise", "A.laplace": "Laplace white noise",
    "A.student-t": "Student-t white noise", "A.skewed": "Skewed white noise", "A.bimodal": "Bimodal white noise",
    "A.exponential-pareto": "Exponential white noise", "A.heavy-finite": "Heavy-tailed white noise",
    "B.ar1": "AR(1) process", "B.ar2": "AR(2) process", "B.arp": "High-order AR process", "B.maq": "Moving-average process",
    "B.arma": "ARMA process", "B.seasonal-arma": "Seasonal AR process", "B.narrowband": "Narrowband noise",
    "B.lowhigh-pass": "Filtered noise", "B.random-spectrum": "Random-spectrum Gaussian process",
    "C.ar-skew": "AR with skewed innovations", "C.arma-heavy": "AR with heavy-tailed innovations",
    "C.ma-asym-skew": "Asymmetric skewed MA", "C.levy-ou": "Lévy-driven OU process", "C.ar-bounded": "AR with bounded innovations",
    "C.shot-noise": "Shot noise",
    "D.fgn": "Fractional Gaussian noise", "D.arfima": "ARFIMA process", "D.mrw": "Multifractal random walk",
    "D.discrete-cascade": "Multiplicative cascade", "D.lmsv": "Long-memory stochastic volatility",
    "D.one-over-f-stationary": "1/f noise",
    "E.setar": "Threshold AR (SETAR)", "E.expar": "Exponential AR", "E.bilinear": "Bilinear process",
    "E.random-coef-ar": "Random-coefficient AR", "E.garch": "GARCH returns", "E.stoch-vol": "Stochastic volatility",
    "E.markov-switching-ar": "Markov-switching AR", "E.hmm": "Hidden Markov model", "E.stochastic-map": "Noisy chaotic map",
    "E.star": "Smooth-transition AR", "E.volterra": "Volterra series", "E.bistable-map": "Noisy double-well map",
    "E.cubic-crisis": "Noisy cubic map near crisis", "E.kesten": "Kesten multiplicative process",
    "F.logistic": "Logistic map", "F.classic-1d": "Chaotic 1-D map", "F.circle-map": "Circle map",
    "F.pomeau-manneville": "Pomeau–Manneville map", "F.shift-gauss": "Shift map", "F.piecewise-impact": "Impact map",
    "F.dysts-map": "Chaotic map", "F.map-sweep": "2-D chaotic map", "F.aperiodic-real": "Rule-30 cellular automaton",
    "F.rulkov": "Rulkov map neuron", "F.sna": "Strange nonchaotic attractor",
    "G.dysts-flow": "Chaotic flows (dysts)", "G.canonical-sweep": "Canonical flow regimes", "G.dde-stationary": "Delay-differential equation",
    "G.dysts-flow-coarse": "Coarsely sampled chaotic flows", "G.dysts-flow-extra": "Chaotic flows, second realisation", "G.blinking-rotlet": "Blinking rotlet",
    "G.billiard": "Stadium billiard", "G.bouncing-ball": "Bouncing ball",
    "H.sinusoid": "Sinusoid", "H.harmonic": "Harmonic waveform", "H.quasiperiodic": "Quasi-periodic torus",
    "H.limit-cycle": "Limit-cycle oscillator", "H.modulated-stationary": "Modulated oscillation",
    "H.period-doubled-flows": "Periodic orbits of chaotic flows", "H.cycle-shapes": "Unusual cycle shapes",
    "I.ou": "Ornstein–Uhlenbeck process", "I.double-well": "Double-well Langevin", "I.near-critical": "Noisy normal form",
    "I.noisy-limit-cycle": "Noisy limit cycle", "I.noisy-chaos": "Noisy chaotic flow",
    "I.stochastic-resonance": "Stochastic resonance", "I.excitable-fhn": "Noise-driven excitable system",
    "I.multiplicative-coloured": "Multiplicative-noise Langevin", "I.heteroclinic": "Noisy heteroclinic cycle",
    "J.renewal": "Renewal process", "J.hawkes": "Hawkes process", "J.spike-signs": "Signed spike train",
    "J.compound-poisson-increments": "Compound Poisson increments", "J.poisson-smoothed": "Smoothed Poisson rate",
    "J.cox-smoothed": "Smoothed Cox-process rate", "J.markov-chain-emitted": "Markov chain with noisy levels",
    "J.telegraph-noisy": "Noisy telegraph signal",
    "L.longlag-comb": "Long-lag dependence", "L.cyclostationary-switch": "Cyclostationary switching",
    "L.replay-recurrence": "Replayed recurrences", "L.pac": "Phase–amplitude coupling", "L.qpc": "Quadratic phase coupling",
    "L.coupled-systems": "Coupled chaotic systems", "L.mixture": "Mixture of processes", "L.on-off": "On-off intermittency",
    "N.predator-prey-ssa": "Stochastic predator–prey", "N.blowflies-ricker": "Population dynamics",
    "N.sir-seir": "Stochastic epidemic", "N.rainfall-pulse": "Bartlett–Lewis rainfall", "N.stick-slip": "Earthquake stick-slip",
    "N.etas": "ETAS earthquake sequence", "N.barnes-sunspot": "Barnes sunspot model", "N.climate-model": "Stochastic climate model",
    "N.turbulence": "Turbulent velocity", "N.richardson-weather-stationary": "Richardson weather generator",
    "N.river-discharge-stationary": "River discharge", "N.onoff-traffic": "ON/OFF network traffic", "N.speech": "Synthetic speech",
    "N.bearing-vibration": "Bearing-fault vibration", "N.collective": "Collective dynamics", "N.laser-feedback": "Laser with feedback",
    "N.oregonator": "Oregonator (BZ reaction)", "N.kirman": "Kirman herding model", "N.rr-ipfm": "Heartbeat intervals",
    "N.rr-ectopic": "Heartbeat intervals with ectopy", "N.rr-af": "Atrial fibrillation intervals", "N.deboer": "Baroreflex model",
    "N.ecgsyn": "Synthetic ECG", "N.periodic-breathing": "Periodic breathing", "N.neural-mass": "Neural-mass EEG",
    "N.neuron": "Neuron model", "N.glucose-insulin": "Glucose–insulin dynamics", "N.circadian-hormone": "Circadian and hormonal rhythm",
    "N.gene-cell": "Cellular oscillator", "N.gait-emg-tremor": "Movement physiology",
}

# Named variants, by the value of an instance's string parameter (kind / system / kernel / ...).
VARIANT = {
    "lognormal": "Log-normal white noise", "chisq": "Chi-square white noise", "gamma": "Gamma white noise",
    "pareto": "Pareto white noise", "student": "Student-t white noise", "scale-mixture": "Gaussian scale-mixture noise",
    "low": "Low-pass filtered noise", "high": "High-pass filtered noise",
    "alpha": "Shot noise (alpha pulses)", "exponential": "Shot noise (exponential pulses)", "gaussian": "Shot noise (Gaussian pulses)",
    "mrw-lognormal": "Multifractal random walk", "mrw-student": "Multifractal random walk (Student-t)",
    "binomial-cascade": "Binomial cascade", "log-poisson": "Log-Poisson cascade",
    "garch": "GARCH(1,1)", "gjr": "GJR-GARCH", "arch": "ARCH(1)", "egarch": "EGARCH",
    "gauss2": "Two-state hidden Markov model", "cyclic3": "Cyclic hidden Markov model",
    "tent": "Tent map", "logistic": "Logistic map", "ricker": "Ricker map", "henon": "Hénon map",
    "estar": "Exponential STAR", "lstar": "Logistic STAR", "sin": "Sine nonlinear AR", "tanh": "Tanh nonlinear AR",
    "sine": "Sine map", "cubic": "Cubic map", "chebyshev": "Chebyshev map", "doubling": "Doubling map", "gauss": "Gauss map",
    "lozi": "Lozi map", "ikeda": "Ikeda map", "standard": "Chirikov standard map", "cat": "Arnold's cat map",
    "burgers": "Burgers map", "coupled-logistic": "Coupled logistic maps",
    "lorenz-rho24.5": "Lorenz system", "lorenz-rho160": "Lorenz system", "lorenz-rho130": "Lorenz system", "rossler-funnel": "Rössler funnel", "chen": "Chen system", "rossler-c8.5": "Rössler funnel",
    "chua": "Chua circuit", "duffing-forced": "Forced Duffing oscillator", "driven-pendulum": "Driven pendulum",
    "double-pendulum": "Double pendulum", "lorenz84": "Lorenz-84 system",
    "mackey-glass": "Mackey–Glass equation", "ikeda-dde": "Ikeda delay equation", "hutchinson": "Hutchinson delayed logistic", "fhn": "Excitable FitzHugh–Nagumo", "active-rotator": "Active rotator (type-I excitable)", "insulin-resistant": "Glucose–insulin dynamics, insulin-resistant", "asymmetric": "Noisy heteroclinic cycle, asymmetric", "ucar": "Uçar delay equation", "bandpass-ikeda": "Band-pass Ikeda oscillator",
    "random": "Random harmonic waveform", "triangle": "Triangle wave", "sawtooth": "Sawtooth wave",
    "vdp": "Van der Pol oscillator", "vdp-relaxation": "Van der Pol relaxation oscillator", "brusselator": "Brusselator",
    "fhn": "FitzHugh–Nagumo oscillator", "am": "Amplitude modulation", "fm": "Frequency modulation", "beats": "Beats",
    "rossler-p2": "Rössler period-2 orbit", "rossler-p4": "Rössler period-4 orbit", "lorenz-periodic": "Lorenz periodic orbit",
    "hr-bursting": "Hindmarsh–Rose bursting", "rayleigh": "Rayleigh oscillator", "lotka-volterra": "Lotka–Volterra cycle",
    "pendulum-separatrix": "Pendulum near its separatrix",
    "hopf-radial": "Noisy Hopf (amplitude)", "hopf-planar": "Noisy Hopf", "transcritical": "Noisy transcritical",
    "pitchfork": "Noisy pitchfork", "saddle-node": "Noisy saddle-node",
    "lorenz": "Noisy Lorenz", "rossler": "Noisy Rössler", "multiplicative": "Multiplicative-noise Langevin",
    "ou-driven": "Coloured-noise relaxation",
    "weibull": "Renewal process (Weibull)", "exp": "Hawkes process (exponential kernel)", "powerlaw": "Hawkes process (power-law kernel)",
    "cyclic": "Cyclic Markov chain with noisy levels", "linear": "Long-lag linear dependence", "quadratic": "Long-lag nonlinear dependence",
    "theta-gamma-narrow": "Theta–gamma coupling", "theta-gamma-broad": "Theta–gamma coupling", "delta-beta": "Delta–beta coupling", "slow-spindle": "Slow-oscillation–spindle coupling",
    "alpha-gamma": "Alpha–gamma coupling", "lorenz-rossler": "Lorenz driving Rössler", "rossler-rossler": "Coupled Rössler pair",
    "delayed-master-slave": "Delayed master–slave pair", "cml-intermittency": "Coupled map lattice: spatiotemporal intermittency", "cml-turbulence": "Coupled map lattice: spatiotemporal chaos", "lorenz+ar": "Lorenz plus AR noise", "lorenz-floor": "Lorenz under a noise floor",
    "rossler+seasonal": "Rössler plus seasonal AR", "ar+telegraph": "AR plus telegraph signal",
    "rosenzweig-macarthur": "Rosenzweig–MacArthur predator–prey", "nicholson": "Nicholson's blowflies", "ricker-env": "Ricker map with environmental noise",
    "sir": "Stochastic SIR epidemic", "seir": "Stochastic SEIR epidemic", "time-predictable": "Earthquake stick-slip (time-predictable)",
    "slip-predictable": "Earthquake stick-slip (slip-predictable)", "hasselmann": "Hasselmann climate model", "enso": "ENSO delayed oscillator",
    "stommel": "Stommel thermohaline model", "daisyworld": "Daisyworld", "sabra-shell": "Sabra shell-model turbulence",
    "burgers-point": "Burgers turbulence", "kuramoto": "Kuramoto synchronisation", "ising": "Ising magnetisation",
    "jansen-rit": "Jansen–Rit neural mass", "wilson-cowan": "Wilson–Cowan populations", "epileptor": "Epileptor seizures",
    "hh-V": "Hodgkin–Huxley neuron", "hh-irregular": "Hodgkin–Huxley neuron near threshold", "epileptor-interictal": "Epileptor, interictal spiking", "rule110-density": "Rule-110 cellular automaton", "rule30-density": "Rule-30 cellular automaton", "holmes": "Noisy Holmes (Duffing) map", "izh-TC": "Izhikevich thalamo-cortical neuron", "izh-RS": "Izhikevich regular spiking", "izh-CH": "Izhikevich chattering",
    "morris-lecar": "Morris–Lecar neuron", "hr-V": "Hindmarsh–Rose neuron", "kronauer-forger": "Kronauer circadian pacemaker",
    "kronauer-forger-melatonin": "Circadian melatonin rhythm", "keenan-veldhuis": "Pulsatile hormone secretion",
    "telegraph-ssa-protein": "Bursty gene expression", "goldbeter": "Calcium oscillations", "gait": "Stride intervals",
    "emg": "Surface EMG", "tremor": "Physiological tremor",
}
# Family-specific names where a variant value means different things in different families.
OVERRIDE = {
    "A.exponential-pareto": {"exponential": "Exponential white noise", "pareto": "Pareto white noise"},
    "C.arma-heavy": {"student": "AR with Student-t innovations"},
    "I.excitable-fhn": {"fhn": "Excitable FitzHugh–Nagumo"},
    "J.renewal": {"gamma": "Renewal process (gamma)", "pareto": "Renewal process (Pareto)",
                  "lognormal": "Renewal process (log-normal)", "weibull": "Renewal process (Weibull)"},
    "J.markov-chain-emitted": {"random": "Markov chain with noisy levels"},
    "E.stochastic-map": {"tent": "Noisy tent map", "logistic": "Noisy logistic map", "ricker": "Noisy Ricker map",
                         "henon": "Noisy Hénon map"},
    "I.noisy-chaos": {"chua": "Noisy Chua circuit"},
    "I.noisy-limit-cycle": {"vdp": "Noisy van der Pol oscillator", "vdp-relaxation": "Noisy van der Pol relaxation oscillator"},
    "N.predator-prey-ssa": {"lotka-volterra": "Stochastic Lotka–Volterra"},
}
VARIANT_KEYS = ("kind", "system", "kernel", "innovation", "readout")
# dysts system names that need more than splitting CamelCase
DYSTS = {
    "Rossler": "Rössler system", "Henon": "Hénon map", "Chua": "Chua circuit", "Laser": "Laser model", "Finance": "Finance model",
    "Hopfield": "Hopfield network", "Hadley": "Hadley circulation", "Torus": "Torus flow", "Tsucs2": "TSUCS2 system",
    "Bouali2": "Bouali system 2", "YuWang2": "Yu–Wang system 2", "BeerRNN": "Beer RNN", "HyperLu": "Hyperchaotic Lü system",
    "CaTwoPlus": "Calcium oscillator", "CaTwoPlusQuasiperiodic": "Quasi-periodic calcium oscillator",
    "ArnoldBeltramiChildress": "Arnold–Beltrami–Childress flow", "AnishchenkoAstakhov": "Anishchenko–Astakhov oscillator",
    "BelousovZhabotinsky": "Belousov–Zhabotinsky reaction", "BurkeShaw": "Burke–Shaw system", "ChenLee": "Chen–Lee system",
    "DequanLi": "Dequan Li system", "ForcedFitzHughNagumo": "Forced FitzHugh–Nagumo", "ForcedVanDerPol": "Forced van der Pol",
    "GenesioTesi": "Genesio–Tesi system", "GuckenheimerHolmes": "Guckenheimer–Holmes system", "HastingsPowell": "Hastings–Powell food chain",
    "HenonHeiles": "Hénon–Heiles system", "HindmarshRose": "Hindmarsh–Rose neuron", "ItikBanksTumor": "Itik–Banks tumour model",
    "KawczynskiStrizhak": "Kawczynski–Strizhak reaction", "LiuChen": "Liu–Chen system", "LorenzStenflo": "Lorenz–Stenflo system",
    "Lorenz84": "Lorenz-84 system", "Lorenz96": "Lorenz-96 system", "LorenzBounded": "Bounded Lorenz system",
    "LorenzCoupled": "Coupled Lorenz system", "LuChen": "Lü–Chen system", "LuChenCheng": "Lü–Chen–Cheng system",
    "MacArthur": "MacArthur consumer–resource model", "MooreSpiegel": "Moore–Spiegel oscillator", "MultiChua": "Multi-scroll Chua circuit",
    "NewtonLiepnik": "Newton–Leipnik system", "NoseHoover": "Nosé–Hoover oscillator", "PanXuZhou": "Pan–Xu–Zhou system",
    "PehlivanWei": "Pehlivan–Wei system", "QiChen": "Qi–Chen system", "RabinovichFabrikant": "Rabinovich–Fabrikant system",
    "RayleighBenard": "Rayleigh–Bénard convection", "RikitakeDynamo": "Rikitake dynamo", "SaltonSea": "Salton Sea ecosystem",
    "SanUmSrisuchinwong": "San-Um–Srisuchinwong system", "ShimizuMorioka": "Shimizu–Morioka system", "SprottJerk": "Sprott jerk system",
    "SprottMore": "Sprott–More system", "SprottTorus": "Sprott torus", "TurchinHanski": "Turchin–Hanski vole model",
    "VallisElNino": "Vallis El Niño model", "WangSun": "Wang–Sun system", "WindmiReduced": "WINDMI magnetosphere model",
    "YuWang": "Yu–Wang system", "ZhouChen": "Zhou–Chen system", "ArnoldWeb": "Arnold web", "AtmosphericRegime": "Atmospheric regime model",
    "BickleyJet": "Bickley jet", "BlinkingRotlet": "Blinking rotlet", "BlinkingVortex": "Blinking vortex",
    "CellularNeuralNetwork": "Cellular neural network", "CircadianRhythm": "Circadian rhythm", "CoevolvingPredatorPrey": "Coevolving predator–prey",
    "DoubleGyre": "Double gyre", "DoublePendulum": "Double pendulum", "ExcitableCell": "Excitable cell", "FluidTrampoline": "Fluid trampoline",
    "ForcedBrusselator": "Forced Brusselator", "GlycolyticOscillation": "Glycolytic oscillation", "InteriorSquirmer": "Interior squirmer",
    "IsothermalChemical": "Isothermal chemical reaction", "JerkCircuit": "Jerk circuit", "LidDrivenCavityFlow": "Lid-driven cavity flow",
    "NuclearQuadrupole": "Nuclear quadrupole", "OscillatingFlow": "Oscillating flow", "StickSlipOscillator": "Stick-slip oscillator",
    "SwingingAtwood": "Swinging Atwood machine", "ThomasLabyrinth": "Thomas labyrinth",
    # maps
    "Baker": "Baker's map", "BlinkingVortexMap": "Blinking vortex map", "Chirikov": "Chirikov standard map", "DeJong": "De Jong map",
    "KaplanYorke": "Kaplan–Yorke map", "MaynardSmith": "Maynard Smith map",
}
OBSERVATION = {"clipped": "clipped", "missing-data": "with gaps", "irregular-sampling": "irregularly sampled",
               "aliased": "aliased", "oversampled": "oversampled", "nonlinear-readout": "through a nonlinear readout",
               "outliers": "with outliers", "heavy-noise": "in heavy noise", "downsampled": "downsampled"}


def _dysts(s: str, noun: str) -> str:
    if s in DYSTS:
        return DYSTS[s]
    m = re.fullmatch(r"(Sprott|Hyper)([A-Z]\w*)", s)
    if m and m.group(1) == "Sprott":
        return f"Sprott {m.group(2)}"
    if m:
        return f"Hyperchaotic {re.sub(r'(?<=[a-z])(?=[A-Z])', '–', m.group(2))} system"
    return f"{s} {noun}"


def series_name(family: str, params: dict, all_params: dict | None = None) -> str:
    """``family`` is class.key; ``all_params`` maps series id -> params (to name an observed base series)."""
    cls = family.split(".")[0]
    if cls == "M":
        obs = OBSERVATION.get(params.get("observation", ""), "observed")
        if "base_id" in params and all_params and params["base_id"] in all_params:
            bid = params["base_id"]
            c = bid.split('_')[1]
            c = {v: k for k, v in CLASS_CODES.items()}.get(c, c)  # IDs carry the class code (FLOW) in stationary1000
            base = series_name(f"{c}.{bid.split('_')[2]}", all_params[bid])
        elif "base_family" in params:
            base = FAMILY.get(params["base_family"], params["base_family"])
        elif "system" in params:
            base = {"lorenz": "Lorenz system", "rossler": "Rössler system"}.get(params["system"], params["system"])
        else:
            base = "Base process"
        return f"{base}, {obs}"
    if family in ("G.dysts-flow", "G.dysts-flow-coarse", "G.dysts-flow-extra", "F.dysts-map") and "system" in params:
        return _dysts(params["system"], "map" if family == "F.dysts-map" else "system")
    for k in VARIANT_KEYS:
        v = params.get(k)
        if isinstance(v, str):
            if v in OVERRIDE.get(family, {}):
                return OVERRIDE[family][v]
            if v in VARIANT:
                return VARIANT[v]
    return FAMILY.get(family, family)


LABEL_ORDER = ("chaotic", "quasiperiodic", "periodic", "long_memory", "regime_switching", "bursty", "heavy_tailed",
               "event_like", "heteroskedastic", "skewed", "continuous_time", "gaussian", "linear", "deterministic")
LABEL_TEXT = {"long_memory": "long memory", "regime_switching": "regime switching", "heavy_tailed": "heavy-tailed",
              "event_like": "event-like", "continuous_time": "continuous time", "heteroskedastic": "volatility clustering",
              "quasiperiodic": "quasi-periodic", "gaussian": "Gaussian"}


def series_labels(tags: dict, k: int = 3) -> list[str]:
    """Up to ``k`` property labels: an applied domain first, then the most distinctive 'yes' tags."""
    out = []
    if tags.get("domain") not in (None, "abstract"):
        out.append(tags["domain"])
    for t in LABEL_ORDER:
        if len(out) >= k:
            break
        if tags.get(t) == "yes":
            out.append(LABEL_TEXT.get(t, t))
    return out
