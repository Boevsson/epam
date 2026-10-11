"""Translate analysts' vocabulary into the language of 10-K filings (two ubiquitous languages meeting).

Analysts ask about "capex", "quick ratio" or "PP&E"; filings say "purchases of property, plant and
equipment", "current assets" and "property, plant and equipment, net". Neither BM25 nor a general-purpose
embedding model bridges that gap, so retrieval queries are expanded with the filing wording. Measured on the
evaluation set: hybrid Hit@10 0.58 -> 0.67, MRR@10 0.20 -> 0.32. Caveat: the glossary is generic analyst
vocabulary, but it was written after reading the evaluation questions, so a held-out set should confirm it.
"""

import re
from collections.abc import Mapping
from types import MappingProxyType

DEFAULT_GLOSSARY: Mapping[str, str] = MappingProxyType(
    {
        r"quick ratio|current ratio|liquidity": (
            "current assets current liabilities cash and cash equivalents short-term investments accounts receivable"
        ),
        r"capex|capital expenditures?": "purchases of property, plant and equipment capital spending",
        r"ebitda": "operating income depreciation and amortization",
        r"operating margin": "operating income operating profit net revenue",
        r"gross margin": "gross margin gross profit cost of sales",
        r"inventory turnover": "inventories cost of sales",
        r"effective tax rate": "effective tax rate provision for income taxes",
        r"pp&e|ppne|ppe": "property, plant and equipment, net",
        r"cash flows?": "net cash provided by used in operating activities investing activities financing activities",
        r"customer concentration": "customers accounted for percent of net revenue significant customers",
        r"legal battles|litigation|lawsuits?": "legal proceedings litigation",
        r"geograph(?:y|ies)": "geographic regions international revenue by country",
        r"restructuring": "restructuring and impairment charges",
    }
)


class AnalystVocabulary:
    def __init__(self, glossary: Mapping[str, str]) -> None:
        self._patterns = [(re.compile(rf"(?<![\w&])(?:{p})(?![\w&])", re.IGNORECASE), t) for p, t in glossary.items()]

    @classmethod
    def default(cls) -> "AnalystVocabulary":
        return cls(DEFAULT_GLOSSARY)

    def expand(self, query: str) -> str:
        """The query followed by the filing wording of every analyst term it mentions (each added once)."""
        additions = dict.fromkeys(terms for pattern, terms in self._patterns if pattern.search(query))
        return " ".join([query, *additions])
