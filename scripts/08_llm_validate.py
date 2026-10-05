"""Step 10: validate our findings with an LLM (Claude Haiku) as a second, blind annotator.

1. Sample comments per game (GTA VI: gameplay reveal only)
2. Claude labels each one (it never sees the game name or outcome)
3. Compare Claude's labels with VADER and our word lists (agreement)
4. Re-run the flop vs hit permutation test using Claude's labels

Run:            python scripts/08_llm_validate.py
Smaller test:   python scripts/08_llm_validate.py --per-game 25
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from hype.config import RAW_DIR
from hype.llm import LABELS, get_client, label_batch
from hype.stats import permutation_test

PROC_DIR = RAW_DIR.parent / "processed"
OUT = PROC_DIR / "llm_labels.csv"
GTA_EARLY_TRAILERS = {"QdBZY2fkU-0", "VQRLujxTm3c"}    # excluded: use the gameplay reveal only
BATCH = 50


def build_sample(per_game: int) -> pd.DataFrame:
    df = pd.read_csv(PROC_DIR / "comment_features.csv", encoding="utf-8-sig")
    df = df[~((df["game"] == "gta-vi") & df["video_id"].isin(GTA_EARLY_TRAILERS))]
    key = pd.util.hash_pandas_object(df["comment_id"], index=False)     # stable random order
    return df.assign(_r=key).sort_values("_r").groupby("game").head(per_game).drop(columns="_r")


def run_labeling(sample: pd.DataFrame) -> pd.DataFrame:
    """Label comments not yet in llm_labels.csv (so re-running continues where it stopped)."""
    done = pd.read_csv(OUT, encoding="utf-8-sig") if OUT.exists() else pd.DataFrame(columns=["comment_id"])
    todo = sample[~sample["comment_id"].isin(done["comment_id"])]
    print(f"{len(done):,} already labeled, {len(todo):,} to go ({-(-len(todo) // BATCH)} requests)")
    if todo.empty:
        return done

    client, model = get_client()
    print(f"Using model: {model}")
    todo = todo.sample(frac=1, random_state=42)    # mix games inside each batch (helps blinding)
    for start in range(0, len(todo), BATCH):
        chunk = todo.iloc[start:start + BATCH]
        labels = label_batch(client, model, chunk["text_clean"].astype(str).tolist())
        new = pd.DataFrame(labels).add_prefix("llm_")
        new.insert(0, "comment_id", chunk["comment_id"].to_numpy())
        new.to_csv(OUT, mode="a", header=not OUT.exists(), index=False, encoding="utf-8-sig")
        print(f"  {min(start + BATCH, len(todo)):,}/{len(todo):,} labeled")
    return pd.read_csv(OUT, encoding="utf-8-sig")


def agreement(df: pd.DataFrame):
    """How often do VADER / word lists agree with Claude? Cohen's kappa: 0 = chance, 1 = perfect."""
    vader_class = pd.cut(df["sentiment"], [-1.01, -0.05, 0.05, 1.01], labels=["negative", "neutral", "positive"])
    llm_class = df["llm_sentiment"].replace({"mixed": "neutral"})
    rows = [{"check": "Sentiment: VADER vs Claude (pos / neutral / neg)",
             "agree_pct": round(100 * (vader_class.astype(str) == llm_class).mean(), 1),
             "kappa": round(cohen_kappa_score(vader_class.astype(str), llm_class), 2)}]
    for ours, theirs in [("has_skepticism", "llm_skepticism"), ("has_excitement", "llm_excitement")]:
        a, b = df[ours].astype(bool), df[theirs].astype(bool)
        rows.append({"check": f"{ours} vs {theirs}",
                     "agree_pct": round(100 * (a == b).mean(), 1),
                     "kappa": round(cohen_kappa_score(a, b), 2)})
    print("\n=== Agreement: our tools vs Claude ===")
    print(pd.DataFrame(rows).to_string(index=False))
    print("Kappa guide: < 0.2 slight, 0.2-0.4 fair, 0.4-0.6 moderate, 0.6-0.8 substantial, > 0.8 almost perfect")

    sarcastic = df[df["llm_sarcasm"].astype(bool)]
    if len(sarcastic):
        fooled = (sarcastic["sentiment"] >= 0.05) & (sarcastic["llm_sentiment"] == "negative")
        print(f"\nSarcasm: Claude flagged {len(sarcastic)} comments as sarcastic. "
              f"VADER called {fooled.sum()} of them positive when Claude read them as negative.")


def per_game_and_tests(df: pd.DataFrame):
    df = df.assign(
        llm_negative=df["llm_sentiment"] == "negative",
        llm_positive=df["llm_sentiment"] == "positive",
    )
    cols = ["llm_negative", "llm_positive", "llm_excitement", "llm_skepticism",
            "llm_sarcasm", "llm_comparison", "llm_live_service"]
    per_game = df.groupby(["game", "group"])[cols].mean().mul(100).round(1).reset_index()
    per_game.insert(2, "n", df.groupby("game").size().reindex(per_game["game"]).to_numpy())
    order = {"overhyped": 0, "delivered": 1, "predict": 2}
    per_game = per_game.sort_values(["group", "game"], key=lambda s: s.map(order) if s.name == "group" else s)
    print("\n=== Claude's labels per game (% of comments) ===")
    print(per_game.to_string(index=False))
    per_game.to_csv(PROC_DIR / "llm_per_game.csv", index=False)

    train = per_game[per_game["group"].isin(["overhyped", "delivered"])].set_index("game")
    rows = []
    for c in cols:
        gap, p = permutation_test(train[c], train["group"])
        rows.append({"metric": c, "flops_avg": round(train.loc[train.group == "overhyped", c].mean(), 1),
                     "hits_avg": round(train.loc[train.group == "delivered", c].mean(), 1),
                     "gap": round(gap, 1), "p_value": round(p, 3)})
    res = pd.DataFrame(rows).sort_values("p_value")
    print("\n=== Flops vs hits using Claude's labels (exact permutation test) ===")
    print(res.to_string(index=False))
    res.to_csv(PROC_DIR / "llm_permutation_tests.csv", index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-game", type=int, default=200)
    args = parser.parse_args()

    sample = build_sample(args.per_game)
    labels = run_labeling(sample)
    df = sample.merge(labels, on="comment_id", how="inner")
    print(f"\nAnalyzing {len(df):,} labeled comments")
    agreement(df)
    per_game_and_tests(df)


if __name__ == "__main__":
    main()