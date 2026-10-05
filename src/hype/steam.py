"""Small helper for Steam's public store review API (no key or quota needed)."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

STORE = "https://store.steampowered.com"
HEADERS = {"User-Agent": "hype-or-hit student research project"}


def _get(path: str, params: dict) -> dict:
    """One Steam request, with polite retries when Steam is busy."""
    for attempt in range(4):
        r = requests.get(f"{STORE}/{path}", params=params, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            d = r.json()
            if d.get("success") == 1:
                return d
            raise RuntimeError(f"Steam said success={d.get('success')} for {path}")
        if r.status_code == 429 or r.status_code >= 500:   # too many requests / server issue
            time.sleep(5 * (attempt + 1))
            continue
        raise RuntimeError(f"Steam error {r.status_code} for {path}")
    raise RuntimeError(f"Steam kept failing for {path}")


def _range_params(start: datetime | None, end: datetime | None) -> dict:
    """Date filter params. No dates = all time."""
    if start is None or end is None:
        return {}
    return {"start_date": int(start.timestamp()), "end_date": int(end.timestamp()),
            "date_range_type": "include"}


def review_summary(appid: int, start: datetime | None = None, end: datetime | None = None,
                   language: str = "english") -> dict:
    """Positive / negative review counts for a date range (or all time)."""
    d = _get(f"appreviews/{appid}", {
        "json": 1, "filter": "all", "language": language,
        "purchase_type": "all", "num_per_page": 1, **_range_params(start, end),
    })
    q = d["query_summary"]
    pos, neg = q.get("total_positive", 0), q.get("total_negative", 0)
    return {"positive": pos, "negative": neg, "total": pos + neg,
            "pct_positive": round(100 * pos / (pos + neg), 1) if pos + neg else None}


def monthly_history(appid: int, language: str = "english") -> list[dict]:
    """Month-by-month positive/negative counts over the game's whole life."""
    d = _get(f"appreviewhistogram/{appid}", {"l": language, "review_score_preference": 0})
    rows = []
    for r in d["results"].get("rollups", []):
        rows.append({
            "month": datetime.fromtimestamp(r["date"], tz=timezone.utc).strftime("%Y-%m"),
            "positive": r["recommendations_up"],
            "negative": r["recommendations_down"],
        })
    return rows


def iter_reviews(appid: int, start: datetime, end: datetime, max_reviews: int = 2000,
                 language: str = "english"):
    """Yield review texts posted between start and end (newest first)."""
    cursor, count, seen = "*", 0, set()
    while True:
        d = _get(f"appreviews/{appid}", {
            "json": 1, "filter": "recent", "language": language, "purchase_type": "all",
            "num_per_page": 100, "cursor": cursor, **_range_params(start, end),
        })
        reviews = d.get("reviews", [])
        if not reviews:
            return
        for rv in reviews:
            if rv["recommendationid"] in seen:      # Steam occasionally repeats one
                continue
            seen.add(rv["recommendationid"])
            yield {
                "review_id": rv["recommendationid"],
                "created_at": datetime.fromtimestamp(rv["timestamp_created"], tz=timezone.utc),
                "voted_up": rv["voted_up"],                       # True = recommended
                "helpful_votes": rv.get("votes_up", 0),
                "playtime_hours": round(rv.get("author", {}).get("playtime_at_review", 0) / 60, 1),
                "text": rv.get("review", ""),
            }
            count += 1
            if count >= max_reviews:
                return
        new_cursor = d.get("cursor")
        if not new_cursor or new_cursor == cursor:  # no more pages
            return
        cursor = new_cursor
        time.sleep(1)                               # be polite to Steam