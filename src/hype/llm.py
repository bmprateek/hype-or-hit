"""Label comments with Claude (blind: the model never sees game names or outcomes)."""
import json
import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

from hype.config import ROOT

LABELS = ["sentiment", "excitement", "skepticism", "sarcasm", "comparison", "live_service"]

SYSTEM_PROMPT = """You are annotating YouTube comments posted under video game trailers BEFORE the game was released.
For EACH comment, return these labels:

- sentiment: the commenter's overall attitude toward the game: "positive", "negative", "neutral" or "mixed".
  If the comment is sarcastic, judge the REAL meaning, not the literal words.
- excitement: true if the commenter expresses eagerness or anticipation to play or buy it.
- skepticism: true if the commenter doubts the game's quality, honesty of the trailer, value or business model.
  Impatience about release dates alone ("hurry up", "delayed again") is NOT skepticism.
  "No doubt this is GOTY" is NOT skepticism.
- sarcasm: true if the comment is sarcastic or ironic.
- comparison: true if the comment compares the game to another game, franchise or studio.
- live_service: true if the comment mentions or worries about online-only, battle passes, microtransactions,
  live service or monetization.

Return ONLY a JSON array, one object per comment, in the same order, like:
[{"id": 0, "sentiment": "positive", "excitement": true, "skepticism": false, "sarcasm": false,
  "comparison": false, "live_service": false}]"""


def get_client() -> tuple[Anthropic, str]:
    load_dotenv(ROOT / ".env")
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is missing. Add ANTHROPIC_API_KEY=your_key to .env")
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5").strip()
    return Anthropic(api_key=key, max_retries=5), model


def parse_labels(text: str, n: int) -> list[dict]:
    """Pull the JSON array out of the model's reply and check it has n items."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON array in reply")
    items = json.loads(match.group(0))
    if len(items) != n:
        raise ValueError(f"Expected {n} labels, got {len(items)}")
    out = []
    for item in items:
        row = {"sentiment": str(item.get("sentiment", "neutral")).lower()}
        for k in LABELS[1:]:
            row[k] = bool(item.get(k, False))
        out.append(row)
    return out


def label_batch(client: Anthropic, model: str, comments: list[str]) -> list[dict]:
    """Send one batch of comments, get one label dict per comment."""
    numbered = "\n".join(f"[{i}] {c[:800]}" for i, c in enumerate(comments))   # cap very long comments
    for attempt in range(3):
        resp = client.messages.create(
        model=model, max_tokens=4000, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Comments:\n{numbered}"}],
        )
        try:
            return parse_labels(resp.content[0].text, len(comments))
        except (ValueError, json.JSONDecodeError):
            if attempt == 2:
                raise
    return []