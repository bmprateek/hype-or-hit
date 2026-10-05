"""Small helper for the YouTube Data API v3 (search, video stats, comments)."""
from __future__ import annotations

import time
from datetime import datetime

import requests

API = "https://www.googleapis.com/youtube/v3"


class QuotaExceeded(Exception):
    """Raised when today's free YouTube API quota (10,000 units) is used up."""


class CommentsDisabled(Exception):
    """Raised when a video has comments turned off."""


def _get(endpoint: str, params: dict, key: str) -> dict:
    """Call one YouTube API endpoint. Retries on server hiccups, explains common errors."""
    params = {**params, "key": key}
    for attempt in range(3):
        r = requests.get(f"{API}/{endpoint}", params=params, timeout=30)
        if r.status_code == 200:
            return r.json()

        # YouTube explains what went wrong in error -> errors -> reason
        reason = ""
        try:
            reason = r.json()["error"]["errors"][0]["reason"]
        except Exception:
            pass

        if reason in ("quotaExceeded", "dailyLimitExceeded"):
            raise QuotaExceeded("Daily YouTube quota used up. It resets at midnight Pacific time.")
        if reason == "commentsDisabled":
            raise CommentsDisabled(params.get("videoId", ""))
        if r.status_code >= 500:          # YouTube server problem: wait, then retry
            time.sleep(2 ** attempt)
            continue
        raise RuntimeError(f"YouTube API error {r.status_code} ({reason}): {r.text[:300]}")
    raise RuntimeError("YouTube API kept failing after 3 retries.")


def to_rfc3339(dt: datetime) -> str:
    """YouTube wants dates like 2020-12-10T00:00:00Z."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def search_trailers(query: str, published_before: datetime, key: str,
                    must_contain: list[str], n: int = 5) -> list[dict]:
    """Most viewed videos matching `query`, uploaded before `published_before`,
    whose title contains at least one of `must_contain` (case-insensitive).

    Quota cost: 100 units for the search + 1 unit for the stats call.
    """
    found = _get("search", {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "viewCount",
        "publishedBefore": to_rfc3339(published_before),
        "maxResults": 25,                       # same cost as 5, gives room to filter
    }, key)
    ids = [item["id"]["videoId"] for item in found.get("items", [])]
    if not ids:
        return []

    stats = _get("videos", {"part": "snippet,statistics", "id": ",".join(ids)}, key)
    words = [w.lower() for w in must_contain]
    results = []
    for v in stats.get("items", []):
        title = v["snippet"]["title"]
        if not any(w in title.lower() for w in words):
            continue                            # unrelated video, skip it
        s = v.get("statistics", {})
        results.append({
            "video_id": v["id"],
            "title": title,
            "channel": v["snippet"]["channelTitle"],
            "uploaded": v["snippet"]["publishedAt"][:10],
            "views": int(s.get("viewCount", 0)),
            "comments": int(s["commentCount"]) if "commentCount" in s else None,
        })
    return sorted(results, key=lambda x: x["views"], reverse=True)[:n]

def iter_comments(video_id: str, key: str, max_comments: int | None = None):
    """Yield top-level comments on a video, newest first.

    Quota cost: 1 unit per 100 comments.
    Usernames are deliberately NOT collected (privacy).
    """
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": 100,           # the most YouTube allows per page
        "order": "time",             # newest first
        "textFormat": "plainText",   # no HTML tags in the text
    }
    count = 0
    while True:
        data = _get("commentThreads", params, key)
        for item in data.get("items", []):
            top = item["snippet"]["topLevelComment"]
            s = top["snippet"]
            yield {
                "comment_id": top["id"],
                "published_at": s["publishedAt"],
                "updated_at": s.get("updatedAt", s["publishedAt"]),   # last edit time
                "like_count": s.get("likeCount", 0),
                "reply_count": item["snippet"].get("totalReplyCount", 0),
                "text": s.get("textDisplay", ""),
            }
            count += 1
            if max_comments and count >= max_comments:
                return
        token = data.get("nextPageToken")
        if not token:                # no more pages: we have everything
            return
        params["pageToken"] = token