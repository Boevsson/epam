"""ASGI entry point: ``uvicorn filings_qa.entrypoints.http.main:app``."""

from filings_qa import bootstrap
from filings_qa.entrypoints.http.app import create_app
from filings_qa.infrastructure.settings import Settings

settings = Settings()
app = create_app(lambda: bootstrap.build_research_services(settings), cors_origins=settings.cors_origins)
