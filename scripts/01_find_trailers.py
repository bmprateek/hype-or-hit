"""Step 2: suggest official trailers for each game (uploaded before its release).

Run:               python scripts/01_find_trailers.py
Some games only:   python scripts/01_find_trailers.py --games cyberpunk-2077 elden-ring
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # lets us import hype.*

import pandas as pd

from hype.config import RAW_DIR, load_games, select_games, youtube_api_key
from hype.youtube import QuotaExceeded, search_trailers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", nargs="*", help="game slugs (default: all)")
    parser.add_argument("--n", type=int, default=5, help="suggestions per game")
    args = parser.parse_args()

    key = youtube_api_key()
    games = select_games(load_games(), args.games)
    rows = []

    for g in games:
        print(f"\n=== {g.name} (released {g.release_date}) ===")
        try:
            hits = search_trailers(g.search_query, g.release_dt, key, must_contain=g.match, n=args.n)
        except QuotaExceeded as e:
            print(f"STOPPED: {e}")
            break
        for h in hits:
            print(f"  {h['video_id']}  {h['views']:>12,} views  {str(h['comments']):>8} comments  "
                  f"{h['uploaded']}  [{h['channel']}]  {h['title'][:60]}")
            rows.append({"game": g.slug, **h})

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "trailer_candidates.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nSaved {len(rows)} suggestions to {out}")


if __name__ == "__main__":
    main()