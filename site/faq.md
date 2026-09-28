<!--
FAQ for the 1000×1000 website, shown at #/faq in this order.
Format: each "## " line is a question; the paragraphs under it (separated by blank lines) are its answer.
Inline: **bold**, *italic*, `code`, [link text](https://…), and maths as \( … \) (KaTeX).
The first question starts open. After editing: commit, then run scripts/deploy_pages.sh.
-->

## What is the 1000×1000 collection?

1000 simulated time series, each 1000 samples long, from 133 generating mechanisms in 13 classes: noise and linear processes, maps, chaotic flows, oscillators, stochastic differential equations, point processes, measurement effects, and models of hearts, brains, climate and ecosystems. It is built to span the kinds of dynamics that scientists have modeled, to provide a unified resource for understanding the interdisciplinary  models so methods can be tested across all of them.

## Are all the series stationary?

Yes, in this release. Every series passed a five-window mean and variance stationarity check and has a real-valued, finite-variance distribution. A second, non-stationary stage will follow.

## Why do the series IDs start with S1000?

S1000 is the collection's short code: IDs read `S1000_<class>_<family>_<index>`, e.g. `S1000_FLOW_dysts-flow_020` (the Chua circuit), where FLOW is the class code used throughout the site. The prefix means IDs never begin with a digit, which keeps them safe as column, row or field names in spreadsheets and data frames.

## How was a particular series generated?

Open it (or, in the quiz, press Full details). This series' parameters lists every value drawn for it; Fixed settings lists the constants shared by its whole family; Family simulation details describes how values were sampled across the family. Each series also has its own named random stream (its seed), so it can be regenerated exactly.

## What does 'time-reversible' mean, and how can a chaotic series be time-reversible?

A series is time-reversible if its statistics are the same run backwards (in theory, for an infinitely long record): no feature of it could tell you which way time runs. That needs two things. First, reversible dynamics: played backwards, the system's motion is also a valid motion, once velocity-like variables have their signs flipped. Second, an observed variable that the reversal leaves unchanged. Chaos doesn't prevent it: conservative systems like the double pendulum, Hénon–Heiles or a billiard are chaotic without an attractor, and their positions are time-reversible. Dissipative chaos, like Lorenz or Rössler, contracts onto an attractor and is not. The Nosé–Hoover oscillator shows why the observed variable matters. Its dynamics are reversible, and its x and y are time-reversible series, but its thermostat variable z (the one observed here) changes sign under reversal and rises slowly but falls fast, so it is not.

## What does 'measurement noise' mean on a card?

White observation noise added on top of the clean dynamics, given as a fraction of the clean series' standard deviation. Many deterministic series carry a little, so they don't look unrealistically clean.

## How is τ chosen for the phase portrait and recurrence plot?

For a series that iterates a discrete-time rule (a map), τ = 1, one step of the rule. Otherwise τ is the lag at which the autocorrelation first drops below 1/e.

## What is the dashed line on the spectrum?

The spectrum of white noise with the same variance. A spectrum flat along it means no linear memory; one falling away (red) means correlation across time; peaks mean periodicity. The spectrum is a Welch estimate from 256-sample Hann-windowed segments with 50% overlap.

## How were the hctsa features computed, and how is 'similar dynamics' measured?

With hctsa (commit b1759834) in MATLAB R2025a on NCI Gadi: 7077 features per series, of which about 6100 are well-behaved across the collection. Similarity uses all of those, each robust-sigmoid normalised and z-scored, with Euclidean distance. The map shows a t-SNE or UMAP of the same space.

## What do the quiz's 'near match' and 'close match' tags mean?

How far a wrong option sits from the right answer in hctsa feature space. A near match is closer than a typical series' nearest neighbour (about 61); a close match is within about 68; a loose match is among its 16 closest series from other families; far apart is anything beyond.

## Why isn't white noise used as the base for the downsampled or heavy-noise transforms?

Because it shows nothing about the transform: downsampled white noise only reveals the anti-aliasing filter, and white noise under white noise is still white noise. Those families draw their bases from structured processes instead.

## How do I cite the collection?

Please cite the dataset: Fulcher, B. D. (2026). The 1000×1000 collection: 1000 synthetic time series from 133 dynamical processes. figshare. Dataset. [https://doi.org/10.6084/m9.figshare.34013331](https://doi.org/10.6084/m9.figshare.34013331). If you use the hctsa features, please also cite Fulcher & Jones, *Cell Systems* 5, 527 (2017). The Data page has the citation and all the download files.
