"""Step 9: how certain are our findings?

1. Confidence intervals: a +/- range for each game's numbers
2. Permutation test: could the flop vs hit gap be luck, given only 8 games?
3. GTA VI broken down by trailer (Trailer 1, Trailer 2, Gameplay reveal)

Run:  python scripts/07_stats.py
"""
import re
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from hype.config import RAW_DIR
from hype.features import LEXICONS

PROC_DIR = RAW_DIR.parent / "processed"
TRAIN_GROUPS = ["overhyped", "delivered"]

# Topic numbers from the LAST run of 06_topics.py. Update these if you re-run it and they change.
ROBUST_TOPICS = {"T06": "topic_generic_comparisons", "T10": "topic_live_service"}

GTA_TRAILERS = {"QdBZY2fkU-0": "1. Trailer 1 (Dec 2023)",
                "VQRLujxTm3c": "2. Trailer 2 (May 2025)"}   # anything else = gameplay reveal

# Skepticism WITHOUT delay words, so waiting complaints don't count as doubt
_no_delay_terms = [t for t in LEXICONS["skepticism"] if not t.startswith("delay")]
NO_DELAY = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in _no_delay_terms) + r")", re.IGNORECASE)

PCT_METRICS = {                       # column in comment_features -> name in output
    "is_negative": "pct_negative",
    "is_positive": "pct_positive",
    "has_excitement": "pct_excitement",
    "has_skepticism": "pct_skepticism",
    "skeptic_no_delay": "pct_skepticism_no_delay",
}


def ci_table(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Value and 95% confidence interval for each metric, per group in `by`.

    For a percentage p from n comments:  p +/- 1.96 * sqrt(p * (1 - p) / n)
    For an average:                      mean +/- 1.96 * std / sqrt(n)
    """
    rows = []
    for key, g in df.groupby(by):
        n = len(g)
        row = {by: key, "n": n}
        for col, name in PCT_METRICS.items():
            p = g[col].mean()
            half = 1.96 * np.sqrt(p * (1 - p) / n)
            row[name] = f"{100 * p:.1f} ± {100 * half:.1f}"
        m, s = g["sentiment"].mean(), g["sentiment"].std()
        row["avg_sentiment"] = f"{m:.3f} ± {1.96 * s / np.sqrt(n):.3f}"
        rows.append(row)
    return pd.DataFrame(rows)


def permutation_test(per_game: pd.Series, groups: pd.Series):
    """Exact permutation test on the 8 games.

    Try every possible way to split the 8 games into two groups of 4 (70 ways).
    p-value = share of splits with a gap at least as big as the real one.
    With 8 games, the smallest possible p-value is 2/70 = 0.029.
    """
    games = list(per_game.index)
    values = per_game.to_numpy()
    real_o = groups.to_numpy() == "overhyped"
    observed = values[real_o].mean() - values[~real_o].mean()

    gaps = []
    for idx in combinations(range(len(games)), int(real_o.sum())):
        mask = np.zeros(len(games), dtype=bool)
        mask[list(idx)] = True
        gaps.append(values[mask].mean() - values[~mask].mean())
    p = np.mean(np.abs(gaps) >= abs(observed) - 1e-12)
    return observed, p


def main():
    df = pd.read_csv(PROC_DIR / "comment_features.csv", encoding="utf-8-sig")
    df["skeptic_no_delay"] = df["text_clean"].fillna("").str.contains(NO_DELAY)
    pd.set_option("display.width", 250)

    # 1. Confidence intervals per game
    print("=== 95% confidence intervals per game (value ± margin) ===")
    ci = ci_table(df, "game")
    ci = ci.merge(df[["game", "group"]].drop_duplicates(), on="game").sort_values(["group", "game"])
    print(ci.to_string(index=False))
    ci.to_csv(PROC_DIR / "confidence_intervals.csv", index=False, encoding="utf-8-sig")

    # 2. Permutation tests (unit = game, 4 flops vs 4 hits)
    per_game = df.groupby("game").agg(
        group=("group", "first"),
        pct_negative=("is_negative", "mean"),
        pct_positive=("is_positive", "mean"),
        pct_excitement=("has_excitement", "mean"),
        pct_skepticism=("has_skepticism", "mean"),
        pct_skepticism_no_delay=("skeptic_no_delay", "mean"),
        pct_nostalgia=("has_nostalgia", "mean"),
        avg_sentiment=("sentiment", "mean"),
    )
    topic_file = PROC_DIR / "topic_share_per_game.csv"
    if topic_file.exists():
        topics = pd.read_csv(topic_file).set_index("game")
        for t, name in ROBUST_TOPICS.items():
            if t in topics.columns:
                per_game[name] = topics[t] / 100

    train = per_game[per_game["group"].isin(TRAIN_GROUPS)]
    results = []
    for col in [c for c in train.columns if c != "group"]:
        gap, p = permutation_test(train[col], train["group"])
        scale = 1 if col == "avg_sentiment" else 100
        results.append({
            "metric": col,
            "flops_avg": round(train.loc[train.group == "overhyped", col].mean() * scale, 2),
            "hits_avg": round(train.loc[train.group == "delivered", col].mean() * scale, 2),
            "gap": round(gap * scale, 2),
            "p_value": round(p, 3),
            "verdict": "strong (p<0.05)" if p < 0.05 else ("suggestive (p<0.15)" if p < 0.15 else "could be chance"),
        })
    res = pd.DataFrame(results).sort_values("p_value")
    print("\n=== Flops vs hits: is the gap bigger than chance? (exact permutation test, 8 games) ===")
    print(res.to_string(index=False))
    res.to_csv(PROC_DIR / "permutation_tests.csv", index=False)

    # 3. GTA VI by trailer
    gta = df[df["game"] == "gta-vi"].copy()
    if not gta.empty:
        gta["trailer"] = gta["video_id"].map(GTA_TRAILERS).fillna("3. Gameplay reveal (Aug 2026)")
        print("\n=== GTA VI by trailer ===")
        print(ci_table(gta, "trailer").to_string(index=False))

    print(f"\nSaved confidence_intervals.csv and permutation_tests.csv to {PROC_DIR}")


if __name__ == "__main__":
    main()