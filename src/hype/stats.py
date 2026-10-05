"""Shared statistics helpers."""
from itertools import combinations

import numpy as np
import pandas as pd


def permutation_test(values: pd.Series, groups: pd.Series, positive: str = "overhyped"):
    """Exact permutation test: gap between group means, and its p-value.

    Tries every way to split the games into two groups of the same sizes.
    p-value = share of splits with a gap at least as big as the real one.
    """
    v = values.to_numpy(dtype=float)
    real = groups.to_numpy() == positive
    observed = v[real].mean() - v[~real].mean()
    gaps = []
    for idx in combinations(range(len(v)), int(real.sum())):
        mask = np.zeros(len(v), dtype=bool)
        mask[list(idx)] = True
        gaps.append(v[mask].mean() - v[~mask].mean())
    return observed, float(np.mean(np.abs(gaps) >= abs(observed) - 1e-12))