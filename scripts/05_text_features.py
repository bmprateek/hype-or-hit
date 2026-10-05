"""Step 7: sentiment, hype/skepticism word lists, and words that separate flops from hits.

Run:  python scripts/05_text_features.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from hype.config import RAW_DIR
from hype.features import LEXICONS, add_comment_features

PROC_DIR = RAW_DIR.parent / "processed"
TRAIN_GROUPS = ["overhyped", "delivered"]          # GTA VI ("predict") is kept out of comparisons


def per_game_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per game: averages and % of comments with each feature."""
    agg = {"comments": ("text_clean", "size"),
           "avg_sentiment": ("sentiment", "mean"),
           "pct_positive": ("is_positive", "mean"),
           "pct_negative": ("is_negative", "mean")}
    for name in LEXICONS:
        agg[f"pct_{name}"] = (f"has_{name}", "mean")
    table = df.groupby(["game", "group"]).agg(**agg).reset_index()

    # Skepticism among the most-liked comments (top 10% by likes, per game)
    def top_liked_skeptic(g):
        cutoff = g["like_count"].quantile(0.9)
        return g.loc[g["like_count"] >= cutoff, "has_skepticism"].mean()
    top = df.groupby("game")[["like_count", "has_skepticism"]].apply(top_liked_skeptic)
    table["pct_skepticism_top_liked"] = table["game"].map(top)

    pct_cols = [c for c in table.columns if c.startswith("pct_")]
    table[pct_cols] = (table[pct_cols] * 100).round(1)          # show as percentages
    table["avg_sentiment"] = table["avg_sentiment"].round(3)
    order = {"overhyped": 0, "delivered": 1, "predict": 2}
    return table.sort_values(["group", "game"], key=lambda s: s.map(order) if s.name == "group" else s)


def distinctive_words(df: pd.DataFrame, top_n: int = 20, min_games: int = 3, min_docs: int = 40,
                      max_one_game: float = 0.5):
    """Words used relatively more in overhyped vs delivered pre-release comments ("lift").

    lift = (% of overhyped comments containing word) / (% of delivered comments containing word)
    To skip game names (e.g. 'wukong'), a word must appear in at least `min_games` different games.
    """
    train = df[df["group"].isin(TRAIN_GROUPS)]
    rows = []
    for game, group, text in train[["game", "group", "text_clean"]].itertuples(index=False):
        words = set(re.findall(r"[a-z][a-z']+", str(text).lower())) - ENGLISH_STOP_WORDS
        rows += [(game, group, w) for w in words]
    long = pd.DataFrame(rows, columns=["game", "group", "word"])

    n_comments = train.groupby("group").size()
    docs = long.groupby(["word", "group"]).size().unstack(fill_value=0)
    games_per_word = long.groupby("word")["game"].nunique()
    per_game = long.groupby(["word", "game"]).size()
    top_game_share = per_game.groupby("word").max() / per_game.groupby("word").sum()

    keep = ((games_per_word >= min_games)
            & (docs.sum(axis=1) >= min_docs)
            & (top_game_share <= max_one_game))
    docs = docs[keep.reindex(docs.index, fill_value=False)]
    rate_o = (docs["overhyped"] + 1) / n_comments["overhyped"]     # +1 avoids dividing by zero
    rate_d = (docs["delivered"] + 1) / n_comments["delivered"]
    out = pd.DataFrame({
        "pct_overhyped": (rate_o * 100).round(2),
        "pct_delivered": (rate_d * 100).round(2),
        "lift": (rate_o / rate_d).round(2),
    })
    return (out.sort_values("lift", ascending=False).head(top_n),
            out.sort_values("lift").head(top_n))


def main():
    df = pd.read_csv(PROC_DIR / "hype_sample.csv", encoding="utf-8-sig")
    print(f"Scoring {len(df):,} comments...")
    df = add_comment_features(df)
    df.to_csv(PROC_DIR / "comment_features.csv", index=False, encoding="utf-8-sig")

    table = per_game_table(df)
    table.to_csv(PROC_DIR / "game_text_features.csv", index=False)
    pd.set_option("display.width", 200)
    print("\n=== Per game (pct_ columns are % of comments) ===")
    print(table.to_string(index=False))

    print("\n=== Group averages ===")
    num_cols = [c for c in table.columns if c.startswith(("pct_", "avg_"))]
    print(table[table["group"].isin(TRAIN_GROUPS)].groupby("group")[num_cols].mean().round(2).T.to_string())

    more_o, more_d = distinctive_words(df)
    print("\n=== Words used MORE before overhyped launches (lift > 1) ===")
    print(more_o.to_string())
    print("\n=== Words used MORE before delivered launches (lift < 1) ===")
    print(more_d.to_string())
    print(f"\nSaved comment_features.csv and game_text_features.csv to {PROC_DIR}")


if __name__ == "__main__":
    main()