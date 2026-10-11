"""The Research use cases bundled for driving adapters (HTTP API, CLI)."""

from dataclasses import dataclass

from filings_qa.research.application.ask_question import AskQuestion
from filings_qa.research.application.list_filings import ListFilings
from filings_qa.research.application.ports import DocumentLocator
from filings_qa.research.application.search_passages import SearchPassages


@dataclass(frozen=True, slots=True)
class ResearchServices:
    ask: AskQuestion
    search: SearchPassages
    list_filings: ListFilings
    documents: DocumentLocator
    snapshot_version: str
    answer_generator: str
