"""Text helpers shared by the cleaning and analysis steps."""
import re

URL_RE = re.compile(r"https?://\S+|www\.\S+")
SPACE_RE = re.compile(r"\s+")

# Very common English words. Real English sentences of 4+ words almost always contain one.
COMMON_EN = {
    "the", "a", "an", "is", "are", "was", "be", "this", "that", "it", "i", "you",
    "and", "or", "to", "of", "in", "on", "for", "with", "my", "me", "so", "not",
    "game", "looks", "like", "just", "will", "can", "what", "they", "we", "if",
}


def clean_text(s) -> str:
    """Remove links and collapse whitespace. Keeps emojis, punctuation, timestamps."""
    if not isinstance(s, str):
        return ""
    s = URL_RE.sub(" ", s)
    return SPACE_RE.sub(" ", s).strip()


def is_english(s: str) -> bool:
    """Fast heuristic language check.

    1. At least 80% of letters must be Latin (a-z). Drops Chinese, Russian, Arabic, etc.
    2. Comments of 4+ words must contain at least one common English word.
       Drops Spanish, Portuguese, etc. Short comments ("Looks amazing") pass on rule 1 alone.
    """
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    if sum(c.isascii() for c in letters) / len(letters) < 0.8:
        return False
    words = re.findall(r"[a-z']+", s.lower())
    if len(words) >= 4 and not COMMON_EN.intersection(words):
        return False
    return True