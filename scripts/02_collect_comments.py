"""Step 3: download YouTube comments for each game's chosen trailers.

Run:               python scripts/02_collect_comments.py
Some games only:   python scripts/02_collect_comments.py --games redfall
Re-download:       add --force
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from hype.config import RAW_DIR, load_games, select_games, youtube_api_key
from hype.youtube import CommentsDisabled, QuotaExceeded, iter_comments

OUT_DIR = RAW_DIR / "youtube"


def collect_video(game, video_id, key, max_comments):
    """Download one video's comments and label them pre/post release."""
    rows = []
    for c in iter_comments(video_id, key, max_comments=max_comments):
        rows.append(c)
        if len(rows) % 5000 == 0:
            print(f"    ...{len(rows):,} comments so far")

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates(subset="comment_id")            # paging can repeat a comment
    df.insert(0, "game", game.slug)
    df.insert(1, "video_id", video_id)
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    df["updated_at"] = pd.to_datetime(df["updated_at"], utc=True)
    release = pd.Timestamp(game.release_dt)
    df["days_to_release"] = -(df["published_at"] - release).dt.total_seconds() / 86400
    df["pre_release"] = df["published_at"] < release
    # Posted before launch but edited after: text may contain hindsight, so exclude from training
    df["edited_after_release"] = df["pre_release"] & (df["updated_at"] >= release)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", nargs="*", help="game slugs (default: all)")
    parser.add_argument("--max-comments", type=int, default=100_000,
                        help="safety cap per video (default 100,000)")
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args()

    key = youtube_api_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for g in select_games(load_games(), args.games):
        if not g.trailers:
            print(f"\n{g.name}: no trailers in games.yaml, skipping")
            continue
        print(f"\n=== {g.name} (released {g.release_date}) ===")

        for vid in g.trailers:
            out = OUT_DIR / f"{g.slug}__{vid}.csv"
            if out.exists() and not args.force:
                print(f"  {vid}: already downloaded, skipping")
                continue

            print(f"  {vid}: downloading...")
            try:
                df = collect_video(g, vid, key, args.max_comments)
            except CommentsDisabled:
                print(f"  {vid}: comments are disabled, pick another trailer")
                continue
            except QuotaExceeded as e:
                print(f"\nSTOPPED: {e}\nRe-run the same command tomorrow; finished videos are kept.")
                return

            if df.empty:
                print(f"  {vid}: no comments returned")
                continue
            df.to_csv(out, index=False, encoding="utf-8-sig")   # utf-8-sig = emojis open fine in Excel
            pre = int(df["pre_release"].sum())
            print(f"  {vid}: {len(df):,} comments ({pre:,} pre-release, {len(df) - pre:,} post) -> {out.name}")


if __name__ == "__main__":
    main()