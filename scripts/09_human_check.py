"""Step 11: human "gold standard" check of Claude and VADER.

Step A (create the file to label):   python scripts/09_human_check.py --create
   -> data/processed/human_check.csv      (YOU fill this in: only comment text, no answers)
   -> data/processed/human_check_key.csv  (hidden answers: do NOT open until you're done)

Step B (after labeling):             python scripts/09_human_check.py --score
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from hype.config import RAW_DIR

PROC_DIR = RAW_DIR.parent / "processed"
TO_LABEL = PROC_DIR / "human_check.csv"
KEY = PROC_DIR / "human_check_key.csv"
N_TOTAL = 50
SEED = 7
BOOL_COLS = ["excitement", "skepticism", "sarcasm"]


def create():
    if TO_LABEL.exists():
        raise SystemExit(f"{TO_LABEL.name} already exists. Delete it first if you really want a new sample.")
    feats = pd.read_csv(PROC_DIR / "comment_features.csv", encoding="utf-8-sig")
    llm = pd.read_csv(PROC_DIR / "llm_labels.csv", encoding="utf-8-sig")
    df = feats.merge(llm, on="comment_id", how="inner")

    per_game = -(-N_TOTAL // df["game"].nunique())               # about equal per game
    sample = (df.groupby("game", group_keys=False)
                .sample(n=per_game, random_state=SEED)
                .sample(frac=1, random_state=SEED)               # shuffle so games are mixed
                .head(N_TOTAL)
                .reset_index(drop=True))
    sample.insert(0, "check_id", range(1, len(sample) + 1))

    sheet = sample[["check_id", "text_clean"]].copy()
    sheet["sentiment"] = ""          # positive / negative / neutral / mixed
    for c in BOOL_COLS:
        sheet[c] = ""                # 1 = yes, 0 = no
    sheet.to_csv(TO_LABEL, index=False, encoding="utf-8-sig")

    key_cols = ["check_id", "comment_id", "game", "sentiment", "has_skepticism", "has_excitement",
                "llm_sentiment", "llm_excitement", "llm_skepticism", "llm_sarcasm"]
    sample[key_cols].to_csv(KEY, index=False, encoding="utf-8-sig")
    print(f"Created {TO_LABEL.name} ({len(sheet)} comments) and {KEY.name}.")
    print("Fill in human_check.csv in Excel. Do NOT open the key file until you're done.")


def kappa_row(name, human, tool):
    return {"comparison": name, "agree_pct": round(100 * (human == tool).mean(), 1),
            "kappa": round(cohen_kappa_score(human, tool), 2)}


def score():
    human = pd.read_csv(TO_LABEL, encoding="utf-8-sig")
    key = pd.read_csv(KEY, encoding="utf-8-sig")
    df = key.merge(human.drop(columns=["text_clean"]), on="check_id", suffixes=("", "_human"))

    df["h_sent"] = df["sentiment_human"].astype(str).str.strip().str.lower().replace({"mixed": "neutral"})
    df = df[df["h_sent"].isin(["positive", "negative", "neutral"])]
    for c in BOOL_COLS:
        df[f"h_{c}"] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int).astype(bool)
    print(f"Scoring {len(df)} labeled comments\n")

    vader = pd.cut(df["sentiment"], [-1.01, -0.05, 0.05, 1.01],
                   labels=["negative", "neutral", "positive"]).astype(str)
    claude = df["llm_sentiment"].astype(str).str.lower().replace({"mixed": "neutral"})
    rows = [
        kappa_row("Sentiment: YOU vs Claude", df["h_sent"], claude),
        kappa_row("Sentiment: YOU vs VADER", df["h_sent"], vader),
        kappa_row("Skepticism: YOU vs Claude", df["h_skepticism"], df["llm_skepticism"].astype(bool)),
        kappa_row("Skepticism: YOU vs word list", df["h_skepticism"], df["has_skepticism"].astype(bool)),
        kappa_row("Excitement: YOU vs Claude", df["h_excitement"], df["llm_excitement"].astype(bool)),
        kappa_row("Excitement: YOU vs word list", df["h_excitement"], df["has_excitement"].astype(bool)),
        kappa_row("Sarcasm: YOU vs Claude", df["h_sarcasm"], df["llm_sarcasm"].astype(bool)),
    ]
    res = pd.DataFrame(rows)
    print(res.to_string(index=False))
    print("\nKappa guide: < 0.2 slight, 0.2-0.4 fair, 0.4-0.6 moderate, 0.6-0.8 substantial, > 0.8 almost perfect")
    res.to_csv(PROC_DIR / "human_check_results.csv", index=False)

    wrong = df[df["h_sent"] != claude]
    out = PROC_DIR / "human_vs_claude_disagreements.csv"
    wrong.merge(human[["check_id", "text_clean"]], on="check_id")[
        ["check_id", "game", "text_clean", "h_sent", "llm_sentiment"]].to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n{len(wrong)} sentiment disagreements with Claude saved to {out.name} (worth reading)")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true")
    group.add_argument("--score", action="store_true")
    args = parser.parse_args()
    create() if args.create else score()


if __name__ == "__main__":
    main()