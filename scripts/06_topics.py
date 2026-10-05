"""Step 8: topic modeling (LDA) on pre-release comments.

The computer groups words that tend to appear together into "topics",
without being told what to look for. We then compare topic shares between
overhyped and delivered games.

Run:              python scripts/06_topics.py
Different count:  python scripts/06_topics.py --topics 10
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

from hype.config import RAW_DIR

PROC_DIR = RAW_DIR.parent / "processed"
SEED = 42
TRAIN_GROUPS = ["overhyped", "delivered"]

# Words that would make topics about "which game" instead of "what people say".
# Game titles, studios, and filler words common to every trailer comment section.
EXTRA_STOP = {
    "cyberpunk", "2077", "concord", "suicide", "squad", "kill", "justice", "league",
    "redfall", "elden", "ring", "baldur", "baldurs", "gate", "bg3", "wukong", "black",
    "myth", "hogwarts", "legacy", "gta", "grand", "theft", "auto", "vi", "rockstar",
    "cd", "projekt", "cdpr", "arkane", "bethesda", "rocksteady", "larian", "fromsoftware",
    "firewalk", "avalanche", "science",
    "game", "games", "trailer", "just", "like", "looks", "look", "really", "im", "dont",
    "don", "it's", "i'm", "can't", "cant", "gonna", "going", "got", "get", "make", "know",
    "think", "lol", "yeah", "oh", "wow", "video", "people", "time", "thing", "want",
}


def top_words(model, vocab, n=12):
    return [", ".join(vocab[i] for i in comp.argsort()[::-1][:n]) for comp in model.components_]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics", type=int, default=12, help="number of topics (K)")
    args = parser.parse_args()

    df = pd.read_csv(PROC_DIR / "hype_sample.csv", encoding="utf-8-sig")
    text = df["text_clean"].fillna("").str.lower()

    # 1. Turn comments into word counts (bag of words)
    vectorizer = CountVectorizer(
        stop_words=list(ENGLISH_STOP_WORDS | EXTRA_STOP),
        token_pattern=r"(?u)\b[a-z][a-z']{2,}\b",   # words of 3+ letters
        min_df=10,          # ignore words in fewer than 10 comments (typos, rare names)
        max_df=0.2,         # ignore words in more than 20% of comments (too common to help)
    )
    # Learn vocabulary and topics ONLY from the 8 games with known outcomes,
    # then apply them to every comment (including GTA VI). Learn first, predict after.
    is_train = df["group"].isin(TRAIN_GROUPS)
    vectorizer.fit(text[is_train])
    X_all = vectorizer.transform(text)
    vocab = np.array(vectorizer.get_feature_names_out())
    print(f"Topics learned from {is_train.sum():,} comments (8 games), "
          f"{X_all.shape[1]:,} words in vocabulary")

    # 2. Fit LDA (Latent Dirichlet Allocation) on training games only
    lda = LatentDirichletAllocation(n_components=args.topics, random_state=SEED,
                                    learning_method="batch", max_iter=20)
    lda.fit(X_all[is_train.to_numpy()])
    doc_topics = lda.transform(X_all)           # topic mix for every comment, incl. GTA VI
    words = top_words(lda, vocab)
    print("\n=== Topics (top words) ===")
    for k, w in enumerate(words):
        print(f"T{k:02d}: {w}")

    # 3. Topic share per game = average topic mix of its comments
    topic_cols = [f"T{k:02d}" for k in range(args.topics)]
    mix = pd.DataFrame(doc_topics, columns=topic_cols)
    mix["game"], mix["group"] = df["game"].values, df["group"].values
    df["main_topic"] = mix[topic_cols].idxmax(axis=1).values

    per_game = (mix.groupby(["group", "game"])[topic_cols].mean() * 100).round(1)
    pd.set_option("display.width", 250)
    print("\n=== Topic share per game (% of each game's conversation) ===")
    print(per_game.to_string())

    # 4. Which topics lean overhyped vs delivered?
    train = per_game.loc[TRAIN_GROUPS]
    by_group = train.groupby(level="group").mean().T
    by_group["ratio_o_vs_d"] = (by_group["overhyped"] / by_group["delivered"]).round(2)
    by_group["top_words"] = words
    by_group = by_group.sort_values("ratio_o_vs_d", ascending=False)
    print("\n=== Topics by group (ratio > 1 = more common before flops) ===")
    by_group[["delivered", "overhyped"]] = by_group[["delivered", "overhyped"]].round(1)
    print(by_group.to_string())

    # 5. Save results
    pd.DataFrame({"topic": topic_cols, "top_words": words}).to_csv(PROC_DIR / "topics.csv", index=False)
    per_game.reset_index().to_csv(PROC_DIR / "topic_share_per_game.csv", index=False)
    examples = (df.assign(weight=doc_topics.max(axis=1))
                  .sort_values("weight", ascending=False)
                  .groupby("main_topic").head(5)[["main_topic", "game", "weight", "text_clean"]]
                  .sort_values(["main_topic", "weight"], ascending=[True, False]))
    examples.to_csv(PROC_DIR / "topic_examples.csv", index=False, encoding="utf-8-sig")
    print(f"\nSaved topics.csv, topic_share_per_game.csv, topic_examples.csv to {PROC_DIR}")


if __name__ == "__main__":
    main()