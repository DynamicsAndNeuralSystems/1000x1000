# Synthetic1000 family catalogue — profile `stationary1000`

Generated from the registry; one row per family. Quotas are the profile's.

## A. i.i.d. noise — 30 of 30

| family | n | tags (yes) | description |
|---|---|---|---|
| `gaussian` | 4 | linear, stationary, reversible, gaussian | Standard Gaussian white noise. |
| `uniform` | 3 | linear, stationary, reversible | Uniform white noise on [-1, 1]. |
| `laplace` | 2 | linear, stationary, reversible | Laplace (double-exponential) white noise. |
| `student-t` | 4 | linear, stationary, reversible, heavy_tailed | Student-t white noise, nu in {1.5, 2, 3, 5}; in the stationary profile nu in {3, 4, 5, 7} (finite variance). |
| `skewed` | 6 | linear, stationary, reversible, skewed | Skewed white noise: gamma (shape LU[0.3, 3]), log-normal (sigma U[0.3, 1.5]), chi-square. |
| `bimodal` | 3 | linear, stationary, reversible | Two-component Gaussian mixture, separation U[2, 5] SD, weight U[0.2, 0.5]. |
| `exponential-pareto` | 2 | linear, stationary, reversible, skewed | Exponential (i=0) or Pareto with tail index LU[1.2, 4] (i=1). |
| `heavy-finite` | 6 | linear, stationary, reversible, heavy_tailed | Finite-variance heavy-tailed white noise: Student-t nu S[3, 6] (even i) or a scale mixture of Gaussians (SD 1 with probability 1-p, SD 5 with probability p, p U[0.02, 0.1]; odd i). |

## B. linear Gaussian, short memory — 85 of 85

| family | n | tags (yes) | description |
|---|---|---|---|
| `ar1` | 11 | linear, gaussian, stationary, reversible | AR(1), phi stratified over (-0.98, 0.98); negative phi included. |
| `ar2` | 16 | linear, gaussian, stationary, reversible | AR(2): half with complex roots (pseudo-period S[3, 80] samples, modulus S[0.5, 0.99]), half with two real roots. |
| `arp` | 11 | linear, gaussian, stationary, reversible | AR(p), p in 3..12, coefficients from reflection coefficients U(-0.8, 0.8). |
| `maq` | 9 | linear, gaussian, stationary, reversible | MA(q), q in 1..10, theta_j = U(-1, 1) r^j, r U[0.5, 0.95]; non-invertible cases allowed. |
| `arma` | 12 | linear, gaussian, stationary, reversible | ARMA(p, q), p, q <= 4. |
| `seasonal-arma` | 9 | linear, gaussian, stationary, reversible | Multiplicative seasonal AR: (1 - phi B)(1 - Phi B^s) x_t = e_t, s S[4, 60], Phi U[0.5, 0.95], phi U[-0.5, 0.5]. |
| `narrowband` | 9 | linear, gaussian, stationary, reversible | Butterworth band-pass (order 2) filtered noise: centre LU[0.05, 0.4] cycles/sample, Q LU[2, 30]. |
| `lowhigh-pass` | 4 | linear, gaussian, stationary, reversible | Low-pass (even i) or high-pass (odd i) Butterworth-filtered noise, cutoff LU[0.02, 0.4], order U{2..8}. |
| `random-spectrum` | 4 | linear, gaussian, stationary, reversible | A spectrum nobody named: log-PSD is a smooth Gaussian process in log-frequency, phases random. |

## C. linear non-Gaussian — 52 of 52

| family | n | tags (yes) | description |
|---|---|---|---|
| `ar-skew` | 10 | linear, stationary, skewed | AR(p<=3) with centred-gamma innovations, shape LU[0.4, 3] (skewness 2/sqrt(shape)). |
| `arma-heavy` | 9 | linear, stationary, heavy_tailed, reversible | AR(p <= 3) -- no MA part, despite the family name -- with Student-t (nu S[1.5, 4]) or symmetric alpha-stable (alpha S[1.2, 1.9]) innovations; in the stationary profile Student-t only, nu S[3, 6] (finite variance). |
| `ma-asym-skew` | 7 | linear, stationary, skewed | One-sided decaying MA(q) with skewed innovations (Weiss 1975): linear, non-Gaussian, asymmetric filter. |
| `levy-ou` | 9 | linear, stationary | Levy-driven OU: compound-Poisson jumps (rate LU[0.05, 0.4]/sample, exponential sizes, one-sided for even i, two-sided for odd i) with exponential decay S[0.6, 0.93]; i % 4 < 2 add Gaussian noise (SD 0.3). |
| `ar-bounded` | 8 | linear, stationary, reversible | AR(1) with binary (+-1, even i) or uniform (odd i) innovations, phi S(-0.9, 0.9). |
| `shot-noise` | 9 | linear, stationary, skewed, event_like | Poisson-driven pulses with a random pulse shape (exponential, alpha-function, Gaussian, rectangular; the stationary profile omits rectangular), rate LU[0.05, 0.3]/sample, width LU[1.5, 6] samples. |

## D. long memory, self-similar, multifractal — 62 of 62

| family | n | tags (yes) | description |
|---|---|---|---|
| `fgn` | 14 | linear, gaussian, stationary, long_memory, reversible | Fractional Gaussian noise (exact Davies-Harte), H stratified over [0.02, 0.9]. |
| `arfima` | 14 | linear, gaussian, stationary, long_memory, reversible | ARFIMA(p, d, q), d stratified over [-0.45, 0.4], p, q in {0, 1}. |
| `mrw` | 12 | stationary, long_memory, heteroskedastic, bursty, heavy_tailed | Multifractal random walk increments (Bacry-Delour-Muzy): fGn_H x exp(log-correlated volatility); H S[0.3, 0.7], lambda^2 S[0.03, 0.15], integral scale LU[64, 1024]; odd i on Student-t (nu U[3.5, 8]) innovations. Generated at 8192 and windowed. |
| `discrete-cascade` | 10 | stationary, long_memory, heteroskedastic, bursty | Binomial p-model (even i, p S[0.55, 0.68]) or log-Poisson cascade (odd i): fGn x dyadic multiplicative volatility, random grid phase. |
| `lmsv` | 4 | stationary, long_memory, heteroskedastic | Long-memory stochastic volatility: fGn_H x exp(s fGn_{Hw}), Hw S[0.75, 0.95], s S[0.3, 0.8]. |
| `one-over-f-stationary` | 8 | linear, gaussian, stationary, long_memory, reversible | 1/f^beta noise by spectral synthesis, beta stratified over [0, 0.95] (the stationary range). |

## E. nonlinear stochastic, discrete time — 122 of 122

| family | n | tags (yes) | description |
|---|---|---|---|
| `setar` | 21 | stationary | SETAR with 2 (even i) or 3 (odd i) regimes, delay d in {1, 2, 3}; regime AR coefficients phi+ S[0.4, 0.9], phi- U[-0.6, 0.2] (third regime U[-0.3, 0.7]); threshold 0 (2 regimes) or two U[-1, 1] (3 regimes). |
| `expar` | 6 | stationary | Exponential AR (Haggan-Ozaki): x_t = (a + b exp(-x_{t-1}^2)) x_{t-1} + e_t. |
| `bilinear` | 6 | stationary | Bilinear MA x_t = e_t + c e_{t-1} e_{t-2}, c S[0.4, 1]; Gaussian (even i: irreversible only above third order) or skewed (odd i) innovations. |
| `random-coef-ar` | 5 | stationary, heteroskedastic | Random-coefficient AR(1): phi_t = phi + sigma_phi eps_t, sigma_phi S[0.1, 0.4]. |
| `garch` | 19 | stationary, heteroskedastic, bursty, heavy_tailed | ARCH(1) / GARCH(1,1) / GJR-GARCH / EGARCH returns with Gaussian or Student-t innovations; persistence S[0.6, 0.99]. |
| `stoch-vol` | 8 | stationary, heteroskedastic | Stochastic volatility: r_t = exp(h_t/2) z_t, h_t = phi h_{t-1} + sigma eta_t, phi S[0.8, 0.95], sigma S[0.15, 0.4]. |
| `markov-switching-ar` | 10 | stationary, regime_switching | Markov-switching AR(1) with 2-4 regimes (dwell LU[8, 60]); regimes differ in a drawn subset of {phi, mean, variance}. |
| `hmm` | 8 | stationary, regime_switching | Hidden Markov: 2-state Gaussian (i%3==0), cyclic 3-state Gaussian (i%3==1, detailed balance violated), or categorical emissions from a 3-5 state chain (i%3==2). |
| `stochastic-map` | 12 | stationary | Logistic, tent, Henon or Ricker map with dynamical noise LU[0.001, 0.1] (scaled per map; multiplicative for Ricker); parameter drawn in chaotic *and* periodic regimes (noisy periodicity, noise-induced chaos), except in the stationary profile, where it is redrawn until the noise-free map is chaotic. |
| `star` | 14 | stationary | Smooth-transition AR (LSTAR / ESTAR) or additive nonlinear AR (sin / tanh); transition steepness LU[1, 20]. |
| `volterra` | 4 | stationary | Second-order Volterra (nonlinear MA): linear MA(3) plus quadratic lag products, weight S[0.3, 1]. |
| `bistable-map` | 5 | stationary, regime_switching | Noisy double-well map x_t = x_{t-1} + h(x_{t-1} - x_{t-1}^3) + sigma e_t; h = 0.1, sigma S[0.22, 0.4]: >= ~40 well crossings per record. |
| `cubic-crisis` | 2 | stationary, chaotic, regime_switching | Noise-induced switching between chaotic attractors: the symmetric cubic map x -> a x - x^3 just below its attractor-merging crisis (a < 3 sqrt(3)/2 ~ 2.598) has two mirror-image chaotic bands; dynamical noise LU[0.03, 0.06] kicks the orbit between them, so chaotic motion within a band is broken by switches at irregular times. a stratified over [2.50, 2.58]. |
| `kesten` | 2 | stationary, heavy_tailed, bursty, skewed | Kesten random multiplicative process x_{n+1} = a_n x_n + b_n, ln a_n ~ N(m, s^2) with m < 0 and b_n > 0: occasional runs of a_n > 1 give bursts of exponential growth, and the stationary law has a power-law tail with exponent kappa = -2m/s^2, stratified over [2.3, 4] (finite variance). |

## F. deterministic maps — 81 of 81

| family | n | tags (yes) | description |
|---|---|---|---|
| `logistic` | 5 | deterministic, stationary | Logistic map, r stratified over [3.5, 4] (periodic windows included, retagged by lambda; the stationary profile redraws r on [3.57, 4] until lambda > 0.01). |
| `classic-1d` | 11 | deterministic, stationary | Tent, sine, cubic and Chebyshev maps across their chaotic ranges. |
| `circle-map` | 9 | deterministic, stationary | Circle map theta_{n+1} = theta_n + Omega - (K/2pi) sin(2 pi theta_n): mode-locked and quasi-periodic (K < 1) and chaotic (K > 1); observed as sin(2 pi theta). |
| `pomeau-manneville` | 8 | deterministic, stationary, bursty, event_like | Pomeau-Manneville intermittency x_{n+1} = x_n + x_n^z mod 1, z S[1.3, 1.85] (finite invariant measure; laminar phases of tens of samples, many per record). |
| `shift-gauss` | 4 | deterministic, stationary | Bernoulli (doubling) shift (even i, iterated in exact rational arithmetic) and Gauss map (odd i). |
| `piecewise-impact` | 3 | deterministic, stationary | Piecewise-linear / square-root (Nordmark impact) maps: x -> a x + b (x<0), x -> -c sqrt(x) + d (x>=0). |
| `dysts-map` | 18 | deterministic, stationary, chaotic | One trajectory per usable dysts map (22 of 23), one coordinate, perturbed initial condition. |
| `map-sweep` | 16 | deterministic, stationary | Regime sweeps of higher-dimensional maps: Henon (a), Lozi, Ikeda (u), Chirikov standard map (K across KAM -> chaotic; wrapped and unwrapped), Zaslavskii, Arnold cat, Burgers, coupled logistic pair. |
| `aperiodic-real` | 2 | deterministic, stationary | Real-valued deterministic aperiodic sequences: cellular-automaton row density, rule 30 (class 3, i = 0) and rule 110 (class 4: a periodic background crossed by gliders, i = 1; until 2026-09-26 a second rule-30 density at another width, which was redundant with the first). |
| `rulkov` | 3 | deterministic, stationary, chaotic, bursty | Rulkov (2001) map neuron: fast x_{n+1} = alpha / (1 + x_n^2) + y_n and slow y_{n+1} = y_n - mu (x_n - sigma). Chaotic bursts of spikes separated by slow silent recovery; alpha stratified over [4.1, 4.6], mu LU[0.003, 0.01] sets the burst period (~10 bursts per record). |
| `sna` | 2 | deterministic, stationary | Strange nonchaotic attractor (Grebogi, Ott, Pelikan & Yorke 1984): the quasi-periodically forced map x_{n+1} = 2 sigma tanh(x_n) cos(2 pi theta_n), theta_{n+1} = theta_n + omega mod 1, omega the golden mean. For sigma > 1 the attractor is fractal but its Lyapunov exponent is negative. |

## G. chaotic flows — 181 of 181

| family | n | tags (yes) | description |
|---|---|---|---|
| `dysts-flow` | 126 | deterministic, chaotic, stationary, continuous_time | One trajectory per usable non-delay dysts flow (126): DOP853, resampled to ppp S[15, 40] points per period, random coordinate, perturbed initial condition, burn 400. lyapunov_max from a Benettin table (per sample); 13 systems are reversible in law. |
| `canonical-sweep` | 9 | deterministic, stationary, continuous_time | Regimes of canonical flows not represented by the dysts defaults: Lorenz rho = 24.5 (co-existing attractors) and rho = 160 (NB: inside a periodic window); Rossler c = 4 (a period-1 cycle; replaced by Chen in the stationary profile) and c = 8.5 (NB: a periodic orbit at a = b = 0.1, not a funnel); Chua double scroll; forced Duffing; driven damped pendulum; double pendulum; Lorenz-84. |
| `dde-stationary` | 15 | deterministic, stationary, continuous_time | Delay-differential systems with bounded state: Mackey-Glass (tau stratified over [17, 40], chaotic, 9), Ikeda DDE (4), and two chaotic delay systems of distinct character (2): Ucar's prototype x' = x(t - tau) - x(t - tau)^3 (tau S[1.6, 1.7], slow wandering chaos) and the band-pass optoelectronic Ikeda oscillator (beta U[2, 2.5], chaotic square-wave switching). These replaced Hutchinson's delayed logistic (2026-09-26), whose delay-induced cycle is not chaotic and duplicates Nicholson's blowflies. The sine-delay system (an unbounded phase) is left to the full profile. |
| `dysts-flow-coarse` | 15 | deterministic, chaotic, stationary, continuous_time | dysts flows sampled coarsely, ppp S[4, 10] points per period (80-250 periods per record): the regime of Empirical1000's own chaotic-flow series, which the 15-40 ppp convention does not reach. |
| `dysts-flow-extra` | 6 | deterministic, chaotic, stationary, continuous_time | A second realisation of six systems whose single instance was visually the most interesting: Sakarya, ZhouChen, BlinkingRotlet, Halvorsen, RabinovichFabrikant, Dadras. Different observed coordinate, sampling density and initial condition from the one in ``dysts-flow``. |
| `blinking-rotlet` | 6 | deterministic, stationary, continuous_time | Blinking rotlet (Meleshko & Aref 1996): a tracer in a Stokes flow stirred by two rotlets that switch on and off alternately. The switching period tau is stratified log-uniformly over [0.8, 10]: short periods give fast irregular mixing, long ones smooth rotations broken by bursts at each switch. Observed x or y, speed-normalised like the other flows. |
| `billiard` | 2 | deterministic, chaotic, stationary, continuous_time, reversible | Bunimovich stadium billiard: Hamiltonian chaos made of straight flights and specular bounces. One coordinate (x for i = 0, y for i = 1) sampled at fixed time steps; half-length L stratified over [0.5, 2]; about three samples per flight. |
| `bouncing-ball` | 2 | deterministic, chaotic, stationary, continuous_time | Ball bouncing on a sinusoidally vibrating table (Holmes 1982): ballistic flights under gravity joined by inelastic impacts (restitution e) with the table; chaotic for normalised table acceleration Gamma ~ 2.5-4. Ball height sampled at 6 points per table period. |

## H. periodic, quasi-periodic, oscillatory — 32 of 32

| family | n | tags (yes) | description |
|---|---|---|---|
| `sinusoid` | 3 | deterministic, linear, stationary, periodic, reversible | Pure sinusoid, points per period LU[2.2, 300] (near-Nyquist and very slow both present; the stationary profile stops at 60). |
| `harmonic` | 5 | deterministic, stationary, periodic, reversible | Square, sawtooth, triangle, pulse train, or a random set of 2-20 harmonics with random phases. |
| `quasiperiodic` | 7 | deterministic, linear, stationary, reversible, quasiperiodic | 2-torus (even i) or 3-torus (odd i): incommensurate frequencies (ratios near the golden mean and sqrt 2), random amplitudes. |
| `limit-cycle` | 5 | deterministic, stationary, periodic, reversible, continuous_time | Limit cycles: van der Pol (mu S[0.1, 10], sinusoidal to relaxation), Stuart-Landau, Brusselator, FitzHugh-Nagumo (oscillatory), integrated and resampled to ppp S[15, 40]. |
| `modulated-stationary` | 6 | deterministic, stationary, reversible | AM, FM or beats (the stationary modulations; chirps are left to the full profile). |
| `period-doubled-flows` | 2 | deterministic, stationary, periodic, reversible, continuous_time | Periodic orbits of chaotic flows: Rossler c = 8.5 (a period-4 orbit of the doubling cascade; c = 3.5, a plain period-1 cycle, until 2026-09-26) and Lorenz rho = 350 (periodic). |
| `cycle-shapes` | 4 | deterministic, stationary, periodic, reversible, continuous_time | Periodic orbits with waveforms not otherwise in H: Hindmarsh-Rose periodic bursting (a train of spikes in every cycle), the Rayleigh oscillator (triangle-like), a conservative Lotka-Volterra orbit far from equilibrium (sharp pulses on a flat floor), and a pendulum librating just inside its separatrix (flat-topped, lingering at the turning points). |

## I. noise-driven continuous-time dynamics — 104 of 104

| family | n | tags (yes) | description |
|---|---|---|---|
| `ou` | 16 | continuous_time, linear, gaussian, stationary, reversible | Ornstein-Uhlenbeck subsampled: correlation time tau LU[1, 20] samples (>= 50 correlation times per record). |
| `double-well` | 20 | continuous_time, stationary, regime_switching | Langevin in V = x^4/4 - x^2/2: dx = (x - x^3) dt + sigma dW; sigma S[0.5, 1.1]: >= ~30 hops per record. |
| `near-critical` | 18 | continuous_time, stationary | Normal forms with noise, kappa = mu/eta stratified over near (-0.15..-0.01) and far (-3..-1): pitchfork, radial Hopf (reflected), planar Hopf (omega drawn, observe x), saddle-node, transcritical. |
| `noisy-limit-cycle` | 8 | continuous_time, stationary | Van der Pol (even i) or Stuart-Landau (odd i) with additive noise LU[0.2, 1] (stationary: LU[0.3, 1], and odd i is a relaxation van der Pol in Lienard form instead): phase diffusion; ppp S[15, 40]. |
| `noisy-chaos` | 14 | continuous_time, stationary, chaotic | Lorenz, Rossler or Chua with *dynamical* noise LU[0.03, 0.3] (stationary: LU[0.1, 0.5], ppp S[8, 20]) of the attractor SD: visibly noisy trajectories (below ~0.02 the noise is invisible against the deterministic motion). |
| `stochastic-resonance` | 12 | continuous_time, stationary, regime_switching | Double well + weak periodic forcing + noise: dx = (x - x^3 + A cos(w t)) dt + sigma dW, sigma stratified around the resonance optimum. |
| `excitable-fhn` | 8 | continuous_time, stationary, event_like | FitzHugh-Nagumo in the excitable regime, noise-driven spiking: sigma stratified so spikes per 1000 samples run over ~[5, 80]. |
| `multiplicative-coloured` | 5 | continuous_time, stationary | Langevin with multiplicative noise dx = -x dt + sigma x dW (+ small additive, even i), or a linear relaxation driven by OU-coloured noise (odd i). |
| `heteroclinic` | 3 | continuous_time, stationary, regime_switching | Noisy heteroclinic cycle (May & Leonard 1975; Busse & Heikes): three competing species x_k' = x_k (1 - x_k - alpha x_{k+1} - beta x_{k+2}) with alpha < 1 < beta, alpha + beta > 2, cycle between saddle states where one species dominates. Small noise delta sets how long each plateau lasts (~ln(1/delta)); observed as x_1 + x_2 / 2, so the three saddles read as three levels and the cyclic order of the switching is visible. Reflected at zero; ~30 dwells per record. |

## J. events, point processes, discrete states — 48 of 48

| family | n | tags (yes) | description |
|---|---|---|---|
| `renewal` | 9 | stationary, event_like, discrete_valued, skewed | Renewal process with gamma, log-normal, Weibull or Pareto intervals, mean interval S[5, 60]; burstiness stratified over [-0.5, 0.8]; observed as a 0/1 event train (even i) or the interval sequence (odd i); the stationary profile uses intervals only. |
| `hawkes` | 9 | stationary, event_like, discrete_valued, skewed, bursty | Hawkes self-exciting process, branching ratio S[0.2, 0.98] (upper quarter near-critical), exponential (even i) or power-law (odd i) kernel; binned counts, or inter-event intervals (i % 4 == 3); the stationary profile reads every instance out as a kernel-smoothed rate. |
| `spike-signs` | 5 | stationary, event_like | Marked point process on an AR floor: spikes 4-7 SD at gamma(4) intervals (mean tau S[10, 40]), sign rule s_n = -s_{n-1} s_{n-2} r_n (third-order, sign-balanced, no pairwise correlation). |
| `compound-poisson-increments` | 2 | stationary, skewed, heavy_tailed, bursty | Compound Poisson increments with Pareto jumps (tail S[2.2, 3.5], finite variance): zero-inflated, rainfall-total shape. |
| `poisson-smoothed` | 6 | stationary, event_like, reversible | Homogeneous Poisson event train (rate LU[0.05, 0.5]) read out as a kernel-smoothed rate. |
| `cox-smoothed` | 6 | stationary, event_like, skewed, bursty, reversible | Doubly stochastic Poisson (rate = mean exp(s OU), OU tau LU[2, 10], mean LU[0.5, 3]) read out as a kernel-smoothed rate. |
| `markov-chain-emitted` | 7 | stationary, regime_switching | Markov chain with 2-6 states (dwell LU[2, 40]; random or cyclic transitions) read out through state-dependent Gaussian emissions (means = state index, SD U[0.15, 0.4]). |
| `telegraph-noisy` | 4 | stationary, reversible, regime_switching | Random telegraph noise (+-1, switching rate LU[0.03, 0.3]) in Gaussian noise of SD U[0.1, 0.4]. |

## L. structured, composite, coupled — 43 of 43

| family | n | tags (yes) | description |
|---|---|---|---|
| `longlag-comb` | 6 | gaussian, stationary, linear, reversible | Long-lag-only dependence: u_t = e_t + phi u_{t-L} on the innovations (white below L), then a random stable AR(p <= 4); L S[40, 160], |phi| S[0.2, 0.35]; odd i use the nonlinear variant u_t = e_t + phi (min(u_{t-L}^2, 4) - c) with c ~ its mean (AC(L) ~ 0, dependence present; c = 0.953 is approximate: E[min(Z^2, 4)] = 0.921 for standard normal Z, and u is not N(0, 1), so AC(L) is ~0.03 at |phi| = 0.35). |
| `cyclostationary-switch` | 6 | gaussian, linear | One-sample switch of the dynamics: x_t = phi(t) x_{t-L} + s(t) e_t with phi alternating with period P (P = 2 for even i, P in {3, 4} for odd i); equal chain variances so only the correlation switches. |
| `replay-recurrence` | 4 | stationary | AR(1)-coloured innovations (phi U[0.3, 0.8]) replay 15-30% of their own past in segments of 20-60 samples copied from random earlier positions, with fresh noise U[0.05, 0.2] SD added. |
| `pac` | 5 | stationary | Phase-amplitude coupling: a fast rhythm whose envelope follows a slow rhythm's phase (theta-gamma narrow and broad band, delta-beta, alpha-gamma; noise sigma = 0.8). |
| `qpc` | 5 | stationary | Quadratic phase coupling: three narrowband components with theta3 = theta1 + theta2 + pi/2 tracked at every instant; complex-OU envelopes with coherence time tau LU[20, 120]. |
| `coupled-systems` | 8 | stationary, deterministic, chaotic | Coupled chaotic systems, coupling stratified across the synchronisation transition: Lorenz -> Rossler unidirectional (observe the slave), two bidirectionally coupled Rosslers with a frequency mismatch (phase synchronisation), coupled logistic maps, master-slave with delay (full profile), and in stationary1000 a Kaneko coupled map lattice (one site of a ring of 100 diffusively coupled logistic maps x -> 1 - a x^2) in two regimes: spatiotemporal intermittency (i=5) and fully developed turbulence (i=6). |
| `mixture` | 6 | stationary | Additive mixtures: Lorenz + AR(1) (ratio S[0.3, 3]); Lorenz under a heavy noise floor (SNR <= 0 dB); Rossler + a seasonal AR; sum of two independent processes of different kinds. |
| `on-off` | 3 | stationary, bursty, skewed | On-off intermittency (Platt, Spiegel & Tresser 1993; Heagy, Platt & Hammel 1994): a logistic response x_{n+1} = a xi_n x_n (1 - x_n) driven by a chaotic signal xi_n that is exactly uniform on [0, 1] (the r = 4 logistic map through its conjugacy to the tent map). The invariant state x = 0 loses transverse stability at a = e; just above it the response idles near zero and bursts. |

## M. observation effects — 40 of 40

| family | n | tags (yes) | description |
|---|---|---|---|
| `clipped` | 4 |  | Base series clipped (saturated) at +-c SD about the mean, c S[0.5, 1.5]. |
| `missing-data` | 4 |  | Missing fraction U[0.05, 0.4] in gaps of mean length LU[1, 30], filled by zero-order hold (even i) or linear interpolation (odd i). |
| `irregular-sampling` | 3 |  | Base series sampled at jittered times (jitter U[0.1, 0.8] of the interval) and linearly re-interpolated to the grid. |
| `aliased` | 4 | deterministic, chaotic, stationary, continuous_time | A chaotic flow undersampled: ppp U[2.5, 6] points per period. |
| `oversampled` | 3 | deterministic, chaotic, stationary, continuous_time | A chaotic flow oversampled: ppp U[150, 400] (2.5-7 periods per series; stationary: U[40, 70], 14-25 periods). |
| `nonlinear-readout` | 5 |  | Base series observed through x^2, |x|, exp(x), sign(x) or x * x_{t-1}. |
| `outliers` | 4 |  | Additive outliers at rate U[0.005, 0.05], size U[4, 10] SD, random sign. |
| `heavy-noise` | 7 |  | Base series under heavy white measurement noise, SNR U[-6, 0] dB. |
| `downsampled` | 6 |  | A stationary base process generated at k x the record length (k S{2..5}) and decimated (anti-aliased) by k: the same process observed at a coarser sampling interval. Class A (i.i.d.) bases are skipped: decimating white noise yields only the anti-aliasing filter's band-limited noise. For the same reason a linear-Gaussian base whose decimated lag-1 autocorrelation is below 0.3 (e.g. AR(1) with |phi| small) is redrawn. |

## N. named models of natural and engineered processes — 120 of 120

| family | n | tags (yes) | description |
|---|---|---|---|
| `predator-prey-ssa` | 3 | stationary, skewed | Stochastic Lotka-Volterra (i<2) or Rosenzweig-MacArthur (i=2) predator-prey by Gillespie SSA; population scale stratified so demographic noise is visible; prey series sampled at fixed intervals. |
| `blowflies-ricker` | 4 | stationary, skewed | Nicholson's blowflies (delayed feedback N' = P N(t - tau) exp(-N(t - tau)/N0) - delta N, i<2, P stratified over the cycling regime; limit cycles, not chaos, at these parameters) and the Ricker map with environmental noise (i>=2). |
| `sir-seir` | 6 | stationary, skewed, bursty | Seasonally forced stochastic SIR (even i) / SEIR (odd i) with births, deaths and immigration (Gillespie; weekly case counts): measles-like multi-annual epidemics, fade-outs and reintroduction. |
| `rainfall-pulse` | 6 | stationary, skewed, bursty, event_like | Bartlett-Lewis rectangular-pulse rainfall, aggregated to hourly (even i) or daily (odd i) totals; storm rate S over temperate <-> convective regimes. Zero-inflated, heavily right-skewed. |
| `stick-slip` | 2 | stationary, skewed | Stress on a fault under steady tectonic loading with stick-slip release: a noisy linear ramp that drops at each earthquake, giving an irregular sawtooth. i = 0 is time-predictable (a random failure threshold, full drop to a base level); i = 1 is slip-predictable (a fixed threshold, random stress drop). Loading rate stratified so ~15-50 cycles fall in the record (Shimazaki & Nakata 1980). |
| `etas` | 5 | stationary, bursty, event_like, heavy_tailed, discrete_valued | ETAS earthquake model (Ogata): background rate + Omori-Utsu aftershock cascades with Gutenberg-Richter magnitudes; branching ratio S[0.5, 0.95], Omori p S[1.05, 1.4]. Daily counts (even i) or inter-event times (odd i; the stationary profile uses inter-event times only) — the burstiest thing in the corpus. |
| `barnes-sunspot` | 1 | stationary | Barnes-type sunspot model: an ARMA(2,2) with an 11-year pseudo-period (monthly sampling, 132 samples) passed through a static nonlinearity y = z^2 + 0.03 z^3. |
| `climate-model` | 4 | stationary, continuous_time | Stochastic climate models: Hasselmann (OU forced by weather noise with an annual cycle), the ENSO delayed oscillator (Suarez-Schopf T' = T - T^3 - alpha T(t - delta)), Stommel two-box thermohaline circulation with noise (bistable), and Daisyworld with noisy luminosity. |
| `turbulence` | 2 | stationary, bursty, heavy_tailed, heteroskedastic, continuous_time | Turbulence: Sabra shell-model velocity at a mid-inertial shell (intermittent), and a point velocity of the randomly forced viscous Burgers equation (spectral, 128 modes). |
| `richardson-weather-stationary` | 3 | stationary, skewed, regime_switching, reversible | Richardson weather generator without the annual cycle: Markov wet/dry days (P(wet|wet) S[0.4, 0.8]) with gamma amounts. |
| `river-discharge-stationary` | 3 | stationary, skewed | Daily discharge from a Nash cascade (n S[2, 5], k U[1, 6] days) driven by Markov-gamma rainfall, plus baseflow; no seasonal input. |
| `onoff-traffic` | 3 | stationary, long_memory, bursty, reversible | Aggregated ON/OFF sources with heavy-tailed (Pareto, tail S[1.5, 1.9]) ON and OFF periods (Willinger et al.): self-similar packet counts per bin. |
| `speech` | 3 | stationary, regime_switching | Source-filter speech: a glottal pulse train (Rosenberg pulses with jitter and shimmer) or noise, through a slowly time-varying all-pole vocal-tract filter, with voiced/unvoiced switching; 8 kHz equivalent, ~125 ms of signal. |
| `bearing-vibration` | 2 | stationary | Rotating-machine vibration with a bearing fault: a jittered impulse train at the fault frequency (period S[15, 60] samples) exciting a resonance (Q S[5, 30]) plus broadband noise. |
| `collective` | 3 | stationary | Collective dynamics: Kuramoto ensemble (N = 100) order parameter r(t) with coupling stratified across the synchronisation transition (i<2), and 2-D Ising magnetisation (Metropolis, 32 x 32) with T/T_c S[1.03, 1.4], the disordered side (i=2). |
| `laser-feedback` | 2 | stationary, bursty, continuous_time | Lang-Kobayashi semiconductor laser with delayed optical feedback in the low-frequency- fluctuation regime: intensity dropouts. Dimensionless form; feedback strength stratified. |
| `oregonator` | 2 | stationary, continuous_time | Belousov-Zhabotinsky reaction (Oregonator, Tyson scaling): relaxation oscillations, f S[0.6, 1.4] (inside the oscillatory range, about 0.52 < f < 2.4); observe log(x) (HBrO2). |
| `kirman` | 3 | stationary, regime_switching, bursty | Kirman herding (ants) model: fraction of agents in one state, recruitment k = 0.5 and spontaneous conversion epsilon LU[0.01, 0.05] (unimodal to bimodal with bursty switches). |
| `rr-ipfm` | 9 | stationary | RR intervals from an IPFM model driven by LF (0.1 Hz) and HF (0.25 Hz) modulation, 1/f^beta (beta S[0.8, 1.3]) and white noise; LF/HF power ratio S[0.3, 4]; 1000 beats. |
| `rr-ectopic` | 3 | stationary, event_like, bursty, heavy_tailed | RR intervals with premature ectopic beats (rate LU[1, 6]% of beats): a short coupling interval followed by a compensatory pause. |
| `rr-af` | 3 | stationary | RR intervals in atrial fibrillation: atrial impulses arrive as a Poisson stream (rate S[4, 9]/s) at an AV node with a refractory period (0.25-0.45 s) that lengthens after each conducted beat (concealed conduction) — the 'irregularly irregular' rhythm. |
| `deboer` | 3 | stationary | DeBoer-type beat-to-beat baroreflex model: systolic pressure S_n, RR interval I_n and peripheral resistance coupled through a fast vagal and a slow sympathetic baroreflex, a Windkessel diastolic decay, and respiratory modulation of pressure; observe RR (i<2) or SBP. |
| `ecgsyn` | 4 | stationary, continuous_time | ECGSYN (McSharry et al. 2003): a trajectory around a limit cycle in (x, y) with Gaussian PQRST events in z; RR variability from Mayer (0.1 Hz) + respiratory (0.25 Hz) modulation; n_beats S[20, 40] in the 1000-sample record; R peak normalised to 1 mV, then 0.05 mV respiratory baseline wander and 0.03 mV noise added. |
| `periodic-breathing` | 3 | stationary, continuous_time | Chemoreflex loop with circulatory delay (Mackey-Glass form): dC/dt = P - V(C(t - tau)) C, V = Vmax C^n / (theta^n + C^n); the ventilation drive V(t) is observed as a breathing waveform whose amplitude it modulates. Delay stratified from stable to periodic breathing (Cheyne-Stokes). |
| `neural-mass` | 11 | stationary, continuous_time | Neural-mass EEG models: Jansen-Rit (input p stratified: noise-driven alpha, 3 Hz spike-wave, high-input), Wilson-Cowan with noise, Epileptor (Jirsa et al. 2014: seizure onset/offset cycles, bursty by construction). Sampled at ~250 Hz equivalent. |
| `neuron` | 10 | stationary, continuous_time | Neuron models with noisy input current: Hodgkin-Huxley (V; binned spikes), Izhikevich regular / chattering / intrinsically bursting, Morris-Lecar, Hindmarsh-Rose bursting (V; binned spikes). |
| `glucose-insulin` | 3 | continuous_time | Bergman minimal model with meals as gamma-shaped glucose appearance pulses at irregular times (bursty input) plus a Sturis-type ultradian oscillation from delayed insulin action; glucose sampled every 5 min over ~3.5 days. |
| `circadian-hormone` | 4 | stationary | Kronauer circadian oscillator (the higher-order revised model of Jewett, Forger & Kronauer 1999) driven by a light-dark cycle, sampled hourly (i<2; the process is a forced van-der-Pol-type limit cycle with tau_x S[23.5, 25]) and pulsatile hormone secretion (Keenan-Veldhuis: renewal pulses of gamma mass through exponential clearance, sampled every 10 min; i>=2). |
| `gene-cell` | 6 | stationary | Goodwin oscillator (n = 10), the repressilator (Elowitz-Leibler), telegraph-model transcription by Gillespie SSA (bursty integer mRNA counts sampled at fixed intervals, x2), Goldbeter calcium-induced calcium release oscillations (x2, stimulation beta stratified). |
| `gait-emg-tremor` | 4 | stationary | Stride-interval series with fractal fluctuations (Hausdorff: 1.1 s + 0.03 fGn_H, H S[0.6, 0.9]; x2), surface EMG (Gaussian carrier gated by a bursting envelope at the gait cycle), and physiological tremor (8-12 Hz narrowband at 100 Hz sampling). |
