"""Step 4: collect Steam launch outcomes (scores, monthly history, launch reviews).

Run:              python scripts/03_collect_steam.py
Some games only:  python scripts/03_collect_steam.py --games redfall
Re-download reviews: add --force
"""
import argparse
import sys
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from hype.config import RAW_DIR, load_games, select_games
from hype.steam import iter_reviews, monthly_history, review_summary

DAYS_BEFORE = 3     # include early-access / deluxe-edition launch days
WEEK_AFTER = 7
MONTH_AFTER = 30


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", nargs="*", help="game slugs (default: all)")
    parser.add_argument("--max-reviews", type=int, default=2000, help="launch reviews per game")
    parser.add_argument("--force", action="store_true", help="re-download review texts")
    args = parser.parse_args()

    review_dir = RAW_DIR / "steam"
    review_dir.mkdir(parents=True, exist_ok=True)
    outcomes, monthly = [], []

    for g in select_games(load_games(), args.games):
        if not g.steam_appid:
            print(f"\n{g.name}: not on Steam, skipping")
            continue
        print(f"\n=== {g.name} (appid {g.steam_appid}, released {g.release_date}) ===")

        start = g.release_dt - timedelta(days=DAYS_BEFORE)
        week_end = g.release_dt + timedelta(days=WEEK_AFTER)
        month_end = g.release_dt + timedelta(days=MONTH_AFTER)

        try:
            week = review_summary(g.steam_appid, start, week_end)
            time.sleep(1)
            month = review_summary(g.steam_appid, start, month_end)
            time.sleep(1)
            alltime = review_summary(g.steam_appid)
            time.sleep(1)
            hist = monthly_history(g.steam_appid)
        except RuntimeError as e:
            print(f"  FAILED: {e}  (game may be delisted)")
            continue

        outcomes.append({
            "game": g.slug, "group": g.group,
            "week_positive": week["positive"], "week_negative": week["negative"],
            "week_pct_positive": week["pct_positive"],
            "month_total": month["total"], "month_pct_positive": month["pct_positive"],
            "alltime_total": alltime["total"], "alltime_pct_positive": alltime["pct_positive"],
        })
        monthly += [{"game": g.slug, **row} for row in hist]
        print(f"  launch week: {week['pct_positive']}% positive ({week['total']:,} reviews)")
        print(f"  first 30d  : {month['pct_positive']}% positive ({month['total']:,} reviews)")
        print(f"  all time   : {alltime['pct_positive']}% positive ({alltime['total']:,} reviews)")

        out = review_dir / f"{g.slug}_launch_reviews.csv"
        if out.exists() and not args.force:
            print("  launch reviews: already downloaded, skipping")
            continue
        days = DAYS_BEFORE + WEEK_AFTER
        per_day = max(1, args.max_reviews // days)
        rows, day = [], start
        while day < week_end:
            nxt = min(day + timedelta(days=1), week_end)
            rows += list(iter_reviews(g.steam_appid, day, nxt, max_reviews=per_day))
            day = nxt
        rows = list({r["review_id"]: r for r in rows}.values())   # drop any boundary duplicates
        df = pd.DataFrame(rows)
        if not df.empty:
            df.insert(0, "game", g.slug)
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"  launch reviews: {len(df):,} saved -> {out.name}")

    if outcomes:
        pd.DataFrame(outcomes).to_csv(RAW_DIR / "steam_outcomes.csv", index=False)
        pd.DataFrame(monthly).to_csv(RAW_DIR / "steam_monthly.csv", index=False)
        print(f"\nSaved steam_outcomes.csv ({len(outcomes)} games) and steam_monthly.csv")
        print(pd.DataFrame(outcomes)[["game", "group", "week_pct_positive",
                                      "month_pct_positive", "alltime_pct_positive"]].to_string(index=False))


if __name__ == "__main__":
    main()