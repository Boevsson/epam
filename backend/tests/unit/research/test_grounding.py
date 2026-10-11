import pytest

from filings_qa.research.domain.answer import (
    AnswerSegment,
    Citation,
    DraftAnswer,
    Evidence,
    GroundingStatus,
)
from filings_qa.research.domain.grounding import GroundingPolicy
from filings_qa.research.domain.passage import Passage
from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import FilingId, FiscalYear, ItemCode, PageRange, PassageId, Ticker

SUPPLY = Passage(
    id=PassageId("AMD-10K-2022#0042"),
    filing_id=FilingId("AMD-10K-2022"),
    company="Advanced Micro Devices, Inc.",
    ticker=Ticker("AMD"),
    fiscal_year=FiscalYear(2022),
    item=ItemCode.RISK_FACTORS,
    pages=PageRange(17, 18),
    sentences=("We rely on third parties to manufacture our products.", "Supply may be constrained."),
)
EVIDENCE = Evidence((SUPPLY,))
policy = GroundingPolicy(min_coverage=0.6)


def draft(*segments: AnswerSegment, generator: str = "claude") -> DraftAnswer:
    return DraftAnswer(segments=segments, generator=generator)


def cite(quote: str, passage_id: str = "AMD-10K-2022#0042") -> Citation:
    return Citation(PassageId(passage_id), quote)


def test_a_fully_cited_answer_is_grounded() -> None:
    answer = policy.assess(
        draft(
            AnswerSegment("AMD relies on third-party manufacturers.", (cite("Supply may be constrained."),))
        ),
        EVIDENCE,
    )

    assert answer.status is GroundingStatus.GROUNDED
    assert answer.coverage == pytest.approx(1.0)


def test_an_answer_without_citations_reports_insufficient_evidence() -> None:
    answer = policy.assess(draft(AnswerSegment("The filings do not say anything about dividends.")), EVIDENCE)

    assert answer.status is GroundingStatus.INSUFFICIENT_EVIDENCE


def test_mostly_uncited_claims_make_the_answer_partially_grounded() -> None:
    answer = policy.assess(
        draft(
            AnswerSegment("AMD relies on outside manufacturers.", (cite("Supply may be constrained."),)),
            AnswerSegment("It also plans to build three new fabs in Arizona by 2025 and expand in Europe."),
        ),
        EVIDENCE,
    )

    assert answer.status is GroundingStatus.PARTIALLY_GROUNDED
    assert 0 < answer.coverage < 0.6


def test_connective_text_does_not_count_against_coverage() -> None:
    answer = policy.assess(
        draft(
            AnswerSegment("According to the filing, "),
            AnswerSegment("AMD relies on third-party manufacturing.", (cite("Supply may be constrained."),)),
        ),
        EVIDENCE,
    )

    assert answer.status is GroundingStatus.GROUNDED


def test_citations_to_passages_outside_the_evidence_are_dropped() -> None:
    answer = policy.assess(
        draft(AnswerSegment("A claim.", (cite("Supply may be constrained.", "PFE-10K-2021#0001"),))), EVIDENCE
    )

    assert answer.segments[0].citations == ()
    assert answer.status is GroundingStatus.INSUFFICIENT_EVIDENCE


def test_citations_whose_quote_is_not_in_the_passage_are_dropped() -> None:
    answer = policy.assess(draft(AnswerSegment("A claim.", (cite("Revenue tripled."),))), EVIDENCE)

    assert answer.segments[0].citations == ()


def test_the_extractive_fallback_is_reported_as_such() -> None:
    answer = policy.assess(
        draft(
            AnswerSegment("Supply may be constrained.", (cite("Supply may be constrained."),)),
            generator="extractive",
        ),
        EVIDENCE,
    )

    assert answer.status is GroundingStatus.EXTRACTIVE_FALLBACK


def test_evidence_must_not_be_empty() -> None:
    with pytest.raises(InvalidValueError):
        Evidence(())


def test_passage_label_is_a_human_readable_source_reference() -> None:
    assert SUPPLY.label == "Advanced Micro Devices, Inc. · 10-K FY2022 · Item 1A Risk Factors · pp. 17-18"
