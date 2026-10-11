import pytest
from hypothesis import given
from hypothesis import strategies as st

from filings_qa.ingestion.domain.chunking import Chunker, ChunkingPolicy
from filings_qa.ingestion.domain.document import Line, Section
from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import ItemCode, PageRange


class WordCounter:
    """Counts whitespace-separated words: a deterministic stand-in for the embedder's tokenizer."""

    def count(self, text: str) -> int:
        return len(text.split())


def section(*lines: tuple[int, str], item: ItemCode = ItemCode.RISK_FACTORS) -> Section:
    return Section(item, tuple(Line(page, text) for page, text in lines))


def sentence(words: int, tag: str) -> str:
    """A sentence of `words` words, capitalized like a real one so the splitter sees a boundary."""
    word = tag.upper()
    return " ".join([word] * (words - 1) + [f"{word}."])


def chunker(max_tokens: int, overlap_tokens: int = 0) -> Chunker:
    return Chunker(WordCounter(), ChunkingPolicy(max_tokens=max_tokens, overlap_tokens=overlap_tokens))


def test_a_short_section_becomes_one_chunk_with_its_item_and_pages() -> None:
    chunks = chunker(50).chunk(section((3, "Item 1A. Risk Factors"), (3, "Supply may be"), (4, "constrained.")))

    assert len(chunks) == 1
    assert chunks[0].item is ItemCode.RISK_FACTORS
    assert chunks[0].pages == PageRange(3, 4)
    assert chunks[0].text == "Item 1A. Risk Factors Supply may be constrained."


def test_sentences_are_packed_until_the_token_budget_is_reached() -> None:
    lines = [(1, sentence(4, "a")), (1, sentence(4, "b")), (2, sentence(4, "c"))]

    chunks = chunker(8).chunk(section(*lines))

    assert [chunk.text for chunk in chunks] == [f"{sentence(4, 'a')} {sentence(4, 'b')}", sentence(4, "c")]
    assert [chunk.pages for chunk in chunks] == [PageRange.single(1), PageRange.single(2)]


def test_consecutive_chunks_share_trailing_sentences_within_the_overlap_budget() -> None:
    lines = [(1, sentence(4, tag)) for tag in "abcd"]

    chunks = chunker(8, overlap_tokens=4).chunk(section(*lines))

    assert [chunk.sentences for chunk in chunks] == [
        (sentence(4, "a"), sentence(4, "b")),
        (sentence(4, "b"), sentence(4, "c")),
        (sentence(4, "c"), sentence(4, "d")),
    ]


def test_a_sentence_longer_than_the_budget_is_split_into_word_windows() -> None:
    table_like_run = " ".join(f"cell{n}" for n in range(10))

    chunks = chunker(4).chunk(section((7, table_like_run)))

    assert [chunk.text for chunk in chunks] == [
        "cell0 cell1 cell2 cell3",
        "cell4 cell5 cell6 cell7",
        "cell8 cell9",
    ]
    assert all(chunk.pages == PageRange.single(7) for chunk in chunks)


def test_policy_rejects_an_overlap_that_leaves_no_room_for_new_text() -> None:
    with pytest.raises(InvalidValueError):
        ChunkingPolicy(max_tokens=10, overlap_tokens=10)


words = st.text(alphabet="abcdefgh", min_size=1, max_size=6)
sentences = st.lists(words, min_size=1, max_size=12).map(lambda ws: " ".join(ws) + ".")
section_lines = st.lists(st.tuples(st.integers(1, 3), sentences), min_size=1, max_size=15).map(
    lambda rows: sorted(rows, key=lambda row: row[0])
)


@given(section_lines, st.integers(min_value=3, max_value=20), st.integers(min_value=0, max_value=2))
def test_no_chunk_exceeds_the_budget_and_every_word_is_kept_in_order(
    rows: list[tuple[int, str]], max_tokens: int, overlap_tokens: int
) -> None:
    source = section(*rows)

    chunks = chunker(max_tokens, overlap_tokens).chunk(source)

    assert all(len(chunk.text.split()) <= max_tokens for chunk in chunks)
    assert all(source.pages.start <= c.pages.start <= c.pages.end <= source.pages.end for c in chunks)
    kept = [word for chunk in chunker(max_tokens, 0).chunk(source) for word in chunk.text.split()]
    assert kept == " ".join(text for _, text in rows).split()
