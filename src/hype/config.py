"""Load project settings: the games list (config/games.yaml) and API keys (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]          # the hype-or-hit folder
CONFIG_PATH = ROOT / "config" / "games.yaml"
RAW_DIR = ROOT / "data" / "raw"


@dataclass
class Game:
    """One game from games.yaml."""
    slug: str
    name: str
    release_date: date
    steam_appid: int | None
    group: str
    search_query: str
    trailers: list[str] = field(default_factory=list)
    notes: str = ""
    match: list[str] = field(default_factory=list)  
    @property
    def release_dt(self) -> datetime:
        """Release date as a UTC timestamp at midnight (start of launch day)."""
        d = self.release_date
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def load_games(path: Path = CONFIG_PATH) -> list[Game]:
    """Read games.yaml and return a list of Game objects."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    games = []
    for g in raw["games"]:
        rd = g["release_date"]
        if isinstance(rd, str):
            rd = date.fromisoformat(rd)
        games.append(Game(
            slug=g["slug"],
            name=g["name"],
            release_date=rd,
            steam_appid=g.get("steam_appid"),
            group=g["group"],
            search_query=g.get("search_query", f"{g['name']} official trailer"),
            trailers=list(g.get("trailers") or []),
            notes=g.get("notes", ""),
            match=list(g.get("match") or [g["name"]]),
        ))
    return games


def select_games(games: list[Game], slugs: list[str] | None) -> list[Game]:
    """Keep only the games asked for on the command line (or all of them)."""
    if not slugs:
        return games
    unknown = set(slugs) - {g.slug for g in games}
    if unknown:
        raise SystemExit(f"Unknown game slug(s): {', '.join(sorted(unknown))}")
    return [g for g in games if g.slug in set(slugs)]


def youtube_api_key() -> str:
    """Read YOUTUBE_API_KEY from the .env file."""
    load_dotenv(ROOT / ".env")
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise SystemExit("YOUTUBE_API_KEY is missing. Create a .env file with YOUTUBE_API_KEY=your_key")
    return key