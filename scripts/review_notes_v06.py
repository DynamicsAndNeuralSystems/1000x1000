"""Claude's review of stationary1000 v0.6 (2026-09-25), as machine-readable notes:
data/stationary1000/review_notes.csv with columns id, category, note (one row per note)."""
import json
from pathlib import Path
import pandas as pd

D = Path("data/stationary1000")
m = pd.read_csv(D / "metadata.csv")
scr = pd.read_csv(D / "screen.csv").set_index("id")
kind = {r.id: (json.loads(r.params).get("kind") or json.loads(r.params).get("system") or "") for r in m.itertuples()}
notes = []


def add(ids, cat, note):
    for i in ids:
        sid = i if i.startswith("S1000_") else f"S1000_{i}"
        assert sid in kind, sid
        notes.append((sid, cat, note))


def rng(prefix, idx):
    return [f"{prefix}_{k:03d}" for k in idx]


# 1 too slow
add(rng("I_ou", [5, 7, 11, 12, 13, 15]), "slow", "slow wander (tau up to 20 samples)")
add(rng("I_near-critical", [1, 3, 5, 9, 11, 15, 17]), "slow", "wanders: sampling rule puts relaxation time at ~25 samples")
add(rng("I_double-well", [3, 5, 9, 12, 13, 16]), "slow", "too few hops per record")
lorenz_chua = [i for i in m.id if "I_noisy-chaos" in i and kind[i] in ("lorenz", "chua")]
rossler = [i for i in m.id if "I_noisy-chaos" in i and kind[i] == "rossler"]
add(lorenz_chua, "slow", "slow lobe switching")
add(lorenz_chua + rossler, "other", "doesn't look noisy: dynamical noise mostly perturbs timing, not visible jitter")
add(rng("I_stochastic-resonance", [2, 4, 5]), "slow", "slow hopping")
add(rng("I_multiplicative-coloured", [1, 3]), "slow", "OU-driven: tau 15-20")
add(rng("I_excitable-fhn", range(8)), "duplicate", "all 8 near-identical regular spiking; candidate to squeeze")
add(rng("E_bistable-map", range(5)), "slow", "slow hopping (tau 13-28)")
add(rng("E_hmm", [1, 2, 4]), "slow", "long regime dwells")
add(rng("E_star", [2, 11]), "slow", "sin-AR hops slowly")
add(rng("C_ar-skew", [1, 8]) + ["C_arma-heavy_006"], "slow", "AR root near 1: slow drift")
add(rng("C_shot-noise", [0, 3, 5, 6, 7]), "slow", "still sparse / long flat stretches (flagged twice before)")
add(rng("J_hawkes", range(9)), "slow", "slow bumps, long zero stretches")
add(rng("J_cox-smoothed", [0, 1, 2, 3, 5]), "slow", "slow, spiky, long zero stretches")
add(rng("J_poisson-smoothed", [0, 4, 5]), "slow", "long zero stretches")
add(["J_markov-chain-emitted_001"], "nonstationary", "6-state cyclic chain, long dwells: staircase")
add(["B_random-spectrum_001"], "slow", "tau 33: slow wander")
add(["G_dysts-flow_026"], "slow", "DequanLi still slow: coarse re-integration fails, falls back (flagged twice)")
add(["G_dysts-flow_113"], "slow", "StickSlipOscillator: near-sinusoid, can't be sped up (integration fails)")
add(rng("M_oversampled", range(3)), "slow", "slow by construction (7-17 cycles): contradicts 'faster' rule")
add(rng("N_sir-seir", range(6)), "slow", "~10-15 epidemics, long troughs")
add(rng("N_sir-seir", range(6)), "onset", "first epidemic larger: needs longer burn-in")
add(["N_barnes-sunspot_000"], "slow", "~7 cycles in the record")
add(rng("N_gene-cell", range(4)), "slow", "telegraph-protein: tau 23-33")
add(rng("N_turbulence", [0, 1]), "slow", "Sabra quiet-then-burst / Burgers tau 28")
add(["N_climate-model_000"], "slow", "Hasselmann tau 17")
add(rng("N_river-discharge-stationary", range(3)), "slow", "baseflow memory: tau 8-19")
add(["N_collective_002"], "slow", "Ising near T_c: tau 32")
add(rng("N_predator-prey-ssa", range(3)), "slow", "slow cycles (002 has flat stretches)")
add(["N_neuron_000"], "slow", "only ~13 spikes")
add(rng("N_neuron", [4, 8]), "slow", "Hindmarsh-Rose: long silences")
add(rng("N_glucose-insulin", range(3)), "slow", "~15 meals per record")
add(["H_sinusoid_000"], "slow", "~3 cycles")
add(["H_harmonic_004"], "slow", "sawtooth period ~70")
# 2 non-stationary looking
add(rng("B_narrowband", [1, 3, 6]) + ["B_arp_000"], "nonstationary", "high-Q envelope swells over the record")
add(rng("H_modulated-stationary", [2, 3, 5]), "nonstationary", "only ~2-4 beats/modulation cycles per record")
add(["D_fgn_003"] + rng("D_arfima", [0, 10, 11]) + rng("D_one-over-f-stationary", [5, 7]) + rng("N_gait-emg-tremor", [0, 1]),
    "nonstationary", "long memory at high end (H->0.9, d->0.4, beta->0.95) drifts to the eye")
add(rng("D_discrete-cascade", [0, 1, 2]) + rng("D_mrw", [6, 7, 8, 11]), "nonstationary",
    "volatility bursts on quiet floor: integral scale >= record")
add(["G_dysts-flow_105"], "nonstationary", "SprottMore: low-amplitude episodes (10-window variance ratio 34)")
add(["G_dysts-flow_037"], "nonstationary", "GuckenheimerHolmes: quiet stretches (variance ratio 119)")
add(["G_dysts-flow_048"], "nonstationary", "HyperLu: amplitude changes over record")
add(["G_dysts-flow_050"], "nonstationary", "HyperQi: rare large spikes")
add(rng("F_pomeau-manneville", [3, 6]), "nonstationary", "long flat laminar phases (as your earlier 001 flag)")
add(["E_garch_015"], "spiky", "ARCH with t(3.35) innovations: one dominant spike")
add(["E_stoch-vol_005"], "nonstationary", "corner of prior (you said probably OK)")
add(rng("N_rainfall-pulse", [2, 4]), "nonstationary", "storms cluster in part of the record")
# 3 onset
add(["N_neuron_005"], "onset", "hh-V drifts at start")
add(["G_dysts-flow_010", "C_levy-ou_003", "J_renewal_007"], "onset", "flagged at onset (milder, possibly chance)")
# 4 periodic / near-sinusoidal
add(rng("F_circle-map", [2, 3, 4, 8]), "periodic", "quasi-periodic: looks like drifting sinusoid")
add(rng("F_map-sweep", [8, 9]), "periodic", "standard map K=0.97 (KAM regime): regular")
add(["F_dysts-map_003"], "periodic", "Bogdanov: near-periodic")
add(rng("G_dysts-flow", [5, 36, 3, 99, 100, 117]) + ["G_canonical-sweep_003", "G_dysts-flow-extra_002"], "periodic",
    "near-sinusoid (ac at period 0.95-0.97, under the 0.97 check)")
add(rng("G_dde-stationary", [2, 13]), "periodic", "periodic regime, not tagged periodic so escapes gate")
add(rng("L_coupled-systems", [2, 3, 4, 7]), "periodic", "phase-coherent slave Rossler: near-sinusoid")
add(rng("N_circadian-hormone", [0, 1]), "periodic", "locked to 24h: periodic (and duplicates)")
add(rng("N_gene-cell", [4, 5]), "periodic", "Goldbeter limit cycle")
add(["N_climate-model_001"], "periodic", "ENSO in periodic regime")
add(rng("N_blowflies-ricker", [0, 1]), "periodic", "Nicholson limit cycle (duplicates)")
add(rng("N_periodic-breathing", [1, 2]), "periodic", "periodic, near-duplicates")
for i in m.id[m.family == "limit-cycle"]:
    if kind[i] == "stuart-landau":
        add([i], "periodic", "Stuart-Landau: pure sinusoid, redundant with H.sinusoid")
    else:
        add([i], "duplicate", "one of 17 similar clean limit cycles in H")
add(rng("I_noisy-limit-cycle", [0, 1, 7]), "periodic", "near-sinusoidal (you flagged I's sinusoid-like series)")
# 5 duplicates
dm = m[m.family == "dysts-map"]
seen = set()
for r in dm.itertuples():
    k = kind[r.id]
    if k in seen:
        add([r.id], "duplicate", f"{k} repeated: 22 slots, 18 maps -> index wraps")
    seen.add(k)
add(rng("E_expar", [0, 1]), "duplicate", "near-identical pair")
add(rng("E_stochastic-map", [8, 14]), "duplicate", "near-identical pair")
add(rng("L_pac", [2, 4]), "duplicate", "near-identical pair")
add([i for i in m.id[m.family == "neuron"] if scr.loc[i, "duplicate"]], "duplicate", "near-identical to another neuron instance")
# 6 spiky
add(rng("J_renewal", [2, 5, 7]), "spiky", "a few huge intervals dominate")
add(rng("M_nonlinear-readout", [0, 4]), "spiky", "square/exp readout of skewed base: spikes dominate")
# 7 quasi-discrete
add(["M_clipped_001"], "discrete", "most samples at clip bounds: solid band")
add(rng("N_kirman", range(3)), "discrete", "N=300 -> <200 distinct values")
for fam in ("rainfall-pulse", "richardson-weather-stationary", "compound-poisson-increments"):
    add(list(m.id[m.family == fam]), "discrete", ">40% exact zeros (point mass): keep? your call")
# 8 banded chaos
add(rng("F_logistic", [4, 5, 7, 8, 12]) + ["F_classic-1d_010", "E_stochastic-map_003"], "banded",
    "banded chaos (lambda>0): reads as a solid band")

out = pd.DataFrame(notes, columns=["id", "category", "note"]).drop_duplicates()
out.to_csv(D / "review_notes.csv", index=False)
print(len(out), "notes on", out.id.nunique(), "series;", out.category.value_counts().to_dict())
