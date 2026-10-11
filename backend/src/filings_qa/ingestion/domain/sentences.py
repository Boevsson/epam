"""Rule-based sentence splitting tuned for SEC filings.

Sentences are the citable unit of an answer, so a wrong split shows up as a truncated quote.
"""

import re

_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\s+(?=•)")
_ABBREVIATIONS = frozenset(
    {
        "approx", "co", "corp", "dr", "e.g", "etc", "fig", "i.e", "inc", "jr", "llc", "ltd", "mr", "ms",
        "no", "nos", "plc", "sr", "st", "u.k", "u.s", "vs",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    }
)  # fmt: skip


def split_sentences(text: str) -> list[str]:
    """Split text into sentences; bullets ("•") start new sentences."""
    normalized = " ".join(text.split())
    if not normalized:
        return []
    sentences: list[str] = []
    for piece in _BOUNDARY.split(normalized):
        if sentences and _continues(sentences[-1], piece):
            sentences[-1] = f"{sentences[-1]} {piece}"
        else:
            sentences.append(piece)
    return sentences


def _continues(previous: str, piece: str) -> bool:
    """True when the boundary before `piece` was a false one (abbreviation, or no capital to start)."""
    if piece.startswith("•"):
        return False
    last_word = previous.rsplit(" ", 1)[-1].lower().rstrip(".")
    return last_word in _ABBREVIATIONS or piece[:1].islower()
