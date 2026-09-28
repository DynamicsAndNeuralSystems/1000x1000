"""Seed contract.

Every random draw is addressed by a *name*: ``(CORPUS, class, family, index,
...)``. The name is hashed with BLAKE2b to a 64-bit integer that seeds a
PCG64 generator. BLAKE2b and PCG64 are both fully specified, so the same name
gives the same stream on any platform; and because streams are keyed by name
rather than by draw order, adding, removing or re-ordering families changes
nobody else's series. Regenerating series 37 of one family alone reproduces
it exactly. The seed of every series is written into its metadata.
"""
from __future__ import annotations

from hashlib import blake2b
from typing import Any

import numpy as np

from . import CORPUS


def seed_of(*parts: Any) -> int:
    key = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(blake2b(key, digest_size=8).digest(), "little")


def name_of(*parts: Any) -> str:
    return "/".join(str(p) for p in parts)


def rng_for(*parts: Any) -> np.random.Generator:
    """A generator addressed by name under the corpus root."""
    return np.random.Generator(np.random.PCG64(seed_of(CORPUS, *parts)))
