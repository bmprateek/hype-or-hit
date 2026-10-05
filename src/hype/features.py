"""Comment-level text features: sentiment (VADER) and hype/skepticism word lists."""
import re

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Word lists ("lexicons"). Each term matches at the START of a word, so
# "delay" also matches "delayed", "microtransaction" matches "microtransactions".
LEXICONS = {
    "excitement": [
        "can't wait", "cant wait", "day one", "day 1", "preordered", "pre-ordered",
        "pre ordered", "take my money", "hype", "goty", "game of the year",
        "masterpiece", "chills", "goosebumps", "insane", "incredible", "amazing",
        "so excited", "need this", "shut up and take",
    ],
    "skepticism": [
        "delay", "downgrade", "bullshot", "microtransaction", "battle pass",
        "season pass", "live service", "games as a service", "always online",
        "cash grab", "scam", "fake", "too good to be true", "i doubt", "doubtful", "skeptic",
        "not convinced", "worried", "concern", "red flag", "copium", "overhyped",
        "lower your expectations", "don't preorder", "dont preorder",
        "do not preorder", "don't pre-order", "dont pre-order", "no man's sky",
        "anthem", "we'll see", "well see", "scripted",
    ],
    "nostalgia": [
        "childhood", "grew up", "remember when", "back in the day", "nostalg",
        "the original", "old school", "classic", "arkham", "dishonored",
        "witcher", "dark souls", "harry potter", "the books",
    ],
    "gameplay": [
        "gameplay", "combat", "mechanic", "boss", "skill tree", "open world",
        "quest", "dialogue", "choices", "level design", "stealth", "parry",
        "co-op", "coop", "multiplayer", "rpg", "customiz", "loot",
    ],
    "visuals": [
        "graphics", "visual", "beautiful", "gorgeous", "stunning", "realistic",
        "ray tracing", "4k", "art style", "animation",
    ],
}

_PATTERNS = {
    name: re.compile(r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")", re.IGNORECASE)
    for name, terms in LEXICONS.items()
}
_vader = SentimentIntensityAnalyzer()


def add_comment_features(df: pd.DataFrame, text_col: str = "text_clean") -> pd.DataFrame:
    """Add sentiment and lexicon columns to every comment."""
    text = df[text_col].fillna("").astype(str)

    # VADER compound score: -1 (very negative) to +1 (very positive)
    df["sentiment"] = text.map(lambda s: _vader.polarity_scores(s)["compound"])
    df["is_positive"] = df["sentiment"] >= 0.05      # standard VADER cut-offs
    df["is_negative"] = df["sentiment"] <= -0.05

    for name, pattern in _PATTERNS.items():
        df[f"has_{name}"] = text.str.contains(pattern)
    return df