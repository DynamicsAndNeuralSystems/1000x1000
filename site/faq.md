<!--
FAQ for the 1000×1000 website, shown at #/faq in this order.
Format: each "## " line is a question; the paragraphs under it (separated by blank lines) are its answer.
Inline: **bold**, *italic*, `code`, [link text](https://…), and maths as \( … \) (KaTeX).
The first question starts open. After editing: commit, then run scripts/deploy_pages.sh.
-->

## What is the 1000×1000 collection?

1000 simulated time series, each 1000 samples long, from 133 generating mechanisms in 13 classes: noise and linear processes, maps, chaotic flows, oscillators, stochastic differential equations, point processes, measurement effects, and models of hearts, brains, climate and ecosystems. It aims to provide a unified resource for understanding the types of dynamical patterns we have models for. As well as being educational, uses include testing time-series methods on a wider range of data types and matching patterns in real data to underlying mechanisms.

## Why do the series IDs start with S1000?

S1000 is the collection's short code: IDs read `S1000_<class>_<family>_<index>`, e.g., `S1000_FLOW_dysts-flow_020` (the Chua circuit), where FLOW is the class code used throughout the site. The prefix means IDs never begin with a digit, which keeps them safe as column, row or field names in spreadsheets and data frames.

## How was a particular series generated?

Open it (or press 'Full details' in the quiz) to find out! Each series also has its own named random stream (its seed), so it can be regenerated exactly.

## What does 'time-reversible' mean?

Here we've used the statistical definition that a series is time-reversible if its statistics are the same run backwards (in theory, for an infinitely long record), so no statistical property could tell you which way time runs.

## What does 'measurement noise' mean?

White observation noise added on top of the clean dynamics, given as a fraction of the clean series' standard deviation. Many deterministic series carry a small amount of additive noise, so they don't look unrealistically clean.

## How is τ chosen for the phase portrait and recurrence plot?

For a series that iterates a discrete-time rule (a map), τ = 1, one step of the rule. Otherwise τ is the lag at which the autocorrelation first drops below 1/e.

## What is the dashed line on the spectrum?

The spectrum of white noise with the same variance. A spectrum flat along it means no linear memory; one falling away (red) means correlation across time; peaks mean periodicity. The spectrum is a Welch estimate from 256-sample Hann-windowed segments with 50% overlap.

## How were the hctsa features computed, and how is 'similar dynamics' measured?

With hctsa (commit b1759834, a v3.0 development version) in MATLAB R2025a on a supercomputer (NCI Gadi): 7077 features per series, of which about 6100 are well-behaved across the collection. Similarity quantification is based on the full set of these features (each robust-sigmoid normalized and z-scored, with Euclidean distance). The map shows a t-SNE or UMAP dimension reduction of this normalized feature space.

## What do the quiz's 'near match' and 'close match' tags mean?

How far a wrong option sits from the right answer in hctsa feature space. A near match is closer than a typical series' nearest neighbor (about 61); a close match is within about 68; a loose match is among its 16 closest series from other families; far apart is anything beyond.

## Does the site track me?

No. The site counts anonymous visits with [GoatCounter](https://www.goatcounter.com): which pages and series are viewed, and roughly where visitors come from. It sets no cookies and stores no personal information. Your quiz scores stay in your own browser.

## How do I cite the collection?

Please cite the dataset: Fulcher, B. D. (2026). The 1000×1000 collection: 1000 synthetic time series from 133 dynamical processes. figshare. Dataset. [https://doi.org/10.6084/m9.figshare.34013331](https://doi.org/10.6084/m9.figshare.34013331).

If you use the hctsa features, please also cite Fulcher & Jones, *Cell Systems* 5, 527 (2017).

The Data page has the citation and all the download files.
