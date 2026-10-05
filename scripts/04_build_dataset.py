"""Step 6: clean and combine raw data into analysis-ready files in data/processed/.

Run:  python scripts/04_build_dataset.py
Optional: --per-game 3000   (sample size per game for hype_sample.csv)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from hype.config import RAW_DIR, load_games
from hype.text import clean_text, is_english

PROC_DIR = RAW_DIR.parent / "processed"
SEED = 42          # fixed seed = same random sample every run (reproducible)
MIN_WORDS = 3


def add_text_features(df: pd.DataFrame, text_col: str) -> pd.DataFrame:
    """Add cleaned text, word count, English flag and duplicate flag."""
    df["text_clean"] = df[text_col].map(clean_text)
    df["n_words"] = df["text_clean"].str.split().str.len().fillna(0).astype(int)
    df["is_english"] = df["text_clean"].map(is_english)
    key = df["text_clean"].str.lower()
    df["is_duplicate"] = key.groupby(df["game"]).transform(lambda s: s.duplicated())
    return df


def build_youtube(per_game: int, game_info: pd.DataFrame):
    files = sorted((RAW_DIR / "youtube").glob("*.csv"))
    yt = pd.concat([pd.read_csv(f, encoding="utf-8-sig") for f in files], ignore_index=True)

    if "edited_after_release" not in yt.columns:          # older files may lack it
        yt["edited_after_release"] = False
    yt["edited_after_release"] = yt["edited_after_release"].fillna(False).astype(bool)
    yt["pre_release"] = yt["pre_release"].astype(bool)

    yt = add_text_features(yt, "text")
    yt["usable_hype"] = (
        yt["pre_release"]
        & ~yt["edited_after_release"]
        & yt["is_english"]
        & (yt["n_words"] >= MIN_WORDS)
        & ~yt["is_duplicate"]
    )
    yt = yt.merge(game_info, on="game", how="left")
    yt.to_csv(PROC_DIR / "youtube_clean.csv", index=False, encoding="utf-8-sig")

    usable = yt[yt["usable_hype"]]
    # Each comment gets a fixed pseudo-random number from its own ID, so one game's
    # sample never changes when another game's data changes
    rand_key = pd.util.hash_pandas_object(usable["comment_id"], index=False)
    sample = usable.assign(_r=rand_key).sort_values("_r").groupby("game").head(per_game).drop(columns="_r")
    sample.to_csv(PROC_DIR / "hype_sample.csv", index=False, encoding="utf-8-sig")

    # Summary: how many comments each rule removed, per game
    pre = yt[yt["pre_release"]]
    summary = pd.DataFrame({
        "total": yt.groupby("game").size(),
        "pre_release": pre.groupby("game").size(),
        "edited_after": pre.groupby("game")["edited_after_release"].sum(),
        "not_english": (~pre["is_english"]).groupby(pre["game"]).sum(),
        "too_short": (pre["n_words"] < MIN_WORDS).groupby(pre["game"]).sum(),
        "duplicates": pre.groupby("game")["is_duplicate"].sum(),
        "usable": usable.groupby("game").size(),
        "in_sample": sample.groupby("game").size(),
    }).fillna(0).astype(int)
    print("\nYouTube comments (rules can overlap, so removals don't add up exactly):")
    print(summary.to_string())
    return sample


def build_steam(game_info: pd.DataFrame):
    files = sorted((RAW_DIR / "steam").glob("*_launch_reviews.csv"))
    st = pd.concat([pd.read_csv(f, encoding="utf-8-sig") for f in files], ignore_index=True)
    st = add_text_features(st, "text")
    st["usable"] = st["is_english"] & (st["n_words"] >= MIN_WORDS) & ~st["is_duplicate"]
    st = st.merge(game_info, on="game", how="left")
    st.to_csv(PROC_DIR / "steam_reviews_clean.csv", index=False, encoding="utf-8-sig")

    print("\nSteam launch reviews:")
    print(st.groupby("game").agg(reviews=("text", "size"), usable=("usable", "sum"),
                                 pct_recommended=("voted_up", "mean")).round(2).to_string())


def build_games(game_info: pd.DataFrame):
    steam = pd.read_csv(RAW_DIR / "steam_outcomes.csv").drop(columns=["group"], errors="ignore")
    manual = pd.read_csv(RAW_DIR / "manual_outcomes.csv")
    games = game_info.merge(steam, on="game", how="left").merge(manual, on="game", how="left")
    games.to_csv(PROC_DIR / "games.csv", index=False)
    print(f"\nSaved games.csv ({len(games)} games, {games.shape[1]} columns)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-game", type=int, default=3000)
    args = parser.parse_args()
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    game_info = pd.DataFrame([{"game": g.slug, "name": g.name, "group": g.group,
                               "release_date": g.release_date} for g in load_games()])

    build_youtube(args.per_game, game_info)
    build_steam(game_info)
    build_games(game_info)
    print(f"\nAll processed files are in {PROC_DIR}")


if __name__ == "__main__":
    main()