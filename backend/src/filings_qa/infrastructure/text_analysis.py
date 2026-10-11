"""Finance-aware tokenization for BM25, shared by the index builder and the keyword retriever.

Both sides must tokenize identically, which is why this lives in shared infrastructure.
"""

import re
import unicodedata
from functools import lru_cache

import Stemmer

_THOUSANDS_SEPARATOR = re.compile(r"(?<=\d),(?=\d{3}\b)")
_TOKEN = re.compile(r"[a-z0-9]+(?:[-&.'][a-z0-9]+)*")
_HAS_DIGIT = re.compile(r"\d")
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for", "from", "has", "have", "in",
        "into", "is", "it", "its", "of", "on", "or", "our", "such", "that", "the", "their", "there", "these",
        "they", "this", "to", "was", "we", "were", "which", "will", "with",
    }
)  # fmt: skip


@lru_cache(maxsize=1)
def _stemmer() -> Stemmer.Stemmer:
    return Stemmer.Stemmer("english")


def tokenize(text: str) -> list[str]:
    """Lowercase, normalize and stem words; keep filing codes ("10-k", "1a", "covid-19", "s&p") intact."""
    normalized = _THOUSANDS_SEPARATOR.sub("", unicodedata.normalize("NFKC", text).lower())
    tokens: list[str] = []
    for raw in _TOKEN.findall(normalized):
        token = raw.removesuffix("'s").replace("'", "")
        parts = token.split("-") if "-" in token and not _HAS_DIGIT.search(token) else [token]
        tokens.extend(part for part in parts if part and part not in _STOPWORDS)
    return [token if not token.isalpha() else _stemmer().stemWord(token) for token in tokens]
