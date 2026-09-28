"""The 1000×1000 collection (internal name Synthetic1000): a simulated counterpart to Empirical1000.

1000 time series, 1000 samples each, spanning the dynamical processes that
have been devised.

Everything regenerates bit-identically from names: see ``rng.py``.
"""
T = 1000            # samples per series; the corpus is defined at this length
CORPUS = "synthetic1000"   # root of every seed name
