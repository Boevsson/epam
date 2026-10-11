"""Value objects shared by the Ingestion and Research contexts (the shared kernel)."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import NewType, Self

from filings_qa.shared_kernel.errors import InvalidValueError

FilingId = NewType("FilingId", str)
"""Stable identity of a filing, e.g. ``AMD-10K-2022``."""

PassageId = NewType("PassageId", str)
"""Stable identity of a passage within a filing, e.g. ``AMD-10K-2022#0142``."""

EDGAR_FIRST_YEAR = 1993  # electronic filing on EDGAR began in 1993
LAST_SUPPORTED_YEAR = 2100

_TICKER = re.compile(r"[A-Z]{1,5}(?:[.-][A-Z]{1,2})?")
_ITEM_LABEL = re.compile(r"(?:item\s+)?(\d{1,2}[a-z]?)[.:]?", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Ticker:
    """An exchange ticker symbol in canonical upper-case form (``AMD``, ``BRK.B``)."""

    symbol: str

    def __post_init__(self) -> None:
        if not _TICKER.fullmatch(self.symbol):
            raise InvalidValueError(f"not a ticker symbol: {self.symbol!r}")

    @classmethod
    def parse(cls, raw: str) -> Self:
        return cls(raw.strip().upper())

    def __str__(self) -> str:
        return self.symbol


@dataclass(frozen=True, slots=True, order=True)
class FiscalYear:
    """The fiscal year as the company designates it.

    Deliberately not derived from the period-end date: 52/53-week fiscal years can end in early January.
    """

    value: int

    def __post_init__(self) -> None:
        if not EDGAR_FIRST_YEAR <= self.value <= LAST_SUPPORTED_YEAR:
            raise InvalidValueError(f"fiscal year out of range: {self.value}")

    def __str__(self) -> str:
        return f"FY{self.value}"


@dataclass(frozen=True, slots=True)
class PageRange:
    """A 1-based, inclusive range of pages in a source PDF: the unit analysts verify against."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 1 or self.end < self.start:
            raise InvalidValueError(f"invalid page range: {self.start}-{self.end}")

    @classmethod
    def single(cls, page: int) -> Self:
        return cls(page, page)

    def overlaps(self, other: Self) -> bool:
        return self.start <= other.end and other.start <= self.end

    def __str__(self) -> str:
        return f"p. {self.start}" if self.start == self.end else f"pp. {self.start}-{self.end}"


class ItemCode(StrEnum):
    """The standard items (sections) of a Form 10-K.

    Detection works on the code, never the title: titles change over time (Item 6) and newer items
    (1C, 9C) are missing from older filings.
    """

    COVER = "COVER"  # front matter before Item 1: cover page, table of contents
    BUSINESS = "1"
    RISK_FACTORS = "1A"
    UNRESOLVED_STAFF_COMMENTS = "1B"
    CYBERSECURITY = "1C"
    PROPERTIES = "2"
    LEGAL_PROCEEDINGS = "3"
    MINE_SAFETY_DISCLOSURES = "4"
    MARKET_FOR_EQUITY = "5"
    SELECTED_FINANCIAL_DATA = "6"
    MD_AND_A = "7"
    MARKET_RISK = "7A"
    FINANCIAL_STATEMENTS = "8"
    CHANGES_IN_ACCOUNTANTS = "9"
    CONTROLS_AND_PROCEDURES = "9A"
    OTHER_INFORMATION = "9B"
    FOREIGN_JURISDICTION_INSPECTIONS = "9C"
    DIRECTORS_AND_GOVERNANCE = "10"
    EXECUTIVE_COMPENSATION = "11"
    SECURITY_OWNERSHIP = "12"
    RELATIONSHIPS_AND_INDEPENDENCE = "13"
    ACCOUNTANT_FEES = "14"
    EXHIBITS = "15"
    FORM_10K_SUMMARY = "16"
    UNKNOWN = "?"

    @property
    def heading(self) -> str:
        return _HEADINGS[self]

    @classmethod
    def parse(cls, raw: str) -> Self:
        """Parse labels such as ``1A``, ``Item 7A`` or ``ITEM 7.``."""
        label = _ITEM_LABEL.fullmatch(raw.strip())
        if label is None:
            raise InvalidValueError(f"not a 10-K item: {raw!r}")
        try:
            return cls(label.group(1).upper())
        except ValueError:
            raise InvalidValueError(f"not a 10-K item: {raw!r}") from None


_HEADINGS: Mapping[ItemCode, str] = MappingProxyType(
    {
        ItemCode.COVER: "Cover Page and Front Matter",
        ItemCode.BUSINESS: "Business",
        ItemCode.RISK_FACTORS: "Risk Factors",
        ItemCode.UNRESOLVED_STAFF_COMMENTS: "Unresolved Staff Comments",
        ItemCode.CYBERSECURITY: "Cybersecurity",
        ItemCode.PROPERTIES: "Properties",
        ItemCode.LEGAL_PROCEEDINGS: "Legal Proceedings",
        ItemCode.MINE_SAFETY_DISCLOSURES: "Mine Safety Disclosures",
        ItemCode.MARKET_FOR_EQUITY: (
            "Market for Registrant's Common Equity, Related Stockholder Matters "
            "and Issuer Purchases of Equity Securities"
        ),
        ItemCode.SELECTED_FINANCIAL_DATA: "[Reserved] (formerly Selected Financial Data)",
        ItemCode.MD_AND_A: (
            "Management's Discussion and Analysis of Financial Condition and Results of Operations"
        ),
        ItemCode.MARKET_RISK: "Quantitative and Qualitative Disclosures About Market Risk",
        ItemCode.FINANCIAL_STATEMENTS: "Financial Statements and Supplementary Data",
        ItemCode.CHANGES_IN_ACCOUNTANTS: (
            "Changes in and Disagreements with Accountants on Accounting and Financial Disclosure"
        ),
        ItemCode.CONTROLS_AND_PROCEDURES: "Controls and Procedures",
        ItemCode.OTHER_INFORMATION: "Other Information",
        ItemCode.FOREIGN_JURISDICTION_INSPECTIONS: (
            "Disclosure Regarding Foreign Jurisdictions that Prevent Inspections"
        ),
        ItemCode.DIRECTORS_AND_GOVERNANCE: "Directors, Executive Officers and Corporate Governance",
        ItemCode.EXECUTIVE_COMPENSATION: "Executive Compensation",
        ItemCode.SECURITY_OWNERSHIP: (
            "Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters"
        ),
        ItemCode.RELATIONSHIPS_AND_INDEPENDENCE: (
            "Certain Relationships and Related Transactions, and Director Independence"
        ),
        ItemCode.ACCOUNTANT_FEES: "Principal Accountant Fees and Services",
        ItemCode.EXHIBITS: "Exhibits and Financial Statement Schedules",
        ItemCode.FORM_10K_SUMMARY: "Form 10-K Summary",
        ItemCode.UNKNOWN: "Unknown section",
    }
)
